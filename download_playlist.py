import os
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog

import yt_dlp


# --- Config ---

BROWSERS = ["chrome", "edge", "firefox", "opera", "brave", "vivaldi"]

MODES = ["Video(s)", "Playlist(s)", "Chaine complete"]

QUALITIES = {
    "2160p (4K)":      "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]/best",
    "1080p (Full HD)": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]/best",
    "720p (HD)":       "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]/best",
    "480p":            "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]/best",
    "360p":            "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]/best",
    "Audio uniquement": "bestaudio/best",
}

AUDIO_FORMATS = ["mp3", "wav", "flac", "aac"]

SUBTITLE_LANGS = ["fr", "en", "es", "de", "pt", "ar", "zh", "ja", "ko", "it", "ru"]

NODE_PATH = shutil.which("node")
ARIA2C_PATH = shutil.which("aria2c")


# --- Logique ---

def clean_folder_name(name):
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name if name else "download"


def base_opts():
    opts = {}
    if NODE_PATH:
        opts["js_runtimes"] = {"node": {"path": NODE_PATH}}
    opts["remote_components"] = {"ejs": "github"}
    return opts


def aria2c_opts():
    if not ARIA2C_PATH:
        return {}
    return {
        "external_downloader": {"default": "aria2c"},
        "external_downloader_args": {
            "aria2c": [
                "--max-connection-per-server=16",
                "--min-split-size=1M",
                "--split=16",
                "--max-overall-download-limit=0",
            ],
        },
    }


def build_cookie_opts(cookie_mode, cookie_value):
    if cookie_mode == "file" and cookie_value and os.path.isfile(cookie_value):
        return {"cookiefile": cookie_value}
    elif cookie_mode == "browser" and cookie_value:
        return {"cookiesfrombrowser": (cookie_value,)}
    return {}


def build_audio_postprocessor(audio_fmt):
    return [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": audio_fmt,
        "preferredquality": "192" if audio_fmt == "mp3" else "0",
    }]


def build_subtitle_opts(subs_enabled, sub_lang):
    if not subs_enabled:
        return {}
    return {
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [sub_lang, f"{sub_lang}.*"],
        "subtitlesformat": "srt/best",
    }


def fetch_channel_playlists(channel_url, cookie_opts, log_func):
    log_func(f"  Scan de la chaine : {channel_url}")
    log_func(f"  Recuperation des playlists...")

    url = channel_url.rstrip("/")
    if not url.endswith("/playlists"):
        url += "/playlists"

    opts = base_opts()
    opts.update({"quiet": True, "extract_flat": True})
    opts.update(cookie_opts)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info or "entries" not in info:
        log_func("  ERREUR : impossible de recuperer les playlists.")
        return []

    urls = [e["url"] for e in info.get("entries", []) if e and e.get("url")]
    log_func(f"  {len(urls)} playlists trouvees !")
    return urls


def fetch_channel_all_videos(channel_url, cookie_opts, log_func):
    """Recupere le lien /videos d'une chaine pour tout telecharger."""
    log_func(f"  Scan complet de la chaine : {channel_url}")

    url = channel_url.rstrip("/")
    # Retirer un eventuel suffixe et mettre /videos
    for suffix in ["/playlists", "/videos", "/shorts", "/streams", "/community", "/about"]:
        if url.endswith(suffix):
            url = url[:-len(suffix)]
            break
    url += "/videos"

    log_func(f"  URL : {url}")
    return url


def make_progress_hook(tag, log_func):
    def progress_hook(d):
        if d["status"] == "downloading":
            pct = d.get("_percent_str", "?")
            speed = d.get("_speed_str", "?")
            log_func(f"  {tag} {pct}  {speed}", replace_last=True)
        elif d["status"] == "finished":
            log_func(f"  {tag} Fichier termine.")
    return progress_hook


def download_one_item(url, index, total, output_dir, cookie_opts, quality_fmt,
                      is_audio, audio_fmt, fragments, sub_opts, playlist_range, log_func):
    """Telecharge un item (video, playlist, ou chaine). Retourne True si OK."""
    tag = f"[{index}/{total}]"

    log_func(f"\n{'='*50}")
    log_func(f"  {tag} {url}")
    log_func(f"{'='*50}\n")

    # Recuperer les infos
    log_func(f"  {tag} Recuperation des infos...")
    info_opts = base_opts()
    info_opts["quiet"] = True
    info_opts.update(cookie_opts)

    with yt_dlp.YoutubeDL(info_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            log_func(f"  {tag} ERREUR : {e}")
            return False

    if not info:
        log_func(f"  {tag} ERREUR : aucune info trouvee.")
        return False

    # Determiner le nom et le template de sortie
    is_playlist = "entries" in info
    title = info.get("title") or info.get("playlist_title") or "download"
    folder = clean_folder_name(title)

    if is_playlist:
        video_count = sum(1 for e in info.get("entries", []) if e)
        log_func(f"  {tag} Playlist : {title}")
        log_func(f"  {tag} Videos   : {video_count}")
        log_func(f"  {tag} Dossier  : {folder}/\n")
        out_path = f"{output_dir}/{folder}" if output_dir else folder
        outtmpl = f"{out_path}/%(playlist_index)03d - %(title)s.%(ext)s"
    else:
        log_func(f"  {tag} Video : {title}\n")
        out_path = output_dir if output_dir else "."
        outtmpl = f"{out_path}/%(title)s.%(ext)s"

    archive_path = f"{out_path}/.downloaded.txt" if is_playlist else None

    # Construire les options
    opts = base_opts()
    opts.update({
        "format": quality_fmt,
        "outtmpl": outtmpl,
        "ignoreerrors": True,
        "progress_hooks": [make_progress_hook(tag, log_func)],
        "concurrent_fragment_downloads": fragments,
    })
    opts.update(aria2c_opts())

    if archive_path:
        opts["download_archive"] = archive_path

    # Plage de videos (playlist uniquement)
    if is_playlist and playlist_range:
        start, end = playlist_range
        if start:
            opts["playliststart"] = start
        if end:
            opts["playlistend"] = end
        log_func(f"  {tag} Plage : videos {start or 1} a {end or 'fin'}")

    # Audio ou video
    if is_audio:
        opts["postprocessors"] = build_audio_postprocessor(audio_fmt)
    else:
        opts["merge_output_format"] = "mp4"

    # Sous-titres
    opts.update(sub_opts)

    opts.update(cookie_opts)

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    log_func(f"\n  {tag} '{title}' OK !")
    return True


def download_all(urls, output_dir, cookie_mode, cookie_value, quality_fmt,
                 is_audio, audio_fmt, fragments, parallel, sub_opts, playlist_range,
                 log_func, on_done):
    total = len(urls)
    cookie_opts = build_cookie_opts(cookie_mode, cookie_value)

    log_func(f"  {fragments} fragments simultanes par video")
    log_func(f"  {parallel} telechargement(s) en parallele\n")

    ok = 0
    fail = 0

    if parallel <= 1:
        for i, url in enumerate(urls, 1):
            if download_one_item(url, i, total, output_dir, cookie_opts, quality_fmt,
                                 is_audio, audio_fmt, fragments, sub_opts, playlist_range, log_func):
                ok += 1
            else:
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            futures = {}
            for i, url in enumerate(urls, 1):
                f = pool.submit(download_one_item, url, i, total, output_dir, cookie_opts,
                                quality_fmt, is_audio, audio_fmt, fragments, sub_opts, playlist_range, log_func)
                futures[f] = url

            for f in as_completed(futures):
                try:
                    if f.result():
                        ok += 1
                    else:
                        fail += 1
                except Exception as e:
                    log_func(f"  ERREUR : {e}")
                    fail += 1

    log_func(f"\n{'='*50}")
    log_func(f"  TERMINE — {ok} reussie(s), {fail} echouee(s)")
    log_func(f"{'='*50}")
    on_done()


# --- Interface graphique ---

BG = "#1e1e2e"
SURFACE = "#2a2a3d"
COOKIE_BG = "#252538"
ACCENT = "#7c3aed"
ACCENT_HOVER = "#6d28d9"
TEXT_COLOR = "#e2e8f0"
MUTED = "#94a3b8"
GREEN = "#22c55e"
ORANGE = "#f59e0b"
BLUE = "#3b82f6"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("750x820")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(600, 700)

        self.output_dir = tk.StringVar(value="")
        self.cookie_mode = tk.StringVar(value="file")
        self.browser_var = tk.StringVar(value="chrome")
        self.cookie_file = tk.StringVar(value="")
        self.quality_var = tk.StringVar(value="1080p (Full HD)")
        self.audio_fmt_var = tk.StringVar(value="mp3")
        self.fragments_var = tk.StringVar(value="4")
        self.parallel_var = tk.StringVar(value="3")
        self.mode_var = tk.StringVar(value="Video(s)")
        self.subs_var = tk.BooleanVar(value=False)
        self.sub_lang_var = tk.StringVar(value="fr")
        self.range_start_var = tk.StringVar(value="")
        self.range_end_var = tk.StringVar(value="")
        self.channel_url = tk.StringVar(value="")
        self.downloading = False
        self.fetching = False

        self._setup_styles()
        self._build_ui()
        self._on_mode_change()

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=TEXT_COLOR, font=("Segoe UI", 16, "bold"))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                         font=("Segoe UI", 11, "bold"), padding=(20, 10))
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER), ("disabled", "#4a4a5e")])
        style.configure("Dir.TButton", background=SURFACE, foreground=TEXT_COLOR,
                         font=("Segoe UI", 9), padding=(10, 5))
        style.map("Dir.TButton", background=[("active", "#3a3a4d")])
        style.configure("Channel.TButton", background="#1e3a5f", foreground=TEXT_COLOR,
                         font=("Segoe UI", 9), padding=(10, 5))
        style.map("Channel.TButton", background=[("active", "#254a6f"), ("disabled", "#4a4a5e")])
        style.configure("Mode.TRadiobutton", background=BG, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.map("Mode.TRadiobutton", background=[("active", BG)])

    def _build_ui(self):
        # Canvas scrollable pour les petits ecrans
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        main = ttk.Frame(canvas, padding=20)
        canvas.create_window((0, 0), window=main, anchor="nw")

        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # Titre
        ttk.Label(main, text="YouTube Downloader", style="Title.TLabel").pack(pady=(0, 5))
        ttk.Label(main, text="Telecharge des videos, playlists ou chaines completes",
                  style="Muted.TLabel").pack()

        # === MODE DE TELECHARGEMENT ===
        ttk.Label(main, text="Mode :").pack(anchor="w", pady=(14, 5))
        mode_frame = ttk.Frame(main)
        mode_frame.pack(fill="x")
        for m in MODES:
            ttk.Radiobutton(mode_frame, text=m, variable=self.mode_var, value=m,
                            style="Mode.TRadiobutton", command=self._on_mode_change).pack(side="left", padx=(0, 20))

        # === CHAINE (visible seulement en mode Chaine/Playlist) ===
        self.channel_frame = tk.Frame(main, bg="#1a1a2e", bd=0, highlightthickness=1,
                                      highlightbackground="#3a3a5e")
        channel_pad = tk.Frame(self.channel_frame, bg="#1a1a2e")
        channel_pad.pack(fill="x", padx=10, pady=8)

        tk.Label(channel_pad, text="Lien de la chaine :", bg="#1a1a2e", fg=ORANGE,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        channel_row = tk.Frame(channel_pad, bg="#1a1a2e")
        channel_row.pack(fill="x", pady=(5, 0))

        self.channel_entry = tk.Entry(channel_row, textvariable=self.channel_url, bg=SURFACE, fg=TEXT_COLOR,
                                      insertbackground=TEXT_COLOR, font=("Consolas", 10), bd=0,
                                      selectbackground=ACCENT)
        self.channel_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 8))

        self.fetch_btn = ttk.Button(channel_row, text="Recuperer les playlists", style="Channel.TButton",
                                    command=self._fetch_channel)
        self.fetch_btn.pack(side="right")

        # === ZONE DE LIENS ===
        self.links_label = ttk.Label(main, text="Liens :")
        input_frame = tk.Frame(main, bg=SURFACE, bd=0, highlightthickness=1, highlightbackground="#3a3a5e")
        self.input_frame_ref = input_frame
        self.input_text = tk.Text(input_frame, height=5, bg=SURFACE, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                                  font=("Consolas", 10), bd=0, padx=10, pady=10,
                                  selectbackground=ACCENT, wrap="word")
        self.input_text.pack(fill="x")

        self.link_count_label = tk.Label(main, text="0 lien(s)", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.input_text.bind("<KeyRelease>", self._update_link_count)

        # === QUALITE + VITESSE ===
        settings_frame = ttk.Frame(main)
        self.settings_frame_ref = settings_frame

        ttk.Label(settings_frame, text="Qualite :").pack(side="left")
        self.quality_combo = ttk.Combobox(settings_frame, textvariable=self.quality_var,
                                          values=list(QUALITIES.keys()), state="readonly", width=20)
        self.quality_combo.pack(side="left", padx=(8, 0))
        self.quality_combo.bind("<<ComboboxSelected>>", self._on_quality_change)

        # Format audio (visible seulement si Audio uniquement)
        self.audio_fmt_label = ttk.Label(settings_frame, text="  Format :")
        self.audio_fmt_combo = ttk.Combobox(settings_frame, textvariable=self.audio_fmt_var,
                                            values=AUDIO_FORMATS, state="readonly", width=6)

        ttk.Label(settings_frame, text="  Parallele :").pack(side="left", padx=(12, 0))
        ttk.Spinbox(settings_frame, from_=1, to=10, textvariable=self.parallel_var,
                    width=3, font=("Segoe UI", 10)).pack(side="left", padx=(4, 0))

        ttk.Label(settings_frame, text="  Fragments :").pack(side="left", padx=(12, 0))
        ttk.Spinbox(settings_frame, from_=1, to=16, textvariable=self.fragments_var,
                    width=3, font=("Segoe UI", 10)).pack(side="left", padx=(4, 0))

        # === SOUS-TITRES ===
        self.subs_frame = ttk.Frame(main)
        tk.Checkbutton(self.subs_frame, text="Telecharger les sous-titres", variable=self.subs_var,
                       bg=BG, fg=TEXT_COLOR, selectcolor="#3a3a5e", activebackground=BG,
                       activeforeground=TEXT_COLOR, font=("Segoe UI", 10)).pack(side="left")
        ttk.Label(self.subs_frame, text="  Langue :").pack(side="left")
        ttk.Combobox(self.subs_frame, textvariable=self.sub_lang_var,
                     values=SUBTITLE_LANGS, state="readonly", width=5).pack(side="left", padx=(4, 0))

        # === PLAGE DE VIDEOS (playlist uniquement) ===
        self.range_frame = ttk.Frame(main)
        ttk.Label(self.range_frame, text="Plage de videos :").pack(side="left")
        ttk.Label(self.range_frame, text="  De :").pack(side="left", padx=(8, 0))
        ttk.Entry(self.range_frame, textvariable=self.range_start_var, width=5,
                  font=("Segoe UI", 10)).pack(side="left", padx=(4, 0))
        ttk.Label(self.range_frame, text="  A :").pack(side="left", padx=(8, 0))
        ttk.Entry(self.range_frame, textvariable=self.range_end_var, width=5,
                  font=("Segoe UI", 10)).pack(side="left", padx=(4, 0))
        ttk.Label(self.range_frame, text="  (vide = tout)", style="Muted.TLabel").pack(side="left", padx=(8, 0))

        # === COOKIES ===
        ttk.Label(main, text="Authentification YouTube :").pack(anchor="w", pady=(10, 5))
        cookie_frame = tk.Frame(main, bg=COOKIE_BG, bd=0, highlightthickness=1, highlightbackground="#3a3a5e")
        cookie_frame.pack(fill="x")
        cookie_pad = tk.Frame(cookie_frame, bg=COOKIE_BG)
        cookie_pad.pack(fill="x", padx=12, pady=8)

        row1 = tk.Frame(cookie_pad, bg=COOKIE_BG)
        row1.pack(fill="x", pady=(0, 3))
        tk.Radiobutton(row1, text="Fichier cookies.txt (recommande)", variable=self.cookie_mode,
                       value="file", bg=COOKIE_BG, fg=TEXT_COLOR, selectcolor="#3a3a5e",
                       activebackground=COOKIE_BG, activeforeground=TEXT_COLOR,
                       font=("Segoe UI", 10), command=self._update_cookie_ui).pack(side="left")
        self.cookie_file_btn = ttk.Button(row1, text="Choisir le fichier", style="Dir.TButton",
                                          command=self._pick_cookie_file)
        self.cookie_file_btn.pack(side="right")

        self.cookie_file_label = tk.Label(cookie_pad, text="  Aucun fichier selectionne",
                                          bg=COOKIE_BG, fg=MUTED, font=("Segoe UI", 9))
        self.cookie_file_label.pack(anchor="w", pady=(0, 6))

        row2 = tk.Frame(cookie_pad, bg=COOKIE_BG)
        row2.pack(fill="x", pady=(0, 3))
        tk.Radiobutton(row2, text="Depuis le navigateur", variable=self.cookie_mode,
                       value="browser", bg=COOKIE_BG, fg=TEXT_COLOR, selectcolor="#3a3a5e",
                       activebackground=COOKIE_BG, activeforeground=TEXT_COLOR,
                       font=("Segoe UI", 10), command=self._update_cookie_ui).pack(side="left")
        self.browser_combo = ttk.Combobox(row2, textvariable=self.browser_var,
                                          values=BROWSERS, state="disabled", width=10)
        self.browser_combo.pack(side="right")
        tk.Label(cookie_pad, text="  Fermer le navigateur avant de lancer !",
                 bg=COOKIE_BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")

        # === DOSSIER ===
        dir_frame = ttk.Frame(main)
        dir_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(dir_frame, text="Dossier de destination :").pack(side="left")
        ttk.Button(dir_frame, text="Choisir un dossier", style="Dir.TButton",
                   command=self._pick_dir).pack(side="right")
        self.dir_label = ttk.Label(main, text="Dossier courant (par defaut)", style="Muted.TLabel")
        self.dir_label.pack(anchor="w", pady=(3, 0))

        # === BOUTON ===
        self.btn = ttk.Button(main, text="Telecharger", style="Accent.TButton", command=self._start)
        self.btn.pack(pady=12)

        # === CONSOLE ===
        ttk.Label(main, text="Progression :").pack(anchor="w", pady=(0, 5))
        log_frame = tk.Frame(main, bg=SURFACE, bd=0, highlightthickness=1, highlightbackground="#3a3a5e")
        log_frame.pack(fill="both", expand=True)
        self.log = scrolledtext.ScrolledText(log_frame, bg=SURFACE, fg="#a0f0a0", font=("Consolas", 9),
                                             bd=0, padx=10, pady=10, state="disabled",
                                             insertbackground=TEXT_COLOR, wrap="word", height=10)
        self.log.pack(fill="both", expand=True)

        # Sauvegarder la ref du main frame pour le placement dynamique
        self.main_frame = main

    def _on_mode_change(self):
        mode = self.mode_var.get()

        # Cacher tout
        self.channel_frame.pack_forget()
        self.links_label.pack_forget()
        self.input_frame_ref.pack_forget()
        self.link_count_label.pack_forget()
        self.settings_frame_ref.pack_forget()
        self.subs_frame.pack_forget()
        self.range_frame.pack_forget()

        if mode == "Chaine complete":
            self.channel_frame.pack(in_=self.main_frame, fill="x", pady=(10, 0), after=self._get_mode_frame())
            self.fetch_btn.config(text="Tout telecharger")
        elif mode == "Playlist(s)":
            self.channel_frame.pack(in_=self.main_frame, fill="x", pady=(10, 0), after=self._get_mode_frame())
            self.fetch_btn.config(text="Recuperer les playlists")
            self.links_label.pack(in_=self.main_frame, anchor="w", pady=(10, 5), after=self.channel_frame)
            self.input_frame_ref.pack(in_=self.main_frame, fill="x", after=self.links_label)
            self.link_count_label.pack(in_=self.main_frame, anchor="e", after=self.input_frame_ref)
            self.links_label.config(text="Liens des playlists (un par ligne) :")
            # Plage
            self.range_frame.pack(in_=self.main_frame, fill="x", pady=(8, 0), after=self.link_count_label)
            # Settings apres range
            self.settings_frame_ref.pack(in_=self.main_frame, fill="x", pady=(8, 0), after=self.range_frame)
        else:
            # Video(s)
            self.links_label.pack(in_=self.main_frame, anchor="w", pady=(10, 5), after=self._get_mode_frame())
            self.input_frame_ref.pack(in_=self.main_frame, fill="x", after=self.links_label)
            self.link_count_label.pack(in_=self.main_frame, anchor="e", after=self.input_frame_ref)
            self.links_label.config(text="Liens des videos (un par ligne) :")
            self.settings_frame_ref.pack(in_=self.main_frame, fill="x", pady=(8, 0), after=self.link_count_label)

        if mode != "Chaine complete":
            # Sous-titres apres settings
            last = self.settings_frame_ref
            self.subs_frame.pack(in_=self.main_frame, fill="x", pady=(8, 0), after=last)

        if mode == "Chaine complete":
            self.settings_frame_ref.pack(in_=self.main_frame, fill="x", pady=(8, 0), after=self.channel_frame)
            self.subs_frame.pack(in_=self.main_frame, fill="x", pady=(8, 0), after=self.settings_frame_ref)

    def _get_mode_frame(self):
        """Retourne le widget frame du mode radio pour le placement."""
        for w in self.main_frame.winfo_children():
            if isinstance(w, ttk.Frame):
                for child in w.winfo_children():
                    if isinstance(child, ttk.Radiobutton):
                        return w
        return self.main_frame.winfo_children()[1]

    def _on_quality_change(self, event=None):
        is_audio = "Audio" in self.quality_var.get()
        if is_audio:
            self.audio_fmt_label.pack(in_=self.settings_frame_ref, side="left", padx=(12, 0),
                                      after=self.quality_combo)
            self.audio_fmt_combo.pack(in_=self.settings_frame_ref, side="left", padx=(4, 0),
                                      after=self.audio_fmt_label)
        else:
            self.audio_fmt_label.pack_forget()
            self.audio_fmt_combo.pack_forget()

    def _update_link_count(self, event=None):
        raw = self.input_text.get("1.0", "end").strip()
        count = len([u for u in raw.splitlines() if u.strip()])
        self.link_count_label.config(text=f"{count} lien(s)")

    def _get_cookie_opts(self):
        mode = self.cookie_mode.get()
        if mode == "file":
            return build_cookie_opts("file", self.cookie_file.get())
        else:
            return build_cookie_opts("browser", self.browser_var.get())

    def _fetch_channel(self):
        if self.fetching:
            return
        url = self.channel_url.get().strip()
        if not url:
            self._log("Colle le lien de la chaine YouTube d'abord.")
            return

        cookie_opts = self._get_cookie_opts()
        mode = self.mode_var.get()
        self.fetching = True
        self.fetch_btn.config(state="disabled")

        if mode == "Chaine complete":
            # Pas besoin de fetcher, on lance le telechargement directement
            self._log("Chaine complete selectionnee — le lien sera utilise directement.")
            video_url = fetch_channel_all_videos(url, cookie_opts, self._log)
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", video_url)
            self._update_link_count()
            self.fetching = False
            self.fetch_btn.config(state="normal")
            return

        self._log("Scan de la chaine en cours...")

        def _do_fetch():
            try:
                urls = fetch_channel_playlists(url, cookie_opts, self._log)
                if urls:
                    def _fill():
                        self.input_text.delete("1.0", "end")
                        self.input_text.insert("1.0", "\n".join(urls))
                        self._update_link_count()
                        self._log(f"\n  {len(urls)} liens ajoutes dans la zone de texte.")
                    self.after(0, _fill)
            except Exception as e:
                self._log(f"  ERREUR : {e}")
            finally:
                self.after(0, lambda: (
                    self.fetch_btn.config(state="normal"),
                    setattr(self, "fetching", False),
                ))

        threading.Thread(target=_do_fetch, daemon=True).start()

    def _update_cookie_ui(self):
        if self.cookie_mode.get() == "file":
            self.cookie_file_btn.config(state="normal")
            self.browser_combo.config(state="disabled")
        else:
            self.cookie_file_btn.config(state="disabled")
            self.browser_combo.config(state="readonly")

    def _pick_cookie_file(self):
        f = filedialog.askopenfilename(filetypes=[("Cookies TXT", "*.txt"), ("Tous", "*.*")])
        if f:
            self.cookie_file.set(f)
            self.cookie_file_label.config(text=f"  {os.path.basename(f)}", fg=GREEN)

    def _pick_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir.set(d)
            short = d if len(d) < 55 else "..." + d[-52:]
            self.dir_label.config(text=short)

    def _log(self, msg, replace_last=False):
        def _write():
            self.log.config(state="normal")
            if replace_last:
                self.log.delete("end-2l linestart", "end-1l lineend")
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log.config(state="disabled")
        self.after(0, _write)

    def _on_done(self):
        self.after(0, lambda: (
            self.btn.config(text="Telecharger", state="normal"),
            setattr(self, "downloading", False),
        ))

    def _start(self):
        if self.downloading:
            return

        mode = self.mode_var.get()

        # Recuperer les URLs
        if mode == "Chaine complete":
            url = self.channel_url.get().strip()
            if not url:
                self._log("Colle le lien de la chaine YouTube d'abord.")
                return
            cookie_opts_check = self._get_cookie_opts()
            video_url = fetch_channel_all_videos(url, cookie_opts_check, self._log)
            urls = [video_url]
        else:
            raw = self.input_text.get("1.0", "end").strip()
            urls = [u.strip() for u in raw.splitlines() if u.strip()]
            if not urls:
                self._log("Aucun lien fourni.")
                return

        # Cookies
        cookie_mode = self.cookie_mode.get()
        if cookie_mode == "file":
            cookie_value = self.cookie_file.get()
            if not cookie_value or not os.path.isfile(cookie_value):
                self._log("Selectionne un fichier cookies.txt d'abord !")
                return
        else:
            cookie_value = self.browser_var.get()

        # Options
        quality_key = self.quality_var.get()
        quality_fmt = QUALITIES.get(quality_key, QUALITIES["1080p (Full HD)"])
        is_audio = "Audio" in quality_key
        audio_fmt = self.audio_fmt_var.get() if is_audio else "mp3"
        fragments = max(1, int(self.fragments_var.get() or 4))
        parallel = max(1, int(self.parallel_var.get() or 3))

        sub_opts = build_subtitle_opts(self.subs_var.get(), self.sub_lang_var.get())

        # Plage
        playlist_range = None
        if mode == "Playlist(s)":
            start = self.range_start_var.get().strip()
            end = self.range_end_var.get().strip()
            if start or end:
                playlist_range = (int(start) if start.isdigit() else None,
                                  int(end) if end.isdigit() else None)

        self.downloading = True
        self.btn.config(text="Telechargement en cours...", state="disabled")
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self._log(f"Mode : {mode} | {len(urls)} lien(s) | {quality_key}")

        out = self.output_dir.get() or None
        t = threading.Thread(target=download_all,
                             args=(urls, out, cookie_mode, cookie_value, quality_fmt, is_audio,
                                   audio_fmt, fragments, parallel, sub_opts, playlist_range,
                                   self._log, self._on_done),
                             daemon=True)
        t.start()


if __name__ == "__main__":
    App().mainloop()
