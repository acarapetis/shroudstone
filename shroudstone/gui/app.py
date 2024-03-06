import dataclasses
from functools import partial
from pathlib import Path
import platform
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showinfo, showwarning
from tkinter.font import families, nametofont

from shroudstone import config, renamer
from shroudstone.logging import configure_logging
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
    replay_dir: StringVar = field(StringVar)
    replay_name_format_1v1: StringVar = field(StringVar)
    replay_name_format_generic: StringVar = field(StringVar)
    duration_strategy: StringVar = field(StringVar)
    result_strategy: StringVar = field(StringVar)
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

    if cfg.replay_dir is None:
        configure_replay_dir(root, state, cfg)
        cfg.replay_dir = Path(state.replay_dir.get())
        cfg.save()

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


def rename_replays_wrapper(*args, **kwargs):
    try:
        return renamer.rename_replays(*args, **kwargs)
    except Exception:
        logger.exception(
            "Unexpected error occurred! Please report here: "
            "https://github.com/acarapetis/shroudstone/issues"
        )


def main_ui(root: TkWithJobs, state: AppState, cfg: config.Config):
    def reload_config():
        nonlocal cfg
        cfg = config.Config.load()
        state.replay_dir.set(str(cfg.replay_dir or ""))
        state.replay_name_format_1v1.set(cfg.replay_name_format_1v1)
        state.replay_name_format_generic.set(cfg.replay_name_format_generic)
        state.duration_strategy.set(cfg.duration_strategy.value)
        state.result_strategy.set(cfg.result_strategy.value)

    def save_config():
        cfg.save()

    root.title("Shroudstone - Stormgate Replay Renamer")

    config_frame = ttk.LabelFrame(root, text="Configuration")
    config_frame.pack(fill="x", padx=5, pady=5)

    form = ttk.Frame(config_frame)
    form.pack(fill="x")

    form.columnconfigure(0, weight=0)
    form.columnconfigure(1, weight=1)

    ttk.Label(form, text="Replay Directory", justify="right").grid(
        row=0, column=0, sticky="E", padx=2, pady=2
    )
    replay_dir_row = ttk.Frame(form)
    replay_dir_row.grid(row=0, column=1, sticky="NSEW")
    replay_dir_entry = ttk.Entry(
        replay_dir_row, width=50, textvariable=state.replay_dir
    )
    replay_dir_entry.pack(side="left", fill="both", ipadx=2, ipady=2, expand=True)

    replay_dir_error = ttk.Label(form)
    replay_dir_error.grid(row=1, column=1, sticky="WE", ipadx=5, ipady=5)

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
    def _(*_):
        path = Path(state.replay_dir.get())
        if path.is_dir():
            replay_dir_error.configure(text="Looks good!", background="#66ff66")
            cfg.replay_dir = path
            save_config_button.configure(state="normal")
            rename_button.configure(state="normal")
        else:
            replay_dir_error.configure(
                text="Directory does not exist!", background="#ff6666"
            )
            save_config_button.configure(state="disabled")
            rename_button.configure(state="disabled")

    @state.replay_name_format_1v1.on_change
    def _(*_):
        fstr = state.replay_name_format_1v1.get()
        try:
            renamer.validate_format_string(fstr, type="1v1")
        except ValueError as e:
            format_error_1v1.configure(text=f"Error: {e}", background="#ff6666")
            save_config_button.configure(state="disabled")
            rename_button.configure(state="disabled")
        else:
            format_error_1v1.configure(text="Looks good!", background="#66ff66")
            cfg.replay_name_format_1v1 = fstr
            save_config_button.configure(state="normal")
            rename_button.configure(state="normal")

    @state.replay_name_format_generic.on_change
    def _(*_):
        fstr = state.replay_name_format_generic.get()
        try:
            renamer.validate_format_string(fstr, type="generic")
        except ValueError as e:
            format_error_generic.configure(text=f"Error: {e}", background="#ff6666")
            save_config_button.configure(state="disabled")
            rename_button.configure(state="disabled")
        else:
            format_error_generic.configure(text="Looks good!", background="#66ff66")
            cfg.replay_name_format_generic = fstr
            save_config_button.configure(state="normal")
            rename_button.configure(state="normal")

    ttk.Label(form, text="New Filename Format (1v1)", justify="right").grid(
        row=3, column=0, sticky="E", padx=2, pady=2
    )
    format_entry_1v1 = ttk.Entry(
        form,
        width=100,
        textvariable=state.replay_name_format_1v1,
    )
    format_entry_1v1.grid(row=3, column=1, sticky="WE", ipadx=2, ipady=2)
    format_error_1v1 = ttk.Label(form)
    format_error_1v1.grid(row=4, column=1, sticky="WE", ipadx=5, ipady=5)

    ttk.Label(form, text="New Filename Format (other)", justify="right").grid(
        row=5, column=0, sticky="E", padx=2, pady=2
    )
    format_entry_generic = ttk.Entry(
        form,
        width=100,
        textvariable=state.replay_name_format_generic,
    )
    format_entry_generic.grid(row=5, column=1, sticky="WE", ipadx=2, ipady=2)
    format_error_generic = ttk.Label(form)
    format_error_generic.grid(row=6, column=1, sticky="WE", ipadx=5, ipady=5)

    result_frame = ttk.LabelFrame(config_frame, text="How to determine game result")
    result_frame.pack(fill="x")
    ttk.Radiobutton(
        result_frame,
        variable=state.result_strategy,
        value="prefer_stormgateworld",
        text="Prefer Stormgate World, fall back to replay",
    ).pack(side="left", padx=5, pady=5)
    ttk.Radiobutton(
        result_frame,
        variable=state.result_strategy,
        value="always_stormgateworld",
        text="Stormgate World only",
    ).pack(side="left", padx=5, pady=5)
    ttk.Radiobutton(
        result_frame,
        variable=state.result_strategy,
        value="always_replay",
        text="Replay only (incorrect in elimination scenarios!)",
    ).pack(side="left", padx=5, pady=5)

    duration_frame = ttk.LabelFrame(config_frame, text="How to determine game duration")
    duration_frame.pack(fill="x")
    ttk.Radiobutton(
        duration_frame,
        variable=state.duration_strategy,
        value="prefer_stormgateworld",
        text="Prefer Stormgate World, fall back to replay",
    ).pack(side="left", padx=5, pady=5)
    ttk.Radiobutton(
        duration_frame,
        variable=state.duration_strategy,
        value="always_stormgateworld",
        text="Stormgate World only (slightly inaccurate!)",
    ).pack(side="left", padx=5, pady=5)
    ttk.Radiobutton(
        duration_frame,
        variable=state.duration_strategy,
        value="always_replay",
        text="Replay only (incorrect in elimination scenarios!)",
    ).pack(side="left", padx=5, pady=5)

    config_buttons = ttk.Frame(config_frame)
    config_buttons.pack(fill="x")

    save_config_button = ttk.Button(config_buttons, text="Save Config", command=save_config)
    save_config_button.pack(side="right", fill="both", padx=3, pady=3)

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
        cfg.replay_name_format_1v1 = state.replay_name_format_1v1.get()
        cfg.replay_name_format_generic = state.replay_name_format_generic.get()

        root.jobs.submit(
            rename_replays_wrapper,
            callback,
            replay_dir=cfg.replay_dir,
            format_1v1=cfg.replay_name_format_1v1,
            format_generic=cfg.replay_name_format_generic,
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

    @state.replay_dir.on_change
    def _(*_):
        cfg.replay_dir = Path(state.replay_dir.get())

    @state.duration_strategy.on_change
    def _(*_):
        cfg.duration_strategy = config.Strategy(state.duration_strategy.get())

    @state.result_strategy.on_change
    def _(*_):
        cfg.result_strategy = config.Strategy(state.result_strategy.get())

    reload_config()
    root.mainloop()
