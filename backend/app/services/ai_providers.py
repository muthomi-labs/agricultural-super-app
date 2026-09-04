# app/services/ai_providers.py

"""
AI provider abstraction for the AI Farming Assistant.

Keeps the application from being architecturally locked to a single paid
AI vendor. `ai_service.py` (the module the rest of the app talks to)
resolves a concrete AIProvider from config and calls `.complete()` --
everything provider-specific (request shape, auth, response parsing) is
contained inside that provider's class, and the frontend never talks to
a provider directly (Frontend -> Flask /api/ai/assistant -> ai_service
-> AIProvider -> actual provider).

Providers:
  - OllamaProvider    (default): a locally-run, open-source model served
    by Ollama (https://ollama.com). No API key, no external network call
    -- this is what the app uses out of the box with nothing configured
    beyond `ollama serve` running locally.
  - AnthropicProvider (optional): Claude via the Anthropic Messages API,
    for teams that want a hosted model in staging/production. Requires
    ANTHROPIC_API_KEY.
  - GeminiProvider    (optional): Google Gemini via the Generative
    Language API, for a hosted model with a genuinely free tier (no
    billing setup required to get a key, unlike Anthropic). Requires
    GEMINI_API_KEY from https://aistudio.google.com.

Select the active provider with the AI_PROVIDER env var (see
app/config.py): "ollama" (default), "anthropic", or "gemini".
"""

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

# Sensible default per provider when AI_MODEL isn't set. Ollama's is a
# small, widely-available open model; Anthropic's is its current
# fast/general-purpose model. Gemini's is a "flash-lite" tier rather than
# plain "flash": verified live (2026-09-04) that flash-lite gets a much
# higher free-tier daily quota than plain flash (our account hit a 20
# req/day cap on gemini-3.6-flash), doesn't spend hidden "thinking"
# tokens on simple questions (gemini-3.6-flash spent ~404 invisible
# reasoning tokens vs. 177 visible-answer tokens on one test reply --
# pure latency/quota waste for concise farming Q&A), and answers
# correctly in Kiswahili including typo'd/informal input. Deliberately
# gemini-3.1-flash-lite, not the newer gemini-3.5-flash-lite: the latter
# is Google's officially-recommended replacement for the retired
# gemini-2.5-flash-lite, but was returning repeated 503 "high demand"
# errors in live testing at the time of this change -- revisit once its
# availability stabilizes.
DEFAULT_MODELS = {
    "ollama": "llama3.2:1b",
    "anthropic": "claude-sonnet-5",
    "gemini": "gemini-3.1-flash-lite",
}


class AIProviderError(Exception):
    """
    Raised by any provider on failure (unreachable, misconfigured, timed
    out, malformed response, etc). Deliberately the ONE exception type
    every provider raises, regardless of what actually went wrong
    upstream -- ai_service.py only has to catch this single type to
    handle every provider uniformly.

    `public_message` is safe to show a user (no internals, no secrets).
    `log_message` carries the real detail for server-side logs only.
    """

    def __init__(self, public_message, log_message=None):
        super().__init__(public_message)
        self.public_message = public_message
        self.log_message = log_message or public_message


class AIProvider(ABC):
    """Common interface every AI provider implements."""

    @abstractmethod
    def complete(self, messages, system_prompt):
        """
        `messages`: list of {"role": "user"|"assistant", "content": str},
        already trimmed/validated by the caller.

        Returns the assistant's reply text, or raises AIProviderError.
        """
        raise NotImplementedError

    @abstractmethod
    def stream_complete(self, messages, system_prompt):
        """
        Like complete(), but a generator yielding the reply text
        incrementally as chunks arrive, for Server-Sent Events streaming
        (see app/services/ai_service.py's stream_message). Raises
        AIProviderError exactly like complete() -- since this is a
        generator, that can happen on the first `next()` call (nothing
        yielded yet) or after some chunks were already yielded, and
        callers must handle both.
        """
        raise NotImplementedError


class OllamaProvider(AIProvider):
    """
    Calls a local (or self-hosted) Ollama server's chat API
    (POST {base_url}/api/chat). Ollama has no concept of an API key, so
    "not configured" for this provider means "the server isn't running"
    or "the model hasn't been pulled yet" -- both handled explicitly
    below rather than surfacing a generic failure for either.
    """

    REQUEST_TIMEOUT_SECONDS = 60

    # Ollama unloads a model from memory a few minutes after its last
    # request (default 5m), and reloading it costs multiple seconds --
    # measured at ~2.3s for llama3.2:1b on modest hardware, on top of
    # generation time. keep_alive re-arms that timer on every request so
    # a normal back-and-forth conversation never pays the reload cost
    # after the first message.
    KEEP_ALIVE = "5m"

    # Caps a single reply's length so one runaway generation can't stall
    # a request far longer than a farming-advice answer ever needs to be
    # -- SYSTEM_PROMPT already asks for concise answers; this is the
    # backstop. Anthropic has the equivalent via MAX_TOKENS below.
    MAX_OUTPUT_TOKENS = 512

    def __init__(self, base_url, model):
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model

    def _request_body(self, messages, system_prompt, stream):
        return json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "system", "content": system_prompt}, *messages],
                "stream": stream,
                "keep_alive": self.KEEP_ALIVE,
                "options": {"num_predict": self.MAX_OUTPUT_TOKENS},
            }
        ).encode("utf-8")

    def complete(self, messages, system_prompt):
        body = self._request_body(messages, system_prompt, stream=False)

        request_obj = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(request_obj, timeout=self.REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            if err.code == 404 or "not found" in detail.lower():
                raise AIProviderError(
                    f'The AI model "{self.model}" is not available on the configured Ollama '
                    f"server. Ask an admin to run `ollama pull {self.model}`.",
                    log_message=f"Ollama model not found (model={self.model}): {detail}",
                )
            raise AIProviderError(
                "The AI assistant could not process your request right now. Please try again.",
                log_message=f"Ollama HTTP error {err.code}: {detail}",
            )
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            raise AIProviderError(
                "The AI assistant is temporarily unavailable (the local AI server is not "
                "reachable). Please try again shortly.",
                log_message=f"Ollama unreachable at {self.base_url}: {err}",
            )
        except json.JSONDecodeError as err:
            raise AIProviderError(
                "The AI assistant returned an unexpected response. Please try again.",
                log_message=f"Ollama returned non-JSON response: {err}",
            )

        try:
            content = payload["message"]["content"]
        except (KeyError, TypeError) as err:
            raise AIProviderError(
                "The AI assistant returned an unexpected response. Please try again.",
                log_message=f"Ollama malformed response shape: {payload!r} ({err})",
            )

        if not isinstance(content, str) or not content.strip():
            raise AIProviderError(
                "The AI assistant returned an empty response. Please try again.",
                log_message=f"Ollama returned empty content: {payload!r}",
            )
        return content.strip()

    def stream_complete(self, messages, system_prompt):
        body = self._request_body(messages, system_prompt, stream=True)

        request_obj = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            response = urllib.request.urlopen(request_obj, timeout=self.REQUEST_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            if err.code == 404 or "not found" in detail.lower():
                raise AIProviderError(
                    f'The AI model "{self.model}" is not available on the configured Ollama '
                    f"server. Ask an admin to run `ollama pull {self.model}`.",
                    log_message=f"Ollama model not found (model={self.model}): {detail}",
                )
            raise AIProviderError(
                "The AI assistant could not process your request right now. Please try again.",
                log_message=f"Ollama HTTP error {err.code}: {detail}",
            )
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            raise AIProviderError(
                "The AI assistant is temporarily unavailable (the local AI server is not "
                "reachable). Please try again shortly.",
                log_message=f"Ollama unreachable at {self.base_url}: {err}",
            )

        got_any_content = False
        try:
            with response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunk = payload.get("message", {}).get("content", "")
                    if chunk:
                        got_any_content = True
                        yield chunk
                    if payload.get("done"):
                        break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
            raise AIProviderError(
                "The AI assistant is temporarily unavailable (the local AI server is not "
                "reachable). Please try again shortly.",
                log_message=f"Ollama connection dropped mid-stream at {self.base_url}: {err}",
            )

        if not got_any_content:
            raise AIProviderError(
                "The AI assistant returned an empty response. Please try again.",
                log_message="Ollama stream produced no content.",
            )


class AnthropicProvider(AIProvider):
    """Calls the Anthropic Messages API. Requires ANTHROPIC_API_KEY."""

    API_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"
    REQUEST_TIMEOUT_SECONDS = 20
    MAX_TOKENS = 1024

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def complete(self, messages, system_prompt):
        if not self.api_key:
            raise AIProviderError(
                "The AI assistant is not configured. Set the ANTHROPIC_API_KEY "
                "environment variable on the server (with AI_PROVIDER=anthropic) to "
                "enable this feature."
            )

        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": self.MAX_TOKENS,
                "system": system_prompt,
                "messages": messages,
            }
        ).encode("utf-8")

        request_obj = urllib.request.Request(
            self.API_URL,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.API_VERSION,
            },
        )

        try:
            with urllib.request.urlopen(request_obj, timeout=self.REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            raise AIProviderError(
                "The AI assistant could not process your request right now. Please try again.",
                log_message=f"Anthropic HTTP error {err.code}: {detail}",
            )
        except (urllib.error.URLError, TimeoutError) as err:
            raise AIProviderError(
                "The AI assistant is temporarily unavailable. Please try again shortly.",
                log_message=f"Anthropic unreachable: {err}",
            )
        except json.JSONDecodeError as err:
            raise AIProviderError(
                "The AI assistant returned an unexpected response. Please try again.",
                log_message=f"Anthropic returned non-JSON response: {err}",
            )

        try:
            text = "".join(
                block["text"] for block in payload["content"] if block.get("type") == "text"
            ).strip()
        except (KeyError, TypeError) as err:
            raise AIProviderError(
                "The AI assistant returned an unexpected response. Please try again.",
                log_message=f"Anthropic malformed response shape: {payload!r} ({err})",
            )

        if not text:
            raise AIProviderError(
                "The AI assistant returned an empty response. Please try again.",
                log_message=f"Anthropic returned empty content: {payload!r}",
            )
        return text

    def stream_complete(self, messages, system_prompt):
        if not self.api_key:
            raise AIProviderError(
                "The AI assistant is not configured. Set the ANTHROPIC_API_KEY "
                "environment variable on the server (with AI_PROVIDER=anthropic) to "
                "enable this feature."
            )

        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": self.MAX_TOKENS,
                "system": system_prompt,
                "messages": messages,
                "stream": True,
            }
        ).encode("utf-8")

        request_obj = urllib.request.Request(
            self.API_URL,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.API_VERSION,
            },
        )

        try:
            response = urllib.request.urlopen(request_obj, timeout=self.REQUEST_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            raise AIProviderError(
                "The AI assistant could not process your request right now. Please try again.",
                log_message=f"Anthropic HTTP error {err.code}: {detail}",
            )
        except (urllib.error.URLError, TimeoutError) as err:
            raise AIProviderError(
                "The AI assistant is temporarily unavailable. Please try again shortly.",
                log_message=f"Anthropic unreachable: {err}",
            )

        got_any_content = False
        with response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    payload = json.loads(line[len("data:"):].strip())
                except json.JSONDecodeError:
                    continue

                event_type = payload.get("type")
                if event_type == "content_block_delta":
                    delta = payload.get("delta") or {}
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            got_any_content = True
                            yield text
                elif event_type == "error":
                    message = (payload.get("error") or {}).get(
                        "message", "The AI assistant encountered an error."
                    )
                    raise AIProviderError(
                        "The AI assistant could not process your request right now. Please try again.",
                        log_message=f"Anthropic stream error: {message}",
                    )

        if not got_any_content:
            raise AIProviderError(
                "The AI assistant returned an empty response. Please try again.",
                log_message="Anthropic stream produced no content.",
            )


class GeminiProvider(AIProvider):
    """
    Calls the Google Gemini API (Generative Language API). Requires
    GEMINI_API_KEY -- a free key from https://aistudio.google.com with no
    billing setup required, unlike Anthropic.

    Gemini's wire format differs from the internal {"role":
    "user"|"assistant", "content": str} shape in two ways: it calls the
    AI's turns "model" instead of "assistant", and it nests text under
    "parts" rather than a flat "content" string -- both handled in
    _to_gemini_contents() so the rest of the app never has to know.
    """

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    # The free tier queues requests under load and individual chunks (in
    # streaming) can arrive well after Anthropic's tuned 20s -- seen in
    # practice as spurious "read operation timed out" failures on requests
    # that would have succeeded with more headroom.
    REQUEST_TIMEOUT_SECONDS = 60
    MAX_OUTPUT_TOKENS = 1024

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    @staticmethod
    def _to_gemini_contents(messages):
        return [
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{"text": message["content"]}],
            }
            for message in messages
        ]

    def _request_body(self, messages, system_prompt):
        return json.dumps(
            {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": self._to_gemini_contents(messages),
                "generationConfig": {"maxOutputTokens": self.MAX_OUTPUT_TOKENS},
            }
        ).encode("utf-8")

    def complete(self, messages, system_prompt):
        if not self.api_key:
            raise AIProviderError(
                "The AI assistant is not configured. Set the GEMINI_API_KEY "
                "environment variable on the server (with AI_PROVIDER=gemini) to "
                "enable this feature."
            )

        request_obj = urllib.request.Request(
            f"{self.API_BASE}/{self.model}:generateContent",
            data=self._request_body(messages, system_prompt),
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )

        try:
            with urllib.request.urlopen(request_obj, timeout=self.REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            raise AIProviderError(
                "The AI assistant could not process your request right now. Please try again.",
                log_message=f"Gemini HTTP error {err.code}: {detail}",
            )
        except (urllib.error.URLError, TimeoutError) as err:
            raise AIProviderError(
                "The AI assistant is temporarily unavailable. Please try again shortly.",
                log_message=f"Gemini unreachable: {err}",
            )
        except json.JSONDecodeError as err:
            raise AIProviderError(
                "The AI assistant returned an unexpected response. Please try again.",
                log_message=f"Gemini returned non-JSON response: {err}",
            )

        try:
            parts = payload["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts).strip()
        except (KeyError, IndexError, TypeError) as err:
            raise AIProviderError(
                "The AI assistant returned an unexpected response. Please try again.",
                log_message=f"Gemini malformed response shape: {payload!r} ({err})",
            )

        if not text:
            raise AIProviderError(
                "The AI assistant returned an empty response. Please try again.",
                log_message=f"Gemini returned empty content: {payload!r}",
            )
        return text

    def stream_complete(self, messages, system_prompt):
        if not self.api_key:
            raise AIProviderError(
                "The AI assistant is not configured. Set the GEMINI_API_KEY "
                "environment variable on the server (with AI_PROVIDER=gemini) to "
                "enable this feature."
            )

        request_obj = urllib.request.Request(
            f"{self.API_BASE}/{self.model}:streamGenerateContent?alt=sse",
            data=self._request_body(messages, system_prompt),
            method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
        )

        try:
            response = urllib.request.urlopen(request_obj, timeout=self.REQUEST_TIMEOUT_SECONDS)
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", errors="replace")
            raise AIProviderError(
                "The AI assistant could not process your request right now. Please try again.",
                log_message=f"Gemini HTTP error {err.code}: {detail}",
            )
        except (urllib.error.URLError, TimeoutError) as err:
            raise AIProviderError(
                "The AI assistant is temporarily unavailable. Please try again shortly.",
                log_message=f"Gemini unreachable: {err}",
            )

        got_any_content = False
        with response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    payload = json.loads(line[len("data:"):].strip())
                except json.JSONDecodeError:
                    continue

                candidates = payload.get("candidates") or []
                if not candidates:
                    continue
                parts = (candidates[0].get("content") or {}).get("parts") or []
                text = "".join(part.get("text", "") for part in parts)
                if text:
                    got_any_content = True
                    yield text

        if not got_any_content:
            raise AIProviderError(
                "The AI assistant returned an empty response. Please try again.",
                log_message="Gemini stream produced no content.",
            )


def get_provider(config):
    """
    Build the configured AIProvider from Flask app config (`current_app.config`
    or an equivalent mapping). Raises AIProviderError -- not a hard crash --
    for an unknown AI_PROVIDER value, so a typo in config degrades to a
    clean 503 for the caller instead of an unhandled 500.
    """
    provider_name = (config.get("AI_PROVIDER") or "ollama").strip().lower()
    model = config.get("AI_MODEL") or DEFAULT_MODELS.get(provider_name)

    if provider_name == "ollama":
        return OllamaProvider(base_url=config.get("OLLAMA_BASE_URL"), model=model)
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=config.get("ANTHROPIC_API_KEY"), model=model)
    if provider_name == "gemini":
        return GeminiProvider(api_key=config.get("GEMINI_API_KEY"), model=model)

    raise AIProviderError(
        "The AI assistant is misconfigured on the server.",
        log_message=f"Unknown AI_PROVIDER={provider_name!r}; expected 'ollama', 'anthropic', or 'gemini'.",
    )
