from enum import Enum
from typing import TypedDict, Literal

SPEECH_ARRAY_INDEX = TypedDict("SPEECH_ARRAY_INDEX", {"start": float, "end": float})

LANG = Literal[
    "zh",
    "en",
    "Afrikaans",
    "Arabic",
    "Armenian",
    "Azerbaijani",
    "Belarusian",
    "Bosnian",
    "Bulgarian",
    "Catalan",
    "Croatian",
    "Czech",
    "Danish",
    "Dutch",
    "Estonian",
    "Finnish",
    "French",
    "Galician",
    "German",
    "Greek",
    "Hebrew",
    "Hindi",
    "Hungarian",
    "Icelandic",
    "Indonesian",
    "Italian",
    "Japanese",
    "Kannada",
    "Kazakh",
    "Korean",
    "Latvian",
    "Lithuanian",
    "Macedonian",
    "Malay",
    "Marathi",
    "Maori",
    "Nepali",
    "Norwegian",
    "Persian",
    "Polish",
    "Portuguese",
    "Romanian",
    "Russian",
    "Serbian",
    "Slovak",
    "Slovenian",
    "Spanish",
    "Swahili",
    "Swedish",
    "Tagalog",
    "Tamil",
    "Thai",
    "Turkish",
    "Ukrainian",
    "Urdu",
    "Vietnamese",
    "Welsh",
]


class WhisperModel(Enum):
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V2 = "large-v2"

    @staticmethod
    def get_values():
        return [i.value for i in WhisperModel]


class WhisperMode(Enum):
    WHISPER = "whisper"
    OPENAI = "openai"
    FASTER = "faster"

    @staticmethod
    def get_values():
        return [i.value for i in WhisperMode]
