import dataclasses
from functools import partial
from pathlib import Path
import platform
from threading import Thread, Event, get_ident
from typing import Optional
from pystray import Icon, Menu, MenuItem
from pystray._base import Icon as BaseIcon
from PIL import Image
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showinfo, showwarning, askyesno

from shroudstone import config, renamer, __version__
from shroudstone.gui.fonts import setup_style
from shroudstone.gui.logview import LogView
from shroudstone.logging import configure_logging
from .jobs import TkWithJobs

import logging

logger = logging.getLogger(__name__)
assets_dir = Path(__file__).parent / "assets"


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
    reprocess: BoolVar = field(BoolVar)
    dry_run: BoolVar = field(BoolVar)
    autorename: BoolVar = field(BoolVar)
    minimize_to_tray: BoolVar = field(BoolVar)
    show_log_on_autorename: BoolVar = field(BoolVar)


class App(TkWithJobs):
    systray_icon: Optional[BaseIcon] = None
    systray_thread: Optional[Thread] = None
    tray_quit_event: Event
    vars: AppState

    def quit_app(self):
        logger.debug(f"Running quit_app in {get_ident()}")
        if self.systray_thread:
            logger.debug("Joining tray icon thread")
            self.systray_thread.join()
        logger.debug("Destroying main Tk app")
        self.destroy()

    def on_window_close(self):
        if self.systray_icon and self.vars.minimize_to_tray.get():
            self.withdraw()
        else:
            self.request_exit()

    def request_exit(self):
        if (not self.vars.autorename.get()) or askyesno(
            title="Shroudstone - Exit?",
            message="You have autorenaming enabled, which will stop functioning if you exit the program.\n"
            "Consider enabling 'Minimize to tray' if you want to keep auto-renaming without this window open.\n\n"
            "Are you sure you want to exit?\n"
        ):
            # Ask the tray icon to quit
            if self.systray_icon is not None:
                self.systray_icon.stop()
                # When it's done cleaning up, tray_quit_event will be set,
                # so no further action required
            else:
                self.quit_app()

    def setup_tray_icon(self):
        self.systray_thread = Thread(target=self._tray_icon_thread)
        self.systray_thread.start()

    def _tray_icon_thread(self):
        state = self.vars
        def toggle_autorename():
            state.autorename.set(not state.autorename.get())

        def show():
            self.deiconify()
            self.wm_state("normal")
            self.tkraise()

        def hide():
            self.withdraw()

        image = Image.open(assets_dir / "shroudstone.png")
        menu = Menu(
            MenuItem("Show", show, default=True),
            MenuItem("Minimize to tray", hide),
            MenuItem(
                "Auto-renaming",
                toggle_autorename,
                checked=lambda item: state.autorename.get(),
            ),
            MenuItem("Quit", lambda: icon.stop()),
        )
        icon = self.systray_icon = Icon(
            name="Shroudstone",
            icon=image,
            title="Shroudstone: Stormgate Replay Renamer",
            menu=menu,
        )

        @state.autorename.on_change
        def _(*_):
            icon.update_menu()

        logger.debug(f"icon.run() in thread {get_ident()}")
        icon.run()
        logger.debug("icon.run done")
        self.tray_quit_event.set()


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vars = AppState()
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)
        logger.debug(f"Main thread is {get_ident()}")

        self.after(0, self.custom_startup)

    def custom_startup(self):
        """This method performs custom startup actions *after* the mainloop has started."""

        # The systray icon passes this message back from its thread when it's done:
        self.tray_quit_event = Event()
        def _check_quit_event():
            if self.tray_quit_event.is_set():
                self.quit_app()
            self.after(10, _check_quit_event)
        _check_quit_event()

        self.setup_tray_icon()



# TODO: Move the following methods inside our custom App class?
# We currently have some root.after calls in here, and some in our
# custom_startup method, so it's a bit of a mess. Definitely some kind of
# tidyup needs to be done.
def run():
    configure_logging()
    renamer.migrate()
    logger.info(
        "Keep this console open - it will show progress information during renaming."
    )
    cfg: config.Config = config.Config.load()

    root = App(className="Shroudstone")
    setup_style(root)
    setup_window_icon(root)

    if cfg.replay_dir is None:
        root.after(0, lambda: configure_replay_dir(root, root.vars, cfg))

    create_main_ui(root, cfg)
    root.mainloop()


def setup_window_icon(root: tk.Tk):
    if platform.system() == "Windows":
        # TODO: This .ico currently only has a 64x64px image in it, which looks
        # garbage when resized down to fit in window titlebars etc.
        window_icon = assets_dir / "shroudstone.ico"
        root.iconbitmap(str(window_icon))
    else:
        root.iconphoto(True, tk.PhotoImage(file=str(assets_dir / "shroudstone.png")))


def configure_replay_dir(root: TkWithJobs, state: AppState, cfg: config.Config):
    root.withdraw()  # Hide uninitialized main window while we show initial popups
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


def rename_replays_wrapper(*args, **kwargs):
    try:
        return renamer.rename_replays(*args, **kwargs)
    except Exception:
        logger.exception(
            "Unexpected error occurred! Please report here: "
            "https://github.com/acarapetis/shroudstone/issues"
        )


def create_main_ui(root: App, cfg: config.Config):
    state = root.vars
    def reload_config():
        nonlocal cfg
        cfg = config.Config.load()
        state.replay_dir.set(str(cfg.replay_dir or ""))
        state.replay_name_format_1v1.set(cfg.replay_name_format_1v1)
        state.replay_name_format_generic.set(cfg.replay_name_format_generic)
        state.minimize_to_tray.set(cfg.minimize_to_tray)
        state.show_log_on_autorename.set(cfg.show_log_on_autorename)

    def save_config():
        cfg.save()

    root.title(f"Shroudstone v{__version__} - Stormgate Replay Renamer")

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

    config_buttons = ttk.Frame(config_frame)
    config_buttons.pack(fill="x")

    save_config_button = ttk.Button(
        config_buttons, text="Save Config", command=save_config
    )
    save_config_button.pack(side="right", fill="both", padx=3, pady=3)

    load_config = ttk.Button(
        config_buttons, text="Reload Config", command=reload_config
    )
    load_config.pack(side="right", fill="both", padx=3, pady=3)

    renaming = False
    def rename_replays(auto: bool = False):
        nonlocal renaming
        if renaming:
            return
        renaming = True
        show_log = state.show_log_on_autorename.get() or not auto
        btn_text = "Renaming in progress"
        if show_log:
            btn_text += " - See log window"
            log_view.deiconify()
        rename_button.config(text=btn_text, state="disabled")

        def callback(_):
            rename_button.config(
                text="Rename My Replays Now",
                state="normal",
            )
            nonlocal renaming
            renaming = False

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

    gui_toggles = ttk.Frame(root)
    gui_toggles.pack(fill="x")

    ttk.Checkbutton(
        gui_toggles, text="Automatically rename new replays", variable=state.autorename
    ).pack(side="left", padx=5, pady=5)

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
                rename_replays(auto=True)
                autorename_ref = root.after(30000, doit)

            doit()

    ttk.Checkbutton(
        gui_toggles, text="Minimize to tray on close", variable=state.minimize_to_tray
    ).pack(side="left", padx=5, pady=5)

    ttk.Checkbutton(
        gui_toggles, text="Show Log when auto-renaming", variable=state.show_log_on_autorename
    ).pack(side="left", padx=5, pady=5)

    ttk.Button(gui_toggles, text="Exit", command=root.request_exit).pack(side="right", padx=5, pady=5)

    @state.replay_dir.on_change
    def _(*_):
        cfg.replay_dir = Path(state.replay_dir.get())

    @state.minimize_to_tray.on_change
    def _(*_):
        cfg.minimize_to_tray = state.minimize_to_tray.get()

    reload_config()

    log_view = LogView(root)
    log_view.withdraw()
    log_view.protocol("WM_DELETE_WINDOW", log_view.clear_and_close)
