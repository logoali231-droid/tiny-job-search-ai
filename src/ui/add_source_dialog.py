import tkinter as tk
from tkinter import messagebox
from sources import add_api_source

BG, PANEL, PANEL_2 = "#0f1419", "#1a1f2e", "#232938"
TEXT, TEXT_DIM, ACCENT = "#e6e6e6", "#a0a6b2", "#4f8ef7"
FONT = "DejaVu Sans"


class AddSourceDialog(tk.Toplevel):
    def __init__(self, parent, on_added=None):
        super().__init__(parent)
        self.title("Add a custom source")
        self.configure(bg=PANEL)
        self.geometry("560x520")
        self.transient(parent)
        self.grab_set()
        self.on_added = on_added

        pad = tk.Frame(self, bg=PANEL)
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(pad, text="Add a custom source", bg=PANEL, fg=TEXT,
                 font=(FONT, 14, "bold")).pack(anchor="w")
        tk.Label(pad, text="Provide a JSON API endpoint. Use {query} as placeholder.",
                 bg=PANEL, fg=TEXT_DIM, font=(FONT, 9)).pack(anchor="w", pady=(2, 16))

        self.fields = {}
        for label, key, hint in [
            ("Source name", "name", "e.g. My Board"),
            ("URL template", "url", "https://api.example.com/jobs?q={query}"),
            ("Title path", "title", "e.g. data.jobs.title or results.0.name"),
            ("Company path", "company", "e.g. data.jobs.company"),
            ("URL path", "url_path", "e.g. data.jobs.link"),
            ("Location path (optional)", "location", "e.g. data.jobs.city"),
        ]:
            tk.Label(pad, text=label, bg=PANEL, fg=TEXT_DIM,
                     font=(FONT, 9, "bold")).pack(anchor="w", pady=(8, 0))
            e = tk.Entry(pad, bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                         bd=0, font=(FONT, 10), highlightthickness=1,
                         highlightbackground=PANEL_2, highlightcolor=ACCENT)
            e.pack(fill="x", ipady=6, pady=(2, 0))
            e.insert(0, hint)
            e.bind("<FocusIn>", lambda ev, w=e, h=hint: w.delete(0, "end") if w.get() == h else None)
            self.fields[key] = (e, hint)

        btn_row = tk.Frame(pad, bg=PANEL)
        btn_row.pack(side="bottom", fill="x", pady=(16, 0))

        tk.Button(btn_row, text="Cancel", command=self.destroy,
                  bg=PANEL_2, fg=TEXT, bd=0, padx=16, pady=8,
                  font=(FONT, 10), cursor="hand2").pack(side="right", padx=(8, 0))
        tk.Button(btn_row, text="Add source", command=self._save,
                  bg=ACCENT, fg="#fff", bd=0, padx=16, pady=8,
                  font=(FONT, 10, "bold"), cursor="hand2").pack(side="right")

    def _val(self, key):
        e, hint = self.fields[key]
        v = e.get().strip()
        return "" if v == hint else v

    def _save(self):
        name = self._val("name")
        url = self._val("url")
        title = self._val("title")
        company = self._val("company")
        url_path = self._val("url_path")
        location = self._val("location")

        if not (name and url and title):
            messagebox.showerror("Missing fields", "Name, URL template and title path are required.")
            return
        if "{query}" not in url:
            messagebox.showerror("Bad URL", "URL template must contain {query}.")
            return

        add_api_source(name, url, title, company, url_path, location)
        if self.on_added:
            self.on_added()
        self.destroy()