# app/services/auth_service.py

import hashlib
import secrets
from datetime import datetime, timedelta

from flask import current_app

from app.errors import ConflictError, UnauthorizedError, ValidationAPIError
from app.extensions import db
from app.models import PasswordResetToken, User
from app.services import email_service
from app.services.email_service import EmailDeliveryError, EmailNotConfiguredError


def register_user(data):
    """
    Create a new User from validated schema output.

    `data` is the dict returned by UserSchema.load(): plaintext password
    under the key "password_hash" (see user_schema.py for why), plus
    username/email/role. We pre-check uniqueness for a clean 409 with a
    specific message; the DB-level UNIQUE constraint remains the actual
    source of truth against races (see app/errors.py's IntegrityError
    handler).
    """
    plaintext_password = data.pop("password_hash")

    if db.session.query(User).filter_by(username=data["username"]).first():
        raise ConflictError("Username is already taken.")
    if db.session.query(User).filter_by(email=data["email"]).first():
        raise ConflictError("Email is already registered.")

    user = User(
        username=data["username"],
        email=data["email"],
        role=data.get("role", "farmer"),
        language=data.get("language", "en"),
    )
    user.set_password(plaintext_password)

    db.session.add(user)
    db.session.commit()
    _notify_admins_of_new_signup(user)
    return user


def _notify_admins_of_new_signup(user):
    """
    Best-effort email to every address in ADMIN_NOTIFICATION_EMAILS when
    a new user registers, so an admin can promote them without having to
    remember to check the dashboard. Deliberately never raises --
    registration has already succeeded and committed by the time this
    runs, so a notification failure (or nobody being configured to
    notify) must never surface as a registration error.
    """
    admin_emails = current_app.config.get("ADMIN_NOTIFICATION_EMAILS") or []
    if not admin_emails:
        return

    manage_url = f"{current_app.config['FRONTEND_URL']}/admin/users?search={user.username}"
    html_body, text_body = email_service.new_signup_email(
        username=user.username,
        email=user.email,
        role=user.role,
        manage_url=manage_url,
    )

    for admin_email in admin_emails:
        try:
            email_service.send_email(
                to=admin_email,
                subject=f"New AgriConnect signup: {user.username}",
                html_body=html_body,
                text_body=text_body,
            )
        except EmailNotConfiguredError:
            current_app.logger.error(
                "New signup (user_id=%s) but email is not configured "
                "(MAIL_SERVER/MAIL_USERNAME/MAIL_PASSWORD). No admin notification was sent.",
                user.id,
            )
            return  # config gap applies to every recipient -- no point retrying per-address
        except EmailDeliveryError as err:
            current_app.logger.error(
                "New signup (user_id=%s) but the admin notification to %s failed to send: %s",
                user.id,
                admin_email,
                err,
            )


def authenticate_user(identifier, password):
    """
    Verify credentials for login. `identifier` may be a username or an
    email -- accepting either is a small UX kindness with no security
    cost, since both are already unique, indexed columns.

    Deliberately returns the same error message for "no such user" and
    "wrong password" -- distinguishing them lets an attacker enumerate
    valid usernames/emails.
    """
    user = (
        db.session.query(User)
        .filter((User.username == identifier) | (User.email == identifier))
        .first()
    )
    if user is None or not user.check_password(password):
        raise UnauthorizedError("Invalid username/email or password.")
    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.")
    return user


def _hash_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def request_password_reset(email):
    """
    Issue a password reset token for the account matching `email`, if one
    exists, and email the reset link to that address. Deliberately
    silent (no exception, no signal in the return value) when the email
    is unknown -- the route always returns the same generic response
    either way, so this can't be used to enumerate registered emails.

    That same anti-enumeration guarantee is *why* email failures below
    are only ever logged, never raised: if a delivery failure changed
    the route's response, an attacker could distinguish "this address
    has an account (so a send was attempted)" from "it doesn't" purely
    by whether they see an error -- even without ever reading the
    resulting email. So this function's return value/exceptions are
    identical whether the address is unknown, the address is known but
    email isn't configured, or the address is known but the SMTP send
    itself failed. Every one of those is still visible server-side (see
    the logging below), just never surfaced to the caller.
    """
    user = db.session.query(User).filter_by(email=email).first()
    if user is None:
        return

    raw_token = secrets.token_urlsafe(32)
    expires_in_seconds = current_app.config["PASSWORD_RESET_TOKEN_EXPIRES_SECONDS"]
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    db.session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
        )
    )
    db.session.commit()

    reset_url = f"{current_app.config['FRONTEND_URL']}/reset-password?token={raw_token}"
    html_body, text_body = email_service.password_reset_email(
        username=user.username,
        reset_url=reset_url,
        expires_in_minutes=max(1, expires_in_seconds // 60),
    )

    try:
        email_service.send_email(
            to=user.email,
            subject="Reset your AgriConnect password",
            html_body=html_body,
            text_body=text_body,
        )
    except EmailNotConfiguredError:
        # A deployment/config gap, not a per-request failure -- logged
        # without the token or reset_url, which must never appear in
        # logs (a log line is not the secure channel a mailed link is).
        current_app.logger.error(
            "Password reset requested for user_id=%s but email is not configured "
            "(MAIL_SERVER/MAIL_USERNAME/MAIL_PASSWORD). No email was sent.",
            user.id,
        )
    except EmailDeliveryError as err:
        current_app.logger.error(
            "Password reset requested for user_id=%s but the email failed to send: %s",
            user.id,
            err,
        )


def reset_password(raw_token, new_password):
    """
    Consume a password reset token: verify it's known, unused, and
    unexpired, then set the new password and mark the token used so it
    can never be replayed.
    """
    record = (
        db.session.query(PasswordResetToken)
        .filter_by(token_hash=_hash_token(raw_token))
        .first()
    )
    if (
        record is None
        or record.used_at is not None
        or record.expires_at < datetime.utcnow()
    ):
        raise ValidationAPIError("This password reset link is invalid or has expired.")

    user = db.session.get(User, record.user_id)
    user.set_password(new_password)
    record.used_at = datetime.utcnow()
    db.session.commit()


def change_password(current_user, current_password, new_password):
    """
    Change the caller's own password, proving identity via the current
    password (unlike reset_password, which proves identity via a mailed
    token). Password strength is validated by the route before this is
    called -- this function trusts its input, consistent with every
    other service function in this module.
    """
    if not current_user.check_password(current_password):
        raise UnauthorizedError("Current password is incorrect.")

    current_user.set_password(new_password)
    db.session.commit()
