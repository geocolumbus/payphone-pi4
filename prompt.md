# Project Prompt — Rotary Pay Phone LLM Voice Assistant

Use this prompt to recreate this project from scratch. It describes exactly
what was built and what deliverables to produce.

---

## The prompt

> I have an old rotary pay phone. I want to convert it into a voice assistant:
> lift the handset, speak a question, and hear an LLM's spoken answer back
> through the earpiece. Hanging up ends the session. Cost matters, so use an
> inexpensive single-board computer plus a hosted speech + LLM API (e.g. an
> OpenAI key) rather than running models locally.
>
> Reuse the phone's existing **handset shell, cord, and hook switch** (lifting
> the handset is the "start talking" trigger). Optionally wire the **rotary
> dial** pulse contacts to a GPIO so it can select modes/personalities. Leave
> the old telephone line, bell/ringer (~90 V), and coin mechanism
> disconnected. Everything should run on safe 5 V DC.
>
> Design the build around these components and explain *why* each is chosen:
> - **Raspberry Pi 4** — runs full Linux + Python, has built-in Wi-Fi and GPIO,
>   and has full-size USB-A ports so the USB sound card plugs straight in (no
>   OTG adapter); it's easy to debug and a pay phone has plenty of room for it.
>   (A cheaper, smaller Pi Zero 2 W is an alternative if you don't mind a
>   micro-USB OTG adapter and slower debugging.)
> - **USB sound card (CM108-class)** — the Pi has no mic input; this adds
>   mic-in + headphone-out, plug-and-play on Raspberry Pi OS.
> - **PAM8302A mono amplifier** — boosts the headphone output to drive the
>   handset speaker; powered from the Pi's 5 V rail. (BTL output — speaker goes
>   between OUT+ and OUT−, never to ground.)
> - **Electret microphone capsule** (biased by the USB card) and a small
>   **8 Ω, ~40 mm speaker** in the handset.
> - **Hook switch → GPIO17 (pin 11) + GND (pin 9)** with an internal pull-up.
> - **5 V / 3 A USB-C power supply** (the Pi 4's requirement).
>
> Define the full signal chain: hook switch (GPIO) triggers a session →
> electret mic → USB sound card → Raspberry Pi → speech-to-text → LLM →
> text-to-speech → PAM8302 amp → handset speaker, with the Pi reaching the
> hosted API over Wi-Fi/HTTPS.
>
> Produce these deliverables:
> 1. **`README.md`** — overview, how-it-works, hardware rationale, a wiring
>    summary table (with Pi physical pin numbers), hardware build steps,
>    software setup (Raspberry Pi OS Lite, Python venv, `arecord`/`aplay`
>    checks, API key via env var), both a simple request/response pipeline and
>    a recommended realtime speech-to-speech approach, cost expectations, and
>    safety notes.
> 2. **`wiring-diagram.svg`** — a color-coded wiring diagram (boxes for
>    handset/mic/speaker, USB sound card, PAM8302 amp, Raspberry Pi, hook
>    switch, optional rotary dial, 5 V supply, and the cloud API) with a legend
>    distinguishing audio / 5 V power / GPIO / USB / Wi-Fi connections.
> 3. **`PARTS.md`** — a parts list with purpose, quantity, and rough US prices
>    (~$85–110 total), plus what's reused from the phone, what's not needed, and
>    optional upgrades (Pi Zero 2 W to shrink/cheapen, Pi 5, I2S mic+amp HAT,
>    MAX9814, push-button, status LED).
> 4. **`assistant.py`** — a runnable Python starter using `gpiozero` for the
>    hook switch, `sounddevice`/`soundfile` for audio, and the OpenAI SDK for
>    STT → chat → TTS. It should beep when listening, record while the handset
>    is lifted, stop talking if hung up mid-answer, survive API errors without
>    crashing, and include a `systemd` unit (in comments) to run on boot. Keep
>    answers short and listenable — instruct the model (in the system prompt)
>    to reply in 2-3 short sentences, ≤60 words, offering to explain more for
>    big topics — and keep them family-friendly / appropriate for all ages (no
>    profanity, sexual, violent, or other adult content). Back the length limit
>    with a hard `max_completion_tokens` cap so a reply can never run long.
> 5. Replace this prompt file (`prompt.md`) so the project can be replicated
>    from the prompt alone.

---

## What was built (deliverables in this repo)

- `README.md` — full project guide (architecture, wiring summary, build &
  software setup, cost, safety).
- `wiring-diagram.svg` — color-coded wiring diagram; open in any browser.
- `PARTS.md` — itemized parts list with prices and optional upgrades.
- `assistant.py` — request/response voice-assistant starter script.
- `prompt.md` — this file.

## Key design decisions to preserve when replicating

- **Hosted API, not local models** — keeps the SBC cheap and the latency/cost
  predictable.
- **USB sound card is mandatory** — the Pi has no analog mic input.
- **Amp powered from the Pi 5 V rail**, common ground with the Pi; **speaker
  only across OUT+/OUT−** (PAM8302 is bridge-tied).
- **Hook switch on GPIO17 with software pull-up**; "lifted" starts a turn,
  "hung up" ends it.
- **Only 5 V DC anywhere** — never touch the legacy line/ringer voltage.
- **Short, all-ages replies** — system prompt limits answers to 2-3 sentences
  / ≤60 words and forbids profanity and sexual/violent/adult content, backed by
  a hard `max_completion_tokens` cap so audio never runs long.
- Offer a **realtime speech-to-speech** upgrade path for a natural call feel,
  but ship the simple pipeline first.
