# Parts List

Prices are rough US street prices (mid-2020s) and vary by vendor and quantity.
Everything is low-voltage (5 V) and beginner-friendly to solder/wire.

## Core electronics

| # | Part | Purpose | Qty | ~Price |
|---|------|---------|-----|--------|
| 1 | **Raspberry Pi 4 (2 GB)** | Single-board computer + Wi-Fi (runs the assistant); full-size USB-A ports | 1 | $45 |
| 2 | **microSD card, 16–32 GB (A1/Class 10)** | Boot + OS storage | 1 | $7 |
| 3 | **USB sound card (CM108-class), with mic-in + headphone-out** | Adds audio input the Pi lacks | 1 | $8 |
| 4 | **PAM8302A mono amplifier board** | Drives the handset speaker | 1 | $4 |
| 5 | **Electret microphone capsule** (or a cheap lavalier mic on a 3.5 mm plug) | New mouthpiece mic | 1 | $2 |
| 6 | **8 Ω speaker, ~40–50 mm / 1–3 W** | New earpiece speaker (fits handset) | 1 | $3 |
| 7 | **5 V / 3 A USB-C power supply** (official Pi 4 PSU) | Powers the Pi (and amp via 5 V rail) | 1 | $10 |

## Connectors, cabling, hardware

| # | Part | Purpose | Qty | ~Price |
|---|------|---------|-----|--------|
| 8 | **3.5 mm TRS/TRRS plug or pigtail** | Mic → USB card mic-in (if not using a pre-terminated mic) | 1 | $2 |
| 9 | **Dupont jumper wires (F-F / M-F assortment)** | Hook switch + amp power to GPIO header | 1 pk | $4 |
| 10 | **Thin hookup wire (26–28 AWG)** | Mic/speaker runs inside the handset & cord | small | $3 |
| 11 | **Heat-shrink tubing + solder** | Tidy, durable joints | — | $4 |
| 12 | **Foam tape / hot glue** | Mount mic, speaker, and boards inside the phone | — | $3 |

> The Pi 4's full-size USB-A ports take the USB sound card directly — no OTG
> adapter needed (unlike the Pi Zero, which would require one).

**Estimated total: ~$85–110** (excluding the phone itself and ongoing API usage).

---

## You already have (reused from the phone)

- The **rotary pay phone** handset shell, body, and cord
- The **hook switch** (switchhook) — reused as the "lift to talk" trigger
- *(Optional)* The **rotary dial** with its pulse contacts — wire it up to
  "dial" different modes/personalities

## Not needed (can stay disconnected / removed)

- Original **carbon microphone** capsule (replaced by item 5)
- Original **earpiece** element (replaced by item 6)
- **Ringer/bell** and its high-voltage coil (~90 V AC — leave disconnected)
- **Coin mechanism** and line-interface electronics

---

## Optional upgrades

| Part | Why |
|------|-----|
| **Raspberry Pi Zero 2 W** instead of the Pi 4 | Cheaper (~$15) and smaller; needs a micro-USB OTG adapter for the USB sound card and is slower to debug |
| **Raspberry Pi 5** instead of the Pi 4 | Faster still; pricier and needs more cooling/power — overkill for this workload |
| **I2S mic + I2S amp HAT** (e.g. MEMS mic + MAX98357A) | Higher audio quality, no USB sound card needed; requires device-tree config |
| **MAX9814 mic module (auto gain)** | More consistent mic levels in a noisy room |
| **Small push-button** | Manual "push to talk" if you'd rather not trigger on the hook switch |
| **Status LED** | Visual cue for listening / thinking / speaking states |

---

## Notes on choosing parts

- **USB sound card:** Pick one that shows up as a USB Audio Class device (most
  CM108/CM109 dongles do) — these need no drivers on Raspberry Pi OS. Make sure
  it has a **separate mic input**, not just headphone-out.
- **Speaker size:** Measure your handset earpiece cup first. ~40 mm round
  speakers fit most handsets; thin/"slim" profiles help.
- **Mic:** An electret capsule is cheapest; a 3.5 mm lavalier mic is the
  easiest because it's already wired for the USB card's mic-in bias.
