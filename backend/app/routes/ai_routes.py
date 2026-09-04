# app/routes/ai_routes.py

import json

from flask import Blueprint, Response, jsonify, request, stream_with_context

from app.auth.decorators import get_current_user, jwt_required
from app.errors import ValidationAPIError
from app.schemas import (
    ai_conversation_detail_schema,
    ai_conversation_schema,
    ai_conversations_schema,
    ai_message_schema,
)
from app.services import ai_service
from app.services.ai_providers import AIProviderError
from app.services.ai_service import MAX_MESSAGE_LENGTH

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

ALLOWED_ROLES = {"user", "assistant"}
MAX_MESSAGES = 20


@ai_bp.post("/assistant")
@jwt_required
def ask_assistant():
    """
    Auth required -- this proxies an AI provider (local or hosted; see
    app/services/ai_providers.py) that costs real compute/money to run,
    so it shouldn't be open to anonymous callers.

    Body: {"messages": [{"role": "user"|"assistant", "content": "..."}]}
    The full conversation so far; the backend is stateless and doesn't
    persist chat history.
    ---
    tags:
      - AI
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [messages]
          properties:
            messages:
              type: array
              maxItems: 20
              items:
                type: object
                required: [role, content]
                properties:
                  role:
                    type: string
                    enum: [user, assistant]
                  content:
                    type: string
    responses:
      200:
        description: The assistant's reply.
        schema:
          type: object
          properties:
            reply:
              type: string
      422:
        description: Malformed or empty messages, or the last message is not from the user.
        schema:
          $ref: '#/definitions/Error'
      503:
        description: The configured AI provider is unreachable or misconfigured.
        schema:
          $ref: '#/definitions/Error'
    """
    payload = request.get_json(silent=True) or {}
    messages = payload.get("messages")

    if not isinstance(messages, list) or not messages:
        raise ValidationAPIError("messages must be a non-empty list.")
    if len(messages) > MAX_MESSAGES:
        raise ValidationAPIError(f"messages cannot exceed {MAX_MESSAGES} entries.")

    for entry in messages:
        if not isinstance(entry, dict):
            raise ValidationAPIError("Each message must be an object with role and content.")
        role = entry.get("role")
        content = entry.get("content")
        if role not in ALLOWED_ROLES:
            raise ValidationAPIError("Each message's role must be 'user' or 'assistant'.")
        if not isinstance(content, str) or not content.strip():
            raise ValidationAPIError("Each message must have non-empty text content.")
        if len(content) > MAX_MESSAGE_LENGTH:
            raise ValidationAPIError(f"Message content cannot exceed {MAX_MESSAGE_LENGTH} characters.")

    if messages[-1]["role"] != "user":
        raise ValidationAPIError("The last message must be from the user.")

    reply = ai_service.ask_assistant(messages, language=get_current_user().language)
    return jsonify({"reply": reply}), 200


# ---------------------------------------------------------------------------
# Persistent conversations. /assistant above stays exactly as it was (some
# other part of the app, or an external client, may still depend on its
# stateless contract) -- these are additive, not a replacement.
# ---------------------------------------------------------------------------


@ai_bp.post("/conversations")
@jwt_required
def create_conversation():
    """
    Start a new persisted AI Farming Assistant conversation.
    ---
    tags:
      - AI
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            title:
              type: string
              x-nullable: true
    responses:
      201:
        description: Conversation created.
        schema:
          $ref: '#/definitions/AIConversation'
      422:
        description: title must be a string.
        schema:
          $ref: '#/definitions/Error'
    """
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    if title is not None and not isinstance(title, str):
        raise ValidationAPIError("title must be a string.")

    conversation = ai_service.create_conversation(get_current_user(), title=title.strip() if title else None)
    return jsonify(ai_conversation_schema.dump(conversation)), 201


@ai_bp.get("/conversations")
@jwt_required
def list_conversations():
    """
    List the current user's AI Farming Assistant conversations.
    ---
    tags:
      - AI
    security:
      - BearerAuth: []
    responses:
      200:
        description: Conversation summaries (without messages).
        schema:
          type: array
          items:
            $ref: '#/definitions/AIConversation'
    """
    conversations = ai_service.list_conversations(get_current_user())
    return jsonify(ai_conversations_schema.dump(conversations)), 200


@ai_bp.get("/conversations/<int:conversation_id>")
@jwt_required
def get_conversation(conversation_id):
    """
    Get one AI Farming Assistant conversation, with its messages.
    ---
    tags:
      - AI
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: conversation_id
        type: integer
        required: true
    responses:
      200:
        description: The conversation and its messages.
        schema:
          $ref: '#/definitions/AIConversationDetail'
      403:
        description: Not this conversation's owner.
        schema:
          $ref: '#/definitions/Error'
      404:
        description: Conversation not found.
        schema:
          $ref: '#/definitions/Error'
    """
    conversation = ai_service.get_conversation_for_user(get_current_user(), conversation_id)
    return jsonify(ai_conversation_detail_schema.dump(conversation)), 200


@ai_bp.delete("/conversations/<int:conversation_id>")
@jwt_required
def delete_conversation(conversation_id):
    """
    Delete an AI Farming Assistant conversation, and its messages.
    ---
    tags:
      - AI
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: conversation_id
        type: integer
        required: true
    responses:
      204:
        description: Conversation deleted.
      403:
        description: Not this conversation's owner.
        schema:
          $ref: '#/definitions/Error'
      404:
        description: Conversation not found.
        schema:
          $ref: '#/definitions/Error'
    """
    ai_service.delete_conversation(get_current_user(), conversation_id)
    return "", 204


def _sse(event, data):
    """Formats one Server-Sent Event. `data` is JSON-encoded so multi-line
    or special-character content can never break the SSE line framing."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream_conversation_message(conversation_id, content):
    """
    Returns a text/event-stream Response emitting, in order:
      - a "user_message" event with the saved user message
      - zero or more "chunk" events, each a piece of the reply as it's
        generated
      - either a "done" event (success -- the full reply is already
        saved to the database by this point) or an "error" event (the
        HTTP response is already committed to status 200 by the time a
        mid-generation failure can happen, so the failure has to be
        signaled in-band rather than via an HTTP error status)
    """
    user_message, chunks = ai_service.stream_message(get_current_user(), conversation_id, content)

    def generate():
        yield _sse("user_message", ai_message_schema.dump(user_message))
        try:
            for chunk in chunks:
                yield _sse("chunk", chunk)
        except AIProviderError as err:
            yield _sse("error", err.public_message)
            return
        yield _sse("done", {})

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    # Render sits behind Cloudflare's edge proxy in production, which by
    # default buffers/compresses responses before forwarding them --
    # fine for normal JSON, but it defeats the entire point of an SSE
    # stream (observed in practice: the connection delivered only the
    # first event, then silently died, well before any AI-generated
    # chunk -- verified this was NOT a gunicorn/Flask issue by
    # reproducing true incremental delivery against gunicorn directly).
    # `no-transform` tells any compliant intermediary (Cloudflare
    # included) not to alter/buffer the body for compression;
    # `X-Accel-Buffering: no` is the equivalent instruction nginx-style
    # proxies look for specifically.
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@ai_bp.post("/conversations/<int:conversation_id>/messages")
@jwt_required
def send_conversation_message(conversation_id):
    """
    Body: {"content": "..."}. Persists the user's message, asks the AI
    for a reply using only the recent context window (not the whole
    conversation -- see ai_service._recent_context), and persists the
    reply. ?stream=true switches to a Server-Sent Events response (see
    _stream_conversation_message) that renders the reply incrementally
    instead of waiting for the whole thing.
    ---
    tags:
      - AI
    security:
      - BearerAuth: []
    parameters:
      - in: path
        name: conversation_id
        type: integer
        required: true
      - in: query
        name: stream
        type: boolean
        description: When "true", responds as text/event-stream instead of JSON.
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [content]
          properties:
            content:
              type: string
    responses:
      201:
        description: User message and assistant reply (non-streaming).
        schema:
          type: object
          properties:
            user_message:
              $ref: '#/definitions/AIMessage'
            assistant_message:
              $ref: '#/definitions/AIMessage'
      200:
        description: text/event-stream of user_message/chunk/done|error events (when stream=true).
      403:
        description: Not this conversation's owner.
        schema:
          $ref: '#/definitions/Error'
      404:
        description: Conversation not found.
        schema:
          $ref: '#/definitions/Error'
      422:
        description: content is required.
        schema:
          $ref: '#/definitions/Error'
    """
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if not content:
        raise ValidationAPIError("content is required.")

    if request.args.get("stream") == "true":
        return _stream_conversation_message(conversation_id, content)

    user_message, assistant_message = ai_service.send_message(get_current_user(), conversation_id, content)
    return (
        jsonify(
            {
                "user_message": ai_message_schema.dump(user_message),
                "assistant_message": ai_message_schema.dump(assistant_message),
            }
        ),
        201,
    )
