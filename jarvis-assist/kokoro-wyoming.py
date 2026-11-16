#!/usr/bin/env python3
"""Wyoming text-to-speech server for Home Assistant Assist, using the JARVIS Kokoro voice.

Runs in the JARVIS venv (~/.local/share/jarvis-venv) and loads the same model as jarvis-speak.
Listens on 127.0.0.1:10200; HA (host network) adds it as a Wyoming integration.
Voices offered: george (default), lewis, daniel, fable (British male Kokoro voices)."""
import asyncio, os
import numpy as np
from kokoro_onnx import Kokoro
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import Synthesize

KOKORO = os.path.expanduser("~/.local/share/jarvis-voice/kokoro")
VOICES = ["george", "lewis", "daniel", "fable"]
SPEED = 1.15  # same as jarvis-speak
RATE = 24000
ATTR = Attribution(name="hexgrad / thewh1teagle", url="https://github.com/thewh1teagle/kokoro-onnx")

INFO = Info(tts=[TtsProgram(
    name="kokoro-jarvis", description="JARVIS Kokoro voice", attribution=ATTR, installed=True,
    version="1.0", voices=[TtsVoice(name=v, description=f"Kokoro bm_{v}", attribution=ATTR,
                                    installed=True, version="1.0", languages=["en-GB", "en"])
                           for v in VOICES])])

kokoro = Kokoro(f"{KOKORO}/kokoro-v1.0.int8.onnx", f"{KOKORO}/voices-v1.0.bin")
lock = asyncio.Lock()  # one synthesis at a time; the CPU only has 4 cores


class Handler(AsyncEventHandler):
    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(INFO.event())
            return True
        if not Synthesize.is_type(event.type):
            return True
        req = Synthesize.from_event(event)
        name = req.voice.name if req.voice and req.voice.name in VOICES else VOICES[0]
        async with lock:
            samples, _ = await asyncio.to_thread(
                kokoro.create, req.text.strip() or ".", voice=f"bm_{name}", speed=SPEED, lang="en-gb")
        pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
        await self.write_event(AudioStart(rate=RATE, width=2, channels=1).event())
        for i in range(0, len(pcm), 4096):
            await self.write_event(AudioChunk(rate=RATE, width=2, channels=1, audio=pcm[i:i + 4096]).event())
        await self.write_event(AudioStop().event())
        return True


async def main():
    kokoro.create("Ready.", voice="bm_george", speed=SPEED, lang="en-gb")  # warm up
    await AsyncServer.from_uri("tcp://127.0.0.1:10200").run(Handler)


if __name__ == "__main__":
    asyncio.run(main())
