"""Test setup for the phone assistant.

`assistant.py` imports hardware- and credential-dependent libraries at module
load time (gpiozero for GPIO, sounddevice for audio I/O, openai for the API).
Those can't run on a dev machine, so we inject lightweight fake modules into
`sys.modules` *before* anything imports `assistant`.

numpy and soundfile do real, pure-CPU work (tone synthesis, WAV encoding) that
we actually want to exercise, so we rely on the genuine packages for those.
"""

import sys
import types
from unittest.mock import MagicMock


def _install_fake(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


# gpiozero.Button -> stub that records its construction args.
_install_fake("gpiozero", Button=MagicMock(name="Button"))

# sounddevice -> stub out everything assistant.py touches.
_install_fake(
    "sounddevice",
    play=MagicMock(name="play"),
    wait=MagicMock(name="wait"),
    stop=MagicMock(name="stop"),
    InputStream=MagicMock(name="InputStream"),
    get_stream=MagicMock(name="get_stream"),
)

# openai.OpenAI -> stub; tests that need a client patch assistant.get_client().
_install_fake("openai", OpenAI=MagicMock(name="OpenAI"))
