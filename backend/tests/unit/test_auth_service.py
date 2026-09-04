# tests/unit/test_auth_service.py

from datetime import datetime, timedelta

import pytest

from app.errors import ConflictError, UnauthorizedError, ValidationAPIError
from app.extensions import db
from app.models import PasswordResetToken
from app.services import auth_service


def _register_data(username="amina", email="amina@example.com", password="supersecret123", role="farmer"):
    """
    Matches the shape UserSchema.load() produces: password under the
    key "password_hash" (see app/schemas/user_schema.py's data_key), not
    a schema call itself -- these are unit tests of the SERVICE, so we
    hand it exactly what the schema would have handed it, without going
    through the schema (or HTTP) at all.
    """
    return {"username": username, "email": email, "password_hash": password, "role": role}


class TestRegisterUser:
    def test_creates_user_with_hashed_password(self):
        user = auth_service.register_user(_register_data())
        assert user.id is not None
        assert user.username == "amina"
        assert user.email == "amina@example.com"
        # The whole point of hashing: the stored value is never the
        # plaintext we handed in.
        assert user.password_hash != "supersecret123"
        assert user.check_password("supersecret123") is True

    def test_defaults_role_to_farmer_when_omitted(self):
        data = _register_data()
        data.pop("role")
        # register_user reads data.get("role", "farmer") -- this proves
        # that default holds even when the caller omits the key
        # entirely, not just when it's explicitly "farmer".
        user = auth_service.register_user(data)
        assert user.role == "farmer"

    def test_duplicate_username_raises_conflict(self):
        auth_service.register_user(_register_data(username="amina", email="a1@example.com"))
        with pytest.raises(ConflictError):
            auth_service.register_user(_register_data(username="amina", email="a2@example.com"))

    def test_duplicate_email_raises_conflict(self):
        auth_service.register_user(_register_data(username="amina", email="shared@example.com"))
        with pytest.raises(ConflictError):
            auth_service.register_user(_register_data(username="different", email="shared@example.com"))

    def test_notifies_no_one_when_admin_notification_emails_unset(self):
        # TestingConfig leaves ADMIN_NOTIFICATION_EMAILS at its default
        # (empty) -- registration must still succeed and send nothing.
        from app.extensions import mail

        with mail.record_messages() as outbox:
            auth_service.register_user(_register_data())

        assert len(outbox) == 0

    def test_emails_every_configured_admin_on_signup(self, app, monkeypatch):
        from app.extensions import mail

        monkeypatch.setitem(
            app.config, "ADMIN_NOTIFICATION_EMAILS", ["admin1@example.com", "admin2@example.com"]
        )

        with mail.record_messages() as outbox:
            auth_service.register_user(_register_data(username="amina", email="amina@example.com"))

        assert len(outbox) == 2
        recipients = {message.recipients[0] for message in outbox}
        assert recipients == {"admin1@example.com", "admin2@example.com"}
        assert "amina" in outbox[0].body
        assert "amina@example.com" in outbox[0].body

    def test_manage_url_url_encodes_the_username(self, app, monkeypatch):
        from app.extensions import mail

        monkeypatch.setitem(app.config, "ADMIN_NOTIFICATION_EMAILS", ["admin@example.com"])

        with mail.record_messages() as outbox:
            auth_service.register_user(_register_data(username="a&b=c", email="ab@example.com"))

        assert "search=a%26b%3Dc" in outbox[0].body
        assert "search=a&b=c" not in outbox[0].body

    def test_subject_strips_newlines_from_username(self, app, monkeypatch):
        from app.extensions import mail

        monkeypatch.setitem(app.config, "ADMIN_NOTIFICATION_EMAILS", ["admin@example.com"])

        with mail.record_messages() as outbox:
            auth_service.register_user(_register_data(username="amina\r\nBcc: evil@example.com", email="a@example.com"))

        assert "\r" not in outbox[0].subject
        assert "\n" not in outbox[0].subject

    def test_does_not_raise_when_email_is_not_configured(self, app, monkeypatch):
        monkeypatch.setitem(app.config, "ADMIN_NOTIFICATION_EMAILS", ["admin@example.com"])
        monkeypatch.setitem(app.config, "MAIL_SERVER", None)
        monkeypatch.setitem(app.config, "MAIL_USERNAME", None)
        monkeypatch.setitem(app.config, "MAIL_PASSWORD", None)

        # Registration itself must still succeed -- a notification gap
        # is never allowed to block or fail the actual signup.
        user = auth_service.register_user(_register_data())
        assert user.id is not None

    def test_does_not_raise_when_smtp_send_fails(self, app, monkeypatch):
        from app.services import email_service

        monkeypatch.setitem(app.config, "ADMIN_NOTIFICATION_EMAILS", ["admin@example.com"])

        def _boom(**kwargs):
            raise email_service.EmailDeliveryError("SMTP server unexpectedly closed the connection")

        monkeypatch.setattr(email_service, "send_email", _boom)

        user = auth_service.register_user(_register_data())
        assert user.id is not None

    def test_one_failing_admin_does_not_block_the_next(self, app, monkeypatch):
        from app.services import email_service

        monkeypatch.setitem(
            app.config, "ADMIN_NOTIFICATION_EMAILS", ["bad@example.com", "good@example.com"]
        )

        sent_to = []

        def _send(to, **kwargs):
            sent_to.append(to)
            if to == "bad@example.com":
                raise email_service.EmailDeliveryError("rejected")

        monkeypatch.setattr(email_service, "send_email", _send)

        auth_service.register_user(_register_data())
        assert sent_to == ["bad@example.com", "good@example.com"]


class TestAuthenticateUser:
    def test_valid_username_and_password_succeeds(self, create_user):
        create_user(username="brian", password="anothersecret123")
        user = auth_service.authenticate_user("brian", "anothersecret123")
        assert user.username == "brian"

    def test_valid_email_succeeds(self, create_user):
        create_user(username="brian", email="brian@example.com", password="anothersecret123")
        user = auth_service.authenticate_user("brian@example.com", "anothersecret123")
        assert user.username == "brian"

    def test_wrong_password_raises_unauthorized(self, create_user):
        create_user(username="brian", password="anothersecret123")
        with pytest.raises(UnauthorizedError):
            auth_service.authenticate_user("brian", "wrongpassword")

    def test_unknown_identifier_raises_unauthorized(self):
        with pytest.raises(UnauthorizedError):
            auth_service.authenticate_user("nobody", "whatever123")

    def test_inactive_account_raises_unauthorized(self, create_user):
        create_user(username="deactivated", password="somepassword123", is_active=False)
        with pytest.raises(UnauthorizedError):
            auth_service.authenticate_user("deactivated", "somepassword123")

    def test_same_error_message_for_unknown_user_and_wrong_password(self, create_user):
        # Regression guard for the anti-enumeration design decision noted
        # in auth_service.py: these two failure modes must be
        # indistinguishable to the caller.
        create_user(username="brian", password="anothersecret123")

        with pytest.raises(UnauthorizedError) as unknown_user_exc:
            auth_service.authenticate_user("nobody", "whatever123")

        with pytest.raises(UnauthorizedError) as wrong_password_exc:
            auth_service.authenticate_user("brian", "wrongpassword")

        assert unknown_user_exc.value.message == wrong_password_exc.value.message


class TestRequestPasswordReset:
    def test_creates_a_token_for_known_email(self, create_user):
        create_user(username="amina", email="amina@example.com")
        auth_service.request_password_reset("amina@example.com")
        assert db.session.query(PasswordResetToken).count() == 1

    def test_silently_does_nothing_for_unknown_email(self):
        auth_service.request_password_reset("nobody@example.com")
        assert db.session.query(PasswordResetToken).count() == 0

    def test_sends_an_actual_email_when_configured(self, create_user):
        # TestingConfig has fake-but-present MAIL_* values and
        # MAIL_SUPPRESS_SEND=True (see app/config.py) -- this exercises
        # the real Flask-Mail send path, just without a real socket.
        from app.extensions import mail

        create_user(username="amina", email="amina@example.com")

        with mail.record_messages() as outbox:
            auth_service.request_password_reset("amina@example.com")

        assert len(outbox) == 1
        message = outbox[0]
        assert message.recipients == ["amina@example.com"]
        assert "AgriConnect" in message.subject
        assert message.body is not None  # plain-text fallback present
        assert message.html is not None  # HTML version present

    def test_email_contains_a_working_reset_url(self, create_user, app):
        from app.extensions import mail

        create_user(username="amina", email="amina@example.com")

        with mail.record_messages() as outbox:
            auth_service.request_password_reset("amina@example.com")

        message = outbox[0]
        expected_prefix = f"{app.config['FRONTEND_URL']}/reset-password?token="
        assert expected_prefix in message.body
        assert expected_prefix in message.html

        # The token actually embedded in the email must be the same one
        # that unlocks reset_password() -- not a decorative placeholder.
        token_start = message.body.index(expected_prefix) + len(expected_prefix)
        raw_token = message.body[token_start:].split()[0].rstrip(".")
        auth_service.reset_password(raw_token, "NewPassword123!")  # should not raise

    def test_does_not_raise_when_email_is_not_configured(self, create_user, monkeypatch, app):
        create_user(username="amina", email="amina@example.com")
        monkeypatch.setitem(app.config, "MAIL_SERVER", None)
        monkeypatch.setitem(app.config, "MAIL_USERNAME", None)
        monkeypatch.setitem(app.config, "MAIL_PASSWORD", None)

        auth_service.request_password_reset("amina@example.com")  # should not raise

        # The token is still issued even though the email couldn't be
        # sent -- an admin could still relay it out-of-band if needed,
        # and this proves the two concerns (token issuance vs. delivery)
        # are properly decoupled.
        assert db.session.query(PasswordResetToken).count() == 1

    def test_logs_configuration_error_without_leaking_the_token(self, create_user, monkeypatch, app, caplog):
        import logging

        user = create_user(username="amina", email="amina@example.com")
        monkeypatch.setitem(app.config, "MAIL_SERVER", None)
        monkeypatch.setitem(app.config, "MAIL_USERNAME", None)
        monkeypatch.setitem(app.config, "MAIL_PASSWORD", None)

        with caplog.at_level(logging.ERROR):
            auth_service.request_password_reset("amina@example.com")

        assert any("not configured" in record.message for record in caplog.records)
        # The raw token must never appear in any log line, under any
        # circumstances -- a log is not the secure channel a mailed
        # link is.
        for record in caplog.records:
            assert "reset-password?token=" not in record.getMessage()

        token_record = db.session.query(PasswordResetToken).filter_by(user_id=user.id).first()
        assert token_record is not None  # sanity: the token really was created

    def test_does_not_raise_when_smtp_send_fails(self, create_user, monkeypatch):
        from app.services import email_service

        create_user(username="amina", email="amina@example.com")

        def _boom(**kwargs):
            raise email_service.EmailDeliveryError("SMTP server unexpectedly closed the connection")

        monkeypatch.setattr(email_service, "send_email", _boom)

        auth_service.request_password_reset("amina@example.com")  # should not raise
        assert db.session.query(PasswordResetToken).count() == 1

    def test_response_is_identical_whether_or_not_email_is_configured(self, create_user, monkeypatch, app):
        # Both branches must return the exact same thing (None) to the
        # caller -- see the anti-enumeration reasoning in
        # request_password_reset's docstring.
        create_user(username="amina", email="amina@example.com")
        configured_result = auth_service.request_password_reset("amina@example.com")

        monkeypatch.setitem(app.config, "MAIL_SERVER", None)
        unconfigured_result = auth_service.request_password_reset("nobody@example.com")

        assert configured_result == unconfigured_result == None  # noqa: E711


class TestResetPassword:
    def test_valid_token_changes_password(self, create_user):
        user = create_user(username="amina", email="amina@example.com", password="oldpassword123")
        raw_token = "raw-token-value"
        db.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=auth_service._hash_token(raw_token),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
        )
        db.session.commit()

        auth_service.reset_password(raw_token, "newpassword123")

        db.session.refresh(user)
        assert user.check_password("newpassword123") is True
        assert user.check_password("oldpassword123") is False

    def test_unknown_token_raises_validation_error(self):
        with pytest.raises(ValidationAPIError):
            auth_service.reset_password("not-a-real-token", "newpassword123")

    def test_expired_token_raises_validation_error(self, create_user):
        user = create_user(username="amina", email="amina@example.com")
        raw_token = "raw-token-value"
        db.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=auth_service._hash_token(raw_token),
                expires_at=datetime.utcnow() - timedelta(seconds=1),
            )
        )
        db.session.commit()

        with pytest.raises(ValidationAPIError):
            auth_service.reset_password(raw_token, "newpassword123")

    def test_used_token_cannot_be_reused(self, create_user):
        user = create_user(username="amina", email="amina@example.com")
        raw_token = "raw-token-value"
        db.session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=auth_service._hash_token(raw_token),
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
        )
        db.session.commit()

        auth_service.reset_password(raw_token, "newpassword123")

        with pytest.raises(ValidationAPIError):
            auth_service.reset_password(raw_token, "anotherpassword123")


class TestChangePassword:
    def test_correct_current_password_changes_it(self, create_user):
        user = create_user(username="amina", password="OldPassword123!")
        auth_service.change_password(user, "OldPassword123!", "NewPassword456!")
        assert user.check_password("NewPassword456!") is True
        assert user.check_password("OldPassword123!") is False

    def test_wrong_current_password_raises_unauthorized(self, create_user):
        user = create_user(username="amina", password="OldPassword123!")
        with pytest.raises(UnauthorizedError):
            auth_service.change_password(user, "WrongPassword!", "NewPassword456!")
        # Password must be unchanged after a rejected attempt.
        assert user.check_password("OldPassword123!") is True
