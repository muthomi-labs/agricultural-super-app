import pytest

from app.models.phone_identity import PhoneIdentity
from app.services import ai_service, channel_service
from app.services.ai_service import AIServiceUnavailableError

MAX_INPUT = 500
MAX_USSD = 182


@pytest.fixture
def fake_ask_assistant(monkeypatch):
    def _install(reply=None, error=None):
        calls = []

        def _fake(messages, language=None):
            calls.append({"messages": messages, "language": language})
            if error is not None:
                raise error
            return reply

        monkeypatch.setattr(ai_service, "ask_assistant", _fake)
        return calls

    return _install


class TestResolvePhoneIdentity:
    def test_creates_a_new_identity(self, db):
        identity = channel_service.resolve_phone_identity("0712345678")
        assert identity.phone_number == "+254712345678"
        assert identity.user_id is None
        assert identity.language == "en"

    def test_returns_existing_identity_on_repeat_calls(self, db):
        first = channel_service.resolve_phone_identity("0712345678")
        second = channel_service.resolve_phone_identity("+254712345678")
        assert first.id == second.id
        assert PhoneIdentity.query.count() == 1


class TestAskShortAnswer:
    def test_appends_short_answer_suffix_and_strips_markdown(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="**Water** daily.")
        result = channel_service.ask_short_answer("How often should I water?", "en")
        assert result == "Water daily."
        assert calls[0]["language"] == "en"
        assert "How often should I water?" in calls[0]["messages"][0]["content"]
        assert "basic phone screen" in calls[0]["messages"][0]["content"]

    def test_uses_kiswahili_suffix_for_kiswahili_language(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="Maji kila siku.")
        channel_service.ask_short_answer("Nimwagilie mara ngapi?", "sw")
        assert "simu ya kawaida" in calls[0]["messages"][0]["content"]

    def test_falls_back_to_english_for_unknown_language(self, db, fake_ask_assistant):
        fake_ask_assistant(reply="ok")
        result = channel_service.ask_short_answer("hi", "fr")
        assert result == "ok"

    def test_ai_unavailable_returns_localized_message_not_internal_detail(self, db, fake_ask_assistant):
        fake_ask_assistant(error=AIServiceUnavailableError("internal detail should not leak"))
        result_en = channel_service.ask_short_answer("hi", "en")
        assert result_en == channel_service.AI_UNAVAILABLE_MESSAGE["en"]

        fake_ask_assistant(error=AIServiceUnavailableError("internal detail should not leak"))
        result_sw = channel_service.ask_short_answer("hi", "sw")
        assert result_sw == channel_service.AI_UNAVAILABLE_MESSAGE["sw"]


class TestHandleSms:
    def test_empty_message_returns_localized_prompt(self, db):
        result = channel_service.handle_sms("0712345678", "   ", MAX_INPUT)
        assert result == channel_service.EMPTY_INPUT_MESSAGE["en"]

    def test_processes_a_real_question_via_ask_assistant(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="Water twice a week.")
        result = channel_service.handle_sms("0712345678", "How often should I water tomatoes?", MAX_INPUT)
        assert result == "Water twice a week."
        assert len(calls) == 1

    def test_truncates_overlong_input(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="ok")
        long_text = "a" * 1000
        channel_service.handle_sms("0712345678", long_text, max_input_length=50)
        sent_content = calls[0]["messages"][0]["content"]
        assert len(sent_content) < 200

    def test_uses_the_phone_identitys_saved_language(self, db, fake_ask_assistant):
        identity = channel_service.resolve_phone_identity("0712345678")
        identity.language = "sw"
        db.session.commit()

        calls = fake_ask_assistant(reply="ok")
        channel_service.handle_sms("0712345678", "Swali langu", MAX_INPUT)
        assert calls[0]["language"] == "sw"


class TestHandleUssdWelcomeMenu:
    def test_empty_text_shows_welcome_menu_in_english_by_default(self, db):
        result = channel_service.handle_ussd("0712345678", "", MAX_INPUT, MAX_USSD)
        assert result.startswith("CON ")
        assert "AgriConnect" in result
        assert "1. Ask Farming Question" in result

    def test_welcome_menu_respects_saved_language(self, db):
        identity = channel_service.resolve_phone_identity("0712345678")
        identity.language = "sw"
        db.session.commit()

        result = channel_service.handle_ussd("0712345678", "", MAX_INPUT, MAX_USSD)
        assert result.startswith("CON ")
        assert "Karibu AgriConnect" in result


class TestHandleUssdFarmingQuestion:
    def test_option_1_prompts_for_a_question(self, db):
        result = channel_service.handle_ussd("0712345678", "1", MAX_INPUT, MAX_USSD)
        assert result == "CON Type your farming question:"

    def test_option_1_with_question_calls_ai_and_ends_session(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="Water deeply once a week.")
        result = channel_service.handle_ussd(
            "0712345678", "1*How often should I water tomatoes", MAX_INPUT, MAX_USSD
        )
        assert result == "END Water deeply once a week."
        assert len(calls) == 1

    def test_option_1_with_empty_question_does_not_call_ai(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="should not be used")
        result = channel_service.handle_ussd("0712345678", "1*   ", MAX_INPUT, MAX_USSD)
        assert result.startswith("END ")
        assert len(calls) == 0


class TestHandleUssdCropProblems:
    def test_option_5_prompts_for_a_description(self, db):
        result = channel_service.handle_ussd("0712345678", "5", MAX_INPUT, MAX_USSD)
        assert result == "CON Describe the crop problem:"

    def test_option_5_with_description_calls_ai(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="Likely fall armyworm.")
        result = channel_service.handle_ussd("0712345678", "5*mahindi yana wadudu", MAX_INPUT, MAX_USSD)
        assert result == "END Likely fall armyworm."
        assert len(calls) == 1


class TestHandleUssdWeatherAndMarket:
    def test_weather_is_explicitly_unavailable_not_fabricated(self, db):
        result = channel_service.handle_ussd("0712345678", "2", MAX_INPUT, MAX_USSD)
        assert result.startswith("END ")
        assert "not yet available" in result

    def test_market_prices_is_explicitly_unavailable_not_fabricated(self, db):
        result = channel_service.handle_ussd("0712345678", "3", MAX_INPUT, MAX_USSD)
        assert result.startswith("END ")
        assert "not yet available" in result


class TestHandleUssdFarmingTips:
    def test_option_4_asks_ai_for_a_tip(self, db, fake_ask_assistant):
        calls = fake_ask_assistant(reply="Rotate your crops each season.")
        result = channel_service.handle_ussd("0712345678", "4", MAX_INPUT, MAX_USSD)
        assert result == "END Rotate your crops each season."
        assert "practical farming tip" in calls[0]["messages"][0]["content"]


class TestHandleUssdExperts:
    def test_option_6_returns_informational_message(self, db):
        result = channel_service.handle_ussd("0712345678", "6", MAX_INPUT, MAX_USSD)
        assert result.startswith("END ")
        assert "AgriConnect" in result


class TestHandleUssdLanguage:
    def test_option_7_shows_language_menu(self, db):
        result = channel_service.handle_ussd("0712345678", "7", MAX_INPUT, MAX_USSD)
        assert result == "CON Choose language:\n1. English\n2. Kiswahili"

    def test_option_7_1_sets_english(self, db):
        result = channel_service.handle_ussd("0712345678", "7*1", MAX_INPUT, MAX_USSD)
        assert result == "END Language set to English."
        identity = channel_service.resolve_phone_identity("0712345678")
        assert identity.language == "en"

    def test_option_7_2_sets_kiswahili(self, db):
        result = channel_service.handle_ussd("0712345678", "7*2", MAX_INPUT, MAX_USSD)
        assert result == "END Lugha imewekwa kuwa Kiswahili."
        identity = channel_service.resolve_phone_identity("0712345678")
        assert identity.language == "sw"

    def test_option_7_invalid_choice(self, db):
        result = channel_service.handle_ussd("0712345678", "7*9", MAX_INPUT, MAX_USSD)
        assert result.startswith("END ")
        assert "Invalid" in result


class TestHandleUssdInvalidInput:
    def test_unknown_top_level_option(self, db):
        result = channel_service.handle_ussd("0712345678", "99", MAX_INPUT, MAX_USSD)
        assert result.startswith("END ")
        assert "Invalid" in result

    def test_garbage_input(self, db):
        result = channel_service.handle_ussd("0712345678", "abc", MAX_INPUT, MAX_USSD)
        assert result.startswith("END ")
        assert "Invalid" in result


class TestHandleUssdResponseLengthEnforcement:
    def test_response_is_truncated_to_configured_max_length(self, db, fake_ask_assistant):
        long_reply = "This is a very long AI reply. " * 20
        fake_ask_assistant(reply=long_reply)
        small_max = 40
        result = channel_service.handle_ussd(
            "0712345678", "1*question", MAX_INPUT, small_max
        )
        assert len(result) <= small_max
        assert result.startswith("END ")
        assert result.endswith("...")

    def test_short_response_is_not_truncated(self, db, fake_ask_assistant):
        fake_ask_assistant(reply="Short.")
        result = channel_service.handle_ussd("0712345678", "1*question", MAX_INPUT, MAX_USSD)
        assert result == "END Short."
        assert not result.endswith("...")


class TestHandleUssdRepeatedRequestsAreSafe:
    def test_repeating_the_same_accumulated_text_is_idempotent(self, db, fake_ask_assistant):
        fake_ask_assistant(reply="Once a week.")
        first = channel_service.handle_ussd("0712345678", "1*How often", MAX_INPUT, MAX_USSD)
        second = channel_service.handle_ussd("0712345678", "1*How often", MAX_INPUT, MAX_USSD)
        assert first == second
        assert PhoneIdentity.query.count() == 1
