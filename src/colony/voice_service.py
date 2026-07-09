"""VoiceService — TTS output and wake word detection for the colony.

Provides:
  - Text-to-speech via espeak/gTTS when available, log-only fallback
  - Wake word detection placeholder (programmatic trigger)
  - Audio interrupt placeholder (programmatic trigger)
  - Language selection (en/id support)

Usage:
    voice = VoiceService()
    await voice.say("System is healthy")
    voice.set_wake_word("blackhornet")
    voice.trigger_wake_word()
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from typing import Callable, Optional

from src.config.logging_config import get_logger

logger = get_logger(__name__)


class VoiceService:
    """Voice output and wake word service for the colony.

    TTS backends (tried in order):
      1. espeak-ng / espeak (Linux, most reliable)
      2. gtts (Google TTS, requires internet + gtts package)
      3. say (macOS built-in)
      4. Log-only fallback (always works)
    """

    def __init__(
        self,
        language: str = "en",
        wake_word: str = "queen",
        enabled: bool = True,
        voice_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._language = language
        self._wake_word = wake_word
        self._enabled = enabled
        self._voice_callback = voice_callback

        self._tts_backend: Optional[str] = None
        self._wake_detected = False
        self._interrupt_requested = False
        self._say_count = 0
        self._last_say: Optional[str] = None
        self._last_say_time: Optional[float] = None

        self._detect_backend()

    def _detect_backend(self) -> None:
        if shutil.which("espeak-ng"):
            self._tts_backend = "espeak-ng"
        elif shutil.which("espeak"):
            self._tts_backend = "espeak"
        elif shutil.which("say"):
            self._tts_backend = "say"
        else:
            self._tts_backend = None
        logger.debug("voice_backend=%s", self._tts_backend or "log-only")

    @property
    def tts_backend(self) -> Optional[str]:
        return self._tts_backend

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def set_language(self, lang: str) -> None:
        self._language = lang

    def set_wake_word(self, word: str) -> None:
        self._wake_word = word

    async def say(
        self,
        text: str,
        language: Optional[str] = None,
        blocking: bool = False,
    ) -> None:
        """Speak text through available TTS backend, or log if none.

        Args:
            text: Text to speak.
            language: Override language (default: en, id supported).
            blocking: If True, wait for TTS to finish.
        """
        if not self._enabled:
            logger.debug("voice_disabled text=%s", text[:60])
            return

        self._say_count += 1
        self._last_say = text
        self._last_say_time = time.time()

        lang = language or self._language

        if self._voice_callback:
            try:
                self._voice_callback(text)
            except Exception as e:
                logger.debug("voice_callback_error err=%s", e)

        if self._tts_backend == "espeak-ng" or self._tts_backend == "espeak":
            try:
                cmd = [self._tts_backend, "-v", lang, text]
                if blocking:
                    subprocess.run(cmd, timeout=30)
                else:
                    asyncio.create_task(asyncio.to_thread(subprocess.run, cmd, timeout=30))
                return
            except Exception as e:
                logger.debug("espeak_error err=%s", e)

        if self._tts_backend == "say":
            try:
                cmd = ["say", text]
                if blocking:
                    subprocess.run(cmd, timeout=30)
                else:
                    asyncio.create_task(asyncio.to_thread(subprocess.run, cmd, timeout=30))
                return
            except Exception as e:
                logger.debug("say_error err=%s", e)

        logger.info("voice:%s %s", lang, text)

    async def say_async(self, text: str, language: Optional[str] = None) -> None:
        """Non-blocking TTS (fire-and-forget)."""
        await self.say(text, language, blocking=False)

    def trigger_wake_word(self) -> None:
        """Programmatically trigger wake word detection."""
        self._wake_detected = True
        logger.info("wake_word_detected word=%s", self._wake_word)

    def clear_wake(self) -> None:
        self._wake_detected = False

    @property
    def wake_detected(self) -> bool:
        return self._wake_detected

    def request_interrupt(self) -> None:
        """Programmatically request an audio interrupt."""
        self._interrupt_requested = True
        logger.info("interrupt_requested")

    def clear_interrupt(self) -> None:
        self._interrupt_requested = False

    @property
    def interrupt_requested(self) -> bool:
        return self._interrupt_requested

    def get_stats(self) -> dict:
        return {
            "tts_backend": self._tts_backend or "log-only",
            "enabled": self._enabled,
            "language": self._language,
            "wake_word": self._wake_word,
            "say_count": self._say_count,
            "last_say": self._last_say[:60] if self._last_say else None,
            "wake_detected": self._wake_detected,
            "interrupt_requested": self._interrupt_requested,
        }
