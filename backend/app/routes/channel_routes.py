import hmac
from functools import wraps

from flask import Blueprint, Response, current_app, jsonify, request

from app.errors import RateLimitedError, UnauthorizedError, ValidationAPIError
from app.models.phone_identity import normalize_phone_number
from app.services import channel_service
from app.services.channel_providers import ChannelProviderError, get_sms_provider
from app.services.channel_rate_limiter import check_rate_limit

channels_bp = Blueprint("channels", __name__, url_prefix="/api/channels")


def channel_webhook_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        configured_secret = current_app.config.get("CHANNEL_WEBHOOK_SECRET")
        if not configured_secret:
            raise UnauthorizedError("This channel is not configured.")
        provided_secret = request.headers.get("X-Channel-Webhook-Secret") or request.args.get("secret")
        if not provided_secret or not hmac.compare_digest(provided_secret, configured_secret):
            raise UnauthorizedError("Invalid webhook credentials.")
        return view_func(*args, **kwargs)

    return wrapper


def _request_value(name):
    if request.form:
        value = request.form.get(name)
        if value is not None:
            return value
    body = request.get_json(silent=True) or {}
    return body.get(name)


def _enforce_rate_limit(phone_number):
    allowed = check_rate_limit(
        phone_number,
        max_requests=current_app.config["CHANNEL_RATE_LIMIT_MAX_REQUESTS"],
        window_seconds=current_app.config["CHANNEL_RATE_LIMIT_WINDOW_SECONDS"],
    )
    if not allowed:
        raise RateLimitedError("Too many requests. Please try again shortly.")


@channels_bp.post("/sms")
@channel_webhook_required
def receive_sms():
    """
    ---
    tags:
      - Channels
    parameters:
      - in: header
        name: X-Channel-Webhook-Secret
        type: string
        required: false
      - in: query
        name: secret
        type: string
        required: false
      - in: body
        name: body
        schema:
          type: object
          properties:
            from:
              type: string
            text:
              type: string
    responses:
      200:
        description: SMS processed; `delivered` reflects whether an SMS provider actually sent the reply.
      401:
        description: Missing/invalid webhook secret, or the channel is not configured.
      422:
        description: Missing phone number or malformed input.
      429:
        description: Rate limit exceeded for this phone number.
    """
    raw_phone_number = _request_value("from")
    if not raw_phone_number:
        raise ValidationAPIError("A sender phone number is required.")

    try:
        phone_number = normalize_phone_number(raw_phone_number)
    except ValueError:
        raise ValidationAPIError("Invalid phone number.")

    _enforce_rate_limit(phone_number)

    text = _request_value("text") or ""
    max_input_length = current_app.config["CHANNEL_MAX_INPUT_LENGTH"]
    reply = channel_service.handle_sms(phone_number, text, max_input_length)

    sms_provider = get_sms_provider(current_app.config)
    try:
        sms_provider.send(phone_number, reply)
        delivered = True
        provider_error = None
    except ChannelProviderError as err:
        delivered = False
        provider_error = err.public_message
        current_app.logger.warning("channel_sms provider_send_failed: %s", err.log_message)

    return (
        jsonify(
            {
                "reply": reply,
                "delivered": delivered,
                "provider_error": provider_error,
            }
        ),
        200,
    )


@channels_bp.post("/ussd")
@channel_webhook_required
def receive_ussd():
    """
    ---
    tags:
      - Channels
    parameters:
      - in: header
        name: X-Channel-Webhook-Secret
        type: string
        required: false
      - in: query
        name: secret
        type: string
        required: false
      - in: body
        name: body
        schema:
          type: object
          properties:
            phoneNumber:
              type: string
            text:
              type: string
    responses:
      200:
        description: Plain-text CON/END USSD response.
      401:
        description: Missing/invalid webhook secret, or the channel is not configured.
      422:
        description: Missing phone number.
      429:
        description: Rate limit exceeded for this phone number.
    """
    raw_phone_number = _request_value("phoneNumber")
    if not raw_phone_number:
        raise ValidationAPIError("A phone number is required.")

    try:
        phone_number = normalize_phone_number(raw_phone_number)
    except ValueError:
        raise ValidationAPIError("Invalid phone number.")

    _enforce_rate_limit(phone_number)

    text = _request_value("text") or ""
    max_input_length = current_app.config["CHANNEL_MAX_INPUT_LENGTH"]
    max_response_length = current_app.config["USSD_MAX_RESPONSE_LENGTH"]
    reply = channel_service.handle_ussd(phone_number, text, max_input_length, max_response_length)

    return Response(reply, mimetype="text/plain")


@channels_bp.post("/voice")
@channel_webhook_required
def receive_voice():
    """
    ---
    tags:
      - Channels
    parameters:
      - in: header
        name: X-Channel-Webhook-Secret
        type: string
        required: false
      - in: query
        name: secret
        type: string
        required: false
    responses:
      501:
        description: Voice is not yet configured (no speech-to-text/text-to-speech provider).
      401:
        description: Missing/invalid webhook secret, or the channel is not configured.
    """
    return (
        jsonify(
            {
                "error": "Voice is not yet available. Speech-to-text and text-to-speech "
                "providers are not configured on this server."
            }
        ),
        501,
    )
