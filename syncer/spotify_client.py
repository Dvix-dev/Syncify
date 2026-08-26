"""Cliente de Spotify (lectura de playlists y canciones con 'me gusta')."""
from __future__ import annotations

import spotipy
from spotipy.oauth2 import CacheFileHandler, SpotifyOAuth

from .config import SPOTIFY_CACHE

SCOPE = "user-library-read playlist-read-private playlist-read-collaborative"
REDIRECT_URI = "http://127.0.0.1:8888/callback"


class SpotifyClient:
    def __init__(self) -> None:
        self.sp: spotipy.Spotify | None = None

    @property
    def connected(self) -> bool:
        return self.sp is not None

    def connect(self, client_id: str, client_secret: str) -> str:
        """Abre el navegador para autorizar y devuelve el nombre del usuario."""
        handler = CacheFileHandler(cache_path=SPOTIFY_CACHE)
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_handler=handler,
            open_browser=True,
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        me = self.sp.me()
        return me.get("display_name") or me.get("id", "usuario")

    def disconnect(self) -> None:
        self.sp = None

    def _require(self) -> spotipy.Spotify:
        if self.sp is None:
            raise RuntimeError("No conectado a Spotify")
        return self.sp

    def get_playlists(self) -> list[dict]:
        """Devuelve las playlists propias y colaborativas del usuario."""
        sp = self._require()
        user_id = sp.me()["id"]
        playlists: list[dict] = []
        result = sp.current_user_playlists(limit=50)
        while result:
            for p in result["items"]:
                if p is None:
                    continue
                owner_id = (p.get("owner") or {}).get("id")
                if owner_id == user_id or p.get("collaborative"):
                    playlists.append(
                        {
                            "id": p["id"],
                            "name": p["name"],
                            "tracks": p.get("tracks", {}).get("total", 0),
                        }
                    )
            result = sp.next(result) if result.get("next") else None
        return playlists

    def get_playlist_tracks(self, playlist_id: str) -> list[dict]:
        sp = self._require()
        tracks: list[dict] = []
        result = sp.playlist_items(playlist_id, limit=100)
        while result:
            for item in result.get("items", []):
                track = item.get("track")
                if not track or track.get("is_local"):
                    continue  # ignorar pistas locales
                tracks.append(self._to_track(track))
            result = sp.next(result) if result.get("next") else None
        return tracks

    def get_liked_tracks(self) -> list[dict]:
        sp = self._require()
        tracks: list[dict] = []
        result = sp.current_user_saved_tracks(limit=50)
        while result:
            for item in result.get("items", []):
                track = item.get("track")
                if track:
                    tracks.append(self._to_track(track))
            result = sp.next(result) if result.get("next") else None
        return tracks

    @staticmethod
    def _to_track(track: dict) -> dict:
        artists = ", ".join(a["name"] for a in track.get("artists", []) if a.get("name"))
        return {
            "title": track.get("name", ""),
            "artist": artists,
            "album": (track.get("album") or {}).get("name", ""),
        }
