# app/routes/auth_routes.py

from flask import Blueprint, jsonify, request

from app.auth.decorators import get_current_user, jwt_required
from app.auth.jwt import encode_token
from app.errors import ValidationAPIError
from app.schemas import user_schema
from app.services import auth_service
from app.validators import password_requirement_failures

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    """
    Register a new user account.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, email, password]
          properties:
            username:
              type: string
              minLength: 3
              maxLength: 50
            email:
              type: string
              format: email
            password:
              type: string
              description: 8+ chars, upper+lowercase, a number, and a special character.
            role:
              type: string
              enum: [farmer, expert]
              default: farmer
            language:
              type: string
              enum: [en, sw]
              default: en
              description: UI/AI language preference.
    responses:
      201:
        description: Account created.
        schema:
          type: object
          properties:
            token:
              type: string
            user:
              $ref: '#/definitions/User'
      422:
        description: Validation failed.
        schema:
          $ref: '#/definitions/Error'
      409:
        description: Username or email already taken.
        schema:
          $ref: '#/definitions/Error'
    """
    data = user_schema.load(request.get_json(silent=True) or {})
    user = auth_service.register_user(data)
    token = encode_token(user.id)
    return jsonify({"token": token, "user": user_schema.dump(user)}), 201


@auth_bp.post("/login")
def login():
    """
    Log in with a username or email, plus password.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [password]
          properties:
            username:
              type: string
            email:
              type: string
              format: email
            password:
              type: string
    responses:
      200:
        description: Authenticated.
        schema:
          type: object
          properties:
            token:
              type: string
            user:
              $ref: '#/definitions/User'
      401:
        description: Invalid credentials.
        schema:
          $ref: '#/definitions/Error'
    """
    payload = request.get_json(silent=True) or {}
    identifier = payload.get("username") or payload.get("email")
    password = payload.get("password")

    if not identifier or not password:
        raise ValidationAPIError("username or email, and password, are required.")

    user = auth_service.authenticate_user(identifier, password)
    token = encode_token(user.id)
    return jsonify({"token": token, "user": user_schema.dump(user)}), 200


@auth_bp.get("/me")
@jwt_required
def me():
    """
    Get the authenticated user's own account.
    ---
    tags:
      - Authentication
    security:
      - BearerAuth: []
    responses:
      200:
        description: The current user.
        schema:
          $ref: '#/definitions/User'
      401:
        description: Missing or invalid token.
        schema:
          $ref: '#/definitions/Error'
    """
    return jsonify(user_schema.dump(get_current_user())), 200


@auth_bp.post("/forgot-password")
def forgot_password():
    """
    Request a password reset email.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [email]
          properties:
            email:
              type: string
              format: email
    responses:
      200:
        description: >
          Always the same message whether or not the email is registered,
          to avoid leaking account existence.
        schema:
          type: object
          properties:
            message:
              type: string
    """
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    if not email:
        raise ValidationAPIError("email is required.")

    auth_service.request_password_reset(email)

    # Deliberately identical whether or not the email is registered --
    # see auth_service.request_password_reset for why.
    return jsonify(
        {"message": "If an account exists for that email, a reset link has been sent."}
    ), 200


@auth_bp.post("/reset-password")
def reset_password():
    """
    Reset a password using a mailed reset token.
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [token, password]
          properties:
            token:
              type: string
            password:
              type: string
    responses:
      200:
        description: Password reset.
        schema:
          type: object
          properties:
            message:
              type: string
      422:
        description: Missing fields, weak password, or invalid/expired token.
        schema:
          $ref: '#/definitions/Error'
    """
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    new_password = payload.get("password")

    if not token or not new_password:
        raise ValidationAPIError("token and password are required.")

    failures = password_requirement_failures(new_password)
    if failures:
        raise ValidationAPIError("Password does not meet the required strength.", payload={"password": failures})

    auth_service.reset_password(token, new_password)
    return jsonify({"message": "Password has been reset. You can now log in."}), 200


@auth_bp.put("/change-password")
@jwt_required
def change_password():
    """
    Auth required -- changes the caller's own password. Distinct from
    reset-password (which proves identity via a mailed token instead of
    a session): this proves identity via the CURRENT password, which is
    why it's the only auth endpoint that needs both the old and new
    values.
    ---
    tags:
      - Authentication
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [current_password, new_password]
          properties:
            current_password:
              type: string
            new_password:
              type: string
    responses:
      200:
        description: Password changed.
        schema:
          type: object
          properties:
            message:
              type: string
      401:
        description: Current password is incorrect, or missing/invalid token.
        schema:
          $ref: '#/definitions/Error'
      422:
        description: New password does not meet the required strength.
        schema:
          $ref: '#/definitions/Error'
    """
    payload = request.get_json(silent=True) or {}
    current_password = payload.get("current_password")
    new_password = payload.get("new_password")

    if not current_password or not new_password:
        raise ValidationAPIError("current_password and new_password are required.")

    failures = password_requirement_failures(new_password)
    if failures:
        raise ValidationAPIError("Password does not meet the required strength.", payload={"password": failures})

    auth_service.change_password(get_current_user(), current_password, new_password)
    return jsonify({"message": "Password changed."}), 200
