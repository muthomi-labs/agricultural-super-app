# app/services/email_service.py

"""
Real SMTP email delivery via Flask-Mail. Wired up for password-reset
emails and admin new-signup notifications (see auth_service), but
send_email() itself is generic -- any future transactional email
reuses this rather than a new integration.

Two distinct failure modes, deliberately not collapsed into one:
  - EmailNotConfiguredError: MAIL_SERVER/MAIL_USERNAME/MAIL_PASSWORD
    aren't all set. Nothing was attempted -- this is a deployment
    configuration gap, not a delivery failure.
  - EmailDeliveryError: configuration was present, but the actual SMTP
    send raised (auth rejected, network unreachable, etc).

Callers (auth_service) decide how to handle each; this module never
silently pretends a send succeeded when it didn't.
"""

import html

from flask import current_app
from flask_mail import Message

from app.extensions import mail

APP_NAME = "AgriConnect"


class EmailNotConfiguredError(Exception):
    """MAIL_SERVER/MAIL_USERNAME/MAIL_PASSWORD aren't all set."""


class EmailDeliveryError(Exception):
    """Flask-Mail/smtplib raised while actually trying to send."""


def is_configured(config):
    return bool(config.get("MAIL_SERVER") and config.get("MAIL_USERNAME") and config.get("MAIL_PASSWORD"))


def send_email(to, subject, html_body, text_body):
    """
    Send a single email. Raises EmailNotConfiguredError or
    EmailDeliveryError on failure -- never returns a falsy "it didn't
    work" value, so a caller can't accidentally ignore a failed send.
    """
    config = current_app.config
    if not is_configured(config):
        raise EmailNotConfiguredError(
            "Email is not configured: MAIL_SERVER, MAIL_USERNAME, and MAIL_PASSWORD must all be set."
        )

    message = Message(subject=subject, recipients=[to], body=text_body, html=html_body)
    try:
        mail.send(message)
    except Exception as err:  # smtplib raises several distinct exception types
        raise EmailDeliveryError(str(err)) from err


def password_reset_email(username, reset_url, expires_in_minutes):
    """Returns (html_body, text_body) for the password reset email."""
    text_body = (
        f"Hi {username},\n\n"
        f"We received a request to reset the password for your {APP_NAME} account.\n\n"
        f"Reset your password using the link below:\n{reset_url}\n\n"
        f"This link expires in {expires_in_minutes} minutes and can only be used once.\n\n"
        "If you didn't request this, you can safely ignore this email -- your password "
        "will not be changed.\n\n"
        f"-- The {APP_NAME} Team"
    )

    username = html.escape(username)

    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f7f5f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f5f0;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#ffffff;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:32px 32px 0;">
                <p style="margin:0 0 24px;font-size:20px;font-weight:700;color:#1c1a17;">
                  Agri<span style="color:#2f6b3a;">Connect</span>
                </p>
                <h1 style="margin:0 0 16px;font-size:20px;color:#1c1a17;">Reset your password</h1>
                <p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#6b655c;">
                  Hi {username},
                </p>
                <p style="margin:0 0 24px;font-size:14px;line-height:1.6;color:#6b655c;">
                  We received a request to reset the password for your {APP_NAME} account. Click the
                  button below to choose a new one.
                </p>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:0 32px 24px;">
                <a href="{reset_url}"
                   style="display:inline-block;padding:12px 32px;background-color:#2f6b3a;color:#ffffff;
                          text-decoration:none;border-radius:8px;font-size:15px;font-weight:600;">
                  Reset Password
                </a>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 8px;">
                <p style="margin:0 0 16px;font-size:13px;line-height:1.6;color:#6b655c;">
                  Or copy and paste this link into your browser:<br>
                  <a href="{reset_url}" style="color:#2f6b3a;word-break:break-all;">{reset_url}</a>
                </p>
                <p style="margin:0 0 16px;font-size:13px;line-height:1.6;color:#6b655c;">
                  This link expires in <strong>{expires_in_minutes} minutes</strong> and can only be
                  used once.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px 32px;border-top:1px solid #efece4;">
                <p style="margin:16px 0 0;font-size:12px;line-height:1.6;color:#9e968a;">
                  If you didn't request this, you can safely ignore this email -- your password will
                  not be changed.
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    return html_body, text_body


def new_signup_email(username, email, role, manage_url):
    """Returns (html_body, text_body) notifying an admin of a new signup."""
    text_body = (
        f"A new user just registered on {APP_NAME}.\n\n"
        f"Username: {username}\n"
        f"Email: {email}\n"
        f"Role: {role}\n\n"
        f"Manage this user (e.g. promote to admin) here:\n{manage_url}\n\n"
        f"-- The {APP_NAME} Team"
    )

    username = html.escape(username)
    email = html.escape(email)
    role = html.escape(role)

    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background-color:#f7f5f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7f5f0;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:480px;background-color:#ffffff;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="padding:32px 32px 0;">
                <p style="margin:0 0 24px;font-size:20px;font-weight:700;color:#1c1a17;">
                  Agri<span style="color:#2f6b3a;">Connect</span>
                </p>
                <h1 style="margin:0 0 16px;font-size:20px;color:#1c1a17;">New user signed up</h1>
                <p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#6b655c;">
                  A new user just registered on {APP_NAME}:
                </p>
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
                  <tr>
                    <td style="padding:4px 0;font-size:14px;color:#6b655c;width:90px;">Username</td>
                    <td style="padding:4px 0;font-size:14px;color:#1c1a17;font-weight:600;">{username}</td>
                  </tr>
                  <tr>
                    <td style="padding:4px 0;font-size:14px;color:#6b655c;">Email</td>
                    <td style="padding:4px 0;font-size:14px;color:#1c1a17;font-weight:600;">{email}</td>
                  </tr>
                  <tr>
                    <td style="padding:4px 0;font-size:14px;color:#6b655c;">Role</td>
                    <td style="padding:4px 0;font-size:14px;color:#1c1a17;font-weight:600;">{role}</td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:0 32px 24px;">
                <a href="{manage_url}"
                   style="display:inline-block;padding:12px 32px;background-color:#2f6b3a;color:#ffffff;
                          text-decoration:none;border-radius:8px;font-size:15px;font-weight:600;">
                  Manage this user
                </a>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""
    return html_body, text_body
