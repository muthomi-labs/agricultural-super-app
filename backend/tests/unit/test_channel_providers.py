import pytest

from app.services import channel_providers
from app.services.channel_providers import (
    ChannelProviderError,
    NullSmsProvider,
    NullSpeechToTextProvider,
    NullTextToSpeechProvider,
    SmsProvider,
    SpeechToTextProvider,
    TextToSpeechProvider,
    get_sms_provider,
    get_speech_to_text_provider,
    get_text_to_speech_provider,
)


class TestAbstractInterfaces:
    def test_sms_provider_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            SmsProvider()

    def test_speech_to_text_provider_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            SpeechToTextProvider()

    def test_text_to_speech_provider_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            TextToSpeechProvider()


class TestNullSmsProvider:
    def test_is_an_sms_provider(self):
        assert isinstance(NullSmsProvider(), SmsProvider)

    def test_send_raises_channel_provider_error(self):
        with pytest.raises(ChannelProviderError) as exc_info:
            NullSmsProvider().send("+254712345678", "hello")
        assert "not configured" in exc_info.value.public_message.lower()

    def test_send_error_carries_no_credentials_or_message_content(self):
        with pytest.raises(ChannelProviderError) as exc_info:
            NullSmsProvider().send("+254712345678", "a secret farming question")
        assert "+254712345678" not in exc_info.value.public_message
        assert "secret farming question" not in exc_info.value.public_message
        assert "+254712345678" not in exc_info.value.log_message
        assert "secret farming question" not in exc_info.value.log_message


class TestNullSpeechToTextProvider:
    def test_is_a_speech_to_text_provider(self):
        assert isinstance(NullSpeechToTextProvider(), SpeechToTextProvider)

    def test_transcribe_raises_channel_provider_error(self):
        with pytest.raises(ChannelProviderError) as exc_info:
            NullSpeechToTextProvider().transcribe(b"fake-audio-bytes")
        assert "not configured" in exc_info.value.public_message.lower()


class TestNullTextToSpeechProvider:
    def test_is_a_text_to_speech_provider(self):
        assert isinstance(NullTextToSpeechProvider(), TextToSpeechProvider)

    def test_synthesize_raises_channel_provider_error(self):
        with pytest.raises(ChannelProviderError) as exc_info:
            NullTextToSpeechProvider().synthesize("hello")
        assert "not configured" in exc_info.value.public_message.lower()


class TestGetSmsProvider:
    def test_defaults_to_null(self):
        assert isinstance(get_sms_provider({}), NullSmsProvider)

    def test_explicit_null_selects_null(self):
        assert isinstance(get_sms_provider({"SMS_PROVIDER": "null"}), NullSmsProvider)

    def test_is_case_insensitive_and_trims_whitespace(self):
        assert isinstance(get_sms_provider({"SMS_PROVIDER": "  NULL  "}), NullSmsProvider)

    def test_unknown_provider_raises_instead_of_crashing(self):
        with pytest.raises(ChannelProviderError) as exc_info:
            get_sms_provider({"SMS_PROVIDER": "africastalking"})
        assert "misconfigured" in exc_info.value.public_message.lower()
        assert "africastalking" in exc_info.value.log_message.lower()

    def test_never_touches_network_for_any_configured_value(self, monkeypatch):
        def _fail_if_called(*args, **kwargs):
            raise AssertionError("get_sms_provider must never perform network I/O")

        monkeypatch.setattr("urllib.request.urlopen", _fail_if_called)
        get_sms_provider({})
        with pytest.raises(ChannelProviderError):
            get_sms_provider({"SMS_PROVIDER": "twilio"})


class TestGetSpeechToTextProvider:
    def test_defaults_to_null(self):
        assert isinstance(get_speech_to_text_provider({}), NullSpeechToTextProvider)

    def test_unknown_provider_raises_instead_of_crashing(self):
        with pytest.raises(ChannelProviderError):
            get_speech_to_text_provider({"STT_PROVIDER": "google"})


class TestGetTextToSpeechProvider:
    def test_defaults_to_null(self):
        assert isinstance(get_text_to_speech_provider({}), NullTextToSpeechProvider)

    def test_unknown_provider_raises_instead_of_crashing(self):
        with pytest.raises(ChannelProviderError):
            get_text_to_speech_provider({"TTS_PROVIDER": "elevenlabs"})


class TestModuleHasNoNetworkImports:
    def test_module_does_not_import_urllib_request(self):
        assert not hasattr(channel_providers, "urllib")
