import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from bluetooth.bt_uart import BTUart, list_ports
from graphique.cube_view import CubeView
from vision.color_detection import FACE_ORDER, detect_face_colors

try:
    import cv2
    import numpy as np
    from PIL import Image, ImageTk
    HAS_CV = True
except ImportError:
    HAS_CV = False

C_BG     = "#07070f"
C_BG2    = "#0d0d1a"
C_BG3    = "#13131f"
C_PANEL  = "#10101c"
C_CYAN   = "#00d4ff"
C_GREEN  = "#00ff88"
C_RED    = "#ff3355"
C_ORANGE = "#ff6b00"
C_YELLOW = "#ffd700"
C_TEXT   = "#e2e8f0"
C_DIM    = "#3a4560"
C_BORDER = "#1a1a2e"
FONT_B   = ("Courier New", 10, "bold")
FONT_S   = ("Courier New", 9)
FONT_T   = ("Courier New", 8)

CAM_W, CAM_H = 480, 300
X1, Y1, X2, Y2 = 150, 60, 330, 240
SQ = (X2 - X1) // 3

FACE_LABELS = {
    "U": "Haut (blanc)",
    "R": "Droite (rouge)",
    "F": "Avant (vert)",
    "D": "Bas (jaune)",
    "L": "Gauche (orange)",
    "B": "Arrière (bleu)",
}


def _grid_centers():
    pts = []
    for r in range(3):
        for c in range(3):
            cx = X1 + c * SQ + SQ // 2
            cy = Y1 + r * SQ + SQ // 2
            pts.append((cx, cy))
    return pts

CENTERS = _grid_centers()


def _panel(parent, **kw):
    return tk.Frame(parent, bg=C_PANEL,
                    highlightbackground=C_BORDER,
                    highlightthickness=1, **kw)

def _sec(parent, title, fg=C_CYAN):
    f = tk.Frame(parent, bg=C_PANEL)
    tk.Label(f, text="▸ " + title, font=FONT_B,
             fg=fg, bg=C_PANEL).pack(side="left")
    tk.Frame(f, bg=C_BORDER, height=1).pack(
        side="left", fill="x", expand=True, padx=(6, 0))
    return f

def _btn(parent, text, cmd, fg=C_CYAN):
    return tk.Button(parent, text=text, command=cmd,
                     bg=C_BG3, fg=fg, font=FONT_B,
                     relief="flat", activebackground=fg,
                     activeforeground=C_BG,
                     padx=8, pady=5, cursor="hand2")

class SplashScreen:
    def __init__(self, root, on_done):
        self.root    = root
        self.on_done = on_done
        self._angle  = 0
        self._prog   = 0.0
        self._phase  = 0

        self.frame = tk.Frame(root, bg=C_BG)
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.canvas = tk.Canvas(self.frame, bg=C_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self._tick()

    def _tick(self):
        self._angle += 1.8
        if self._phase == 0:
            self._prog = min(1.0, self._prog + 0.012)
            if self._prog >= 1.0:
                self._phase = 1
                self.frame.after(700,
                    lambda: setattr(self, '_phase', 2))
        elif self._phase == 2:
            self._prog = max(0.0, self._prog - 0.07)
            if self._prog <= 0:
                self.frame.destroy()
                self.on_done()
                return
        self._draw()
        self.frame.after(16, self._tick)

    def _draw(self):
        c = self.canvas
        c.delete("all")
        w = self.root.winfo_width()  or 1400
        h = self.root.winfo_height() or 800
        cx, cy = w // 2, h // 2

        for x in range(0, w, 50):
            c.create_line(x, 0, x, h, fill="#0c0c18")
        for y in range(0, h, 50):
            c.create_line(0, y, w, y, fill="#0c0c18")

        for i, (col, wd) in enumerate(
                [(C_CYAN, 2), (C_ORANGE, 1), (C_BORDER, 1)]):
            r = 110 + i * 55
            a = self._angle + i * 40
            x1 = cx + r * math.cos(math.radians(a))
            y1 = cy + r * math.sin(math.radians(a))
            c.create_oval(cx-r, cy-r, cx+r, cy+r,
                          outline=col, width=wd)
            if i < 2:
                c.create_oval(x1-6, y1-6, x1+6, y1+6,
                              fill=col, outline="")

        c.create_text(cx, cy - 40, text="RUBIK",
                      font=("Courier New", 64, "bold"), fill=C_CYAN)
        c.create_text(cx, cy + 40, text="ROBOT",
                      font=("Courier New", 64, "bold"), fill=C_ORANGE)
        c.create_text(cx, cy + 110,
                      text="CONTROL SYSTEM  v1.0",
                      font=("Courier New", 13), fill=C_DIM)

        bw = 460
        bx = cx - bw // 2
        by = cy + 155
        c.create_rectangle(bx, by, bx+bw, by+5,
                            fill=C_BG3, outline=C_BORDER)
        c.create_rectangle(bx, by,
                            bx + int(bw * self._prog), by+5,
                            fill=C_CYAN, outline="")
        c.create_text(cx, by + 18,
                      text="INITIALISATION... {}%".format(
                          int(self._prog * 100)),
                      font=("Courier New", 9), fill=C_DIM)

# Interface 

class Interface:
    def __init__(self):
        self.bt            = BTUart()
        self.faces         = {}
        self.solution      = None
        self._cap          = None
        self._cam_alive    = False
        self._last_frame   = None
        self._scan_idx     = 0

        self.timer_running = False
        self.timer_start   = 0
        self.elapsed       = 0

        self.root = tk.Tk()
        self.root.title("Rubik Robot — Control System")
        self.root.configure(bg=C_BG)
        self.root.state("zoomed")
        self.root.update()

        SplashScreen(self.root, self._build)

    # Build

    def _build(self):
        hdr = tk.Frame(self.root, bg=C_BG, height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="◈  RUBIK ROBOT  CONTROL SYSTEM",
                 font=("Courier New", 15, "bold"),
                 bg=C_BG, fg=C_CYAN).pack(side="left", padx=20, pady=10)

        self._dot_c = tk.Canvas(hdr, width=14, height=14,
                                 bg=C_BG, highlightthickness=0)
        self._dot_c.pack(side="right", padx=(0, 8), pady=16)
        self._dot = self._dot_c.create_oval(1, 1, 13, 13, fill=C_DIM)
        self._dot_lbl = tk.Label(hdr, text="OFFLINE",
                                  font=FONT_T, bg=C_BG, fg=C_DIM)
        self._dot_lbl.pack(side="right", padx=(0, 4), pady=16)

        tk.Frame(self.root, bg=C_CYAN, height=1).pack(fill="x")

        body = tk.Frame(self.root, bg=C_BG)
        body.pack(fill="both", expand=True, padx=8, pady=8)

        # colonne gauche
        left = tk.Frame(body, bg=C_BG, width=200)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self._build_bt(left)
        self._build_rfid(left)
        self._build_timer(left)

        # colonne centre : caméra + cube
        center = tk.Frame(body, bg=C_BG)
        center.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self._build_camera(center)
        self._build_cube(center)

        # colonne droite : contrôles + solution + log
        right = tk.Frame(body, bg=C_BG, width=280)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)
        self._build_controls(right)
        self._build_solution(right)
        self._build_log(right)

        self.root.after(500, self._start_camera)
        self._poll()

    def _build_bt(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 8), padx=2)
        _sec(p, "BLUETOOTH").pack(fill="x", padx=8, pady=(8, 4))

        row = tk.Frame(p, bg=C_PANEL)
        row.pack(fill="x", padx=8, pady=2)
        tk.Label(row, text="PORT", font=FONT_T,
                 fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.port_var = tk.StringVar()
        ports = list_ports()
        box = ttk.Combobox(row, textvariable=self.port_var, width=9)
        box["values"] = ports
        if ports:
            box.current(0)
        box.pack(side="right")

        row2 = tk.Frame(p, bg=C_PANEL)
        row2.pack(fill="x", padx=8, pady=2)
        tk.Label(row2, text="BAUD", font=FONT_T,
                 fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.baud_var = tk.StringVar(value="38400")
        tk.Entry(row2, textvariable=self.baud_var, width=8,
                 bg=C_BG3, fg=C_CYAN, relief="flat",
                 font=FONT_T).pack(side="right")

        self.conn_btn = _btn(p, "⬡  CONNECTER",
                              self._toggle_bt, C_GREEN)
        self.conn_btn.pack(fill="x", padx=8, pady=(6, 8))

    def _build_rfid(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 8), padx=2)
        _sec(p, "RFID").pack(fill="x", padx=8, pady=(8, 4))

        r1 = tk.Frame(p, bg=C_PANEL)
        r1.pack(fill="x", padx=8, pady=1)
        tk.Label(r1, text="STATUT", font=FONT_T,
                 fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.rfid_status = tk.Label(r1, text="EN ATTENTE",
                                     font=FONT_T, fg=C_DIM, bg=C_PANEL)
        self.rfid_status.pack(side="right")

        r2 = tk.Frame(p, bg=C_PANEL)
        r2.pack(fill="x", padx=8, pady=1)
        tk.Label(r2, text="ID CARTE", font=FONT_T,
                 fg=C_DIM, bg=C_PANEL).pack(side="left")
        self.rfid_id = tk.Label(r2, text="—",
                                 font=("Courier New", 9, "bold"),
                                 fg=C_CYAN, bg=C_PANEL)
        self.rfid_id.pack(side="right")

        self._rfid_badge = tk.Canvas(p, height=26,
                                      bg=C_BG3, highlightthickness=0)
        self._rfid_badge.pack(fill="x", padx=8, pady=(4, 8))
        self._rfid_badge.bind("<Configure>", self._redraw_badge)
        self._badge_txt = "BADGE NON PRÉSENTÉ"
        self._badge_col = C_DIM
        self._badge_bg  = C_BG3

    def _redraw_badge(self, e=None):
        c = self._rfid_badge
        w = c.winfo_width() or 180
        c.delete("all")
        c.create_rectangle(0, 0, w, 26,
                            fill=self._badge_bg, outline="")
        c.create_text(w//2, 13, text=self._badge_txt,
                      fill=self._badge_col, font=FONT_T)

    def _set_badge(self, txt, col, bg):
        self._badge_txt = txt
        self._badge_col = col
        self._badge_bg  = bg
        self._redraw_badge()

    def _build_timer(self, parent):
        p = _panel(parent)
        p.pack(fill="x", padx=2)
        _sec(p, "CHRONOMÈTRE").pack(fill="x", padx=8, pady=(8, 4))
        self.timer_lbl = tk.Label(p, text="00:00.0",
                                   font=("Courier New", 32, "bold"),
                                   fg=C_ORANGE, bg=C_PANEL)
        self.timer_lbl.pack(pady=(2, 8))

    def _build_camera(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 6))
        _sec(p, "CAMERA LIVE").pack(fill="x", padx=8, pady=(8, 4))

        self.cam_label = tk.Label(p, bg="#000000",
                                   text="Démarrage caméra...",
                                   fg=C_DIM, font=FONT_S,
                                   width=CAM_W, height=CAM_H)
        self.cam_label.pack(padx=8, pady=(0, 4))

        # indicateur face à scanner
        self.scan_hint = tk.Label(p,
            text="Face 1/6 — {} — Appuie sur SCANNER".format(
                FACE_LABELS[FACE_ORDER[0]]),
            fg=C_CYAN, bg=C_PANEL, font=FONT_S)
        self.scan_hint.pack(pady=(0, 4))

        _btn(p, "📷  SCANNER CETTE FACE",
             self._scan_face, C_GREEN).pack(
            fill="x", padx=8, pady=(0, 6))

        _btn(p, "↺  RECOMMENCER",
             self._reset_scan, C_DIM).pack(
            fill="x", padx=8, pady=(0, 8))

    def _build_cube(self, parent):
        p = _panel(parent)
        p.pack(fill="both", expand=True)
        _sec(p, "6 FACES EN DIRECT").pack(
            fill="x", padx=8, pady=(8, 6))

        self.cube_view = CubeView(p, cell_size=34, bg=C_BG2)
        self.cube_view.pack(pady=(0, 6))

        self.faces_lbl = tk.Label(p, text="Faces capturées : 0 / 6",
                                   font=FONT_T, fg=C_DIM, bg=C_PANEL)
        self.faces_lbl.pack(pady=(0, 6))

    def _build_controls(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 8), padx=2)
        _sec(p, "CONTRÔLES").pack(fill="x", padx=8, pady=(8, 6))

        _btn(p, "RÉSOUDRE",
             self._solve, C_YELLOW).pack(
            fill="x", padx=8, pady=2)
        _btn(p, "ENVOYER AU PICO",
             self._send_solution, C_ORANGE).pack(
            fill="x", padx=8, pady=(2, 8))

    def _build_solution(self, parent):
        p = _panel(parent)
        p.pack(fill="x", pady=(0, 8), padx=2)
        _sec(p, "SOLUTION KOCIEMBA").pack(
            fill="x", padx=8, pady=(8, 4))

        self.sol_text = tk.Label(p, text="—",
                                  fg=C_GREEN, bg=C_PANEL,
                                  font=("Courier New", 9),
                                  wraplength=256,
                                  justify="left", anchor="w")
        self.sol_text.pack(fill="x", padx=8)

        self.moves_lbl = tk.Label(p, text="",
                                   fg=C_ORANGE, bg=C_PANEL,
                                   font=("Courier New", 9, "bold"))
        self.moves_lbl.pack(anchor="w", padx=8, pady=(2, 4))

        tk.Label(p, text="PROGRESSION", font=FONT_T,
                 fg=C_DIM, bg=C_PANEL).pack(anchor="w", padx=8)
        self._prog_cv = tk.Canvas(p, height=8,
                                   bg=C_BG3, highlightthickness=0)
        self._prog_cv.pack(fill="x", padx=8, pady=2)
        self._prog_rect = self._prog_cv.create_rectangle(
            0, 0, 0, 8, fill=C_CYAN, outline="")
        self.prog_lbl = tk.Label(p, text="",
                                  fg=C_CYAN, bg=C_PANEL, font=FONT_T)
        self.prog_lbl.pack(anchor="w", padx=8, pady=(0, 8))

    def _build_log(self, parent):
        p = _panel(parent)
        p.pack(fill="both", expand=True, padx=2)
        _sec(p, "LOG").pack(fill="x", padx=8, pady=(8, 4))
        self.log = tk.Text(p, bg=C_BG2, fg=C_TEXT,
                           font=("Courier New", 8),
                           relief="flat", state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log.tag_configure("ok",  foreground=C_GREEN)
        self.log.tag_configure("err", foreground=C_RED)
        self.log.tag_configure("tx",  foreground=C_ORANGE)
        self.log.tag_configure("dim", foreground=C_DIM)

    # Caméra

    def _start_camera(self):
        if not HAS_CV:
            self.cam_label.config(text="opencv-python non installé")
            return
        self._cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(0)
        if not self._cap.isOpened():
            self.cam_label.config(text="Caméra introuvable")
            return
        self._cam_alive = True
        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        while self._cam_alive and self._cap:
            ret, frame = self._cap.read()
            if not ret:
                break
            frame = cv2.flip(frame, 1)

            # grille de détection
            cv2.rectangle(frame, (X1, Y1), (X2, Y2),
                          (0, 212, 255), 2)
            for r in range(3):
                for c in range(3):
                    cv2.rectangle(
                        frame,
                        (X1 + c*SQ, Y1 + r*SQ),
                        (X1 + (c+1)*SQ, Y1 + (r+1)*SQ),
                        (0, 90, 140), 1)
            for (px, py) in CENTERS:
                cv2.circle(frame, (px, py), 3,
                           (0, 212, 255), -1)

            self._last_frame = frame.copy()

            frame_r = cv2.resize(frame, (CAM_W, CAM_H))
            img = Image.fromarray(
                cv2.cvtColor(frame_r, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(img)
            self.root.after(
                0, lambda i=imgtk: self._update_cam(i))
            time.sleep(0.033)

    def _update_cam(self, imgtk):
        self.cam_label.config(image=imgtk, text="",
                               width=CAM_W, height=CAM_H)
        self.cam_label.imgtk = imgtk

    # Scan face

    def _scan_face(self):
        if self._last_frame is None:
            messagebox.showwarning("Caméra", "Caméra non disponible")
            return
        if self._scan_idx >= len(FACE_ORDER):
            messagebox.showinfo("Scan", "6 faces déjà capturées")
            return

        frame_hsv = cv2.cvtColor(self._last_frame,
                                  cv2.COLOR_BGR2HSV)
        colors = detect_face_colors(frame_hsv, CENTERS)

        if "?" in colors:
            messagebox.showwarning(
                "Détection",
                "Couleurs non détectées, repositionne le cube")
            return

        face_name = FACE_ORDER[self._scan_idx]
        self.faces[face_name] = list(colors)
        self.cube_view.update_face(face_name, colors)
        self._scan_idx += 1

        n = self._scan_idx
        self.faces_lbl.config(
            text="Faces capturées : {} / 6".format(n))
        self._log("Face {} : {}".format(face_name, colors))

        if n < len(FACE_ORDER):
            next_face = FACE_ORDER[n]
            self.scan_hint.config(
                text="Face {}/6 — {} — Appuie sur SCANNER".format(
                    n + 1, FACE_LABELS[next_face]))
        else:
            self.scan_hint.config(
                text="✓  6 faces capturées — Lance RÉSOUDRE",
                fg=C_GREEN)
            self._log("6 faces capturées, prêt à résoudre", "ok")

    def _reset_scan(self):
        self._scan_idx = 0
        self.faces = {}
        self.cube_view.reset()
        self.faces_lbl.config(text="Faces capturées : 0 / 6")
        self.scan_hint.config(
            text="Face 1/6 — {} — Appuie sur SCANNER".format(
                FACE_LABELS[FACE_ORDER[0]]),
            fg=C_CYAN)
        self._log("Scan recommencé", "dim")

    # Bluetooth

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
            self._dot_lbl.config(
                text="ONLINE  " + port, fg=C_GREEN)
            self.conn_btn.config(
                text="⬡  DÉCONNECTER", fg=C_RED)
            self._log("Connecté {} @ {}".format(port, baud), "ok")

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

        if tag == "PROG":
            try:
                done, total = map(int, payload.split("/"))
                w = self._prog_cv.winfo_width() or 250
                self._prog_cv.coords(
                    self._prog_rect, 0, 0,
                    int(w * done / total), 8)
                self.prog_lbl.config(
                    text="Move {}/{}".format(done, total))
            except:
                pass

        elif tag == "DONE" and payload == "MOVE":
            w = self._prog_cv.winfo_width() or 250
            self._prog_cv.coords(self._prog_rect, 0, 0, w, 8)
            self.prog_lbl.config(text="✓  Terminé")
            self._timer_stop()
            self._log("Résolution terminée !", "ok")

        elif tag == "AUTH":
            parts   = payload.split(",")
            card_id = parts[0]
            ok      = len(parts) > 1 and parts[1] == "1"
            self.rfid_id.config(text=card_id)
            if ok:
                self.rfid_status.config(text="AUTORISÉ", fg=C_GREEN)
                self._set_badge(
                    "✓  ACCÈS AUTORISÉ — " + card_id,
                    C_GREEN, "#001a0d")
                self._log("RFID autorisé : {}".format(card_id), "ok")
            else:
                self.rfid_status.config(text="REFUSÉ", fg=C_RED)
                self._set_badge("✗  ACCÈS REFUSÉ", C_RED, "#1a0005")
                self._log("RFID refusé : {}".format(card_id), "err")

        elif tag == "ERR":
            self._log("Erreur : {}".format(payload), "err")

    # Solver

    def _solve(self):
        if len(self.faces) != 6:
            messagebox.showwarning("Solver",
                "Capture les 6 faces d'abord")
            return
        try:
            from solver.cube_solver import solve
            _, solution = solve(self.faces)
            self.solution = solution
            moves = solution.split()
            self.sol_text.config(text=solution)
            self.moves_lbl.config(
                text="◈  {} mouvements".format(len(moves)))
            self._prog_cv.coords(self._prog_rect, 0, 0, 0, 8)
            self.prog_lbl.config(text="Prêt à envoyer")
            self._log("Solution ({} moves) : {}".format(
                len(moves), solution), "ok")
        except Exception as e:
            messagebox.showerror("Solver", str(e))
            self._log("Erreur solver : {}".format(e), "err")

    def _send_solution(self):
        if not self.solution:
            messagebox.showwarning("Solution",
                "Résous d'abord le cube")
            return
        if not self.bt.is_connected():
            messagebox.showwarning("BT", "Non connecté")
            return
        self._prog_cv.coords(self._prog_rect, 0, 0, 0, 8)
        self.prog_lbl.config(text="Envoi en cours...")
        self._send("MOVE", self.solution)
        self._timer_reset()
        self._timer_start()

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
        t = ((time.time() - self.timer_start)
             if self.timer_running else self.elapsed)
        m = int(t) // 60
        s = t % 60
        self.timer_lbl.config(
            text="{:02d}:{:04.1f}".format(m, s))

    # Log

    def _log(self, text, style=""):
        ts = time.strftime("%H:%M:%S")
        self.log.config(state="normal")
        self.log.insert("end",
                        "[{}] {}\n".format(ts, text), style)
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
        self._cam_alive = False
        if self._cap:
            self._cap.release()
        self.bt.disconnect()
        self.root.destroy()


def run_app():
    Interface().run()


if __name__ == "__main__":
    run_app()