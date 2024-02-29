import dataclasses
from functools import partial
from pathlib import Path
import platform
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showinfo, showwarning
from tkinter.font import Font, families, nametofont
import webbrowser

from shroudstone import config, renamer, stormgateworld as sgw
from shroudstone.logging import configure_logging
from shroudstone.sgw_api import PlayersApi
from .jobs import TkWithJobs

import logging

logger = logging.getLogger(__name__)


class StringVar(tk.StringVar):
    def on_change(self, func):
        self.trace_add("write", func)


class BoolVar(tk.BooleanVar):
    def on_change(self, func):
        self.trace_add("write", func)


def field(factory, **kw):
    return dataclasses.field(default_factory=partial(factory, **kw))


@dataclasses.dataclass
class AppState:
    player_id: StringVar = field(StringVar)
    player_id_state: StringVar = field(StringVar)
    nickname_text: StringVar = field(StringVar)
    replay_dir: StringVar = field(StringVar)
    replay_name_format: StringVar = field(StringVar)
    reprocess: BoolVar = field(BoolVar)
    dry_run: BoolVar = field(BoolVar)
    autorename: BoolVar = field(BoolVar)


def run():
    configure_logging()
    renamer.migrate()
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
            nickname = PlayersApi.get_player(pid).nickname
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
        configure_replay_dir(root, state, cfg)
        if cfg.replay_dir and (player := renamer.guess_player(cfg.replay_dir)):
            state.player_id.set(player.id)
            cfg.my_player_id = player.id
            showinfo(
                title="Stormgate World Player ID Detected",
                message="Autodetected your player identity: "
                f"player_id={player.id}, nickname={player.nickname}",
            )
            cfg.save()
            root.deiconify()  # No need to show setup window
        else:
            player_id_setup(root, state, cfg)
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


def configure_replay_dir(root: TkWithJobs, state: AppState, cfg: config.Config):
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


def player_id_setup(root: TkWithJobs, state: AppState, cfg: config.Config):
    dialog = tk.Toplevel()
    dialog.geometry("800x300")
    dialog.title("Shroudstone First-Time Setup")
    text = tk.Text(dialog, height=7, font="TkDefaultFont")
    text.pack(side="top", fill="both", expand=True)
    append = partial(text.insert, "end")
    append(
        "Unfortunately, we could not automatically determine your Stormgate World Player ID. To find it:\n"
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
        cfg.save()
        root.deiconify()

    button = ttk.Button(row, text="Continue", command=submit)
    button.pack(side="left")

    row.pack(side="top")

    # Terminate the program if this window is closed:
    dialog.protocol("WM_DELETE_WINDOW", root.destroy)


def rename_replays_wrapper(*args, **kwargs):
    try:
        return renamer.rename_replays(*args, **kwargs)
    except Exception as e:
        logger.exception(
            "Unexpected error occurred! Please report here: "
            "https://github.com/acarapetis/shroudstone/issues"
        )


def main_ui(root: TkWithJobs, state: AppState, cfg: config.Config):
    def reload_config():
        nonlocal cfg
        cfg = config.Config.load()
        state.player_id.set(cfg.my_player_id or "")
        state.replay_dir.set(str(cfg.replay_dir or ""))
        state.replay_name_format.set(cfg.replay_name_format)

    root.title("Shroudstone - Stormgate Replay Renamer")

    # root.resizable(width=False, height=False)
    # heading = ttk.Label(
    #     root, text="Shroudstone", font="TkHeadingFont",
    # )
    # heading.pack(fill="x")

    config_frame = ttk.LabelFrame(root, text="Configuration")
    config_frame.pack(fill="x", padx=5, pady=5)

    form = ttk.Frame(config_frame)
    form.pack(fill="x")

    form.columnconfigure(0, weight=0)
    form.columnconfigure(1, weight=1)

    ttk.Label(form, text="Your Player ID", justify="right").grid(
        row=0,
        column=0,
        sticky="E",
        padx=2,
        pady=2,
    )
    player_cell = ttk.Frame(form)
    player_cell.grid(row=0, column=1, sticky="W")
    player_id_entry = ttk.Entry(
        player_cell, width=6, font="TkFixedFont", textvariable=state.player_id
    )
    player_id_entry.pack(side="left", fill="y", ipadx=2, ipady=2)
    nickname_label = tk.Label(player_cell, textvariable=state.nickname_text)
    nickname_label.pack(side="left", fill="y", ipadx=2, ipady=2)

    ttk.Label(form, text="Replay Directory", justify="right").grid(
        row=1, column=0, sticky="E", padx=2, pady=2
    )
    replay_dir_row = ttk.Frame(form)
    replay_dir_row.grid(row=1, column=1, sticky="NSEW")
    replay_dir_entry = ttk.Entry(
        replay_dir_row, width=50, textvariable=state.replay_dir
    )
    replay_dir_entry.pack(side="left", fill="both", ipadx=2, ipady=2, expand=True)

    replay_dir_error = ttk.Label(form)
    replay_dir_error.grid(row=2, column=1, sticky="WE", ipadx=5, ipady=5)

    def browse_replay_dir():
        current = Path(state.replay_dir.get())
        initial = current if current.exists() else None
        new = askdirectory(
            title="Stormgate Replay Directory", initialdir=initial, mustexist=True
        )
        state.replay_dir.set(new)

    def guess_replay_dir():
        rd = renamer.guess_replay_dir()
        if rd is not None:
            state.replay_dir.set(str(rd))

    ttk.Button(replay_dir_row, text="Browse", command=browse_replay_dir).pack(
        side="left", fill="y", padx=2, ipadx=2, ipady=2
    )

    ttk.Button(replay_dir_row, text="Autodetect", command=guess_replay_dir).pack(
        side="left", fill="y", padx=2, ipadx=2, ipady=2
    )

    @state.replay_dir.on_change
    def validate_replay_dir(*args):
        path = Path(state.replay_dir.get())
        if path.is_dir():
            replay_dir_error.configure(text="Looks good!", background="#66ff66")
            cfg.replay_dir = path
            save_config.configure(state="normal")
            rename_button.configure(state="normal")
        else:
            replay_dir_error.configure(
                text="Directory does not exist!", background="#ff6666"
            )
            save_config.configure(state="disabled")
            rename_button.configure(state="disabled")

    @state.replay_name_format.on_change
    def validate_format(*args):
        fstr = state.replay_name_format.get()
        try:
            renamer.validate_format_string(fstr)
        except ValueError as e:
            format_error.configure(text=f"Error: {e}", background="#ff6666")
            save_config.configure(state="disabled")
            rename_button.configure(state="disabled")
        else:
            format_error.configure(text="Looks good!", background="#66ff66")
            cfg.replay_name_format = fstr
            save_config.configure(state="normal")
            rename_button.configure(state="normal")

    ttk.Label(form, text="Desired Name Format", justify="right").grid(
        row=3, column=0, sticky="E", padx=2, pady=2
    )
    format_entry = ttk.Entry(
        form,
        width=100,
        textvariable=state.replay_name_format,
    )
    format_entry.grid(row=3, column=1, sticky="WE", ipadx=2, ipady=2)
    format_error = ttk.Label(form)
    format_error.grid(row=4, column=1, sticky="WE", ipadx=5, ipady=5)

    config_buttons = ttk.Frame(config_frame)
    config_buttons.pack(fill="x")

    save_config = ttk.Button(config_buttons, text="Save Config", command=cfg.save)
    save_config.pack(side="right", fill="both", padx=3, pady=3)

    load_config = ttk.Button(
        config_buttons, text="Reload Config", command=reload_config
    )
    load_config.pack(side="right", fill="both", padx=3, pady=3)

    def rename_replays():
        rename_button.config(
            text="Renaming in progress - See console window",
            state="disabled",
        )

        def callback(_):
            rename_button.config(
                text="Rename My Replays Now",
                state="normal",
            )

        cfg.replay_dir = Path(state.replay_dir.get())
        cfg.replay_name_format = state.replay_name_format.get()
        cfg.my_player_id = state.player_id.get()

        root.jobs.submit(
            rename_replays_wrapper,
            callback,
            replay_dir=cfg.replay_dir,
            format=cfg.replay_name_format,
            my_player_id=cfg.my_player_id,
            reprocess=state.reprocess.get(),
            dry_run=state.dry_run.get(),
        )

    options_frame = ttk.LabelFrame(root, text="Options")
    options_frame.pack(fill="x", padx=5, pady=5)

    reprocess_cb = tk.Checkbutton(
        options_frame,
        variable=state.reprocess,
        text="Reprocess replays that have already been renamed",
    )
    reprocess_cb.pack(anchor="w")
    dry_run_cb = tk.Checkbutton(
        options_frame,
        variable=state.dry_run,
        text="Dry run - don't actually rename file, just show output",
    )
    dry_run_cb.pack(anchor="w")

    rename_button = ttk.Button(
        root,
        text="Rename My Replays Now",
        command=rename_replays,
    )

    rename_button.pack(fill="x")

    autorename_cb = ttk.Checkbutton(
        root, text="Automatically rename new replays", variable=state.autorename
    )
    autorename_cb.pack(padx=5, pady=5)

    autorename_ref = None

    @state.autorename.on_change
    def _(*_):
        nonlocal autorename_ref
        if autorename_ref is not None:
            root.after_cancel(autorename_ref)
            autorename_ref = None
        if state.autorename.get():

            def doit():
                nonlocal autorename_ref
                rename_replays()
                autorename_ref = root.after(30000, doit)

            doit()

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
