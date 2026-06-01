#!/usr/bin/env bash
#
# One-command installer for the rotary-phone LLM assistant on Raspberry Pi OS.
#
# It is idempotent — safe to re-run. It:
#   1. installs apt packages (python venv, ALSA tools, PortAudio runtime)
#   2. adds you to the `audio` group
#   3. creates the project venv and installs requirements.txt
#   4. makes the USB sound card the default ALSA device (/etc/asound.conf)
#   5. stores OPENAI_API_KEY in /etc/phone.env (root-only)
#   6. installs + enables the phone.service systemd unit
#
# Usage:
#   ./setup.sh                 # prompts for the API key
#   ./setup.sh sk-...          # takes the key as the first argument
#   ./setup.sh sk-... 1        # also force the USB ALSA card index (skip auto-detect)
#
# Run it as your normal user (e.g. `pi`) — NOT with sudo. The script calls
# sudo itself for the system-level steps so the venv stays owned by you.

set -euo pipefail

# ---------------------------------------------------------------- guardrails
if [[ "${EUID}" -eq 0 ]]; then
    echo "ERROR: run this as your normal user (e.g. pi), not as root / via sudo." >&2
    echo "       The script calls sudo itself only where needed." >&2
    exit 1
fi

API_KEY_ARG="${1:-}"
CARD_OVERRIDE="${2:-}"

echo "==> Checking sudo access..."
sudo -v

# ----------------------------------------------------------- resolve paths
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
VENV_DIR="${PROJECT_DIR}/.venv"
REBOOT_NEEDED=0

echo "    Project dir : ${PROJECT_DIR}"
echo "    User        : ${RUN_USER}"
echo "    Venv        : ${VENV_DIR}"

# --------------------------------------------------------------- apt packages
echo "==> Installing system packages..."
sudo apt-get update
# libportaudio2 is the PortAudio runtime sounddevice needs — easy to miss and
# the most common silent audio failure on Pi OS Lite.
sudo apt-get install -y python3-pip python3-venv alsa-utils libportaudio2

# ---------------------------------------------------------------- audio group
echo "==> Ensuring ${RUN_USER} is in the 'audio' group..."
if id -nG "${RUN_USER}" | grep -qw audio; then
    echo "    already a member."
else
    sudo usermod -aG audio "${RUN_USER}"
    echo "    added — a reboot/relogin is required for it to take effect."
    REBOOT_NEEDED=1
fi

# ---------------------------------------------------------------------- venv
echo "==> Setting up Python venv..."
if [[ ! -d "${VENV_DIR}" ]]; then
    python3 -m venv "${VENV_DIR}"
    echo "    created ${VENV_DIR}"
else
    echo "    reusing existing ${VENV_DIR}"
fi
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip
"${VENV_DIR}/bin/pip" install --quiet -r "${PROJECT_DIR}/requirements.txt"
echo "    runtime dependencies installed."

# --------------------------------------------- USB sound card -> default ALSA
echo "==> Configuring the USB sound card as the default ALSA device..."
detect_usb_card() {
    # Pick the first card in /proc/asound/cards that is NOT the onboard bcm2835.
    # Lines look like:  " 1 [Device         ]: USB-Audio - USB PnP Sound Device"
    awk '/^[[:space:]]*[0-9]+[[:space:]]*\[/ {
        idx=$1
        if (tolower($0) !~ /bcm2835/) { print idx; exit }
    }' /proc/asound/cards
}

CARD=""
if [[ -n "${CARD_OVERRIDE}" ]]; then
    CARD="${CARD_OVERRIDE}"
    echo "    using card index from argument: ${CARD}"
elif [[ -r /proc/asound/cards ]]; then
    CARD="$(detect_usb_card || true)"
fi

if [[ -z "${CARD}" ]]; then
    echo "    WARNING: could not auto-detect a USB sound card. Current cards:" >&2
    cat /proc/asound/cards 2>/dev/null || echo "    (/proc/asound/cards unreadable)" >&2
    echo "    Skipping /etc/asound.conf. Re-run as: ./setup.sh '<key>' <cardIndex>" >&2
else
    echo "    detected USB card index: ${CARD}"
    RENDERED="$(sed "s|__CARD__|${CARD}|g" "${PROJECT_DIR}/asound.conf")"
    if [[ -f /etc/asound.conf ]] && ! grep -q "managed-by: telephone-setup.sh" /etc/asound.conf; then
        BAK="/etc/asound.conf.bak.$(date +%s)"
        sudo cp /etc/asound.conf "${BAK}"
        echo "    backed up existing /etc/asound.conf -> ${BAK}"
    fi
    if [[ -f /etc/asound.conf ]] && [[ "$(cat /etc/asound.conf)" == "${RENDERED}" ]]; then
        echo "    /etc/asound.conf already up to date."
    else
        printf '%s\n' "${RENDERED}" | sudo tee /etc/asound.conf >/dev/null
        echo "    wrote /etc/asound.conf (default card ${CARD})."
    fi
fi

# ------------------------------------------------------- API key -> phone.env
echo "==> Configuring the OpenAI API key (/etc/phone.env)..."
if sudo test -f /etc/phone.env; then
    echo "    /etc/phone.env already exists — keeping it (edit by hand to change)."
else
    KEY="${API_KEY_ARG}"
    if [[ -z "${KEY}" ]]; then
        read -rsp "    Enter OPENAI_API_KEY: " KEY
        echo
    fi
    if [[ -z "${KEY}" ]]; then
        echo "    WARNING: no key given — skipping. Create /etc/phone.env later with:" >&2
        echo "      echo 'OPENAI_API_KEY=sk-...' | sudo tee /etc/phone.env && sudo chmod 600 /etc/phone.env" >&2
    else
        # EnvironmentFile does NOT strip quotes or run `export`, so write a bare
        # KEY=VALUE line with no quotes and no `export`.
        printf 'OPENAI_API_KEY=%s\n' "${KEY}" | sudo tee /etc/phone.env >/dev/null
        sudo chown root:root /etc/phone.env
        sudo chmod 600 /etc/phone.env
        echo "    wrote /etc/phone.env (root-only)."
    fi
fi

# ------------------------------------------------------------ systemd service
echo "==> Installing the phone.service systemd unit..."
sed -e "s|__USER__|${RUN_USER}|g" \
    -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    -e "s|__VENV_DIR__|${VENV_DIR}|g" \
    "${PROJECT_DIR}/phone.service" | sudo tee /etc/systemd/system/phone.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable phone.service
echo "    enabled phone.service (starts on boot)."

if [[ "${REBOOT_NEEDED}" -eq 1 ]]; then
    echo "    NOT starting now — reboot first so the audio group takes effect."
else
    sudo systemctl restart phone.service
    echo "    (re)started phone.service."
fi

# -------------------------------------------------------------------- summary
echo
echo "=================================================================="
echo " Setup complete."
echo "   project : ${PROJECT_DIR}"
echo "   venv    : ${VENV_DIR}"
echo "   ALSA    : default card = ${CARD:-<unset, see warning above>}"
echo "   key     : /etc/phone.env (root-only)"
echo "   service : phone.service (enabled on boot)"
echo
if [[ "${REBOOT_NEEDED}" -eq 1 ]]; then
    echo " NEXT: reboot now ->  sudo reboot"
    echo "       (needed for the 'audio' group to take effect)"
fi
echo " Verify:"
echo "   arecord -d 3 -f cd /tmp/t.wav && aplay /tmp/t.wav   # tests default device"
echo "   systemctl status phone.service"
echo "   journalctl -u phone.service -f                      # watch logs"
echo "   ...then lift the handset and ask a question."
echo "=================================================================="
