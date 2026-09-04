from app.extensions import db
from app.models.phone_identity import PhoneIdentity, normalize_phone_number
from app.services import ai_service
from app.services.ai_service import AIServiceUnavailableError
from app.services.text_formatting import strip_markdown_to_plain_text

SUPPORTED_LANGUAGES = ("en", "sw")

WELCOME_MENU = {
    "en": (
        "Welcome to AgriConnect\n"
        "1. Ask Farming Question\n"
        "2. Weather\n"
        "3. Market Prices\n"
        "4. Farming Tips\n"
        "5. Crop Problems\n"
        "6. Agricultural Experts\n"
        "7. Language"
    ),
    "sw": (
        "Karibu AgriConnect\n"
        "1. Uliza Swali la Kilimo\n"
        "2. Hali ya Hewa\n"
        "3. Bei za Soko\n"
        "4. Vidokezo vya Kilimo\n"
        "5. Matatizo ya Mazao\n"
        "6. Wataalamu wa Kilimo\n"
        "7. Lugha"
    ),
}

ASK_QUESTION_PROMPT = {
    "en": "Type your farming question:",
    "sw": "Andika swali lako la kilimo:",
}

CROP_PROBLEM_PROMPT = {
    "en": "Describe the crop problem:",
    "sw": "Eleza tatizo la zao lako:",
}

WEATHER_UNAVAILABLE = {
    "en": "Weather information is not yet available on AgriConnect. Please check back soon.",
    "sw": "Taarifa za hali ya hewa bado hazipatikani kwenye AgriConnect. Tafadhali angalia baadaye.",
}

MARKET_PRICES_UNAVAILABLE = {
    "en": "Market price information is not yet available on AgriConnect. Please check back soon.",
    "sw": "Taarifa za bei za soko bado hazipatikani kwenye AgriConnect. Tafadhali angalia baadaye.",
}

EXPERTS_INFO = {
    "en": (
        "AgriConnect connects farmers with verified agricultural experts in the app. "
        "Ask a farming question here for AI guidance, or open the app to reach an expert."
    ),
    "sw": (
        "AgriConnect huunganisha wakulima na wataalamu wa kilimo walioidhinishwa kwenye programu. "
        "Uliza swali la kilimo hapa kwa mwongozo wa AI, au fungua programu kufikia mtaalamu."
    ),
}

FARMING_TIP_PROMPT = {
    "en": "Give one short, practical farming tip for a smallholder farmer.",
    "sw": "Toa ushauri mmoja mfupi na wa vitendo wa kilimo kwa mkulima mdogo.",
}

LANGUAGE_MENU = {
    "en": "Choose language:\n1. English\n2. Kiswahili",
    "sw": "Chagua lugha:\n1. Kiingereza\n2. Kiswahili",
}

LANGUAGE_SET_CONFIRMATION = {
    "en": "Language set to English.",
    "sw": "Lugha imewekwa kuwa Kiswahili.",
}

INVALID_INPUT_MESSAGE = {
    "en": "Invalid option. Please try again.",
    "sw": "Chaguo batili. Tafadhali jaribu tena.",
}

EMPTY_INPUT_MESSAGE = {
    "en": "We didn't receive your message. Please try again.",
    "sw": "Hatujapokea ujumbe wako. Tafadhali jaribu tena.",
}

AI_UNAVAILABLE_MESSAGE = {
    "en": "The AI assistant is temporarily unavailable. Please try again shortly.",
    "sw": "Msaidizi wa AI haupatikani kwa sasa. Tafadhali jaribu tena baadaye.",
}

SHORT_ANSWER_SUFFIX = {
    "en": " Reply in one short paragraph, plain text, under 60 words -- this will be read on a basic phone screen.",
    "sw": " Jibu kwa aya moja fupi, maandishi ya kawaida, chini ya maneno 60 -- hii itasomwa kwenye simu ya kawaida.",
}


def _language_or_default(language):
    return language if language in SUPPORTED_LANGUAGES else "en"


def resolve_phone_identity(raw_phone_number):
    phone_number = normalize_phone_number(raw_phone_number)
    identity = PhoneIdentity.query.filter_by(phone_number=phone_number).first()
    if identity is None:
        identity = PhoneIdentity(phone_number=phone_number)
        db.session.add(identity)
        db.session.commit()
    return identity


def ask_short_answer(question, language):
    language = _language_or_default(language)
    suffix = SHORT_ANSWER_SUFFIX[language]
    messages = [{"role": "user", "content": f"{question.strip()}{suffix}"}]
    try:
        reply = ai_service.ask_assistant(messages, language=language)
    except AIServiceUnavailableError:
        return AI_UNAVAILABLE_MESSAGE[language]
    return strip_markdown_to_plain_text(reply)


def handle_sms(raw_phone_number, message_text, max_input_length):
    identity = resolve_phone_identity(raw_phone_number)
    language = _language_or_default(identity.language)
    text = (message_text or "").strip()

    if not text:
        return EMPTY_INPUT_MESSAGE[language]

    text = text[:max_input_length]
    return ask_short_answer(text, language)


def _parse_ussd_steps(text):
    text = (text or "").strip()
    return text.split("*") if text else []


def _ussd_response(continue_session, message, max_response_length):
    prefix = "CON " if continue_session else "END "
    budget = max(max_response_length - len(prefix), 0)
    plain = strip_markdown_to_plain_text(message)
    if len(plain) > budget:
        ellipsis = "..."
        cut = max(budget - len(ellipsis), 0)
        plain = plain[:cut].rstrip() + ellipsis
    return prefix + plain


def handle_ussd(raw_phone_number, text, max_input_length, max_response_length):
    identity = resolve_phone_identity(raw_phone_number)
    language = _language_or_default(identity.language)
    steps = _parse_ussd_steps(text)

    if not steps:
        return _ussd_response(True, WELCOME_MENU[language], max_response_length)

    first = steps[0]

    if first in ("1", "5"):
        if len(steps) == 1:
            prompt = ASK_QUESTION_PROMPT if first == "1" else CROP_PROBLEM_PROMPT
            return _ussd_response(True, prompt[language], max_response_length)
        question = "*".join(steps[1:]).strip()
        if not question:
            return _ussd_response(False, EMPTY_INPUT_MESSAGE[language], max_response_length)
        question = question[:max_input_length]
        reply = ask_short_answer(question, language)
        return _ussd_response(False, reply, max_response_length)

    if first == "2":
        return _ussd_response(False, WEATHER_UNAVAILABLE[language], max_response_length)

    if first == "3":
        return _ussd_response(False, MARKET_PRICES_UNAVAILABLE[language], max_response_length)

    if first == "4":
        reply = ask_short_answer(FARMING_TIP_PROMPT[language], language)
        return _ussd_response(False, reply, max_response_length)

    if first == "6":
        return _ussd_response(False, EXPERTS_INFO[language], max_response_length)

    if first == "7":
        if len(steps) == 1:
            return _ussd_response(True, LANGUAGE_MENU[language], max_response_length)
        choice = steps[1].strip()
        if choice == "1":
            identity.language = "en"
        elif choice == "2":
            identity.language = "sw"
        else:
            return _ussd_response(False, INVALID_INPUT_MESSAGE[language], max_response_length)
        db.session.commit()
        return _ussd_response(False, LANGUAGE_SET_CONFIRMATION[identity.language], max_response_length)

    return _ussd_response(False, INVALID_INPUT_MESSAGE[language], max_response_length)
