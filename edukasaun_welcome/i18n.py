"""Locale resolution independent of Qt's knowledge of Tetun."""
import json
import os
from pathlib import Path

LOCALES = Path(__file__).parent / "locales"
SUPPORTED = ("en", "tet", "pt", "id")


def system_language(environment=None):
    env = os.environ if environment is None else environment
    locale = env.get("LC_ALL") or env.get("LC_MESSAGES") or env.get("LANG") or "en"
    if locale in ("C", "POSIX") or locale.startswith("C."):
        return "en"
    candidates = env.get("LANGUAGE", "").split(":") + [locale]
    for candidate in candidates:
        language = candidate.split(".")[0].split("@")[0].replace("-", "_").split("_")[0].lower()
        if language in SUPPORTED:
            return language
    return "en"


class Translator:
    def __init__(self, language="system"):
        self.language = system_language() if language == "system" else language
        if self.language not in SUPPORTED:
            self.language = "en"
        self.english = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        self.messages = json.loads((LOCALES / f"{self.language}.json").read_text(encoding="utf-8"))

    def __call__(self, key, **values):
        return self.messages.get(key, self.english.get(key, key)).format(**values)
