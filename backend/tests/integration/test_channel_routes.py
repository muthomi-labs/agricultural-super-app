import pytest

from app.services import ai_service

WEBHOOK_SECRET = "test-channel-webhook-secret"


class _FakeProvider:
    def __init__(self, reply="A short farming answer."):
        self._reply = reply
        self.calls = []

    def complete(self, messages, system_prompt):
        self.calls.append(messages)
        return self._reply

    def stream_complete(self, messages, system_prompt):
        yield self._reply


@pytest.fixture
def fake_ai_provider(monkeypatch):
    def _install(reply="A short farming answer."):
        provider = _FakeProvider(reply=reply)
        monkeypatch.setattr(ai_service, "get_provider", lambda config: provider)
        return provider

    return _install


class TestWebhookAuthentication:
    def test_missing_secret_header_and_query_is_rejected(self, client):
        response = client.post("/api/channels/sms", data={"from": "0712345678", "text": "hi"})
        assert response.status_code == 401

    def test_wrong_secret_is_rejected(self, client):
        response = client.post(
            "/api/channels/sms",
            data={"from": "0712345678", "text": "hi"},
            headers={"X-Channel-Webhook-Secret": "wrong-secret"},
        )
        assert response.status_code == 401

    def test_correct_secret_via_header_is_accepted(self, client, fake_ai_provider):
        fake_ai_provider()
        response = client.post(
            "/api/channels/sms",
            data={"from": "0712345678", "text": "hi"},
            headers={"X-Channel-Webhook-Secret": WEBHOOK_SECRET},
        )
        assert response.status_code == 200

    def test_correct_secret_via_query_param_is_accepted(self, client, fake_ai_provider):
        fake_ai_provider()
        response = client.post(
            f"/api/channels/sms?secret={WEBHOOK_SECRET}",
            data={"from": "0712345678", "text": "hi"},
        )
        assert response.status_code == 200

    def test_fails_closed_when_secret_is_not_configured(self, app, client):
        original = app.config.get("CHANNEL_WEBHOOK_SECRET")
        app.config["CHANNEL_WEBHOOK_SECRET"] = None
        try:
            response = client.post(
                "/api/channels/sms",
                data={"from": "0712345678", "text": "hi"},
                headers={"X-Channel-Webhook-Secret": "anything"},
            )
            assert response.status_code == 401
        finally:
            app.config["CHANNEL_WEBHOOK_SECRET"] = original


def _headers():
    return {"X-Channel-Webhook-Secret": WEBHOOK_SECRET}


class TestSmsRoute:
    def test_missing_phone_number_returns_422(self, client):
        response = client.post("/api/channels/sms", data={"text": "hi"}, headers=_headers())
        assert response.status_code == 422

    def test_invalid_phone_number_returns_422(self, client):
        response = client.post(
            "/api/channels/sms", data={"from": "not-a-phone", "text": "hi"}, headers=_headers()
        )
        assert response.status_code == 422

    def test_processes_message_and_reports_undelivered_without_a_real_provider(
        self, client, fake_ai_provider
    ):
        fake_ai_provider(reply="Water tomatoes deeply once a week.")
        response = client.post(
            "/api/channels/sms",
            data={"from": "0712345678", "text": "How often should I water tomatoes?"},
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body["reply"] == "Water tomatoes deeply once a week."
        assert body["delivered"] is False
        assert body["provider_error"] is not None

    def test_never_claims_a_message_was_sent(self, client, fake_ai_provider):
        fake_ai_provider()
        response = client.post(
            "/api/channels/sms", data={"from": "0712345678", "text": "hi"}, headers=_headers()
        )
        assert response.get_json()["delivered"] is False


class TestUssdRoute:
    def test_returns_plain_text_content_type(self, client):
        response = client.post(
            "/api/channels/ussd", data={"phoneNumber": "0712345678", "text": ""}, headers=_headers()
        )
        assert response.status_code == 200
        assert response.content_type.startswith("text/plain")

    def test_empty_text_returns_welcome_menu(self, client):
        response = client.post(
            "/api/channels/ussd", data={"phoneNumber": "0712345678", "text": ""}, headers=_headers()
        )
        body = response.get_data(as_text=True)
        assert body.startswith("CON ")
        assert "AgriConnect" in body

    def test_farming_question_flow_ends_session(self, client, fake_ai_provider):
        fake_ai_provider(reply="Water deeply once a week.")
        response = client.post(
            "/api/channels/ussd",
            data={"phoneNumber": "0712345678", "text": "1*How often should I water tomatoes"},
            headers=_headers(),
        )
        body = response.get_data(as_text=True)
        assert body == "END Water deeply once a week."

    def test_missing_phone_number_returns_422(self, client):
        response = client.post("/api/channels/ussd", data={"text": "1"}, headers=_headers())
        assert response.status_code == 422


class TestVoiceRoute:
    def test_requires_webhook_auth(self, client):
        response = client.post("/api/channels/voice")
        assert response.status_code == 401

    def test_returns_not_implemented_when_authenticated(self, client):
        response = client.post("/api/channels/voice", headers=_headers())
        assert response.status_code == 501
        body = response.get_json()
        assert "not yet available" in body["error"].lower()


class TestChannelRateLimiting:
    def test_exceeding_the_limit_returns_429(self, app, client, fake_ai_provider):
        fake_ai_provider()
        app.config["CHANNEL_RATE_LIMIT_MAX_REQUESTS"] = 2
        try:
            for _ in range(2):
                response = client.post(
                    "/api/channels/sms",
                    data={"from": "0712345678", "text": "hi"},
                    headers=_headers(),
                )
                assert response.status_code == 200
            response = client.post(
                "/api/channels/sms", data={"from": "0712345678", "text": "hi"}, headers=_headers()
            )
            assert response.status_code == 429
        finally:
            app.config["CHANNEL_RATE_LIMIT_MAX_REQUESTS"] = 5

    def test_different_phone_numbers_have_independent_limits(self, app, client, fake_ai_provider):
        fake_ai_provider()
        app.config["CHANNEL_RATE_LIMIT_MAX_REQUESTS"] = 1
        try:
            first = client.post(
                "/api/channels/sms", data={"from": "0712345678", "text": "hi"}, headers=_headers()
            )
            second = client.post(
                "/api/channels/sms", data={"from": "0700000000", "text": "hi"}, headers=_headers()
            )
            assert first.status_code == 200
            assert second.status_code == 200
        finally:
            app.config["CHANNEL_RATE_LIMIT_MAX_REQUESTS"] = 5
