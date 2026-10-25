"""Paleta y controles ttk; clam permite respetar los colores en Windows."""
from tkinter import ttk

BG = "#101827"
CARD = "#162133"
FIELD = "#202e43"
TEXT = "#e5edf8"
MUTED = "#94a5bd"
MINT = "#70d1ba"
RED = "#ef818e"
AMBER = "#e8bb70"
GREEN = "#8bdaa2"
BORDER = "#304057"


def configure_theme(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TNotebook",background=BG,borderwidth=0,bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER)
    style.configure("TNotebook.Tab",background=FIELD,foreground=MUTED,padding=(16,9),bordercolor=BORDER,lightcolor=BORDER,darkcolor=BORDER)
    style.map("TNotebook.Tab",background=[("selected",CARD),("active","#2b4059")],foreground=[("selected",TEXT)])
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
    style.configure("Card.TLabel", background=CARD)
    style.configure("Title.TLabel", font=("Segoe UI", 21, "bold"))
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)
    style.configure("Eyebrow.TLabel", foreground=MINT, font=("Segoe UI", 9, "bold"))
    style.configure("CardHeading.TLabel", background=CARD, font=("Segoe UI", 11, "bold"))
    style.configure("TButton", background=CARD, foreground=TEXT, bordercolor=BORDER,
                    lightcolor=CARD, darkcolor=CARD, font=("Segoe UI", 10), padding=(11, 8), borderwidth=1)
    for name, color, foreground, hover in (("TButton", CARD, TEXT, "#26364d"),
                                          ("Accent.TButton", MINT, BG, "#96e4d1"),
                                          ("Danger.TButton", "#482937", RED, "#663444")):
        style.configure(name, background=color, foreground=foreground, bordercolor=RED if name.startswith("Danger") else BORDER,
                        lightcolor=color, darkcolor=color)
        style.map(name, background=[("disabled", "#1d2a3c"), ("pressed", hover), ("active", hover)],
                  foreground=[("disabled", "#66758c")], bordercolor=[("disabled", "#283448"), ("focus", MINT)],
                  lightcolor=[("disabled", "#1d2a3c"), ("active", hover)], darkcolor=[("disabled", "#1d2a3c"), ("active", hover)])
    style.configure("Compact.TButton", padding=(8, 5), font=("Segoe UI", 9))
    style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT, insertcolor=MINT,
                    bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD, padding=8)
    style.map("TEntry", fieldbackground=[("disabled", CARD)], foreground=[("disabled", "#66758c")],
              bordercolor=[("focus", MINT)], lightcolor=[("focus", MINT)], darkcolor=[("focus", MINT)])
    style.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=TEXT, arrowcolor=MUTED,
                    bordercolor=BORDER, lightcolor=FIELD, darkcolor=FIELD, padding=7)
    style.map("TCombobox", fieldbackground=[("disabled", CARD), ("readonly", FIELD)],
              foreground=[("disabled", "#66758c"), ("readonly", TEXT)], background=[("active", "#2b4059")],
              bordercolor=[("focus", MINT)], lightcolor=[("focus", MINT)], darkcolor=[("focus", MINT)])
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", "#285b69")
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT, rowheight=32,
                    borderwidth=0, bordercolor=FIELD, lightcolor=FIELD, darkcolor=FIELD, font=("Segoe UI", 10))
    style.map("Treeview", background=[("selected", "#284657")], foreground=[])
    style.configure("Treeview.Heading", background=FIELD, foreground=TEXT, bordercolor=CARD,
                    lightcolor=FIELD, darkcolor=FIELD, font=("Segoe UI", 10, "bold"), padding=(10, 8))
    style.map("Treeview.Heading", background=[("active", "#2b4059")])
    style.configure("Vertical.TScrollbar", background="#34465e", troughcolor=CARD, arrowcolor=MUTED,
                    bordercolor=CARD, lightcolor=CARD, darkcolor=CARD, gripcount=0, arrowsize=12)
    style.map("Vertical.TScrollbar", background=[("active", "#48657d"), ("pressed", "#48657d")])
    style.configure("Horizontal.TProgressbar", background=MINT, troughcolor=FIELD, bordercolor=FIELD,
                    lightcolor=MINT, darkcolor=MINT, thickness=7)
