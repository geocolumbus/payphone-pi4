# Rotary Pay Phone → LLM Voice Assistant

Turn an old rotary pay phone into a voice assistant: lift the handset, ask a
question out loud, and hear the answer spoken back. A small single-board
computer inside the phone records your voice, sends it to a hosted speech +
LLM service, and plays the spoken reply through the handset earpiece.

This repo contains:

- **`README.md`** – this file (overview, build, and software setup)
- **`wiring-diagram.svg`** – the wiring diagram (open in any browser)
- **`PARTS.md`** – the parts list with rough prices
- **`assistant.py`** – a starter Python script that ties it all together

---

## How it works

```
  Lift handset                Speak                    Hear answer
       │                        │                           ▲
       ▼                        ▼                           │
 ┌───────────┐          ┌──────────────┐          ┌──────────────┐
 │ Hook switch│  GPIO   │  Microphone  │   USB    │   Speaker    │
 │  (on Pi)  │ ───────▶ │  (handset)   │ ───────▶ │  (handset)   │
 └───────────┘          └──────┬───────┘          └──────▲───────┘
                               │                          │
                        ┌──────▼──────────────────────────┴──────┐
                        │        Raspberry Pi (Wi-Fi)             │
                        │  record → STT → LLM → TTS → playback    │
                        └──────────────────┬──────────────────────┘
                                           │  HTTPS
                                           ▼
                                  ┌─────────────────┐
                                  │  Hosted API     │
                                  │ (OpenAI etc.)   │
                                  └─────────────────┘
```

1. **Hook switch** — When you lift the handset off the cradle, the original
   switchhook changes state. The Pi reads this on a GPIO pin and starts a
   session (a "beep" tells you it's listening).
2. **Capture** — Your voice is picked up by a small electret microphone in the
   handset and digitized by a cheap USB sound card.
3. **Think** — The Pi sends the audio to a hosted service for speech-to-text
   (STT), asks the LLM your question, and gets text back.
4. **Speak** — The reply is converted to speech (TTS), amplified, and played
   through the handset earpiece speaker.
5. **Hang up** — Setting the handset back on the cradle ends the session.

See the full wiring diagram in **[`wiring-diagram.svg`](wiring-diagram.svg)**.

---

## Why this hardware

- **Raspberry Pi 4** — runs full Linux + Python, has built-in Wi-Fi and the
  GPIO pins for the hook switch, and full-size USB-A ports so the USB sound
  card plugs straight in (no adapter). It's easy to debug, and a pay phone has
  plenty of room for it. (A Pi Zero 2 W is a cheaper, smaller alternative if
  you don't mind a micro-USB OTG adapter and slower debugging.)
- **USB sound card** — The Pi has *no microphone input*, so a tiny USB audio
  adapter (CM108-class) adds a mic-in and a headphone-out. Plug-and-play on
  Raspberry Pi OS.
- **PAM8302 amplifier** — The headphone output is too weak to drive the small
  handset speaker loudly. This 2.5 W mono amp fixes that and runs off the Pi's
  5 V rail.
- **Electret microphone capsule** — Replaces the old carbon mic. The USB sound
  card supplies the bias voltage it needs.

You do **not** need the original carbon mic, the bell ringer, or the coin
mechanism. You only reuse the **handset shell, the hook switch, and
(optionally) the rotary dial.**

---

## Wiring summary

Full diagram: **[`wiring-diagram.svg`](wiring-diagram.svg)**. Pin numbers below
use the physical Pi header numbering (see `pinout.xyz`).

| From | To | Notes |
|------|----|-------|
| Electret mic (+) / (–) | 3.5 mm plug → USB card **MIC IN** | Card supplies mic bias |
| USB card **HEADPHONE OUT** (tip) | PAM8302 **A+** | Audio signal |
| USB card **HEADPHONE OUT** (sleeve/GND) | PAM8302 **A−** | Signal ground |
| PAM8302 **VIN** | Pi **5V** (pin 2 or 4) | Amp power |
| PAM8302 **GND** | Pi **GND** (pin 6) | Common ground |
| PAM8302 **OUT+ / OUT−** | Handset **speaker** (8 Ω) | No common ground on speaker! |
| Hook switch leg A | Pi **GPIO17** (pin 11) | Internal pull-up in software |
| Hook switch leg B | Pi **GND** (pin 9) | |
| *(optional)* Rotary dial pulse contact A | Pi **GPIO27** (pin 13) | Count pulses to read digits |
| *(optional)* Rotary dial pulse contact B | Pi **GND** (pin 14) | |
| USB sound card | Pi **USB-A port** | Plugs in directly (no adapter) |
| 5 V / 3 A supply | Pi **USB-C power** | Pi 4 wants 5 V / 3 A |

> ⚠️ **Speaker warning:** The PAM8302 is a *bridge-tied-load* (BTL) amp. Connect
> the speaker only between **OUT+** and **OUT−**. Do **not** tie either speaker
> wire to ground.

---

## Build steps (hardware)

1. **Gut the handset.** Remove the old carbon mic capsule and the old speaker.
   Note which wires ran to the earpiece vs. mouthpiece.
2. **Fit the new mic + speaker** in the mouthpiece and earpiece cups. Hot glue
   or foam tape works. Run thin wires back down the handset cord (or run a fresh
   cable if the original 4-wire cord is too tangled).
3. **Mount the Pi** inside the phone body. Pay phones have plenty of room.
4. **Wire the hook switch** to GPIO17 / GND. Use a multimeter to find the two
   switchhook contacts that change continuity when the handset is lifted.
5. **Wire the audio chain**: mic → USB card mic-in; USB card out → PAM8302 →
   speaker; PAM8302 power → Pi 5 V/GND.
6. *(Optional)* **Wire the rotary dial** pulse contacts to GPIO27 / GND so you
   can "dial" different assistant personalities or modes.
7. **Power** the Pi from the 5 V supply. Tidy the wiring with zip ties.

---

## Software setup

Flash **Raspberry Pi OS Lite (64-bit)** and enable Wi-Fi + SSH during imaging.
Then clone this repo onto the Pi and run the installer:

```bash
git clone <this-repo> telephone
cd telephone
./setup.sh                # prompts for your OpenAI API key
# or: ./setup.sh sk-...           # pass the key as an argument
# or: ./setup.sh sk-... 1         # also force the USB ALSA card index
```

`setup.sh` is **idempotent** (safe to re-run) and does everything:

- installs apt packages (`python3-venv`, `alsa-utils`, `libportaudio2`, …),
- adds you to the `audio` group,
- creates the project venv at `./.venv` and installs `requirements.txt`,
- makes the **USB sound card the default ALSA device** by writing
  `/etc/asound.conf` (auto-detecting the card; the `plug` layer converts
  sample rate/format so the mic and speaker just work),
- stores your key in **`/etc/phone.env`** (root-only, `chmod 600`) — never in
  git or `~/.bashrc`,
- installs and enables the **`phone.service`** systemd unit (loads the key via
  `EnvironmentFile`), so the assistant starts on boot.

If the installer added you to the `audio` group, **reboot** when it tells you
to. Then verify:

```bash
arecord -d 3 -f cd /tmp/t.wav && aplay /tmp/t.wav   # tests the DEFAULT device
systemctl status phone.service                      # should be active (running)
journalctl -u phone.service -f                      # watch live logs
# ...then lift the handset and ask a question.
```

<details>
<summary><b>Manual setup (fallback, without the installer)</b></summary>

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv alsa-utils libportaudio2
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
arecord -l      # find the USB capture card index
aplay -l        # find the USB playback card index
```

Make the USB card the default device (edit the card number to match):
copy [`asound.conf`](asound.conf) to `/etc/asound.conf`, replacing `__CARD__`
with your USB card index.

Store the key where the service can read it (not `~/.bashrc`, which systemd
won't see):

```bash
echo 'OPENAI_API_KEY=sk-...' | sudo tee /etc/phone.env
sudo chmod 600 /etc/phone.env
```

Install the service: substitute the paths in [`phone.service`](phone.service)
(`__USER__`, `__PROJECT_DIR__`, `__VENV_DIR__`), copy it to
`/etc/systemd/system/phone.service`, then
`sudo systemctl daemon-reload && sudo systemctl enable --now phone.service`.

For a one-off interactive test you can instead `export OPENAI_API_KEY=sk-...`
and run `python assistant.py` directly.

</details>

### Two software approaches

- **Simple request/response pipeline (in `assistant.py`):** record while the
  handset is lifted → send audio to a speech-to-text API → send the text to a
  chat/LLM API → send the reply text to a text-to-speech API → play it. Easiest
  to understand and debug. Latency is a few seconds per turn.

#### Answer length and content

Replies are kept short and family-friendly by the system prompt: **2–3 short
sentences, ≤60 words** (about 20–30 seconds of speech), and — for big topics —
the gist plus an offer to explain more. Every reply is also instructed to stay
**appropriate for all ages** (no profanity, sexual, violent, or other adult
content). A hard `MAX_ANSWER_TOKENS` cap on the chat call is the backstop so a
reply can never run away into minutes of audio even if the model ignores the
prompt. Tune the word/age guidance in `SYSTEM_PROMPT` and the cap via
`MAX_ANSWER_TOKENS`.

On top of the prompt, `assistant.py` runs an **OpenAI moderation check**
(`is_flagged`) on both the transcribed **question** (before any LLM call) and
the generated **answer** (before it's spoken). Anything flagged gets a short
spoken refusal instead. By default a moderation API error *fails open* (allows
the turn, since the system prompt still constrains content) — flip the `except`
branch in `is_flagged` to `return True` to *fail closed* for an unsupervised
all-ages device.
- **Realtime speech-to-speech (recommended for a natural phone feel):** stream
  audio both ways over a single realtime/voice session for low-latency,
  interruptible conversation. More code, but it feels like a real phone call.
  Swap the pipeline in `assistant.py` for the provider's realtime client when
  you're ready.

---

## Tests

A small `pytest` suite covers the pure logic in `assistant.py` (tone
synthesis, the short-audio guard, WAV encoding/round-trip, lazy client/hook
init). The hardware libraries (`gpiozero`, `sounddevice`) and the OpenAI client
are faked in `conftest.py`, so the tests run anywhere — no Raspberry Pi, audio
device, or API key needed:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

The audio-in/out and live API behavior still need to be verified on the actual
Pi (`arecord`/`aplay` and a real call).

---

## Cost

- **Hardware:** roughly **$85–110** total — see **[`PARTS.md`](PARTS.md)**.
- **API usage:** pay-as-you-go. A short spoken question + answer (STT + a small
  chat model + TTS) is typically a fraction of a cent to a few cents. Set a
  monthly spending limit in your API provider's dashboard to be safe.

---

## Safety notes

- Everything here runs on **5 V DC** from a USB supply — safe to handle. Do
  **not** connect anything to the old telephone line (the ringer circuit used
  ~90 V AC; leave it disconnected).
- Double-check polarity on the amp power pins before powering on.
- Don't tie the speaker outputs to ground (see warning above).
