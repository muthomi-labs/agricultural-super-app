from abc import ABC, abstractmethod


class ChannelProviderError(Exception):
    def __init__(self, public_message, log_message=None):
        super().__init__(public_message)
        self.public_message = public_message
        self.log_message = log_message or public_message


class SmsProvider(ABC):
    @abstractmethod
    def send(self, phone_number, text):
        raise NotImplementedError


class SpeechToTextProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes, language=None):
        raise NotImplementedError


class TextToSpeechProvider(ABC):
    @abstractmethod
    def synthesize(self, text, language=None):
        raise NotImplementedError


class NullSmsProvider(SmsProvider):
    def send(self, phone_number, text):
        raise ChannelProviderError(
            "SMS sending is not configured on this server.",
            log_message="NullSmsProvider.send called; no SMS_PROVIDER configured.",
        )


class NullSpeechToTextProvider(SpeechToTextProvider):
    def transcribe(self, audio_bytes, language=None):
        raise ChannelProviderError(
            "Voice transcription is not configured on this server.",
            log_message="NullSpeechToTextProvider.transcribe called; no STT_PROVIDER configured.",
        )


class NullTextToSpeechProvider(TextToSpeechProvider):
    def synthesize(self, text, language=None):
        raise ChannelProviderError(
            "Voice synthesis is not configured on this server.",
            log_message="NullTextToSpeechProvider.synthesize called; no TTS_PROVIDER configured.",
        )


def get_sms_provider(config):
    provider_name = (config.get("SMS_PROVIDER") or "null").strip().lower()
    if provider_name == "null":
        return NullSmsProvider()
    raise ChannelProviderError(
        "SMS sending is misconfigured on the server.",
        log_message=f"Unknown SMS_PROVIDER={provider_name!r}; expected 'null'.",
    )


def get_speech_to_text_provider(config):
    provider_name = (config.get("STT_PROVIDER") or "null").strip().lower()
    if provider_name == "null":
        return NullSpeechToTextProvider()
    raise ChannelProviderError(
        "Voice transcription is misconfigured on the server.",
        log_message=f"Unknown STT_PROVIDER={provider_name!r}; expected 'null'.",
    )


def get_text_to_speech_provider(config):
    provider_name = (config.get("TTS_PROVIDER") or "null").strip().lower()
    if provider_name == "null":
        return NullTextToSpeechProvider()
    raise ChannelProviderError(
        "Voice synthesis is misconfigured on the server.",
        log_message=f"Unknown TTS_PROVIDER={provider_name!r}; expected 'null'.",
    )
