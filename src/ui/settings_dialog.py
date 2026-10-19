"""
Diálogo de configurações — lê e escreve credenciais no .env.
Abre como janela Toplevel modal.
"""
import os
import tkinter as tk
from tkinter import messagebox

from dotenv import load_dotenv, set_key

# Paleta (mesma do app)
BG, PANEL, PANEL_2, PANEL_3 = "#0f1419", "#1a1f2e", "#232938", "#2c3346"
ACCENT, ACCENT_HOV = "#4f8ef7", "#6ba1ff"
TEXT, TEXT_DIM, MUTED = "#e6e6e6", "#a0a6b2", "#6b7280"
SUCCESS, DANGER = "#4ade80", "#f87171"
FONT = "DejaVu Sans"


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, env_path):
        super().__init__(parent)
        self.env_path = env_path
        self.title("⚙️ Configurações — Credenciais")
        self.configure(bg=PANEL)
        self.geometry("560x520")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        # Carrega valores atuais
        load_dotenv(env_path, override=True)
        self.vars = {
            "PUC_CPF":       tk.StringVar(value=os.getenv("PUC_CPF", "")),
            "PUC_SENHA":     tk.StringVar(value=os.getenv("PUC_SENHA", "")),
            "CIEE_PR_CPF":   tk.StringVar(value=os.getenv("CIEE_PR_CPF", "")),
            "CIEE_PR_SENHA": tk.StringVar(value=os.getenv("CIEE_PR_SENHA", "")),
        }

        pad = tk.Frame(self, bg=PANEL)
        pad.pack(fill="both", expand=True, padx=28, pady=24)

        # Header
        tk.Label(pad, text="⚙️  Credenciais de acesso",
                 bg=PANEL, fg=TEXT,
                 font=(FONT, 15, "bold")).pack(anchor="w")
        tk.Label(pad,
                 text="Estas credenciais ficam no arquivo .env (local).\n"
                      "Nunca são enviadas para servidor nenhum.",
                 bg=PANEL, fg=TEXT_DIM, font=(FONT, 9),
                 justify="left").pack(anchor="w", pady=(4, 20))

        # ── PUC Carreiras ─────────────────────────────────────
        self._section(pad, "🎓  PUC Carreiras (Symplicity)")
        self._field(pad, "CPF (só números)", "PUC_CPF", secret=False)
        self._field(pad, "Senha", "PUC_SENHA", secret=True)

        # ── CIEE-PR ───────────────────────────────────────────
        self._section(pad, "🎓  CIEE-PR (autoweb.cieepr.org.br)")
        self._field(pad, "CPF (só números)", "CIEE_PR_CPF", secret=False)
        self._field(pad, "Senha", "CIEE_PR_SENHA", secret=True)

        # ── Info extra ────────────────────────────────────────
        info = tk.Frame(pad, bg=PANEL_2, padx=14, pady=10)
        info.pack(fill="x", pady=(20, 0))
        tk.Label(info, text="ℹ️  Onde ficam esses dados?",
                 bg=PANEL_2, fg=TEXT,
                 font=(FONT, 9, "bold")).pack(anchor="w")
        tk.Label(info,
                 text=f"📁 {self.env_path}\n"
                      "Este arquivo está no .gitignore e NÃO vai pro GitHub.",
                 bg=PANEL_2, fg=TEXT_DIM,
                 font=(FONT, 8), justify="left").pack(anchor="w", pady=(4, 0))

        # ── Botões ────────────────────────────────────────────
        btn_row = tk.Frame(pad, bg=PANEL)
        btn_row.pack(side="bottom", fill="x", pady=(20, 0))

        cancel = tk.Button(btn_row, text="Cancelar", command=self.destroy,
                           bg=PANEL_2, fg=TEXT, bd=0, padx=20, pady=10,
                           font=(FONT, 10), cursor="hand2",
                           activebackground=PANEL_3, activeforeground=TEXT)
        cancel.pack(side="right", padx=(8, 0))

        save = tk.Button(btn_row, text="💾 Salvar", command=self._save,
                         bg=ACCENT, fg="#ffffff", bd=0, padx=20, pady=10,
                         font=(FONT, 10, "bold"), cursor="hand2",
                         activebackground=ACCENT_HOV, activeforeground="#ffffff")
        save.pack(side="right")

    def _section(self, parent, title):
        tk.Label(parent, text=title, bg=PANEL, fg=ACCENT,
                 font=(FONT, 10, "bold")).pack(anchor="w", pady=(14, 4))

    def _field(self, parent, label, key, secret):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=(2, 0))

        tk.Label(row, text=label, bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 8), width=20, anchor="w").pack(side="left")

        entry = tk.Entry(row, textvariable=self.vars[key],
                         bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                         bd=0, font=(FONT, 10), highlightthickness=1,
                         highlightbackground=PANEL_2, highlightcolor=ACCENT,
                         show="●" if secret else "")
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(6, 0))

        if secret:
            # botão pra mostrar/ocultar
            def toggle(_e=entry):
                _e.config(show="" if _e.cget("show") else "●")
            eye = tk.Button(row, text="👁", command=toggle,
                            bg=PANEL_2, fg=TEXT_DIM, bd=0,
                            font=(FONT, 9), cursor="hand2",
                            padx=6, activebackground=PANEL_3)
            eye.pack(side="left", padx=(4, 0))

    def _save(self):
        try:
            # Garante que o .env existe
            if not os.path.exists(self.env_path):
                with open(self.env_path, "w") as f:
                    f.write("# Credenciais Tiny Job Search AI\n")

            for key, var in self.vars.items():
                value = var.get().strip()
                # set_key atualiza ou adiciona a linha
                set_key(self.env_path, key, value)
                # atualiza também em memória pra próxima busca
                os.environ[key] = value

            messagebox.showinfo(
                "Salvo",
                "Credenciais salvas no .env.\n"
                "Próxima busca já usa os novos valores.",
                parent=self,
            )
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar:\n{e}", parent=self)