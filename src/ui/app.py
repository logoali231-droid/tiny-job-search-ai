import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_here))

load_dotenv()  # picks up .env from CWD or project root

from scrapers.gupy import GupyScraper

from config import (
    EXPERTISE_LEVELS,
    PERIOD_LABELS,
    Q_TABLE_PATH,
    ROLE_FAMILIES,
    SKILL_CATALOG,
    get_specialties,
)
from job_apis import FreeJobAPIClient
from q_agent import JobSearchQLearner
from scrapers.ciee_pr import CieePrScraper
from scrapers.puc_carreiras import PucCarreirasScraper
from scrapers.remotive import JobicyScraper, RemotiveScraper
from sources import all_sources, toggle_source
from ui.add_source_dialog import AddSourceDialog

BG, PANEL, PANEL_2, PANEL_3 = "#0f1419", "#1a1f2e", "#232938", "#2c3346"
ACCENT, ACCENT_HOV = "#4f8ef7", "#6ba1ff"
TEXT, TEXT_DIM, MUTED = "#e6e6e6", "#a0a6b2", "#6b7280"
SUCCESS, DANGER, WARN = "#4ade80", "#f87171", "#fbbf24"
BORDER, FONT = "#2a3142", "DejaVu Sans"

# Map source id → scraper instance
SCRAPERS = {
    "remotive": RemotiveScraper(),
    "jobicy": JobicyScraper(),
    "ciee_pr": CieePrScraper(),
    "puc_car": PucCarreirasScraper(),
    "gupy": GupyScraper(),          # ← adicione esta linha
}


def make_button(parent, text, command, bg=ACCENT, fg="#fff",
                hover_bg=ACCENT_HOV, font=(FONT, 11, "bold"),
                padx=18, pady=10):
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                  activebackground=hover_bg, activeforeground=fg,
                  font=font, bd=0, relief="flat", padx=padx, pady=pady,
                  cursor="hand2", highlightthickness=0)
    b.bind("<Enter>", lambda e: b.config(bg=hover_bg))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


class JobCard(tk.Frame):
    def __init__(self, parent, job, on_open):
        super().__init__(parent, bg=PANEL_2, padx=14, pady=12)
        left = tk.Frame(self, bg=PANEL_2)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text=job.get("title") or "(no title)", bg=PANEL_2,
                 fg=TEXT, font=(FONT, 12, "bold"), anchor="w",
                 justify="left", wraplength=560).pack(anchor="w")
        bits = [job.get("company", ""), job.get("location", ""), job.get("salary", "")]
        tk.Label(left, text="  ·  ".join(b for b in bits if b) or "—",
                 bg=PANEL_2, fg=TEXT_DIM, font=(FONT, 10),
                 anchor="w", justify="left", wraplength=560).pack(anchor="w", pady=(2, 0))
        tags = job.get("tags") or []
        if tags:
            tk.Label(left, text="  ".join(f"#{t}" for t in tags[:5]), bg=PANEL_2,
                     fg=ACCENT, font=(FONT, 9), anchor="w").pack(anchor="w", pady=(4, 0))
        right = tk.Frame(self, bg=PANEL_2)
        right.pack(side="right", fill="y", padx=(12, 0))
        tk.Label(right, text=job.get("source", ""), bg=PANEL_3, fg=WARN,
                 font=(FONT, 8, "bold"), padx=8, pady=3).pack(anchor="e")
        b = tk.Button(right, text="Open  ↗", command=lambda: on_open(job),
                      bg=ACCENT, fg="#fff", activebackground=ACCENT_HOV,
                      font=(FONT, 9, "bold"), bd=0, padx=12, pady=5,
                      cursor="hand2", highlightthickness=0)
        b.pack(anchor="e", pady=(8, 0))


class JobSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tiny Job Search AI")
        self.root.geometry("1280x820")
        self.root.minsize(1050, 680)
        self.root.configure(bg=BG)

        self.agent = JobSearchQLearner()
        self.agent.load(Q_TABLE_PATH)
        self.api = FreeJobAPIClient()

        self.selected_skills = []      # current skill chips
        self.current_jobs = []
        self.last_action = None
        self.searching = False

        self._setup_style()
        self._build_ui()
        self._refresh_stats()

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER,
                        padding=6)
        style.map("TCombobox",
                  fieldbackground=[("readonly", PANEL_2)],
                  foreground=[("readonly", TEXT)])
        style.configure("Vertical.TScrollbar", background=PANEL_2, troughcolor=BG,
                        bordercolor=BG, arrowcolor=MUTED)
        self.root.option_add("*TCombobox*Listbox.background", PANEL_2)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#fff")

    def _build_ui(self):
        header = tk.Frame(self.root, bg=PANEL, height=64)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="🎯  Tiny Job Search AI", bg=PANEL, fg=TEXT,
                 font=(FONT, 16, "bold")).pack(side="left", padx=22)
        self.header_stats = tk.Label(header, text="", bg=PANEL, fg=TEXT_DIM,
                                     font=(FONT, 10))
        self.header_stats.pack(side="right", padx=22)

        body = tk.Frame(self.root, bg=BG)
        body.pack(side="top", fill="both", expand=True)

        self._build_sidebar(body)
        self._build_content(body)

        status = tk.Frame(self.root, bg=PANEL, height=32)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)
        self.status_label = tk.Label(status, text="Ready.", bg=PANEL,
                                     fg=TEXT_DIM, font=(FONT, 9), anchor="w")
        self.status_label.pack(side="left", padx=14)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=PANEL, width=360)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Scrollable sidebar (because it now has a lot of content)
        canvas = tk.Canvas(sidebar, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(sidebar, orient="vertical", command=canvas.yview)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=sb.set)
        pad = tk.Frame(canvas, bg=PANEL)
        canvas.create_window((0, 0), window=pad, anchor="nw", width=340)
        pad.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        tk.Label(pad, text="Search Preferences", bg=PANEL, fg=TEXT,
                 font=(FONT, 13, "bold")).pack(anchor="w", padx=20, pady=(20, 2))

        # Role
        tk.Label(pad, text="Role Family", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=20, pady=(12, 0))
        self.role_var = tk.StringVar(value="software_engineering")
        self.role_cb = ttk.Combobox(pad, textvariable=self.role_var,
                                    values=ROLE_FAMILIES, state="readonly",
                                    font=(FONT, 10))
        self.role_cb.pack(fill="x", padx=20, pady=(4, 0))
        self.role_cb.bind("<<ComboboxSelected>>", self._on_role_change)

        # Specialty
        tk.Label(pad, text="Specialty", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=20, pady=(12, 0))
        self.spec_var = tk.StringVar(value="backend")
        self.spec_cb = ttk.Combobox(pad, textvariable=self.spec_var,
                                    values=get_specialties("software_engineering"),
                                    state="readonly", font=(FONT, 10))
        self.spec_cb.pack(fill="x", padx=20, pady=(4, 0))

        # Expertise
        tk.Label(pad, text="Expertise Level", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=20, pady=(12, 0))
        self.exp_var = tk.StringVar(value="mid")
        ttk.Combobox(pad, textvariable=self.exp_var, values=EXPERTISE_LEVELS,
                     state="readonly", font=(FONT, 10)).pack(fill="x", padx=20, pady=(4, 0))

        # Period
        tk.Label(pad, text="Current university period", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=20, pady=(12, 0))
        self.period_var = tk.StringVar(value=PERIOD_LABELS[0])
        ttk.Combobox(pad, textvariable=self.period_var, values=PERIOD_LABELS,
                     state="readonly", font=(FONT, 10)).pack(fill="x", padx=20, pady=(4, 0))

        # Skills (chips)
        tk.Label(pad, text="Skills (multi-select)", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=20, pady=(16, 0))

        self.skill_entry_var = tk.StringVar()
        ent_row = tk.Frame(pad, bg=PANEL)
        ent_row.pack(fill="x", padx=20, pady=(4, 0))
        ent = tk.Entry(ent_row, textvariable=self.skill_entry_var, bg=PANEL_2,
                       fg=TEXT, insertbackground=TEXT, bd=0,
                       font=(FONT, 10), highlightthickness=1,
                       highlightbackground=PANEL_2, highlightcolor=ACCENT)
        ent.pack(side="left", fill="x", expand=True, ipady=6)
        ent.bind("<Return>", lambda e: self._add_custom_skill())
        tk.Button(ent_row, text="+", command=self._add_custom_skill,
                  bg=ACCENT, fg="#fff", bd=0, padx=10, pady=4,
                  font=(FONT, 11, "bold"), cursor="hand2").pack(side="left", padx=(6, 0))

        self.chips_frame = tk.Frame(pad, bg=PANEL)
        self.chips_frame.pack(fill="x", padx=20, pady=(8, 0))

        # Skill catalogue picker (accordion-lite: a dropdown of categories)
        tk.Label(pad, text="Browse catalogue", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9)).pack(anchor="w", padx=20, pady=(10, 0))
        for cat, items in SKILL_CATALOG.items():
            row = tk.Frame(pad, bg=PANEL)
            row.pack(fill="x", padx=20, pady=(2, 0))
            tk.Label(row, text=cat, bg=PANEL, fg=TEXT_DIM,
                     font=(FONT, 8, "bold"), width=14, anchor="w").pack(side="left")
            var = tk.StringVar(value="add…")
            cb = ttk.Combobox(row, textvariable=var, values=items,
                              state="readonly", font=(FONT, 9), width=18)
            cb.pack(side="left", fill="x", expand=True)
            cb.bind("<<ComboboxSelected>>",
                    lambda e, v=var: (self._add_skill(v.get()), v.set("add…")))

        # Sources panel
        tk.Label(pad, text="Sources", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        self.sources_frame = tk.Frame(pad, bg=PANEL)
        self.sources_frame.pack(fill="x", padx=20)
        self._refresh_sources()

        tk.Button(pad, text="＋ Add custom source", command=self._open_add_source,
                  bg=PANEL_2, fg=TEXT, bd=0, padx=10, pady=6,
                  font=(FONT, 9), cursor="hand2").pack(fill="x", padx=20, pady=(8, 0))

        # Search button
        self.search_btn = make_button(pad, "🔍  Search Jobs", self._on_search,
                                      padx=10, pady=11)
        self.search_btn.pack(fill="x", padx=20, pady=(20, 20))

        # Feedback + stats pinned to bottom of the sidebar content (in-flow)
        fb = tk.Frame(pad, bg=PANEL)
        fb.pack(fill="x", padx=20, pady=(0, 20))
        tk.Label(fb, text="Rate the last search:", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9)).pack(anchor="w", pady=(0, 6))
        row = tk.Frame(fb, bg=PANEL)
        row.pack(fill="x")
        for symbol, reward, hov in [("👍", 1.0, SUCCESS), ("⏭️", 0.0, PANEL_3), ("👎", -1.0, DANGER)]:
            b = make_button(row, symbol, lambda r=reward: self._on_feedback(r),
                            bg=PANEL_2, hover_bg=hov, padx=0, pady=6, font=(FONT, 14))
            b.pack(side="left", expand=True, fill="x", padx=2)

        stats_box = tk.Frame(pad, bg=PANEL_2, padx=14, pady=12)
        stats_box.pack(fill="x", padx=20, pady=(0, 20))
        tk.Label(stats_box, text="🧠  Learning Stats", bg=PANEL_2, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w")
        self.stat_updates = tk.Label(stats_box, text="Updates: 0", bg=PANEL_2,
                                     fg=TEXT_DIM, font=(FONT, 9), anchor="w")
        self.stat_updates.pack(anchor="w", pady=(6, 0))
        self.stat_strategies = tk.Label(stats_box, text="Strategies: 0", bg=PANEL_2,
                                        fg=TEXT_DIM, font=(FONT, 9), anchor="w")
        self.stat_strategies.pack(anchor="w")
        self.stat_epsilon = tk.Label(stats_box, text="Exploration: 0.25", bg=PANEL_2,
                                     fg=TEXT_DIM, font=(FONT, 9), anchor="w")
        self.stat_epsilon.pack(anchor="w")

    def _build_content(self, parent):
        content = tk.Frame(parent, bg=BG)
        content.pack(side="right", fill="both", expand=True)

        self.query_bar = tk.Frame(content, bg=BG, height=44)
        self.query_bar.pack(side="top", fill="x", padx=22, pady=(16, 8))
        self.query_bar.pack_propagate(False)
        self.query_label = tk.Label(self.query_bar, text="", bg=BG, fg=TEXT_DIM,
                                    font=(FONT, 10), anchor="w")
        self.query_label.pack(side="left")
        self.result_count = tk.Label(self.query_bar, text="", bg=BG, fg=MUTED,
                                     font=(FONT, 10), anchor="e")
        self.result_count.pack(side="right")

        container = tk.Frame(content, bg=BG)
        container.pack(side="top", fill="both", expand=True, padx=(22, 10), pady=(0, 16))
        self.canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        sb.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=sb.set)
        self.scroll_frame = tk.Frame(self.canvas, bg=BG)
        self.scroll_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>",
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self.scroll_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        self._show_welcome()

    # ── Skills chips ───────────────────────────────────────────────────────
    def _add_skill(self, skill):
        skill = skill.strip().lower()
        if not skill or skill in self.selected_skills:
            return
        self.selected_skills.append(skill)
        self._render_chips()

    def _add_custom_skill(self):
        s = self.skill_entry_var.get().strip()
        if s:
            self._add_skill(s)
            self.skill_entry_var.set("")

    def _remove_skill(self, skill):
        if skill in self.selected_skills:
            self.selected_skills.remove(skill)
            self._render_chips()

    def _render_chips(self):
        for w in self.chips_frame.winfo_children():
            w.destroy()
        if not self.selected_skills:
            tk.Label(self.chips_frame, text="no skills selected yet", bg=PANEL,
                     fg=MUTED, font=(FONT, 8, "italic")).pack(anchor="w")
            return
        row = tk.Frame(self.chips_frame, bg=PANEL)
        row.pack(fill="x")
        col = 0
        for skill in self.selected_skills:
            chip = tk.Frame(row, bg=PANEL_3, padx=6, pady=3)
            chip.grid(row=col // 3, column=col % 3, padx=2, pady=2, sticky="w")
            tk.Label(chip, text=skill, bg=PANEL_3, fg=TEXT,
                     font=(FONT, 8)).pack(side="left")
            tk.Button(chip, text="×", command=lambda s=skill: self._remove_skill(s),
                      bg=PANEL_3, fg=DANGER, bd=0, font=(FONT, 9, "bold"),
                      cursor="hand2", padx=3).pack(side="left")
            col += 1

    # ── Sources panel ──────────────────────────────────────────────────────
    def _refresh_sources(self):
        for w in self.sources_frame.winfo_children():
            w.destroy()
        for s in all_sources():
            row = tk.Frame(self.sources_frame, bg=PANEL)
            row.pack(fill="x", pady=1)
            var = tk.BooleanVar(value=s.get("enabled", True))
            cb = tk.Checkbutton(row, text=s["name"], variable=var,
                                command=lambda sid=s["id"], v=var: self._on_toggle_source(sid, v.get()),
                                bg=PANEL, fg=TEXT, selectcolor=PANEL_2,
                                activebackground=PANEL, activeforeground=TEXT,
                                font=(FONT, 9), anchor="w", bd=0,
                                highlightthickness=0, cursor="hand2")
            cb.pack(anchor="w")
            if s.get("note"):
                tk.Label(row, text=f"  ⓘ {s['note']}", bg=PANEL, fg=MUTED,
                         font=(FONT, 7, "italic"), anchor="w").pack(anchor="w")

    def _on_toggle_source(self, sid, enabled):
        toggle_source(sid, enabled)

    def _open_add_source(self):
        AddSourceDialog(self.root, on_added=self._refresh_sources)

    # ── Search flow ────────────────────────────────────────────────────────
    def _on_role_change(self, _e=None):
        role = self.role_var.get()
        specs = get_specialties(role)
        self.spec_cb.config(values=specs)
        self.spec_var.set(specs[0])

    def _period_num(self):
        label = self.period_var.get()
        if label.startswith("Any"):
            return 0
        return int(label.split("º")[0])

    def _on_search(self):
        if self.searching:
            return
        role = self.role_var.get()
        spec = self.spec_var.get()
        exp = self.exp_var.get()
        if not (role and spec and exp):
            self._set_status("Fill role, specialty and expertise.", WARN)
            return
        if not self.selected_skills:
            if not messagebox.askyesno("No skills",
                                       "You haven't selected any skills. Search anyway?"):
                return

        enabled = [s for s in all_sources() if s.get("enabled")]
        if not enabled:
            self._set_status("Enable at least one source.", WARN)
            return

        self.searching = True
        self.search_btn.config(state="disabled", text="⏳ Searching…")

        period = self._period_num()
        query, action_idx = self.agent.act(role, spec, exp,
                                           self.selected_skills, period)
        self.last_action = action_idx
        self.query_label.config(
            text=f"🔍  Query:  “{query}”   ·   strategy #{action_idx}   ·   "
                 f"{len(self.selected_skills)} skills   ·   "
                 f"{'any period' if period == 0 else f'{period}º sem'}"
        )
        self.result_count.config(text="")
        self._set_status("Querying sources…")
        self._show_loading()
        self._refresh_stats()

        def worker():
            jobs = []
            for s in enabled:
                sid = s["id"]
                scraper = SCRAPERS.get(sid)
                if scraper is None:
                    # user-defined API source handled elsewhere (future)
                    continue
                try:
                    got = scraper.search(query, self.selected_skills, period)
                    jobs.extend(got)
                except Exception as e:
                    print(f"[{sid}] {e}")

            # Deduplicate
            seen, uniq = set(), []
            for j in jobs:
                k = j.get("url", "") or (j.get("title", ""), j.get("company", ""))
                if k in seen:
                    continue
                seen.add(k)
                uniq.append(j)
            self.root.after(0, lambda: self._on_results(uniq, query))

        threading.Thread(target=worker, daemon=True).start()

    def _on_results(self, jobs, query):
        self.searching = False
        self.search_btn.config(state="normal", text="🔍  Search Jobs")
        self.current_jobs = jobs
        self._clear_results()

        if not jobs:
            box = tk.Frame(self.scroll_frame, bg=BG)
            box.pack(fill="x", pady=80)
            tk.Label(box, text="😶", bg=BG, fg=MUTED, font=(FONT, 40)).pack()
            tk.Label(box, text="No results from this strategy.", bg=BG, fg=TEXT,
                     font=(FONT, 12, "bold")).pack(pady=(8, 2))
            tk.Label(box, text="Rate it 👍/👎 so the agent learns, or add more sources.",
                     bg=BG, fg=TEXT_DIM, font=(FONT, 10)).pack()
            self.result_count.config(text="0 results")
            self._set_status("No results.", WARN)
            return

        for job in jobs:
            JobCard(self.scroll_frame, job, self._open_job).pack(fill="x", pady=(0, 10))
        self.result_count.config(text=f"{len(jobs)} results")
        self._set_status(f"Found {len(jobs)} offers.", SUCCESS)

    def _open_job(self, job):
        url = job.get("url") or ""
        if url:
            webbrowser.open_new_tab(url)

    # ── Feedback / stats / helpers ─────────────────────────────────────────
    def _on_feedback(self, reward):
        if self.last_action is None:
            self._set_status("Run a search first.", WARN)
            return
        self.agent.update(reward)
        self.agent.save(Q_TABLE_PATH)
        self._refresh_stats()
        self._set_status(f"Feedback: {reward:+.0f}. Q-table updated.", SUCCESS)
        self.last_action = None

    def _refresh_stats(self):
        s = self.agent.stats()
        if hasattr(self, "stat_updates"):
            self.stat_updates.config(text=f"Updates: {s['updates']}")
            self.stat_strategies.config(text=f"Strategies: {s['strategies']}")
            self.stat_epsilon.config(text=f"Exploration: {s['epsilon']}")
        self.header_stats.config(text=f"🧠 {s['updates']} updates · {s['strategies']} strategies")

    def _set_status(self, text, color=TEXT_DIM):
        self.status_label.config(text=text, fg=color)

    def _show_welcome(self):
        self._clear_results()
        box = tk.Frame(self.scroll_frame, bg=BG)
        box.pack(fill="x", pady=80)
        tk.Label(box, text="🎯", bg=BG, fg=ACCENT, font=(FONT, 48)).pack()
        tk.Label(box, text="Ready to find your next role", bg=BG, fg=TEXT,
                 font=(FONT, 16, "bold")).pack(pady=(12, 4))
        tk.Label(box, text="Select role, specialty, period, and skills — then Search.\n"
                           "Rate results and the agent learns your best keywords.",
                 bg=BG, fg=TEXT_DIM, font=(FONT, 10), justify="center").pack()

    def _show_loading(self):
        self._clear_results()
        box = tk.Frame(self.scroll_frame, bg=BG)
        box.pack(fill="x", pady=100)
        tk.Label(box, text="🤖", bg=BG, fg=ACCENT, font=(FONT, 40)).pack()
        tk.Label(box, text="Agent is exploring strategies…", bg=BG, fg=TEXT,
                 font=(FONT, 12)).pack(pady=(10, 0))

    def _clear_results(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.current_jobs = []