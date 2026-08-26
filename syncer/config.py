"""Configuración persistente de la app (se guarda en ~/.spotify_yt_sync)."""
import json
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".spotify_yt_sync")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SPOTIFY_CACHE = os.path.join(CONFIG_DIR, "spotify_cache.json")
YT_AUTH_FILE = os.path.join(CONFIG_DIR, "yt_headers_auth.json")

DEFAULTS = {
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "include_liked": True,
    "liked_playlist_name": "Me gusta (desde Spotify)",
    "thumb_up_on_yt": False,
    "privacy": "PRIVATE",
    "match_threshold": 0.62,
}


def ensure_config_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> dict:
    ensure_config_dir()
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    ensure_config_dir()
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except OSError as e:
        print(f"No se pudo guardar la configuración: {e}")
