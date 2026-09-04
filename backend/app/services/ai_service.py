# app/services/ai_service.py

"""
AI Farming Assistant -- the entry point the rest of the app calls
(routes/ai_routes.py). Resolves whichever AIProvider is configured (see
app/services/ai_providers.py) and asks it for a completion, translating
any provider failure into the API's standard error envelope.

Why an assistant, specifically: this platform's whole premise is
connecting farmers with agricultural experts. Experts aren't always
online, and a lot of farmer questions ("is this normal flower drop?",
"what's this leaf spot?", "when should I top-dress maize?") are the kind
of first-pass triage an assistant can help with immediately, while still
steering anything serious back to a verified human expert on the
platform -- that's encoded directly in the system prompt below, not
bolted on as an afterthought.

Provider-independent by design: the request flow is always
Frontend -> POST /api/ai/assistant -> ai_service -> AIProvider -> the
actual model. The frontend only ever talks to this Flask endpoint; it
never sees which provider answered or any provider credentials.
"""

import queue
import threading
import time
from datetime import datetime

from flask import current_app

from app.errors import ApiError, ForbiddenError, NotFoundError, ValidationAPIError
from app.extensions import db
from app.models import AIConversation, AIMessage
from app.services.ai_providers import AIProviderError, get_provider

MAX_HISTORY_MESSAGES = 20
MAX_MESSAGE_LENGTH = 4000
CONVERSATION_TITLE_MAX_LENGTH = 60

# How often a stalled stream emits a heartbeat -- see HEARTBEAT below.
# Comfortably shorter than every idle-connection timeout we've actually
# observed cut a stream short in production (Render's deployment sits
# behind Cloudflare's edge proxy, which -- confirmed by reproducing true
# incremental delivery locally through gunicorn on the exact same code --
# was silently dropping the connection after only a couple of seconds of
# no bytes flowing, well before the AI provider's first token).
HEARTBEAT_INTERVAL_SECONDS = 2.5


class _Heartbeat:
    """Sentinel yielded by _iter_with_heartbeats when the wrapped
    iterator hasn't produced anything within HEARTBEAT_INTERVAL_SECONDS.
    Never real content -- routes translate this into an SSE comment line
    (`: keep-alive`), which the SSE spec defines clients must ignore, so
    it's invisible to the user but keeps bytes flowing on the wire."""


HEARTBEAT = _Heartbeat()


def _iter_with_heartbeats(source_iter, interval=HEARTBEAT_INTERVAL_SECONDS):
    """
    Wraps a plain (blocking) iterator -- here, an AIProvider's
    stream_complete() generator, which blocks on network I/O between
    chunks -- so the consumer also gets a HEARTBEAT sentinel at least
    every `interval` seconds while nothing new has arrived. Python gives
    no way to put a timeout on a plain iterator's `next()`, so this runs
    the actual source iteration on a background thread and relays items
    through a queue, which *does* support a timed get().
    """
    q = queue.Queue()
    DONE = object()

    def produce():
        try:
            for item in source_iter:
                q.put(("item", item))
        except Exception as exc:  # re-raised on the consumer side below
            q.put(("error", exc))
        finally:
            q.put(("done", DONE))

    threading.Thread(target=produce, daemon=True).start()

    while True:
        try:
            kind, value = q.get(timeout=interval)
        except queue.Empty:
            yield HEARTBEAT
            continue
        if kind == "item":
            yield value
        elif kind == "error":
            raise value
        else:
            return

SYSTEM_PROMPT = (
    "You are AgriConnect's AI Farming Assistant, helping smallholder "
    "farmers with crops, livestock, soil, pests, and farm management in "
    "plain language. For high-stakes or uncertain topics (disease "
    "outbreaks, chemical dosing, food safety, big financial decisions), "
    "say so plainly and recommend the farmer also consult a verified "
    "AgriConnect expert before acting. Keep answers short -- a few "
    "paragraphs or a tight list, never an essay."
)

# Kiswahili is a first-class language for this assistant, not a bolted-on
# translation pass -- AgriConnect's farmers are Kenyan, and Kiswahili
# agricultural vocabulary (mkulima, shamba, mazao, ...) has specific,
# correct terms that a literal/generic translation routinely gets wrong.
#
# Wording here is deliberately tight -- this whole block (plus
# SYSTEM_PROMPT above) is resent as the system prompt on every single
# request, so its token count is a fixed per-call tax. Measured via
# Gemini's countTokens endpoint: tightening wording alone (same glossary
# terms, same policy, no content removed) took the combined prompt from
# 363 to 276 tokens (-24%).
_LANGUAGE_NAMES = {"en": "English", "sw": "Kiswahili"}

_KISWAHILI_INSTRUCTIONS = (
    " Preferred language: {preferred}. Reply in whichever language the "
    "farmer's message is written in (English, Kiswahili, or a natural "
    "mix) even if it differs from that preference; use the preferred "
    "language only when the message itself is ambiguous (e.g. a bare "
    "crop name). Write Kiswahili the way a fluent Kenyan speaker "
    "actually talks, never a stiff literal translation, using correct "
    "terms: mkulima (farmer), shamba (farm), mazao (crops), udongo "
    "(soil), mbolea (fertilizer), dawa ya kuua wadudu (pesticide), "
    "mavuno (harvest), mifugo (livestock), umwagiliaji (irrigation), "
    "mdudu waharibifu (pest), ugonjwa (disease), mbegu (seed), hali ya "
    "hewa (weather), soko (market), mtaalamu wa kilimo (agricultural "
    "expert). Never translate proper names, usernames, or URLs."
)


def _build_system_prompt(language):
    """
    Appends a language-awareness clause to the base SYSTEM_PROMPT above.
    `language` is the caller's account preference ("en"/"sw", from
    User.language) -- it steers which language the assistant defaults to
    when a message's own language is ambiguous, but the model is always
    instructed to mirror whatever language the user actually wrote in.
    """
    preferred = _LANGUAGE_NAMES.get(language, _LANGUAGE_NAMES["en"])
    return SYSTEM_PROMPT + _KISWAHILI_INSTRUCTIONS.format(preferred=preferred)


class AIServiceUnavailableError(ApiError):
    """The AI assistant is not configured, or the upstream provider failed."""

    status_code = 503


# ---------------------------------------------------------------------------
# ask_assistant() cache -- deliberately narrow in what it's allowed to
# cache. Only a single, standalone user question with no prior history
# qualifies: at that point the reply depends on nothing but the question
# text and the language, both of which are part of the cache key -- never
# on who's asking, so a cached reply can never leak one user's context to
# another. The persisted-conversation paths (send_message/stream_message)
# are NOT cached: their context window makes every request meaningfully
# unique, and there is nothing generic left to safely reuse.
#
# Plain in-process dict, not something like Redis: this deployment runs
# WEB_CONCURRENCY=1 (see render.yaml), so there's only ever one process
# to keep consistent, and a lock is enough to make it safe if that ever
# changes to threaded/multi-worker.
# ---------------------------------------------------------------------------

ASK_ASSISTANT_CACHE_TTL_SECONDS = 6 * 60 * 60  # long enough to meaningfully cut repeated-common-question load; short enough that advice can't go stale for a whole season
ASK_ASSISTANT_CACHE_MAX_ENTRIES = 200

_ask_assistant_cache = {}
_ask_assistant_cache_lock = threading.Lock()


def _ask_assistant_cache_key(language, question):
    normalized = " ".join(question.strip().lower().split())
    return (language or "en", normalized)


def _ask_assistant_cache_get(key):
    with _ask_assistant_cache_lock:
        entry = _ask_assistant_cache.get(key)
        if entry is None:
            return None
        reply, cached_at = entry
        if time.monotonic() - cached_at > ASK_ASSISTANT_CACHE_TTL_SECONDS:
            del _ask_assistant_cache[key]
            return None
        return reply


def _ask_assistant_cache_set(key, reply):
    with _ask_assistant_cache_lock:
        if key not in _ask_assistant_cache and len(_ask_assistant_cache) >= ASK_ASSISTANT_CACHE_MAX_ENTRIES:
            oldest_key = min(_ask_assistant_cache, key=lambda k: _ask_assistant_cache[k][1])
            del _ask_assistant_cache[oldest_key]
        _ask_assistant_cache[key] = (reply, time.monotonic())


def clear_ask_assistant_cache():
    """Test-only hook -- the cache is module-level state that would
    otherwise leak between tests (and between unrelated requests in a
    long-running process only in the sense that it's *supposed* to)."""
    with _ask_assistant_cache_lock:
        _ask_assistant_cache.clear()


def ask_assistant(messages, language=None):
    """
    `messages` is a list of {"role": "user"|"assistant", "content": str},
    already validated by the route (non-empty, roles alternate loosely --
    the provider itself will reject a genuinely malformed sequence).
    `language` is the caller's User.language ("en"/"sw"), passed by the
    route -- see _build_system_prompt.

    Returns the assistant's reply text. Never lets a provider-specific
    exception (connection errors, HTTP errors, malformed JSON, ...)
    escape this function -- everything is normalized to
    AIServiceUnavailableError with a user-safe message, and the real
    detail is logged server-side for debugging.

    A standalone single-question request (no prior history) is served
    from -- and saved to -- the module-level cache above; see its
    comment for why that's safe. Anything with history bypasses the
    cache entirely, in both directions.
    """
    trimmed = messages[-MAX_HISTORY_MESSAGES:]

    cache_key = None
    if len(trimmed) == 1 and trimmed[0]["role"] == "user":
        cache_key = _ask_assistant_cache_key(language, trimmed[0]["content"])
        cached_reply = _ask_assistant_cache_get(cache_key)
        if cached_reply is not None:
            current_app.logger.info("ai_cache hit channel=web mode=oneshot")
            return cached_reply

    try:
        provider = get_provider(current_app.config)
        reply = provider.complete(trimmed, _build_system_prompt(language))
    except AIProviderError as err:
        current_app.logger.error("AI assistant provider error: %s", err.log_message)
        raise AIServiceUnavailableError(err.public_message)

    if cache_key is not None:
        _ask_assistant_cache_set(cache_key, reply)

    return reply


# ---------------------------------------------------------------------------
# Persistent conversations (app/models/ai_conversation.py, ai_message.py).
#
# Deliberately separate from the ask_assistant()/AIProvider machinery above
# only in that these functions add persistence around it -- the actual
# model call still goes through get_provider().complete()/.stream_complete(),
# so there is exactly one place ("SYSTEM_PROMPT" + the provider layer) that
# knows how to talk to the AI.
# ---------------------------------------------------------------------------


def create_conversation(user, title=None):
    conversation = AIConversation(user_id=user.id, title=title or None)
    db.session.add(conversation)
    db.session.commit()
    return conversation


def list_conversations(user):
    return (
        AIConversation.query.filter_by(user_id=user.id)
        .order_by(AIConversation.updated_at.desc())
        .all()
    )


def get_conversation_or_404(conversation_id):
    conversation = db.session.get(AIConversation, conversation_id)
    if conversation is None:
        raise NotFoundError(f"Conversation {conversation_id} not found.")
    return conversation


def get_conversation_for_user(user, conversation_id):
    """
    Combines the existence check and the ownership check -- the single
    entry point routes should call rather than composing
    get_conversation_or_404() + an ownership check themselves. Mirrors
    message_service.get_conversation_for_user's shape: 404 if the
    conversation doesn't exist at all, 403 if it exists but belongs to
    someone else -- so a caller can never see or touch another user's AI
    conversation.
    """
    conversation = get_conversation_or_404(conversation_id)
    if conversation.user_id != user.id:
        raise ForbiddenError("You do not have access to this conversation.")
    return conversation


def delete_conversation(user, conversation_id):
    conversation = get_conversation_for_user(user, conversation_id)
    db.session.delete(conversation)
    db.session.commit()


def _derive_title(content):
    stripped = content.strip()
    if len(stripped) <= CONVERSATION_TITLE_MAX_LENGTH:
        return stripped
    return stripped[: CONVERSATION_TITLE_MAX_LENGTH - 3].rstrip() + "..."


def _validate_content(content):
    if not isinstance(content, str) or not content.strip():
        raise ValidationAPIError("content is required.")
    if len(content) > MAX_MESSAGE_LENGTH:
        raise ValidationAPIError(f"Message content cannot exceed {MAX_MESSAGE_LENGTH} characters.")
    return content.strip()


def _recent_context(conversation_id):
    """
    The last MAX_HISTORY_MESSAGES messages (chronological order), not
    the whole conversation -- this is what keeps a long-running
    conversation from sending an ever-growing (slower, costlier) prompt
    to the AI provider on every turn. See module docstring for the
    provider-independent request flow this feeds into.
    """
    recent = (
        AIMessage.query.filter_by(conversation_id=conversation_id)
        .order_by(AIMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    recent.reverse()
    return recent


def _save_user_message(conversation, content):
    user_message = AIMessage(conversation_id=conversation.id, role="user", content=content)
    db.session.add(user_message)
    if conversation.title is None:
        conversation.title = _derive_title(content)
    conversation.updated_at = datetime.utcnow()
    db.session.commit()
    return user_message


def send_message(user, conversation_id, content):
    """
    Full non-streaming turn: authenticate/authorize (via
    get_conversation_for_user), save the user's message, ask the AI for
    a reply using only the recent context window, save the reply.

    If the AI call fails, the user's message is already committed --
    it's a complete, real record of what they sent -- but no assistant
    message is created, so there is never a half-written reply row.
    """
    conversation = get_conversation_for_user(user, conversation_id)
    content = _validate_content(content)
    user_message = _save_user_message(conversation, content)

    context = [{"role": m.role, "content": m.content} for m in _recent_context(conversation.id)]

    try:
        provider = get_provider(current_app.config)
        reply = provider.complete(context, _build_system_prompt(user.language))
    except AIProviderError as err:
        current_app.logger.error("AI assistant provider error: %s", err.log_message)
        raise AIServiceUnavailableError(err.public_message)

    assistant_message = AIMessage(conversation_id=conversation.id, role="assistant", content=reply)
    db.session.add(assistant_message)
    conversation.updated_at = datetime.utcnow()
    db.session.commit()

    return user_message, assistant_message


def stream_message(user, conversation_id, content):
    """
    Like send_message(), but returns (user_message, chunk_generator)
    instead of (user_message, assistant_message) -- for Server-Sent
    Events (see app/routes/ai_routes.py).

    Authorization, validation, and saving the user's message all happen
    eagerly, before this function returns, so a bad conversation id or
    invalid content raises a normal exception the route can turn into a
    normal JSON error response -- exactly like send_message(). Only
    failures *during generation* are the generator's problem, since by
    then the HTTP response has already started streaming and can't
    switch to a JSON error body/status code anymore; see the generator
    below for how those are surfaced instead.

    The generator yields plain text chunks as they arrive. Once
    exhausted, the full assistant reply has already been saved to the
    database (or, on failure, deliberately has not been -- see below).
    """
    request_received_at = time.monotonic()
    conversation = get_conversation_for_user(user, conversation_id)
    content = _validate_content(content)
    user_message = _save_user_message(conversation, content)

    context = [{"role": m.role, "content": m.content} for m in _recent_context(conversation.id)]
    # Captured now, while `user` is still attached to this request's DB
    # session -- generate_chunks() below runs lazily, during response
    # streaming, by which point Flask has already torn down this
    # session (SQLAlchemy scoped sessions are tied to app-context
    # teardown, which fires as soon as the view returns its Response,
    # not when the streamed body finishes sending). Touching `user` or
    # `conversation` as ORM objects inside the generator raises
    # DetachedInstanceError; plain values captured here are safe.
    user_language = user.language

    try:
        provider = get_provider(current_app.config)
    except AIProviderError as err:
        current_app.logger.error("AI assistant provider error: %s", err.log_message)
        raise AIServiceUnavailableError(err.public_message)

    def generate_chunks():
        """
        Yields real text chunks (never HEARTBEAT -- that sentinel is
        consumed here and never leaks past this function) as they arrive
        from the provider, via _iter_with_heartbeats so a slow-starting
        or sparsely-chunked reply still keeps the SSE connection visibly
        alive for any proxy in front of this app (see
        HEARTBEAT_INTERVAL_SECONDS). Heartbeats themselves are relayed
        up to the route as HEARTBEAT so it can emit an SSE comment line
        instead of a "chunk" event -- see ai_routes.py.
        """
        chunks = []
        ai_request_started_at = time.monotonic()
        first_token_at = None
        try:
            for item in _iter_with_heartbeats(provider.stream_complete(context, _build_system_prompt(user_language))):
                if item is HEARTBEAT:
                    yield HEARTBEAT
                    continue
                if first_token_at is None:
                    first_token_at = time.monotonic()
                chunks.append(item)
                yield item
        except AIProviderError as err:
            # However much (if anything) already reached the client, it
            # isn't a complete, trustworthy reply -- don't persist a
            # truncated assistant message. The route surfaces this
            # failure to the client via an in-band SSE error event
            # (the HTTP response itself is already committed to 200 by
            # this point, so raising here wouldn't reach the client as
            # a clean error response anyway).
            current_app.logger.error("AI assistant provider error (stream): %s", err.log_message)
            raise

        full_text = "".join(chunks).strip()
        # `conversation` (closed over from the outer scope) is a detached
        # instance by this point -- see the comment above `user_language`.
        # `db.session` here also isn't the same Session that loaded it
        # (stream_with_context re-enters the request context, which gets
        # a fresh app context and thus a fresh scoped session), so a
        # plain re-fetch by id is the reliable way to get a live,
        # attached row to update.
        live_conversation = db.session.get(AIConversation, conversation_id)
        assistant_message = AIMessage(conversation_id=conversation_id, role="assistant", content=full_text)
        db.session.add(assistant_message)
        if live_conversation is not None:
            live_conversation.updated_at = datetime.utcnow()
        db.session.commit()

        now = time.monotonic()
        current_app.logger.info(
            "ai_latency channel=web mode=stream "
            "context_ready=%.2fs first_token=%.2fs ai_completed=%.2fs total=%.2fs reply_chars=%d",
            ai_request_started_at - request_received_at,
            (first_token_at - ai_request_started_at) if first_token_at else -1,
            now - ai_request_started_at,
            now - request_received_at,
            len(full_text),
        )

    return user_message, generate_chunks()
