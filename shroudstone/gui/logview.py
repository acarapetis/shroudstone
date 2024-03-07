import tkinter as tk
from tkinter.font import Font, nametofont
from tkinter.scrolledtext import ScrolledText
import traceback
from queue import Empty, Queue
import logging

from .fonts import first_available_font


# We pipe log messages through a queue so that only the main thread touches Tk
class QueueHandler(logging.Handler):
    queue: Queue

    def __init__(self, queue: Queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        self.queue.put(record)


class LogView(tk.Toplevel):
    textbox: ScrolledText
    queue: Queue[logging.LogRecord]
    handler: QueueHandler

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mono = first_available_font(
            "Iosevka",
            "DejaVu Sans Mono",
            "Ubuntu Mono",
            "Monaco",
            "Consolas",
            "Monospace",
        )
        self.title("Shroudstone Log")
        self.geometry("1024x600")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.textbox = ScrolledText(
            self,
            font=Font(name="Term", family=mono, size=12),
            background="black",
            foreground="white",
        )
        self.textbox.grid(column=0, row=0, sticky="NSEW")
        self.textbox.configure(state="disabled")
        self.textbox.tag_config(
            "error",
            foreground="red",
            font=Font(name="TermBold", family=mono, size=12, weight="bold"),
        )
        self.textbox.tag_config("warning", foreground="orange")
        self.queue = Queue()
        self.handler = QueueHandler(self.queue)
        logging.getLogger().addHandler(self.handler)
        self.after(0, self.tick)

    def destroy(self):
        logging.getLogger().removeHandler(self.handler)
        return super().destroy()

    def tick(self):
        self.textbox.configure(state="normal")
        while True:
            try:
                record = self.queue.get_nowait()
            except Empty:
                break
            else:
                self.handle_record(record)
        self.textbox.configure(state="disabled")
        self.after(10, self.tick)

    def handle_record(self, record: logging.LogRecord):
        tags = []
        if record.levelno >= logging.WARNING:
            tags = ["warning"]
        if record.levelno >= logging.ERROR:
            tags = ["error"]
        self.textbox.insert(tk.END, f"{record.msg}\n", *tags)
        # if record.exc_info:
        #     tb = "\n".join(traceback.format_tb(record.exc_info[2]))
        #     self.textbox.insert(tk.END, tb, *tags)
        if record.exc_text:
            self.textbox.insert(tk.END, record.exc_text + "\n", *tags)

    def clear_and_close(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", tk.END)
        self.textbox.configure(state="disabled")
        self.withdraw()
