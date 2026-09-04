# tests/integration/test_ai_routes.py
#
# These hit the real HTTP route, but never a real AI provider -- network
# calls are the provider layer's job, already covered in isolation by
# tests/unit/test_ai_providers.py. Here, `ai_service.get_provider` is
# monkeypatched to a fake provider so route/validation/error-envelope
# behavior is deterministic regardless of whether Ollama happens to be
# running on the machine executing the suite.

import json

import pytest

from app.services import ai_service
from app.services.ai_providers import AIProviderError


class _FakeProvider:
    def __init__(self, reply=None, error=None, chunks=None, stream_error=None):
        self._reply = reply
        self._error = error
        self._chunks = chunks
        self._stream_error = stream_error
        self.calls = []
        # Parallel to `calls` (same index = same request) -- kept as a
        # separate list rather than folded into `calls` so existing
        # assertions that treat `calls[i]` as the messages list directly
        # don't have to change.
        self.system_prompts = []

    def complete(self, messages, system_prompt):
        self.calls.append(messages)
        self.system_prompts.append(system_prompt)
        if self._error is not None:
            raise self._error
        return self._reply

    def stream_complete(self, messages, system_prompt):
        self.calls.append(messages)
        self.system_prompts.append(system_prompt)
        for chunk in self._chunks or []:
            yield chunk
        if self._stream_error is not None:
            raise self._stream_error


@pytest.fixture
def fake_provider(monkeypatch):
    """
    Patches ai_service.get_provider (not the real network-facing
    provider classes) so route tests exercise the full request path --
    validation, auth, ai_service orchestration, error envelope -- without
    depending on any real AI backend being reachable.
    """

    def _install(reply=None, error=None, chunks=None, stream_error=None):
        provider = _FakeProvider(reply=reply, error=error, chunks=chunks, stream_error=stream_error)
        monkeypatch.setattr(ai_service, "get_provider", lambda config: provider)
        return provider

    return _install


def _parse_sse(body):
    """
    Parses a text/event-stream body (as produced by
    app/routes/ai_routes.py's _sse helper) into a list of (event, data)
    tuples, with `data` already JSON-decoded.
    """
    events = []
    for block in body.strip().split("\n\n"):
        if not block.strip():
            continue
        event = None
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
        events.append((event, data))
    return events


class TestAskAssistant:
    def test_requires_auth(self, client):
        response = client.post("/api/ai/assistant", json={"messages": [{"role": "user", "content": "Hi"}]})
        assert response.status_code == 401

    def test_success_returns_reply(self, client, amina, fake_provider):
        fake_provider(reply="Water tomatoes deeply once a week, more often in sandy soil.")
        response = client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "user", "content": "How often should I water tomatoes?"}]},
        )
        assert response.status_code == 200
        assert response.get_json() == {"reply": "Water tomatoes deeply once a week, more often in sandy soil."}

    def test_provider_failure_returns_503_with_public_message_only(self, client, amina, fake_provider):
        fake_provider(
            error=AIProviderError(
                "The AI assistant is temporarily unavailable (the local AI server is not reachable). "
                "Please try again shortly.",
                log_message="Ollama unreachable at http://localhost:11434: Connection refused",
            )
        )
        response = client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "user", "content": "Why are my tomato leaves yellowing?"}]},
        )
        assert response.status_code == 503
        body = response.get_json()
        assert "not reachable" in body["error"].lower()
        # The internal log-only detail must never reach the client.
        assert "Connection refused" not in body["error"]
        assert "localhost:11434" not in body["error"]

    def test_unconfigured_provider_returns_503(self, client, amina, fake_provider):
        fake_provider(error=AIProviderError("The AI assistant is not configured. Set the ANTHROPIC_API_KEY..."))
        response = client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        assert response.status_code == 503

    def test_default_provider_is_ollama_when_unset(self, app):
        assert app.config.get("AI_PROVIDER", "ollama") == "ollama"

    def test_missing_messages_returns_422(self, client, amina):
        response = client.post("/api/ai/assistant", headers=amina["headers"], json={})
        assert response.status_code == 422

    def test_empty_messages_returns_422(self, client, amina):
        response = client.post("/api/ai/assistant", headers=amina["headers"], json={"messages": []})
        assert response.status_code == 422

    def test_invalid_role_returns_422(self, client, amina):
        response = client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "system", "content": "Hi"}]},
        )
        assert response.status_code == 422

    def test_blank_content_returns_422(self, client, amina):
        response = client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "user", "content": "   "}]},
        )
        assert response.status_code == 422

    def test_last_message_must_be_from_user(self, client, amina):
        response = client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "assistant", "content": "How can I help?"}]},
        )
        assert response.status_code == 422

    def test_too_many_messages_returns_422(self, client, amina):
        messages = [{"role": "user", "content": "Hi"} for _ in range(25)]
        response = client.post("/api/ai/assistant", headers=amina["headers"], json={"messages": messages})
        assert response.status_code == 422

    def test_message_too_long_returns_422(self, client, amina):
        response = client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "user", "content": "x" * 5000}]},
        )
        assert response.status_code == 422

    def test_non_dict_message_returns_422(self, client, amina):
        response = client.post(
            "/api/ai/assistant", headers=amina["headers"], json={"messages": ["just a string"]}
        )
        assert response.status_code == 422


class TestAILanguageAwareness:
    """
    The assistant is never told "the user asked in Kiswahili" -- it's
    always told the user's *preferred* language (User.language) and
    instructed to mirror whatever language the message itself is in.
    These tests only check that the right instruction reaches the
    provider for each entry point (one-shot /assistant, a persisted
    conversation's send, and its stream) -- not that a real model
    actually replies in Kiswahili, which is a live-provider concern
    exercised manually (see the session report), not something a fake
    provider can meaningfully verify.
    """

    def test_default_language_is_english(self, client, amina, fake_provider):
        provider = fake_provider(reply="Water deeply once a week.")
        client.post(
            "/api/ai/assistant",
            headers=amina["headers"],
            json={"messages": [{"role": "user", "content": "How often should I water tomatoes?"}]},
        )
        assert "English" in provider.system_prompts[-1]

    def test_swahili_preference_reaches_one_shot_assistant(self, client, register_user, fake_provider):
        fatuma = register_user(username="fatuma", language="sw")
        provider = fake_provider(reply="Mwagilia maji mara moja kwa wiki.")
        client.post(
            "/api/ai/assistant",
            headers=fatuma["headers"],
            json={"messages": [{"role": "user", "content": "Nimwagilie nyanya mara ngapi?"}]},
        )
        prompt = provider.system_prompts[-1]
        assert "Kiswahili" in prompt
        assert "mkulima" in prompt  # a spot-check that real terminology, not a generic mention, made it in

    def test_swahili_preference_reaches_conversation_send(self, client, register_user, fake_provider):
        fatuma = register_user(username="fatuma", language="sw")
        provider = fake_provider(reply="Mwagilia maji mara moja kwa wiki.")
        convo_id = client.post("/api/ai/conversations", headers=fatuma["headers"], json={}).get_json()["id"]
        client.post(
            f"/api/ai/conversations/{convo_id}/messages",
            headers=fatuma["headers"],
            json={"content": "Nimwagilie nyanya mara ngapi?"},
        )
        assert "Kiswahili" in provider.system_prompts[-1]

    def test_swahili_preference_reaches_conversation_stream(self, client, register_user, fake_provider):
        fatuma = register_user(username="fatuma", language="sw")
        provider = fake_provider(chunks=["Mwagilia ", "maji."])
        convo_id = client.post("/api/ai/conversations", headers=fatuma["headers"], json={}).get_json()["id"]
        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages?stream=true",
            headers=fatuma["headers"],
            json={"content": "Nimwagilie nyanya mara ngapi?"},
        )
        response.get_data(as_text=True)  # force the streaming generator to run to completion
        assert "Kiswahili" in provider.system_prompts[-1]

    def test_updating_language_preference_changes_subsequent_ai_requests(self, client, amina, fake_provider):
        provider = fake_provider(reply="Sure.")
        client.post(
            "/api/ai/assistant", headers=amina["headers"], json={"messages": [{"role": "user", "content": "Hi"}]}
        )
        assert "English" in provider.system_prompts[-1]

        update = client.put("/api/users/me/language", headers=amina["headers"], json={"language": "sw"})
        assert update.status_code == 200

        client.post(
            "/api/ai/assistant", headers=amina["headers"], json={"messages": [{"role": "user", "content": "Hi"}]}
        )
        assert "Kiswahili" in provider.system_prompts[-1]


# ---------------------------------------------------------------------------
# Persistent conversations: /api/ai/conversations[...]
# ---------------------------------------------------------------------------


class TestCreateConversation:
    def test_requires_auth(self, client):
        response = client.post("/api/ai/conversations", json={})
        assert response.status_code == 401

    def test_creates_conversation_with_no_title(self, client, amina):
        response = client.post("/api/ai/conversations", headers=amina["headers"], json={})
        assert response.status_code == 201
        body = response.get_json()
        assert body["title"] is None
        assert "id" in body

    def test_creates_conversation_with_explicit_title(self, client, amina):
        response = client.post(
            "/api/ai/conversations", headers=amina["headers"], json={"title": "Maize planting"}
        )
        assert response.status_code == 201
        assert response.get_json()["title"] == "Maize planting"

    def test_non_string_title_returns_422(self, client, amina):
        response = client.post("/api/ai/conversations", headers=amina["headers"], json={"title": 123})
        assert response.status_code == 422


class TestListConversations:
    def test_requires_auth(self, client):
        response = client.get("/api/ai/conversations")
        assert response.status_code == 401

    def test_lists_only_own_conversations(self, client, amina, brian):
        client.post("/api/ai/conversations", headers=amina["headers"], json={})
        client.post("/api/ai/conversations", headers=brian["headers"], json={})

        amina_conversations = client.get("/api/ai/conversations", headers=amina["headers"]).get_json()
        brian_conversations = client.get("/api/ai/conversations", headers=brian["headers"]).get_json()

        assert len(amina_conversations) == 1
        assert len(brian_conversations) == 1

    def test_list_does_not_include_messages(self, client, amina, fake_provider):
        fake_provider(reply="Water deeply once a week.")
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={"content": "Hi"}
        )

        response = client.get("/api/ai/conversations", headers=amina["headers"])
        assert "messages" not in response.get_json()[0]

    def test_most_recently_active_conversation_sorts_first(self, client, amina, fake_provider):
        fake_provider(reply="Sure.")
        first_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        second_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]

        client.post(
            f"/api/ai/conversations/{first_id}/messages", headers=amina["headers"], json={"content": "Hi"}
        )

        conversations = client.get("/api/ai/conversations", headers=amina["headers"]).get_json()
        assert conversations[0]["id"] == first_id
        assert conversations[1]["id"] == second_id


class TestGetConversation:
    def test_requires_auth(self, client, amina):
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        response = client.get(f"/api/ai/conversations/{convo_id}")
        assert response.status_code == 401

    def test_owner_can_view_with_messages(self, client, amina, fake_provider):
        fake_provider(reply="Water deeply once a week.")
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        client.post(
            f"/api/ai/conversations/{convo_id}/messages",
            headers=amina["headers"],
            json={"content": "How often should I water tomatoes?"},
        )

        response = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"])
        assert response.status_code == 200
        body = response.get_json()
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][1]["role"] == "assistant"

    def test_reload_returns_the_same_history(self, client, amina, fake_provider):
        """
        Simulates a page reload: fetching the same conversation twice
        (with no client-side state carried between the calls) must
        return identical, complete history -- this is the behavior that
        was missing before persistence was added.
        """
        fake_provider(reply="Plant in rows 75cm apart.")
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        client.post(
            f"/api/ai/conversations/{convo_id}/messages",
            headers=amina["headers"],
            json={"content": "Maize spacing?"},
        )

        first_load = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        second_load = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert first_load == second_load
        assert len(second_load["messages"]) == 2

    def test_non_owner_returns_403(self, client, amina, brian):
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        response = client.get(f"/api/ai/conversations/{convo_id}", headers=brian["headers"])
        assert response.status_code == 403

    def test_unknown_conversation_returns_404(self, client, amina):
        response = client.get("/api/ai/conversations/999999", headers=amina["headers"])
        assert response.status_code == 404


class TestSendConversationMessage:
    def _create(self, client, headers):
        return client.post("/api/ai/conversations", headers=headers, json={}).get_json()["id"]

    def test_requires_auth(self, client, amina):
        convo_id = self._create(client, amina["headers"])
        response = client.post(f"/api/ai/conversations/{convo_id}/messages", json={"content": "Hi"})
        assert response.status_code == 401

    def test_send_persists_user_and_assistant_messages(self, client, amina, fake_provider):
        fake_provider(reply="Water tomatoes deeply once a week.")
        convo_id = self._create(client, amina["headers"])

        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages",
            headers=amina["headers"],
            json={"content": "How often should I water tomatoes?"},
        )
        assert response.status_code == 201
        body = response.get_json()
        assert body["user_message"]["role"] == "user"
        assert body["user_message"]["content"] == "How often should I water tomatoes?"
        assert body["assistant_message"]["role"] == "assistant"
        assert body["assistant_message"]["content"] == "Water tomatoes deeply once a week."

        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert len(detail["messages"]) == 2

    def test_first_message_sets_conversation_title(self, client, amina, fake_provider):
        fake_provider(reply="Sure.")
        convo_id = self._create(client, amina["headers"])
        client.post(
            f"/api/ai/conversations/{convo_id}/messages",
            headers=amina["headers"],
            json={"content": "Why are my tomato leaves turning yellow?"},
        )

        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert detail["title"] == "Why are my tomato leaves turning yellow?"

    def test_continuing_an_existing_conversation_appends_messages(self, client, amina, fake_provider):
        fake_provider(reply="Sure.")
        convo_id = self._create(client, amina["headers"])
        client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={"content": "First?"}
        )
        client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={"content": "Second?"}
        )

        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert [m["content"] for m in detail["messages"]] == ["First?", "Sure.", "Second?", "Sure."]

    def test_non_owner_cannot_send_to_conversation(self, client, amina, brian, fake_provider):
        fake_provider(reply="Sure.")
        convo_id = self._create(client, amina["headers"])

        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=brian["headers"], json={"content": "Intruding"}
        )
        assert response.status_code == 403

    def test_missing_content_returns_422(self, client, amina):
        convo_id = self._create(client, amina["headers"])
        response = client.post(f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={})
        assert response.status_code == 422

    def test_whitespace_only_content_returns_422(self, client, amina):
        convo_id = self._create(client, amina["headers"])
        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={"content": "   "}
        )
        assert response.status_code == 422

    def test_content_too_long_returns_422(self, client, amina):
        convo_id = self._create(client, amina["headers"])
        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages",
            headers=amina["headers"],
            json={"content": "x" * 5000},
        )
        assert response.status_code == 422

    def test_long_first_message_truncates_the_derived_title(self, client, amina, fake_provider):
        fake_provider(reply="Sure.")
        convo_id = self._create(client, amina["headers"])
        long_content = "Why are my tomato leaves turning yellow and curling at the edges lately"
        assert len(long_content) > 60

        client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={"content": long_content}
        )

        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert len(detail["title"]) <= 60
        assert detail["title"].endswith("...")

    def test_unknown_conversation_returns_404(self, client, amina):
        response = client.post(
            "/api/ai/conversations/999999/messages", headers=amina["headers"], json={"content": "Hi"}
        )
        assert response.status_code == 404

    def test_ai_failure_saves_user_message_but_not_assistant_message(self, client, amina, fake_provider):
        """
        Guards against corrupted/incomplete records: a provider failure
        must not leave a fake or truncated assistant row, but the user's
        own message -- a complete, real record of what they sent -- is
        not lost either.
        """
        fake_provider(
            error=AIProviderError(
                "The AI assistant is temporarily unavailable (the local AI server is not reachable). "
                "Please try again shortly."
            )
        )
        convo_id = self._create(client, amina["headers"])

        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages",
            headers=amina["headers"],
            json={"content": "Why are my tomato leaves yellowing?"},
        )
        assert response.status_code == 503

        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert len(detail["messages"]) == 1
        assert detail["messages"][0]["role"] == "user"


class TestConversationContextWindow:
    def test_only_recent_messages_are_sent_to_the_provider(self, client, amina, fake_provider):
        """
        Long conversations must not send the entire history to the AI
        on every turn -- only the last MAX_HISTORY_MESSAGES messages.
        """
        provider = fake_provider(reply="Sure.")
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]

        turns = ai_service.MAX_HISTORY_MESSAGES  # each turn adds 2 messages (user + assistant)
        for i in range(turns):
            client.post(
                f"/api/ai/conversations/{convo_id}/messages",
                headers=amina["headers"],
                json={"content": f"Question {i}"},
            )

        # By now there are 2 * turns messages in the database...
        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert len(detail["messages"]) == 2 * turns

        # ...but every call to the provider was capped at the context window.
        assert all(len(call) <= ai_service.MAX_HISTORY_MESSAGES for call in provider.calls)
        assert len(provider.calls[-1]) == ai_service.MAX_HISTORY_MESSAGES

        # And the window is the most RECENT messages, not the oldest.
        last_call_contents = [m["content"] for m in provider.calls[-1]]
        assert f"Question {turns - 1}" in last_call_contents
        assert "Question 0" not in last_call_contents


class TestDeleteConversation:
    def test_requires_auth(self, client, amina):
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        response = client.delete(f"/api/ai/conversations/{convo_id}")
        assert response.status_code == 401

    def test_owner_can_delete(self, client, amina, fake_provider):
        fake_provider(reply="Sure.")
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={"content": "Hi"}
        )

        response = client.delete(f"/api/ai/conversations/{convo_id}", headers=amina["headers"])
        assert response.status_code == 204

        assert client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).status_code == 404

    def test_delete_does_not_orphan_messages(self, client, amina, fake_provider):
        fake_provider(reply="Sure.")
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        client.post(
            f"/api/ai/conversations/{convo_id}/messages", headers=amina["headers"], json={"content": "Hi"}
        )

        from app.extensions import db
        from app.models import AIMessage

        client.delete(f"/api/ai/conversations/{convo_id}", headers=amina["headers"])
        assert db.session.query(AIMessage).filter_by(conversation_id=convo_id).count() == 0

    def test_non_owner_cannot_delete(self, client, amina, brian):
        convo_id = client.post("/api/ai/conversations", headers=amina["headers"], json={}).get_json()["id"]
        response = client.delete(f"/api/ai/conversations/{convo_id}", headers=brian["headers"])
        assert response.status_code == 403

    def test_unknown_conversation_returns_404(self, client, amina):
        response = client.delete("/api/ai/conversations/999999", headers=amina["headers"])
        assert response.status_code == 404


class TestStreamConversationMessage:
    def _create(self, client, headers):
        return client.post("/api/ai/conversations", headers=headers, json={}).get_json()["id"]

    def test_streams_chunks_and_persists_full_reply(self, client, amina, fake_provider):
        fake_provider(chunks=["Water ", "deeply ", "once a week."])
        convo_id = self._create(client, amina["headers"])

        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages?stream=true",
            headers=amina["headers"],
            json={"content": "How often should I water tomatoes?"},
        )
        assert response.status_code == 200
        assert response.content_type.startswith("text/event-stream")

        events = _parse_sse(response.get_data(as_text=True))
        event_names = [name for name, _ in events]
        assert event_names[0] == "user_message"
        assert event_names.count("chunk") == 3
        assert event_names[-1] == "done"

        chunk_text = "".join(data for name, data in events if name == "chunk")
        assert chunk_text == "Water deeply once a week."

        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert len(detail["messages"]) == 2
        assert detail["messages"][1]["role"] == "assistant"
        assert detail["messages"][1]["content"] == "Water deeply once a week."

    def test_streaming_failure_emits_error_event_and_saves_no_assistant_message(self, client, amina, fake_provider):
        fake_provider(
            chunks=["Wat"],
            stream_error=AIProviderError(
                "The AI assistant is temporarily unavailable. Please try again shortly."
            ),
        )
        convo_id = self._create(client, amina["headers"])

        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages?stream=true",
            headers=amina["headers"],
            json={"content": "Hi"},
        )
        assert response.status_code == 200  # headers were already committed once streaming started

        events = _parse_sse(response.get_data(as_text=True))
        assert events[-1][0] == "error"

        detail = client.get(f"/api/ai/conversations/{convo_id}", headers=amina["headers"]).get_json()
        assert len(detail["messages"]) == 1  # only the user's message -- no partial/corrupted reply saved
        assert detail["messages"][0]["role"] == "user"

    def test_non_owner_cannot_stream_to_conversation(self, client, amina, brian, fake_provider):
        fake_provider(chunks=["Hi"])
        convo_id = self._create(client, amina["headers"])

        response = client.post(
            f"/api/ai/conversations/{convo_id}/messages?stream=true",
            headers=brian["headers"],
            json={"content": "Intruding"},
        )
        assert response.status_code == 403
