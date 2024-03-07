from tkinter.font import families, nametofont


def first_available_font(*names) -> str:
    fonts = families()
    for name in names:
        if name in fonts:
            return name
    return "times"


def setup_style(root):
    sans = first_available_font(
        "Ubuntu", "DejaVu Sans", "Sans", "Segoe UI", "Helvetica"
    )
    mono = first_available_font(
        "Iosevka", "DejaVu Sans Mono", "Ubuntu Mono", "Monaco", "Consolas", "Monospace",
    )
    nametofont("TkDefaultFont").configure(family=sans)
    nametofont("TkFixedFont").configure(family=mono)
