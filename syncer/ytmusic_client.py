"""Cliente de YouTube Music (escritura de playlists y me gusta)."""
from __future__ import annotations

import os

import ytmusicapi

from .config import YT_AUTH_FILE


class YTMusicClient:
    def __init__(self) -> None:
        self.yt: ytmusicapi.YTMusic | None = None

    @property
    def connected(self) -> bool:
        return self.yt is not None

    @staticmethod
    def save_headers_auth(headers_raw: str, filepath: str = YT_AUTH_FILE) -> str:
        """Convierte los headers copiados del navegador en un archivo de autenticación."""
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
        ytmusicapi.setup(filepath=filepath, headers_raw=headers_raw)
        return filepath

    def connect(self, auth_file: str) -> str:
        """Carga la autenticación y verifica que funcione. Devuelve el nombre de cuenta."""
        yt = ytmusicapi.YTMusic(auth_file)
        # Prueba de que la autenticación es válida
        library = yt.get_library_playlists(limit=1)
        self.yt = yt
        account = ""
        try:
            info = yt.get_account_info()
            account = (info.get("accountInfo") or {}).get("name", "")
        except Exception:
            pass  # no es crítico mostrar el nombre de la cuenta
        if account is None and library is None:
            raise RuntimeError("Autenticación inválida")
        return account or "cuenta de YouTube Music"

    def disconnect(self) -> None:
        self.yt = None

    def _require(self) -> ytmusicapi.YTMusic:
        if self.yt is None:
            raise RuntimeError("No conectado a YouTube Music")
        return self.yt

    def get_playlists(self) -> list[dict]:
        playlists = self._require().get_library_playlists(limit=200) or []
        return [
            {"id": p["playlistId"], "name": p.get("title", ""), "tracks": p.get("count", 0)}
            for p in playlists
            if p.get("playlistId")
        ]

    def find_playlist_by_name(self, name: str) -> str | None:
        for p in self.get_playlists():
            if p["name"].strip().lower() == name.strip().lower():
                return p["id"]
        return None

    def create_playlist(self, title: str, privacy: str = "PRIVATE") -> str:
        pid = self._require().create_playlist(
            title=title,
            description=f"Sincronizado desde Spotify · {title}",
            privacy_status=privacy,
        )
        if not pid:
            raise RuntimeError(f"No se pudo crear la playlist '{title}'")
        return pid

    def get_existing_video_ids(self, playlist_id: str) -> set[str]:
        try:
            pl = self._require().get_playlist(playlist_id, limit=10000)
        except Exception:
            return set()
        ids: set[str] = set()
        for t in pl.get("tracks", []):
            vid = t.get("videoId")
            if vid and t.get("available", True):
                ids.add(vid)
        return ids

    def search_song(self, query: str, limit: int = 5) -> list[dict]:
        try:
            results = self._require().search_songs(query, limit=limit) or []
        except Exception:
            return []
        songs = []
        for r in results:
            artists = ", ".join(a["name"] for a in r.get("artists", []) if a.get("name"))
            songs.append(
                {
                    "videoId": r["videoId"],
                    "title": r.get("title", ""),
                    "artist": artists,
                }
            )
        return songs

    def add_items(self, playlist_id: str, video_ids: list[str]) -> None:
        self._require().add_playlist_items(playlist_id, videoIds=video_ids)

    def rate_song_like(self, video_id: str) -> None:
        self._require().rate_song(video_id, rating="LIKE")

    def get_liked_song_ids(self, limit: int = 5000) -> set[str]:
        try:
            res = self._require().get_liked_songs(limit=limit)
        except Exception:
            return set()
        return {t["videoId"] for t in res.get("tracks", []) if t.get("videoId")}
