from __future__ import annotations

import argparse
import asyncio
import json
import queue
import sys
import threading
from typing import Any, Callable, Iterator, Optional

"""Cliente de voz 'Jarvis' para ARGOS.

Se conecta al mismo WebSocket de chat del dashboard y cierra el ciclo
habla -> STT -> ARGOS -> TTS. Es modular: los backends de STT/TTS se
eligen por argumento y se importan de forma perezosa, de modo que si
faltan las dependencias pesadas cae a modo texto sin romper.

El dash (navegador) ya hace voz con Web Speech API; este módulo es para
uso headless / sistema (sin navegador) o para tests con dobles.
"""


class SttBackend:
    def iter_phrases(self, wake_word: Optional[str] = None) -> Iterator[str]:
        raise NotImplementedError


class TtsBackend:
    def speak(self, text: str) -> None:
        raise NotImplementedError


class Transporter:
    def send(self, msg: dict) -> None:
        raise NotImplementedError

    def on_reply(self, cb: Callable[[dict], None]) -> None:
        raise NotImplementedError


# --------------------------------------------------------------------------
# Backends STT
# --------------------------------------------------------------------------
class TextStt(SttBackend):
    def __init__(self, source=None) -> None:
        self._source = source if source is not None else sys.stdin

    def iter_phrases(self, wake_word: Optional[str] = None) -> Iterator[str]:
        for line in self._source:
            text = line.strip()
            if not text:
                continue
            if wake_word and wake_word.lower() not in text.lower():
                continue
            yield text


class SpeechRecognitionStt(SttBackend):
    def __init__(self, lang: str = "es-ES", wake_word: Optional[str] = None) -> None:
        import speech_recognition as sr  # lazy

        self._sr = sr
        self._lang = lang
        self._wake = wake_word.lower() if wake_word else None

    def iter_phrases(self, wake_word: Optional[str] = None) -> Iterator[str]:
        wake = (wake_word or self._wake or "").lower()
        rec = self._sr.Recognizer()
        mic = self._sr.Microphone()
        with mic as src:
            rec.adjust_for_ambient_noise(src)
        while True:
            with mic as src:
                audio = rec.listen(src)
            try:
                text = rec.recognize_google(audio, language=self._lang)
            except Exception:
                continue
            text = text.strip()
            if not text:
                continue
            if wake and wake not in text.lower():
                continue
            yield text


# --------------------------------------------------------------------------
# Backends TTS
# --------------------------------------------------------------------------
class PrintTts(TtsBackend):
    def speak(self, text: str) -> None:
        print(f"[ARGOS] {text}")


class SilentTts(TtsBackend):
    def speak(self, text: str) -> None:
        return None


class Pyttsx3Tts(TtsBackend):
    def __init__(self, lang: str = "es") -> None:
        import pyttsx3  # lazy

        self._engine = pyttsx3.init()
        self._lang = lang

    def speak(self, text: str) -> None:
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            pass


class EdgeTts(TtsBackend):
    def __init__(self, voice: str = "es-ES-AlvaroNeural") -> None:
        import edge_tts  # lazy

        self._edge = edge_tts
        self._voice = voice

    def speak(self, text: str) -> None:
        try:
            import asyncio

            async def _say() -> None:
                comm = self._edge.Communicate(text, self._voice)
                tmp = "data/tts_tmp.mp3"
                with open(tmp, "wb") as f:
                    async for chunk in comm.stream():
                        if chunk[0] is not None:
                            f.write(chunk[0])
                import os

                os.system(f'(start /min wmplayer "{tmp}")' if os.name == "nt" else f'afplay "{tmp}"')

            asyncio.run(_say())
        except Exception:
            pass


# --------------------------------------------------------------------------
# Transporter WebSocket (cliente sincrónico sobre hilo asyncio)
# --------------------------------------------------------------------------
class WebsocketTransporter(Transporter):
    def __init__(self, uri: str) -> None:
        self.uri = uri
        self._queue: queue.Queue = queue.Queue()
        self._ws: Optional[Any] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._cb: Optional[Callable[[dict], None]] = None
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        asyncio.run(self._loop_main())

    async def _loop_main(self) -> None:
        import websockets  # lazy

        self._loop = asyncio.get_running_loop()
        try:
            async with websockets.connect(self.uri) as ws:
                self._ws = ws
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    if self._cb:
                        self._cb(msg)
        except Exception:
            pass

    def send(self, msg: dict) -> None:
        if self._ws is None or self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._ws.send(json.dumps(msg)), self._loop)

    def on_reply(self, cb: Callable[[dict], None]) -> None:
        self._cb = cb


# --------------------------------------------------------------------------
# Bucle principal (testeable con dobles)
# --------------------------------------------------------------------------
def run(stt: SttBackend, tts: TtsBackend, transport: Transporter,
        wake_word: Optional[str] = None, stop_event: Optional[threading.Event] = None,
        reply_timeout: float = 30.0) -> None:
    pending: queue.Queue = queue.Queue()

    def _inbound(msg: dict) -> None:
        if msg.get("type") == "chat" and msg.get("role") == "assistant":
            pending.put(msg.get("content", ""))
        elif msg.get("type") == "proposal":
            pending.put(f"Propuesta: {msg.get('action')} sobre {msg.get('target')}")

    transport.on_reply(_inbound)

    for phrase in stt.iter_phrases(wake_word=wake_word):
        if stop_event and stop_event.is_set():
            break
        transport.send({"type": "chat", "message": phrase, "session": None})
        # Drena todas las respuestas (chat + propuestas) y las lee en voz alta.
        replies: list[str] = []
        try:
            while True:
                replies.append(pending.get(timeout=0.3))
        except queue.Empty:
            pass
        for r in replies:
            if r:
                tts.speak(r)


# --------------------------------------------------------------------------
# Factory / CLI
# --------------------------------------------------------------------------
def build_stt(mode: str, wake_word: Optional[str]) -> SttBackend:
    if mode == "text":
        return TextStt()
    if mode == "sr":
        return SpeechRecognitionStt(wake_word=wake_word)
    if mode == "whisper":
        raise NotImplementedError("whisper StT pendiente de instalar dependencia")
    return TextStt()


def build_tts(mode: str) -> TtsBackend:
    if mode == "none":
        return SilentTts()
    if mode == "print":
        return PrintTts()
    if mode == "pyttsx3":
        return Pyttsx3Tts()
    if mode == "edge":
        return EdgeTts()
    return PrintTts()


def main() -> None:
    ap = argparse.ArgumentParser(description="ARGOS Jarvis — cliente de voz por WebSocket")
    ap.add_argument("--host", default="127.0.0.1:8000")
    ap.add_argument("--token", default="")
    ap.add_argument("--mode", choices=["text", "sr", "whisper"], default="text")
    ap.add_argument("--tts", choices=["print", "none", "pyttsx3", "edge"], default="print")
    ap.add_argument("--wake-word", default="argos")
    args = ap.parse_args()

    proto = "ws"
    uri = f"{proto}://{args.host}/ws"
    if args.token:
        uri += f"?token={args.token}"

    transport = WebsocketTransporter(uri)
    run(build_stt(args.mode, args.wake_word), build_tts(args.tts), transport,
        wake_word=args.wake_word)


if __name__ == "__main__":
    main()
