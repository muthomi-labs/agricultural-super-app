# tests/unit/test_email_service.py

import pytest

from app.services import email_service


class TestIsConfigured:
    def test_true_when_all_three_are_set(self):
        config = {"MAIL_SERVER": "smtp.example.com", "MAIL_USERNAME": "a@example.com", "MAIL_PASSWORD": "x"}
        assert email_service.is_configured(config) is True

    @pytest.mark.parametrize("missing", ["MAIL_SERVER", "MAIL_USERNAME", "MAIL_PASSWORD"])
    def test_false_when_any_one_is_missing(self, missing):
        config = {"MAIL_SERVER": "smtp.example.com", "MAIL_USERNAME": "a@example.com", "MAIL_PASSWORD": "x"}
        config[missing] = None
        assert email_service.is_configured(config) is False

    def test_false_when_nothing_is_set(self):
        assert email_service.is_configured({}) is False


class TestSendEmail:
    def test_raises_not_configured_when_mail_server_missing(self, app, monkeypatch):
        monkeypatch.setitem(app.config, "MAIL_SERVER", None)
        with pytest.raises(email_service.EmailNotConfiguredError):
            email_service.send_email(to="a@example.com", subject="s", html_body="<p>h</p>", text_body="t")

    def test_sends_successfully_when_configured(self, app):
        # TestingConfig provides fake-but-present MAIL_* values with
        # MAIL_SUPPRESS_SEND=True -- this exercises the real Flask-Mail
        # send path without touching a real socket.
        from app.extensions import mail

        with mail.record_messages() as outbox:
            email_service.send_email(
                to="recipient@example.com", subject="Test subject", html_body="<p>hi</p>", text_body="hi"
            )

        assert len(outbox) == 1
        assert outbox[0].recipients == ["recipient@example.com"]
        assert outbox[0].subject == "Test subject"
        assert outbox[0].html == "<p>hi</p>"
        assert outbox[0].body == "hi"

    def test_wraps_smtp_failures_as_delivery_error(self, app, monkeypatch):
        from app.extensions import mail

        def _raise(*args, **kwargs):
            raise OSError("Connection refused")

        monkeypatch.setattr(mail, "send", _raise)

        with pytest.raises(email_service.EmailDeliveryError):
            email_service.send_email(to="a@example.com", subject="s", html_body="<p>h</p>", text_body="t")


class TestPasswordResetEmail:
    def test_includes_reset_url_in_both_versions(self):
        html, text = email_service.password_reset_email(
            username="amina", reset_url="http://localhost:5173/reset-password?token=abc123", expires_in_minutes=60
        )
        assert "http://localhost:5173/reset-password?token=abc123" in html
        assert "http://localhost:5173/reset-password?token=abc123" in text

    def test_includes_username_and_expiry(self):
        html, text = email_service.password_reset_email(
            username="amina", reset_url="http://example.com/reset?token=x", expires_in_minutes=45
        )
        assert "amina" in html
        assert "amina" in text
        assert "45" in html
        assert "45" in text

    def test_includes_app_name(self):
        html, text = email_service.password_reset_email(
            username="amina", reset_url="http://example.com/reset?token=x", expires_in_minutes=60
        )
        assert "AgriConnect" in html
        assert "AgriConnect" in text

    def test_includes_security_warning_for_unrequested_resets(self):
        html, text = email_service.password_reset_email(
            username="amina", reset_url="http://example.com/reset?token=x", expires_in_minutes=60
        )
        assert "didn't request" in html
        assert "didn't request" in text

    def test_html_is_a_complete_document(self):
        html, _text = email_service.password_reset_email(
            username="amina", reset_url="http://example.com/reset?token=x", expires_in_minutes=60
        )
        assert "<html>" in html
        assert "</html>" in html

    def test_html_escapes_a_malicious_username(self):
        html, text = email_service.password_reset_email(
            username="<img src=x onerror=alert(1)>",
            reset_url="http://example.com/reset?token=x",
            expires_in_minutes=60,
        )
        assert "<img" not in html
        assert "&lt;img" in html
        assert "<img src=x onerror=alert(1)>" in text


class TestNewSignupEmail:
    def test_includes_username_email_and_role(self):
        html, text = email_service.new_signup_email(
            username="amina", email="amina@example.com", role="farmer", manage_url="http://x/admin/users"
        )
        for value in ("amina", "amina@example.com", "farmer"):
            assert value in html
            assert value in text

    def test_includes_manage_url(self):
        html, text = email_service.new_signup_email(
            username="amina",
            email="amina@example.com",
            role="farmer",
            manage_url="http://localhost:5173/admin/users?search=amina",
        )
        assert "http://localhost:5173/admin/users?search=amina" in html
        assert "http://localhost:5173/admin/users?search=amina" in text

    def test_includes_app_name(self):
        html, text = email_service.new_signup_email(
            username="amina", email="amina@example.com", role="farmer", manage_url="http://x/admin/users"
        )
        assert "AgriConnect" in html
        assert "AgriConnect" in text

    def test_html_is_a_complete_document(self):
        html, _text = email_service.new_signup_email(
            username="amina", email="amina@example.com", role="farmer", manage_url="http://x/admin/users"
        )
        assert "<html>" in html
        assert "</html>" in html

    def test_html_escapes_a_malicious_username(self):
        html, text = email_service.new_signup_email(
            username="<img src=x onerror=alert(1)>",
            email="amina@example.com",
            role="farmer",
            manage_url="http://x/admin/users",
        )
        assert "<img" not in html
        assert "&lt;img" in html
        # The plain-text body is not HTML and needs no escaping.
        assert "<img src=x onerror=alert(1)>" in text

    def test_html_escapes_malicious_email_and_role(self):
        html, _text = email_service.new_signup_email(
            username="amina",
            email="<script>alert(1)</script>@example.com",
            role="<b>admin</b>",
            manage_url="http://x/admin/users",
        )
        assert "<script>" not in html
        assert "<b>admin</b>" not in html
