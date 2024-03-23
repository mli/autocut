__version__ = "1.0.2"

from .type import LANG, WhisperModel, WhisperMode
from .utils import load_audio
from .package_transcribe import Transcribe

__all__ = ["Transcribe", "load_audio", "WhisperMode", "WhisperModel", "LANG"]
