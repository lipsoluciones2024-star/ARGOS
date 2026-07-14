from __future__ import annotations

import threading

from argos.voice_jarvis import SttBackend, Transporter, TtsBackend, run


class FakeStt(SttBackend):
    def __init__(self, phrases) -> None:
        self._phrases = list(phrases)

    def iter_phrases(self, wake_word=None) -> None:
        for p in self._phrases:
            text = p.strip()
            if not text:
                continue
            if wake_word and wake_word.lower() not in text.lower():
                continue
            yield text


class FakeTts(TtsBackend):
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


class FakeTransporter(Transporter):
    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.sent: list[dict] = []
        self._cb = None

    def send(self, msg: dict) -> None:
        self.sent.append(msg)
        if self._cb:
            self._cb({"type": "chat", "role": "assistant", "content": self._reply})

    def on_reply(self, cb) -> None:
        self._cb = cb


def test_voice_pipeline_sends_and_speaks_reply():
    stt = FakeStt(["¿hay conexiones a IPs maliciosas?"])
    tts = FakeTts()
    transport = FakeTransporter("No se detectaron conexiones maliciosas.")

    run(stt, tts, transport, stop_event=threading.Event())

    assert len(transport.sent) == 1
    assert transport.sent[0]["type"] == "chat"
    assert transport.sent[0]["message"] == "¿hay conexiones a IPs maliciosas?"
    assert tts.spoken == ["No se detectaron conexiones maliciosas."]


def test_voice_pipeline_wake_word_filter():
    stt = FakeStt(["clima hoy", "argos dime el estado", "otra cosa"])
    tts = FakeTts()
    transport = FakeTransporter("ok")

    run(stt, tts, transport, wake_word="argos", stop_event=threading.Event())

    # Solo la frase que contiene la wake word debe enviarse
    assert [s["message"] for s in transport.sent] == ["argos dime el estado"]


def test_voice_pipeline_proposal_notification():
    stt = FakeStt(["bloquea 1.2.3.4"])
    tts = FakeTts()

    class MixedTransporter(FakeTransporter):
        def send(self, msg):
            self.sent.append(msg)
            if self._cb:
                self._cb({"type": "chat", "role": "assistant", "content": "propongo bloquear"})
                self._cb({"type": "proposal", "action": "block_ip", "target": "1.2.3.4"})

    run(stt, tts, MixedTransporter(""), stop_event=threading.Event())
    assert any("Propuesta" in s for s in tts.spoken)
