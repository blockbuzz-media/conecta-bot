"""Traducciones desde archivos JSON organizados por idioma.

No hay traducción automática en tiempo real: cada idioma tiene su archivo
en locales/. Si falta una clave, se usa español como respaldo.
"""
import json
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
_CACHE = {}


def load_language(lang):
    if lang not in _CACHE:
        path = LOCALES_DIR / f"{lang}.json"
        _CACHE[lang] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _CACHE[lang]


def t(lang, key, **kwargs):
    text = load_language(lang).get(key)
    if text is None:
        text = load_language("es").get(key, key)
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text
