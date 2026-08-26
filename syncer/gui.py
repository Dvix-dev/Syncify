"""Interfaz gráfica de Syncify (Spotify → YouTube Music)."""
from __future__ import annotations

import queue
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .config import (
    CONFIG_DIR,
    YT_AUTH_FILE,
    load_config,
    save_config,
)
from .engine import SyncEngine, SyncOptions
from .spotify_client import SpotifyClient
from .ytmusic_client import YTMusicClient

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class YTMAuthDialog(ctk.CTkToplevel):
    """Diálogo para conectar YouTube Music pegando los headers del navegador."""

    def __init__(self, master, on_success):
        super().__init__(master)
        self.title("Conectar YouTube Music")
        self.geometry("680x520")
        self.grab_set()
        self.on_success = on_success

        ctk.CTkLabel(
            self,
            text="Conectar YouTube Music (paso a paso):",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(padx=16, pady=(14, 4), anchor="w")
        steps = (
            "1. Abre music.youtube.com e inicia sesión.\n"
            "2. Pulsa F12 y abre 'Red' / 'Network'.\n"
            "3. Recarga la página (Ctrl+R).\n"
            "4. Filtra por 'browse' y selecciona una petición POST.\n"
            "5. Clic derecho → 'Copy' → 'Copy request headers'.\n"
            "6. Pega aquí el texto completo y pulsa Conectar.\n\n"
            "Importante: no compartas estos headers; contienen tu sesión.\n"
            "Se guardan solo en tu equipo y pueden caducar."
        )
        ctk.CTkLabel(self, text=steps, justify="left").pack(padx=16, pady=(0, 8), anchor="w")

        self.textbox = ctk.CTkTextbox(self, wrap="none")
        self.textbox.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(btns, text="Conectar", width=140, command=self._connect).pack(side="left")
        ctk.CTkButton(btns, text="Abrir guía online", width=150, fg_color="gray", command=lambda: __import__("webbrowser").open("https://ytmusicapi.readthedocs.io/en/stable/setup/browser.html")).pack(side="left", padx=8)
        ctk.CTkButton(
            btns, text="Usar archivo existente…", width=180, fg_color="gray",
            command=self._use_file,
        ).pack(side="left", padx=8)
        self.status = ctk.CTkLabel(btns, text="")
        self.status.pack(side="left", padx=8)

    def _use_file(self):
        path = filedialog.askopenfilename(
            title="Selecciona archivo de autenticación (JSON)",
            initialdir=CONFIG_DIR,
            filetypes=[("JSON", "*.json")],
        )
        if path:
            self.destroy()
            self.on_success(path)

    def _connect(self):
        raw = self.textbox.get("1.0", "end").strip()
        if not raw:
            self.status.configure(text="Pega los headers primero.", text_color="orange")
            return
        try:
            path = YTMusicClient.save_headers_auth(raw)
        except Exception as e:
            self.status.configure(text=f"Headers inválidos: {e}", text_color="red")
            return
        self.destroy()
        self.on_success(path)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Syncify · Spotify → YouTube Music")
        self.geometry("960x700")
        self.minsize(820, 560)

        self.cfg = load_config()
        self.spotify = SpotifyClient()
        self.yt = YTMusicClient()
        self.engine: SyncEngine | None = None
        self.queue: queue.Queue = queue.Queue()
        self.playlist_vars: dict[str, tk.BooleanVar] = {}

        self._build_ui()
        self.after(100, self._poll_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----------------------------- UI ---------------------------------- #

    def _build_ui(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=12, pady=(12, 6))

        # --- Tarjeta Spotify ---
        sp_card = ctk.CTkFrame(top)
        sp_card.pack(side="left", fill="both", expand=True, padx=(0, 6))
        ctk.CTkLabel(sp_card, text="Syncify · Spotify", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        form = ctk.CTkFrame(sp_card, fg_color="transparent")
        form.pack(fill="x", padx=12)
        ctk.CTkLabel(form, text="Client ID:", width=110, anchor="w").grid(row=0, column=0, sticky="w")
        self.sp_id_entry = ctk.CTkEntry(form, width=300)
        self.sp_id_entry.insert(0, self.cfg.get("spotify_client_id", ""))
        self.sp_id_entry.grid(row=0, column=1, sticky="ew", pady=2)
        ctk.CTkLabel(form, text="Client Secret:", width=110, anchor="w").grid(row=1, column=0, sticky="w")
        self.sp_secret_entry = ctk.CTkEntry(form, width=300, show="•")
        self.sp_secret_entry.insert(0, self.cfg.get("spotify_client_secret", ""))
        self.sp_secret_entry.grid(row=1, column=1, sticky="ew", pady=2)
        form.columnconfigure(1, weight=1)

        row = ctk.CTkFrame(sp_card, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(4, 10))
        self.sp_connect_btn = ctk.CTkButton(row, text="Conectar con Spotify", command=self._connect_spotify, width=170)
        self.sp_connect_btn.pack(side="left")
        self.sp_status = ctk.CTkLabel(row, text="● Desconectado", text_color="#e05555")
        self.sp_status.pack(side="left", padx=10)

        # --- Tarjeta YouTube Music ---
        yt_card = ctk.CTkFrame(top)
        yt_card.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ctk.CTkLabel(yt_card, text="YouTube Music", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=12, pady=(8, 2)
        )
        hint = ctk.CTkLabel(
            yt_card,
            text="Conecta tu cuenta de YouTube Music de forma segura.\nLa app te guiará para importar una sesión del navegador.",
            justify="left",
        )
        hint.pack(anchor="w", padx=12)
        yrow = ctk.CTkFrame(yt_card, fg_color="transparent")
        yrow.pack(fill="x", padx=12, pady=(6, 10))
        self.yt_connect_btn = ctk.CTkButton(yrow, text="Conectar YouTube Music", command=self._open_yt_dialog, width=190)
        self.yt_connect_btn.pack(side="left")
        self.yt_disconnect_btn = ctk.CTkButton(yrow, text="Desconectar", width=100, fg_color="gray",
                                               command=self._disconnect_yt, state="disabled")
        self.yt_disconnect_btn.pack(side="left", padx=6)
        self.yt_status = ctk.CTkLabel(yrow, text="● Desconectado", text_color="#e05555")
        self.yt_status.pack(side="left", padx=10)

        # --- Opciones ---
        opts = ctk.CTkFrame(self)
        opts.pack(fill="x", padx=12, pady=6)
        self.liked_var = tk.BooleanVar(value=self.cfg.get("include_liked", True))
        ctk.CTkCheckBox(opts, text="Incluir canciones con 'me gusta'", variable=self.liked_var).pack(
            side="left", padx=12, pady=8
        )
        self.thumb_var = tk.BooleanVar(value=self.cfg.get("thumb_up_on_yt", False))
        ctk.CTkCheckBox(opts, text="Dar 'me gusta' en YT Music", variable=self.thumb_var).pack(
            side="left", padx=12
        )
        ctk.CTkLabel(opts, text="Playlist de me gusta:").pack(side="left", padx=(20, 4))
        self.likes_name_entry = ctk.CTkEntry(opts, width=220)
        self.likes_name_entry.insert(0, self.cfg.get("liked_playlist_name", "Me gusta (desde Spotify)"))
        self.likes_name_entry.pack(side="left")
        ctk.CTkLabel(opts, text="Privacidad:").pack(side="left", padx=(20, 4))
        self.privacy_menu = ctk.CTkOptionMenu(
            opts, values=["PRIVATE", "PUBLIC", "UNLISTED"], width=120,
            command=lambda v: self._save(),
        )
        self.privacy_menu.set(self.cfg.get("privacy", "PRIVATE"))
        self.privacy_menu.pack(side="left")

        # --- Cuerpo: playlists + log ---
        body = ctk.CTkFrame(self)
        body.pack(fill="both", expand=True, padx=12, pady=6)

        left = ctk.CTkFrame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        lhead = ctk.CTkFrame(left, fg_color="transparent")
        lhead.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(lhead, text="Playlists de Spotify", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(lhead, text="Refrescar", width=90, fg_color="gray", command=self._load_playlists).pack(side="right")
        self.playlists_frame = ctk.CTkScrollableFrame(left)
        self.playlists_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        right = ctk.CTkFrame(body)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ctk.CTkLabel(right, text="Registro", font=ctk.CTkFont(weight="bold"), anchor="w").pack(
            fill="x", padx=10, pady=(8, 2)
        )
        self.log_box = ctk.CTkTextbox(right, state="disabled", wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # --- Pie: progreso + botones ---
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=12, pady=(6, 12))
        self.progress = ctk.CTkProgressBar(bottom)
        self.progress.set(0)
        self.progress.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=10)
        self.progress_label = ctk.CTkLabel(bottom, text="0 %", width=60)
        self.progress_label.pack(side="left")
        self.sync_btn = ctk.CTkButton(bottom, text="Sincronizar seleccionadas", command=self._start_sync, width=210)
        self.sync_btn.pack(side="left", padx=8)
        self.stop_btn = ctk.CTkButton(bottom, text="Detener", command=self._stop_sync, width=90,
                                      fg_color="#a33", state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 12))

    # ------------------------ Conexiones -------------------------------- #

    def _save(self):
        self.cfg.update(
            {
                "spotify_client_id": self.sp_id_entry.get().strip(),
                "spotify_client_secret": self.sp_secret_entry.get().strip(),
                "include_liked": self.liked_var.get(),
                "liked_playlist_name": self.likes_name_entry.get().strip() or "Me gusta (desde Spotify)",
                "thumb_up_on_yt": self.thumb_var.get(),
                "privacy": self.privacy_menu.get(),
            }
        )
        save_config(self.cfg)

    def _connect_spotify(self):
        cid = self.sp_id_entry.get().strip()
        secret = self.sp_secret_entry.get().strip()
        if not cid or not secret:
            messagebox.showwarning(
                "Faltan credenciales",
                "Introduce el Client ID y Client Secret de tu app de\n"
                "developer.spotify.com/dashboard (ver README).",
                parent=self,
            )
            return
        self._save()
        self.sp_status.configure(text="● Conectando…", text_color="orange")
        self.update()
        try:
            name = self.spotify.connect(cid, secret)
        except Exception as e:
            self.sp_status.configure(text="● Error", text_color="#e05555")
            messagebox.showerror("Error de conexión", str(e), parent=self)
            return
        self.sp_status.configure(text=f"● Conectado: {name}", text_color="#4cc94c")
        self.sp_connect_btn.configure(state="disabled")
        self._load_playlists()

    def _open_yt_dialog(self):
        dialog = YTMAuthDialog(self, on_success=self._connect_yt_with_file)
        if YT_AUTH_FILE and __import__("os").path.exists(YT_AUTH_FILE):
            # Si ya existe un auth previo, ofrecer conectar directo
            pass

    def _connect_yt_with_file(self, path: str):
        self.yt_status.configure(text="● Conectando…", text_color="orange")
        self.update()
        try:
            account = self.yt.connect(path)
        except Exception as e:
            self.yt_status.configure(text="● Error", text_color="#e05555")
            messagebox.showerror("YouTube Music", f"No se pudo conectar:\n{e}", parent=self)
            return
        self.yt_status.configure(text=f"● Conectado: {account}", text_color="#4cc94c")
        self.yt_connect_btn.configure(state="disabled")
        self.yt_disconnect_btn.configure(state="normal")

    def _disconnect_yt(self):
        self.yt.disconnect()
        self.yt_status.configure(text="● Desconectado", text_color="#e05555")
        self.yt_connect_btn.configure(state="normal")
        self.yt_disconnect_btn.configure(state="disabled")

    # ------------------------- Playlists -------------------------------- #

    def _load_playlists(self):
        for w in self.playlists_frame.winfo_children():
            w.destroy()
        self.playlist_vars.clear()
        if not self.spotify.connected:
            ctk.CTkLabel(self.playlists_frame, text="Conéctate a Spotify para ver tus playlists.").pack(pady=20)
            return
        try:
            playlists = self.spotify.get_playlists()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron listar las playlists:\n{e}", parent=self)
            return
        if not playlists:
            ctk.CTkLabel(self.playlists_frame, text="No hay playlists propias o colaborativas.").pack(pady=20)
            return
        for p in playlists:
            var = tk.BooleanVar(value=True)
            self.playlist_vars[p["id"]] = var
            label = f'{p["name"]}  ({p["tracks"]} temas)'
            ctk.CTkCheckBox(self.playlists_frame, text=label, variable=var).pack(anchor="w", padx=10, pady=3)

    # --------------------------- Sync ----------------------------------- #

    def _selected_ids(self) -> list[str]:
        return [pid for pid, var in self.playlist_vars.items() if var.get()]

    def _start_sync(self):
        if not self.spotify.connected or not self.yt.connected:
            messagebox.showwarning("Sin conexión", "Conecta ambas cuentas antes de sincronizar.", parent=self)
            return
        selected = self._selected_ids()
        include_liked = self.liked_var.get()
        if not selected and not include_liked:
            messagebox.showinfo("Nada seleccionado", "Selecciona al menos una playlist.", parent=self)
            return
        self._save()
        options = SyncOptions(
            include_liked=include_liked,
            liked_playlist_name=self.likes_name_entry.get().strip() or "Me gusta (desde Spotify)",
            thumb_up_on_yt=self.thumb_var.get(),
            privacy=self.privacy_menu.get(),
            match_threshold=float(self.cfg.get("match_threshold", 0.62)),
        )
        self.engine = SyncEngine(
            self.spotify,
            self.yt,
            on_log=lambda msg: self.queue.put(("log", msg)),
            on_progress=lambda d, t: self.queue.put(("progress", d, t)),
            on_done=lambda res, err: self.queue.put(("done", res, err)),
        )
        self.sync_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.set(0)
        self._log("— Iniciando sincronización —")
        self.engine.start(selected, options)

    def _stop_sync(self):
        if self.engine:
            self.engine.stop()

    # -------------------------- Cola ------------------------------------- #

    def _poll_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._log(item[1])
                elif kind == "progress":
                    done, total = item[1], max(item[2], 1)
                    frac = min(done / total, 1.0)
                    self.progress.set(frac)
                    self.progress_label.configure(text=f"{int(frac * 100)} %")
                elif kind == "done":
                    err = item[2]
                    self.sync_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    if err and err != "detenida":
                        messagebox.showerror("Sincronización", f"Terminó con error:\n{err}", parent=self)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _log(self, msg: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_close(self):
        if self.engine and self.engine.is_running:
            self.engine.stop()
        self._save()
        self.destroy()


def run() -> None:
    app = App()
    app.mainloop()
