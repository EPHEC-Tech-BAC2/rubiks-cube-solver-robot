import tkinter as tk
from tkinter import ttk, messagebox
import time
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from bluetooth.bt_uart import BTUart, list_ports

C_BG     = "#0a0a0f"
C_BG2    = "#0f0f1a"
C_BG3    = "#151525"
C_PANEL  = "#12121e"
C_CYAN   = "#00d4ff"
C_GREEN  = "#00ff88"
C_RED    = "#ff3355"
C_TEXT   = "#e2e8f0"
C_DIM    = "#4a5568"
C_BORDER = "#1e2035"
FONT     = ("Courier New", 10)
FONT_B   = ("Courier New", 10, "bold")


class Interface:
    def __init__(self):
        self.bt = BTUart()

        self.root = tk.Tk()
        self.root.title("Rubik Robot")
        self.root.configure(bg=C_BG)
        self.root.geometry("900x560")

        self._build()
        self._poll()

    def _build(self):
        # titre
        tk.Label(self.root,
                 text="◈  RUBIK ROBOT CONTROL SYSTEM",
                 font=("Courier New", 14, "bold"),
                 bg=C_BG, fg=C_CYAN).pack(pady=(10, 2))
        tk.Frame(self.root, bg=C_CYAN, height=1).pack(fill="x")

        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # colonne gauche : connexion
        left = tk.Frame(body, bg=C_BG, width=200)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self._build_bt(left)

        # colonne droite : log
        right = tk.Frame(body, bg=C_BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_log(right)

    def _build_bt(self, parent):
        p = tk.Frame(parent, bg=C_PANEL,
                     highlightbackground=C_BORDER,
                     highlightthickness=1)
        p.pack(fill="x", pady=(0, 8), padx=2)

        tk.Label(p, text="▸ BLUETOOTH", font=FONT_B,
                 fg=C_CYAN, bg=C_PANEL).pack(anchor="w", padx=8, pady=(8, 4))
        tk.Frame(p, bg=C_CYAN, height=1).pack(fill="x", padx=8)

        row = tk.Frame(p, bg=C_PANEL)
        row.pack(fill="x", padx=8, pady=4)
        tk.Label(row, text="PORT", font=FONT, fg=C_DIM,
                 bg=C_PANEL).pack(side="left")
        self.port_var = tk.StringVar()
        ports = list_ports()
        box = ttk.Combobox(row, textvariable=self.port_var, width=9)
        box["values"] = ports
        if ports:
            box.current(0)
        box.pack(side="right")

        row2 = tk.Frame(p, bg=C_PANEL)
        row2.pack(fill="x", padx=8, pady=2)
        tk.Label(row2, text="BAUD", font=FONT, fg=C_DIM,
                 bg=C_PANEL).pack(side="left")
        self.baud_var = tk.StringVar(value="38400")
        tk.Entry(row2, textvariable=self.baud_var, width=8,
                 bg=C_BG3, fg=C_CYAN, relief="flat",
                 font=FONT).pack(side="right")

        self.conn_btn = tk.Button(
            p, text="⬡  CONNECTER", command=self._toggle_bt,
            bg=C_BG3, fg=C_GREEN, font=FONT_B,
            relief="flat", activebackground=C_GREEN,
            activeforeground=C_BG, padx=8, pady=6)
        self.conn_btn.pack(fill="x", padx=8, pady=8)

        dot_row = tk.Frame(p, bg=C_PANEL)
        dot_row.pack(fill="x", padx=8, pady=(0, 8))
        self._dot_c = tk.Canvas(dot_row, width=12, height=12,
                                 bg=C_PANEL, highlightthickness=0)
        self._dot_c.pack(side="left")
        self._dot = self._dot_c.create_oval(1, 1, 11, 11, fill=C_DIM)
        self._dot_lbl = tk.Label(dot_row, text="OFFLINE",
                                  font=FONT, fg=C_DIM, bg=C_PANEL)
        self._dot_lbl.pack(side="left", padx=4)

    def _build_log(self, parent):
        tk.Label(parent, text="▸ LOG", font=FONT_B,
                 fg=C_CYAN, bg=C_BG).pack(anchor="w", pady=(0, 4))
        self.log = tk.Text(parent, bg=C_BG2, fg=C_TEXT,
                           font=("Courier New", 9),
                           relief="flat", state="disabled")
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("ok",  foreground=C_GREEN)
        self.log.tag_configure("err", foreground=C_RED)
        self.log.tag_configure("tx",  foreground=C_CYAN)
        self.log.tag_configure("dim", foreground=C_DIM)

    def _toggle_bt(self):
        if self.bt.is_connected():
            self.bt.disconnect()
            self._dot_c.itemconfig(self._dot, fill=C_DIM)
            self._dot_lbl.config(text="OFFLINE", fg=C_DIM)
            self.conn_btn.config(text="⬡  CONNECTER", fg=C_GREEN)
            self._log("Déconnecté", "dim")
        else:
            port = self.port_var.get()
            try:
                baud = int(self.baud_var.get())
                self.bt.connect(port, baud)
            except Exception as e:
                messagebox.showerror("Connexion", str(e))
                return
            self.bt.on_receive = self._on_bt
            self._dot_c.itemconfig(self._dot, fill=C_GREEN)
            self._dot_lbl.config(text="ONLINE  " + port, fg=C_GREEN)
            self.conn_btn.config(text="⬡  DÉCONNECTER", fg=C_RED)
            self._log("Connecté sur {} @ {}".format(port, baud), "ok")

    def _on_bt(self, tag, payload):
        self.root.after(0, lambda t=tag, p=payload:
                        self._log("< {} {}".format(t, p)))

    def _log(self, text, style=""):
        ts = time.strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end", "[{}] {}\n".format(ts, text), style)
        self.log.see("end")
        self.log.config(state="disabled")

    def _poll(self):
        while not self.bt.rx_queue.empty():
            _, tag, payload = self.bt.rx_queue.get_nowait()
            if tag:
                self._on_bt(tag, payload)
        self.root.after(100, self._poll)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.bt.disconnect()
        self.root.destroy()


def run_app():
    Interface().run()