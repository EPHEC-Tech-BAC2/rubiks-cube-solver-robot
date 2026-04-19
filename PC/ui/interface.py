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
C_ORANGE = "#ff6b00"
C_YELLOW = "#ffd700"
C_TEXT   = "#e2e8f0"
C_DIM    = "#4a5568"
C_BORDER = "#1e2035"
FONT     = ("Courier New", 10)
FONT_B   = ("Courier New", 10, "bold")
FONT_S   = ("Courier New", 9)


def _panel(parent):
    return tk.Frame(parent, bg=C_PANEL,
                    highlightbackground=C_BORDER,
                    highlightthickness=1)

def _section(parent, title):
    tk.Label(parent, text="▸ " + title, font=FONT_B,
             fg=C_CYAN, bg=C_PANEL).pack(anchor="w", padx=8, pady=(8, 2))
    tk.Frame(parent, bg=C_CYAN, height=1).pack(fill="x", padx=8, pady=(0, 6))

def _btn(parent, text, cmd, fg=C_CYAN):
    return tk.Button(parent, text=text, command=cmd,
                     bg=C_BG3, fg=fg, font=FONT_B,
                     relief="flat", activebackground=fg,
                     activeforeground=C_BG,
                     padx=8, pady=5, cursor="hand2")


class Interface:
    def __init__(self):
        self.bt = BTUart()
        self.timer_running = False
        self.timer_start   = 0
        self.elapsed       = 0

        self.root = tk.Tk()
        self.root.title("Rubik Robot")
        self.root.configure(bg=C_BG)
        self.root.geometry("1000x600")

        self._build()
        self._poll()

    def _build(self):
        tk.Label(self.root,
                 text="◈  RUBIK ROBOT CONTROL SYSTEM",
                 font=("Courier New", 14, "bold"),
                 bg=C_BG, fg=C_CYAN).pack(pady=(10, 2))
        tk.Frame(self.root, bg=C_CYAN, height=1).pack(fill="x")

        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True, padx=10, pady=8)

        left = tk.Frame(body, bg=C_BG, width=210)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        self._build_bt(left)
        self._build_controls(left)
        self._build_rfid(left)
        self._build_timer(left)

        right = tk.Frame(body, bg=C_BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_log(right)

    def _build_bt(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 8), padx=2)
        _section(p, "BLUETOOTH")

        row = tk.Frame(p, bg=C_PANEL)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text="PORT", font=FONT_S, fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.port_var = tk.StringVar()
        ports = list_ports()
        box = ttk.Combobox(row, textvariable=self.port_var, width=9)
        box["values"] = ports
        if ports:
            box.current(0)
        box.pack(side="right")

        row2 = tk.Frame(p, bg=C_PANEL)
        row2.pack(fill="x", padx=8, pady=2)
        tk.Label(row2, text="BAUD", font=FONT_S, fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.baud_var = tk.StringVar(value="38400")
        tk.Entry(row2, textvariable=self.baud_var, width=8,
                 bg=C_BG3, fg=C_CYAN, relief="flat", font=FONT_S).pack(side="right")

        self.conn_btn = _btn(p, "⬡  CONNECTER", self._toggle_bt, C_GREEN)
        self.conn_btn.pack(fill="x", padx=8, pady=8)

        dot_row = tk.Frame(p, bg=C_PANEL)
        dot_row.pack(fill="x", padx=8, pady=(0, 8))
        self._dot_c = tk.Canvas(dot_row, width=12, height=12,
                                 bg=C_PANEL, highlightthickness=0)
        self._dot_c.pack(side="left")
        self._dot = self._dot_c.create_oval(1, 1, 11, 11, fill=C_DIM)
        self._dot_lbl = tk.Label(dot_row, text="OFFLINE",
                                  font=FONT_S, fg=C_DIM, bg=C_PANEL)
        self._dot_lbl.pack(side="left", padx=4)

    def _build_controls(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 8), padx=2)
        _section(p, "CONTRÔLES")

        _btn(p, "CAPTURER 6 FACES", lambda: None, C_CYAN).pack(
            fill="x", padx=8, pady=2)
        _btn(p, "RÉSOUDRE", lambda: None, C_YELLOW).pack(
            fill="x", padx=8, pady=2)
        _btn(p, "ENVOYER AU PICO", lambda: None, C_ORANGE).pack(
            fill="x", padx=8, pady=2)

        tk.Frame(p, bg=C_BORDER, height=1).pack(fill="x", padx=8, pady=6)
        tk.Label(p, text="PINCES", font=FONT_S, fg=C_DIM, bg=C_PANEL).pack(
            anchor="w", padx=8)

        row = tk.Frame(p, bg=C_PANEL)
        row.pack(fill="x", padx=8, pady=4)
        _btn(row, "ATTRAPER", lambda: self._send("GRAB"),   C_CYAN).pack(
            side="left", expand=True, fill="x", padx=(0, 2))
        _btn(row, "RELÂCHER", lambda: self._send("RELEASE"), C_DIM).pack(
            side="left", expand=True, fill="x")

        self.faces_lbl = tk.Label(p, text="Faces : 0 / 6",
                                   font=FONT_S, fg=C_DIM, bg=C_PANEL)
        self.faces_lbl.pack(anchor="w", padx=8, pady=(2, 8))

    def _build_rfid(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 8), padx=2)
        _section(p, "RFID")

        row1 = tk.Frame(p, bg=C_PANEL)
        row1.pack(fill="x", padx=8, pady=2)
        tk.Label(row1, text="STATUT", font=FONT_S, fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.rfid_status = tk.Label(row1, text="EN ATTENTE",
                                     font=FONT_S, fg=C_DIM, bg=C_PANEL)
        self.rfid_status.pack(side="right")

        row2 = tk.Frame(p, bg=C_PANEL)
        row2.pack(fill="x", padx=8, pady=2)
        tk.Label(row2, text="ID CARTE", font=FONT_S, fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.rfid_id = tk.Label(row2, text="—",
                                 font=("Courier New", 9, "bold"),
                                 fg=C_CYAN, bg=C_PANEL)
        self.rfid_id.pack(side="right")

        self._rfid_badge = tk.Canvas(p, width=190, height=26,
                                      bg=C_BG3, highlightthickness=0)
        self._rfid_badge.pack(padx=8, pady=(2, 8))
        self._rfid_badge.create_text(95, 13, text="BADGE NON PRÉSENTÉ",
                                      fill=C_DIM, font=FONT_S,
                                      tags="badge")

    def _build_timer(self, parent):
        p = _panel(parent)
        p.pack(fill="x", padx=2)
        _section(p, "CHRONOMÈTRE")

        self.timer_lbl = tk.Label(p, text="00:00.0",
                                   font=("Courier New", 26, "bold"),
                                   fg=C_ORANGE, bg=C_PANEL)
        self.timer_lbl.pack()

        row = tk.Frame(p, bg=C_PANEL)
        row.pack(pady=(4, 8))
        _btn(row, "▶", self._timer_start, C_GREEN).pack(side="left", padx=1)
        _btn(row, "■", self._timer_stop,  C_RED).pack(side="left", padx=1)
        _btn(row, "↺", self._timer_reset, C_DIM).pack(side="left", padx=1)

    def _build_log(self, parent):
        tk.Label(parent, text="▸ LOG", font=FONT_B,
                 fg=C_CYAN, bg=C_BG).pack(anchor="w", pady=(0, 4))
        self.log = tk.Text(parent, bg=C_BG2, fg=C_TEXT,
                           font=("Courier New", 9),
                           relief="flat", state="disabled")
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("ok",  foreground=C_GREEN)
        self.log.tag_configure("err", foreground=C_RED)
        self.log.tag_configure("tx",  foreground=C_ORANGE)
        self.log.tag_configure("dim", foreground=C_DIM)

    # BT
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

    def _send(self, tag, payload=""):
        if not self.bt.is_connected():
            messagebox.showwarning("BT", "Non connecté")
            return
        try:
            self.bt.send(tag, payload)
            self._log("> {} {}".format(tag, payload), "tx")
        except Exception as e:
            messagebox.showerror("Envoi", str(e))

    def _on_bt(self, tag, payload):
        self.root.after(0, lambda t=tag, p=payload:
                        self._handle_bt(t, p))

    def _handle_bt(self, tag, payload):
        self._log("< {} {}".format(tag, payload))

        if tag == "AUTH":
            parts = payload.split(",")
            card_id = parts[0]
            ok = len(parts) > 1 and parts[1] == "1"
            self.rfid_id.config(text=card_id)
            if ok:
                self.rfid_status.config(text="AUTORISÉ", fg=C_GREEN)
                self._rfid_badge.delete("badge")
                self._rfid_badge.create_rectangle(0, 0, 190, 26,
                                                   fill="#001a0d", outline="")
                self._rfid_badge.create_text(
                    95, 13, text="✓ ACCÈS AUTORISÉ — " + card_id,
                    fill=C_GREEN, font=FONT_S, tags="badge")
                self._log("RFID autorisé : {}".format(card_id), "ok")
            else:
                self.rfid_status.config(text="REFUSÉ", fg=C_RED)
                self._rfid_badge.delete("badge")
                self._rfid_badge.create_rectangle(0, 0, 190, 26,
                                                   fill="#1a0005", outline="")
                self._rfid_badge.create_text(
                    95, 13, text="✗ ACCÈS REFUSÉ",
                    fill=C_RED, font=FONT_S, tags="badge")
                self._log("RFID refusé : {}".format(card_id), "err")

        elif tag == "ERR":
            self._log("Erreur : {}".format(payload), "err")

    # Timer
    def _timer_start(self):
        if not self.timer_running:
            self.timer_start = time.time() - self.elapsed
            self.timer_running = True

    def _timer_stop(self):
        if self.timer_running:
            self.elapsed = time.time() - self.timer_start
            self.timer_running = False

    def _timer_reset(self):
        self.timer_running = False
        self.elapsed = 0
        self.timer_lbl.config(text="00:00.0")

    def _update_timer(self):
        t = (time.time() - self.timer_start) if self.timer_running else self.elapsed
        m = int(t) // 60
        s = t % 60
        self.timer_lbl.config(text="{:02d}:{:04.1f}".format(m, s))

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
                self._handle_bt(tag, payload)
        self._update_timer()
        self.root.after(100, self._poll)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        self.bt.disconnect()
        self.root.destroy()


def run_app():
    Interface().run()