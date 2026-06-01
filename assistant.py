#!/usr/bin/env python3
"""
Rotary pay phone LLM voice assistant — starter script.

Flow:
  lift handset (hook switch) -> beep -> record while lifted
  -> speech-to-text -> LLM -> text-to-speech -> play through earpiece
  -> hang up ends the turn.

This is the simple request/response pipeline. For a natural, low-latency,
interruptible "phone call" feel, swap the transcribe/chat/speak section for
your provider's realtime speech-to-speech client.

Setup:
  python3 -m venv ~/phone-env && source ~/phone-env/bin/activate
  pip install openai sounddevice soundfile gpiozero numpy
  export OPENAI_API_KEY="sk-..."
  # find your USB sound card index with: arecord -l  /  aplay -l
"""

import os
import io
import time
import wave
import tempfile

import numpy as np
import sounddevice as sd
import soundfile as sf
from gpiozero import Button
from openai import OpenAI

# ---------------------------------------------------------------- config
HOOK_GPIO = 17          # hook switch -> GPIO17 (pin 11) + GND (pin 9)
SAMPLE_RATE = 16000     # 16 kHz is plenty for speech
CHANNELS = 1
# Models — adjust to taste / budget.
STT_MODEL = "whisper-1"
CHAT_MODEL = "gpt-4o-mini"
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "alloy"
MODERATION_MODEL = "omni-moderation-latest"
# Spoken when a question or answer is blocked by moderation (or otherwise
# refused). Kept short and friendly so it sounds natural over the handset.
REFUSAL = "Sorry, I can't help with that one. Is there something else I can answer?"
# Hard backstop on answer length so a reply can never run away into minutes of
# speech. ~60 words is roughly 80 tokens; 160 leaves headroom to finish a
# sentence cleanly while still capping a misbehaving response. The soft limit
# lives in SYSTEM_PROMPT below; this is the safety net if the model ignores it.
MAX_ANSWER_TOKENS = 160
SYSTEM_PROMPT = (
    "You are a friendly voice on an old rotary pay phone. The caller hears "
    "your reply out loud — they can't read it — so keep it short and natural. "
    "Answer in 2-3 short sentences, no more than 60 words. If the question is "
    "large or open-ended, give the key point briefly and offer to explain more "
    "if they'd like. "
    "Keep every reply family-friendly and appropriate for all ages: no "
    "profanity and no sexual, violent, or other adult content. If a question "
    "calls for that kind of content, politely decline in one sentence and offer "
    "to help with something else."
)

_client = None


def get_client() -> OpenAI:
    """Lazily create the OpenAI client, so importing this module (e.g. from a
    test) doesn't require an API key or network access."""
    global _client
    if _client is None:
        _client = OpenAI()  # reads OPENAI_API_KEY from the environment
    return _client


# Hook-switch handle. Created in init_hook() (called from main) rather than at
# import time, so importing this module doesn't require real GPIO hardware.
hook = None


def init_hook() -> "Button":
    """Create the hook-switch handle. pull_up=True uses the Pi's internal
    pull-up, so wire the switch between GPIO17 and GND. Test with a multimeter
    and flip the logic in handset_lifted() if your switch reads the other way."""
    global hook
    if hook is None:
        hook = Button(HOOK_GPIO, pull_up=True, bounce_time=0.05)
    return hook


def handset_lifted() -> bool:
    # With pull_up=True, is_pressed == pin pulled to GND. Many switchhooks
    # close to GND when lifted; invert here if yours is the opposite.
    return hook.is_pressed


def beep(freq=880, secs=0.15):
    t = np.linspace(0, secs, int(SAMPLE_RATE * secs), endpoint=False)
    tone = 0.3 * np.sin(2 * np.pi * freq * t)
    sd.play(tone.astype(np.float32), SAMPLE_RATE)
    sd.wait()


def record_while_lifted(max_secs=20) -> np.ndarray:
    """Record audio until the handset is hung up (or max_secs)."""
    frames = []
    start = time.monotonic()
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype="int16") as stream:
        while handset_lifted() and (time.monotonic() - start) < max_secs:
            block, _ = stream.read(int(SAMPLE_RATE * 0.1))
            frames.append(block.copy())
    if not frames:
        return np.zeros((0, CHANNELS), dtype="int16")
    return np.concatenate(frames, axis=0)


def transcribe(audio: np.ndarray) -> str:
    if audio.shape[0] < SAMPLE_RATE // 2:   # < 0.5 s -> nothing useful
        return ""
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV")
    buf.seek(0)
    buf.name = "speech.wav"
    resp = get_client().audio.transcriptions.create(model=STT_MODEL, file=buf)
    return (resp.text or "").strip()


def is_flagged(text: str) -> bool:
    """Return True if OpenAI moderation flags the text (hate, sexual, violence,
    self-harm, etc.). This is a stronger guardrail than the system prompt alone.

    On a moderation API error we log and return False (fail-open) so a network
    blip doesn't brick the phone — the SYSTEM_PROMPT still constrains content.
    For an all-ages device where you'd rather refuse when unsure, change the
    `except` branch to `return True` (fail-closed)."""
    if not text:
        return False
    try:
        result = get_client().moderations.create(model=MODERATION_MODEL, input=text)
        return bool(result.results[0].flagged)
    except Exception as exc:
        print(f"Moderation check failed ({exc}); allowing by default.")
        return False


def ask_llm(question: str) -> str:
    resp = get_client().chat.completions.create(
        model=CHAT_MODEL,
        max_completion_tokens=MAX_ANSWER_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    return resp.choices[0].message.content.strip()


def speak(text: str):
    """Synthesize speech and play it, stopping early if hung up."""
    with get_client().audio.speech.with_streaming_response.create(
        model=TTS_MODEL, voice=TTS_VOICE, input=text, response_format="wav"
    ) as resp:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            for chunk in resp.iter_bytes():
                tmp.write(chunk)
            tmp.flush()
            data, sr = sf.read(tmp.name, dtype="float32")
    sd.play(data, sr)
    while sd.get_stream().active:
        if not handset_lifted():     # caller hung up -> stop talking
            sd.stop()
            break
        time.sleep(0.05)


def handle_call():
    print("Handset lifted — listening.")
    beep()
    audio = record_while_lifted()
    if not handset_lifted():
        print("Hung up before finishing.")
        return
    question = transcribe(audio)
    if not question:
        speak("Sorry, I didn't catch that.")
        return
    print(f"Heard: {question!r}")
    if is_flagged(question):                 # block before spending an LLM call
        print("Question flagged by moderation — declining.")
        if handset_lifted():
            speak(REFUSAL)
        return
    answer = ask_llm(question)
    print(f"Reply: {answer!r}")
    if is_flagged(answer):                    # belt-and-suspenders on the reply
        print("Reply flagged by moderation — declining.")
        answer = REFUSAL
    if handset_lifted():
        speak(answer)


def main():
    print("Phone assistant ready. Lift the handset to talk. Ctrl-C to quit.")
    init_hook()
    try:
        while True:
            hook.wait_for_press()      # handset lifted
            try:
                handle_call()
            except Exception as exc:    # keep the phone alive on any API error
                print(f"Error during call: {exc}")
                if handset_lifted():
                    try:
                        speak("Something went wrong. Please try again.")
                    except Exception:
                        pass
            hook.wait_for_release()    # wait for hang up before next call
            print("Hung up. Ready for next call.\n")
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Run on boot with systemd — save as /etc/systemd/system/phone.service:
#
#   [Unit]
#   Description=Rotary phone LLM assistant
#   After=network-online.target sound.target
#   Wants=network-online.target
#
#   [Service]
#   User=pi
#   Environment=OPENAI_API_KEY=sk-...
#   ExecStart=/home/pi/phone-env/bin/python /home/pi/telephone/assistant.py
#   Restart=on-failure
#
#   [Install]
#   WantedBy=multi-user.target
#
# Then:  sudo systemctl enable --now phone.service
# ---------------------------------------------------------------------------
