# app/errors.py

from flask import jsonify
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.extensions import db


class ApiError(Exception):
    """
    Base class for every deliberately-raised API error. Routes and
    services raise these instead of constructing Flask responses
    directly, keeping HTTP concerns out of the service layer and
    guaranteeing every error reaches the client through the same JSON
    envelope: {"error": "...", "details": {...optional...}}.
    """

    status_code = 400
    code = None

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        body = {"error": self.message}
        if self.payload:
            body["details"] = self.payload
        if self.code:
            body["code"] = self.code
        return body


class ValidationAPIError(ApiError):
    """Malformed or semantically invalid request data. HTTP 422."""

    status_code = 422


class UnauthorizedError(ApiError):
    """
    Missing, invalid, or expired credentials. HTTP 401.

    Also used for authenticated-but-wrong domain checks (e.g. login with
    the wrong password, change-password with the wrong current password)
    where the requester's own session token, if any, is completely valid
    -- only the submitted credential was wrong. See InvalidTokenError for
    the narrower "your session itself is dead" case.
    """

    status_code = 401


class InvalidTokenError(UnauthorizedError):
    """
    The Authorization header/token itself is missing, malformed, expired,
    or no longer valid (e.g. the account was deactivated). HTTP 401.

    Distinguished from UnauthorizedError by `code = "invalid_token"` so
    the frontend can tell "your session is dead, log in again" apart from
    an ordinary wrong-password-style 401 on an otherwise-valid session --
    see jwt_required in app/auth/decorators.py, the only place this is
    raised, and http.js's 401 handler on the frontend, the only place
    that reads `code`.
    """

    code = "invalid_token"


class ForbiddenError(ApiError):
    """Authenticated, but not allowed to perform this action. HTTP 403."""

    status_code = 403


class NotFoundError(ApiError):
    """The requested resource does not exist. HTTP 404."""

    status_code = 404


class ConflictError(ApiError):
    """The request conflicts with existing state (duplicates). HTTP 409."""

    status_code = 409


class RateLimitedError(ApiError):
    """Too many requests from this caller in the current window. HTTP 429."""

    status_code = 429


def register_error_handlers(app):
    """
    Attach handlers so every failure mode -- explicit ApiError subclasses,
    schema validation errors raised directly by a route, database
    integrity violations, and framework-level 404/405/500s -- returns the
    same JSON shape instead of Flask's default HTML error pages.
    """

    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(ValidationError)
    def handle_marshmallow_error(err):
        return jsonify({"error": "Validation failed.", "details": err.messages}), 422

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(err):
        db.session.rollback()
        return (
            jsonify({"error": "A record with conflicting unique data already exists."}),
            409,
        )

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({"error": "The requested resource was not found."}), 404

    @app.errorhandler(405)
    def handle_405(err):
        return jsonify({"error": "Method not allowed on this endpoint."}), 405

    @app.errorhandler(413)
    def handle_413(err):
        return jsonify({"error": "The uploaded file is too large."}), 413

    @app.errorhandler(500)
    def handle_500(err):
        db.session.rollback()
        return jsonify({"error": "An unexpected server error occurred."}), 500
