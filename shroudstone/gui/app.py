from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
import platform
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo, showwarning
from tkinter.font import Font, families, nametofont
import webbrowser

from shroudstone import cli, config, renamer, stormgateworld as sgw
from .jobs import TkWithJobs

import logging

logger = logging.getLogger(__name__)


class StringVar(tk.StringVar):
    def on_change(self, func):
        self.trace_add("write", func)


@dataclass
class AppState:
    player_id: StringVar = field(default_factory=StringVar)
    player_id_state: StringVar = field(default_factory=StringVar)
    nickname_text: StringVar = field(default_factory=StringVar)
    replay_dir: StringVar = field(default_factory=StringVar)


def run():
    logger.info(
        "Keep this console open - it will show progress information during renaming."
    )
    cfg: config.Config = config.Config.load()

    root = TkWithJobs()
    setup_icon(root)
    state = AppState()
    setup_style()

    @state.player_id.on_change
    @root.debounce()
    def check_player_id():
        """Use Stormgate World API to fetch the nickname associated with a player_id."""
        value = state.player_id.get()
        state.player_id_state.set("loading")
        state.nickname_text.set("Checking...")

        def job(pid):
            nickname = sgw.get_nickname(pid)
            return pid, nickname

        def callback(tup):
            pid, nickname = tup
            # Only use the result if it's fresh:
            if state.player_id.get() == pid:
                state.player_id_state.set("valid" if nickname else "invalid")
                state.nickname_text.set(nickname or "Not Found")

        root.jobs.submit(job, callback, value)

    do_setup = cfg.replay_dir is None or cfg.my_player_id is None
    if do_setup:
        root.withdraw()  # Hide the main window to begin with
        first_time_setup(root, state, cfg)
    else:
        state.player_id.set(cfg.my_player_id or "")

    main_ui(root, state, cfg)
    root.mainloop()


def first_available_font(*names) -> str:
    fonts = families()
    for name in names:
        if name in fonts:
            return name
    return "times"


def setup_style():
    sans = first_available_font(
        "Ubuntu", "DejaVu Sans", "Sans", "Segoe UI", "Helvetica"
    )
    nametofont("TkDefaultFont").configure(family=sans)


def setup_icon(root: tk.Tk):
    assets_dir = Path(__file__).parent / "assets"
    if platform.system() == "Windows":
        # TODO: This .ico currently only has a 64x64px image in it, which looks
        # garbage when resized down to fit in window titlebars etc.
        window_icon = assets_dir / "shroudstone.ico"
        root.iconbitmap(str(window_icon))
    else:
        root.iconphoto(True, tk.PhotoImage(file=str(assets_dir / "shroudstone.png")))


def first_time_setup(root: TkWithJobs, state: AppState, cfg: config.Config):
    dialog = tk.Toplevel()
    dialog.geometry("800x300")
    dialog.title("Shroudstone First-Time Setup")
    text = tk.Text(dialog, height=7, font="TkDefaultFont")
    text.pack(side="top", fill="both", expand=True)
    append = partial(text.insert, "end")
    append(
        "You have not yet configured your Stormgate World player ID. To find it:\n"
        "1. visit "
    )
    append("https://stormgateworld.com/leaderboards/ranked_1v1", ["link"])
    append(
        " and search for your in-game nickname.\n"
        "2. find your account in the results and click on it.\n"
        "3. click the characters next to the '#' icon to copy your player ID.\n"
        "4. paste it below and click continue :)"
    )
    text.configure(state="disabled")

    def open_link(event):
        webbrowser.open("https://stormgateworld.com/leaderboards/ranked_1v1")

    text.tag_bind("link", "<Button-1>", open_link)
    text.tag_configure("link", foreground="blue", underline=True)

    row = ttk.Frame(dialog)
    label = ttk.Label(row, text="Player ID:")
    label.pack(side="left")
    entry = ttk.Entry(row, textvariable=state.player_id)
    entry.pack(side="left")
    nickname_label = tk.Label(row, textvariable=state.nickname_text)
    nickname_label.pack(side="left", fill="y")

    @state.nickname_text.on_change
    def _(*_):
        pid_state = state.player_id_state.get()
        button.configure(state="normal" if pid_state == "valid" else "disabled")
        nickname_label.config(
            bg={"valid": "#33ff33", "invalid": "#ff3333", "loading": "#ffff99"}[
                pid_state
            ]
        )

    def submit():
        cfg.my_player_id = state.player_id.get()
        dialog.withdraw()
        cfg.replay_dir = renamer.guess_replay_dir()
        if cfg.replay_dir is None:
            state.replay_dir.set("")
            showwarning(
                title="Stormgate Replay Directory",
                message="Could not automatically find your replay directory - "
                "please configure it manually on the next screen.",
            )
        else:
            state.replay_dir.set(str(cfg.replay_dir))
            showinfo(
                title="Stormgate Replay Directory",
                message=f"Detected your replay directory as {cfg.replay_dir}."
                " If this is incorrect, please configure it manually on the next screen.",
            )
        cfg.save()
        root.deiconify()

    button = ttk.Button(row, text="Continue", command=submit)
    button.pack(side="left")
    row.pack(side="top")

    # Terminate the program if this window is closed:
    dialog.protocol("WM_DELETE_WINDOW", root.destroy)


def main_ui(root: TkWithJobs, state: AppState, cfg: config.Config):
    def reload_config():
        nonlocal cfg
        cfg = config.Config.load()
        state.player_id.set(cfg.my_player_id or "")
        state.replay_dir.set(str(cfg.replay_dir or ""))

    root.title("Shroudstone - Stormgate Replay Renamer")

    # root.resizable(width=False, height=False)
    # heading = ttk.Label(
    #     root, text="Shroudstone", font="TkHeadingFont",
    # )
    # heading.pack(fill="x")

    form = ttk.Frame(root)
    form.pack(fill="x")

    form.columnconfigure(0, weight=0)
    form.columnconfigure(1, weight=1)
    form.columnconfigure(2, weight=0)

    ttk.Label(form, text="Your Stormgate World Player ID", justify="right").grid(
        row=0, column=0, sticky="E"
    )
    player_cell = ttk.Frame(form)
    player_cell.grid(row=0, column=1, sticky="W")
    player_id_entry = ttk.Entry(
        player_cell, width=6, font="TkFixedFont", textvariable=state.player_id
    )
    player_id_entry.pack(side="left", fill="y")
    nickname_label = tk.Label(player_cell, textvariable=state.nickname_text)
    nickname_label.pack(side="left", fill="y")

    ttk.Label(form, text="Stormgate Replay Directory", justify="right").grid(
        row=1, column=0, sticky="E"
    )
    replay_dir_entry = ttk.Entry(form, width=50, textvariable=state.replay_dir)
    replay_dir_entry.grid(row=1, column=1, sticky="WE")

    def guess_replay_dir():
        rd = renamer.guess_replay_dir()
        if rd is not None:
            state.replay_dir.set(str(rd))

    guess_replay_dir_button = ttk.Button(
        form, text="Autodetect", command=guess_replay_dir
    )
    guess_replay_dir_button.grid(row=1, column=2)

    def rename_replays():
        rename_button.config(
            text="Renaming in progress - See console window",
            state="disabled",
        )

        def callback(_):
            rename_button.config(
                text="Rename My Replays!",
                state="normal",
            )

        root.jobs.submit(cli.rename_replays, callback)

    rename_button = ttk.Button(
        root,
        text="Rename My Replays!",
        command=rename_replays,
    )

    rename_button.pack(fill="x")

    save_config = ttk.Button(root, text="Save Config", command=cfg.save)
    save_config.pack(fill="x")

    load_config = ttk.Button(root, text="Reload Config", command=reload_config)
    load_config.pack(fill="x")

    edit_config = ttk.Button(
        root,
        text="Edit Config File (Advanced Users)",
        command=partial(cli.edit_config, xdg_open=True),
    )
    edit_config.pack(fill="x")

    @state.nickname_text.on_change
    def _(*_):
        pid_state = state.player_id_state.get()
        save_config.configure(state="normal" if pid_state == "valid" else "disabled")
        rename_button.configure(state="normal" if pid_state == "valid" else "disabled")
        nickname_label.config(
            bg={"valid": "#33ff33", "invalid": "#ff3333", "loading": "#ffff99"}[
                pid_state
            ]
        )

    @state.replay_dir.on_change
    def _(*args):
        cfg.replay_dir = Path(state.replay_dir.get())

    reload_config()

    root.mainloop()
