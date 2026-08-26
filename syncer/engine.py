"""Motor de sincronización: lleva playlists y me gusta de Spotify a YouTube Music."""
from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field

from .spotify_client import SpotifyClient
from .ytmusic_client import YTMusicClient


def normalize(text: str) -> str:
    """Minúsculas, sin acentos, sin paréntesis/corchetes ni puntuación."""
    text = text.lower()
    text = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a, b).ratio()


@dataclass
class SyncOptions:
    include_liked: bool = True
    liked_playlist_name: str = "Me gusta (desde Spotify)"
    thumb_up_on_yt: bool = False
    privacy: str = "PRIVATE"
    match_threshold: float = 0.62


@dataclass
class SyncResult:
    matched: int = 0
    added: int = 0
    already_present: int = 0
    unmatched: list[str] = field(default_factory=list)


class SyncEngine:
    """Ejecuta la sincronización en un hilo y reporta progreso mediante callbacks."""

    def __init__(
        self,
        spotify: SpotifyClient,
        yt: YTMusicClient,
        on_log: Callable[[str], None],
        on_progress: Callable[[int, int], None],
        on_done: Callable[[SyncResult | None, str | None], None],
    ) -> None:
        self.spotify = spotify
        self.yt = yt
        self.on_log = on_log
        self.on_progress = on_progress
        self.on_done = on_done
        self.stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, selected_playlist_ids: list[str], options: SyncOptions) -> None:
        if self.is_running:
            raise RuntimeError("Ya hay una sincronización en curso")
        self.stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(list(selected_playlist_ids), options),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------ #

    def _log(self, msg: str) -> None:
        self.on_log(msg)

    def _check_stop(self) -> None:
        if self.stop_event.is_set():
            raise StopSync()

    def _find_best_match(self, title: str, artist: str, threshold: float) -> dict | None:
        query = f"{artist} {title}".strip()
        candidates = self.yt.search_song(query)
        n_title, n_artist = normalize(title), normalize(artist)
        best, best_score = None, 0.0
        for cand in candidates:
            t_score = similarity(normalize(cand["title"]), n_title)
            a_score = similarity(normalize(cand["artist"]), n_artist) if n_artist else 1.0
            score = t_score * 0.7 + a_score * 0.3
            if score > best_score:
                best, best_score = cand, score
        if best and best_score >= threshold:
            return best
        return None

    def _collect_tracks(self, playlist_ids: list[str], options: SyncOptions) -> list[tuple[str, list[dict]]]:
        sources: list[tuple[str, list[dict]]] = []
        for pid in playlist_ids:
            name = next((p["name"] for p in self.spotify.get_playlists() if p["id"] == pid), pid)
            tracks = self.spotify.get_playlist_tracks(pid)
            self._log(f"Spotify → '{name}': {len(tracks)} canciones")
            sources.append((name, tracks))
        if options.include_liked:
            liked = self.spotify.get_liked_tracks()
            self._log(f"Spotify → '{options.liked_playlist_name}' (me gusta): {len(liked)} canciones")
            sources.append((options.liked_playlist_name, liked))
        return sources

    def _run(self, playlist_ids: list[str], options: SyncOptions) -> None:
        result = SyncResult()
        try:
            sources = self._collect_tracks(playlist_ids, options)
            total = sum(len(t) for _, t in sources) or 1
            done = 0

            for name, tracks in sources:
                self._check_stop()
                self._log(f"▶ Sincronizando '{name}'…")
                target_id = self.yt.find_playlist_by_name(name)
                if target_id:
                    self._log(f"  Playlist existente encontrada en YT Music.")
                else:
                    target_id = self.yt.create_playlist(name, privacy=options.privacy)
                    self._log(f"  Playlist creada en YT Music.")

                existing = self.yt.get_existing_video_ids(target_id)
                liked_ids = self.yt.get_liked_song_ids() if options.thumb_up_on_yt else set()
                pending: list[str] = []

                for track in tracks:
                    if self.stop_event.is_set():
                        break
                    match = self._find_best_match(track["title"], track["artist"], options.match_threshold)
                    done += 1
                    self.on_progress(done, total)
                    if match is None:
                        result.unmatched.append(f"{track['artist']} — {track['title']}")
                        continue
                    result.matched += 1
                    vid = match["videoId"]
                    if vid in existing:
                        result.already_present += 1
                    else:
                        pending.append(vid)
                        existing.add(vid)

                    if options.thumb_up_on_yt and vid not in liked_ids:
                        try:
                            self.yt.rate_song_like(vid)
                            liked_ids.add(vid)
                        except Exception as e:
                            self._log(f"  ⚠ No se pudo dar me gusta a '{track['title']}': {e}")

                    if len(pending) >= 25:
                        self._flush(pending, target_id, result)

                if pending and not self.stop_event.is_set():
                    self._flush(pending, target_id, result)

            summary = (
                f"✔ Terminado: {result.matched} coincidencias, "
                f"{result.added} añadidas, {result.already_present} ya estaban, "
                f"{len(result.unmatched)} sin encontrar."
            )
            self._log(summary)
            if result.unmatched:
                self._log("Sin encontrar en YouTube Music:")
                for t in result.unmatched[:30]:
                    self._log(f"   · {t}")
                if len(result.unmatched) > 30:
                    self._log(f"   … y {len(result.unmatched) - 30} más")
            self.on_done(result, None)
        except StopSync:
            self._log("■ Sincronización detenida por el usuario.")
            self.on_done(None, "detenida")
        except Exception as e:
            self._log(f"✖ Error: {e}")
            self.on_done(None, str(e))

    def _flush(self, pending: list[str], playlist_id: str, result: SyncResult) -> None:
        batch, pending[:] = pending[:50], pending[50:]
        while batch:
            self._check_stop()
            try:
                self.yt.add_items(playlist_id, batch)
                result.added += len(batch)
                self._log(f"  + {len(batch)} canciones añadidas")
            except Exception as e:
                self._log(f"  ⚠ Error añadiendo lote: {e}")
            batch, pending[:] = pending[:50], pending[50:]
            time.sleep(1)


class StopSync(Exception):
    pass
