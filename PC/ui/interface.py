import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import sys
import os

# Pillow sert à afficher les images de la caméra dans Tkinter
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Ajout du dossier parent pour importer les modules du projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules du projet
from bluetooth.bt_uart import BTUart, list_ports
from graphique.cube_view import CubeView
from vision.camera import OverheadCamera
from vision.color_detection import FACE_ORDER, build_kociemba_string
from solver.cube_solver import solve
from solver.cube_simulator import CubeState

# Couleurs et styles de l'interface
BG        = "#1a1a2e"
BG2       = "#16213e"
FG        = "#e0e0e0"
ACCENT    = "#0f3460"
GREEN     = "#00c853"
RED       = "#ff1744"
ORANGE    = "#ff9100"
BLUE_L    = "#448aff"
PURPLE    = "#7e57c2"
FONT      = ("Segoe UI", 10)
FONT_B    = ("Segoe UI", 10, "bold")
FONT_BIG  = ("Segoe UI", 14, "bold")
FONT_MONO = ("Consolas", 10)
FONT_TIME = ("Consolas", 22, "bold")

# Temps avant capture automatique d'une face
AUTO_CAPTURE_DELAY = 5


class App:
    def __init__(self, root):
        # Fenêtre principale
        self.root = root
        self.root.title("Robot Rubik's Cube — Controle")
        self.root.configure(bg=BG)
        self.root.minsize(1200, 720)

        # Outils du projet
        self.bt = BTUart()
        self.cam = OverheadCamera()
        self.cube_state = CubeState()

        # Données de scan et de résolution
        self.captured_faces = {}
        self.solution_moves = []
        self.solution_str = ""
        self.solving = False
        self.scanning = False
        self.move_index = 0

        # Timer de résolution
        self.timer_running = False
        self.timer_start = 0
        self.timer_elapsed = 0.0

        # RFID
        self.rfid_id = "—"
        self.rfid_status = False

        # Création de l'interface
        self._build_ui()
        self._poll_bt()
        self._update_timer_display()

        # Ouverture de la caméra au démarrage
        if self.cam.open():
            self._log("Camera ouverte au demarrage", "info")
        else:
            self._log("Avertissement : camera non disponible", "error")

        # Mise à jour continue de l'affichage caméra
        self._update_camera_tk()

    def _build_ui(self):
        # Barre du haut : Bluetooth + RFID
        top = tk.Frame(self.root, bg=BG2, pady=6, padx=10)
        top.pack(fill="x")

        tk.Label(top, text="PORT COM", bg=BG2, fg=FG, font=FONT_B).pack(side="left")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(top, textvariable=self.port_var,
                                        width=12, state="readonly")
        self.port_combo.pack(side="left", padx=(4, 2))
        tk.Button(top, text="⟳", command=self._refresh_ports,
                  bg=ACCENT, fg=FG, font=FONT, bd=0, padx=6).pack(side="left", padx=2)
        self.btn_connect = tk.Button(top, text="Connecter", command=self._toggle_connect,
                                      bg=GREEN, fg="black", font=FONT_B, bd=0, padx=12)
        self.btn_connect.pack(side="left", padx=6)
        self.lbl_bt = tk.Label(top, text="● Deconnecte", bg=BG2, fg=RED, font=FONT_B)
        self.lbl_bt.pack(side="left", padx=10)

        # Zone RFID
        rf = tk.Frame(top, bg=BG2)
        rf.pack(side="right")
        tk.Label(rf, text="RFID :", bg=BG2, fg=FG, font=FONT_B).pack(side="left")
        self.lbl_rfid_icon = tk.Label(rf, text="●", bg=BG2, fg=RED, font=FONT_BIG)
        self.lbl_rfid_icon.pack(side="left", padx=2)
        self.lbl_rfid_id = tk.Label(rf, text="Aucun badge", bg=BG2, fg=FG, font=FONT)
        self.lbl_rfid_id.pack(side="left", padx=4)

        # Zone principale
        main = tk.Frame(self.root, bg=BG)
        main.pack(fill="both", expand=True, padx=8, pady=6)

        # Colonne gauche : cube + temps + solution
        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 6))

        tk.Label(left, text="ETAT DU CUBE", bg=BG, fg=BLUE_L, font=FONT_BIG).pack(pady=(4, 2))
        self.cube_view = CubeView(left, cell_size=30, on_change=self._on_sticker_edit)
        self.cube_view.pack(pady=4)

        # Temps de résolution
        tf = tk.Frame(left, bg=BG2, padx=14, pady=8)
        tf.pack(pady=4, fill="x")
        tk.Label(tf, text="TEMPS DE RESOLUTION", bg=BG2, fg=FG, font=FONT_B).pack()
        self.lbl_timer = tk.Label(tf, text="00:00.0", bg=BG2, fg=GREEN, font=FONT_TIME)
        self.lbl_timer.pack()

        # Solution Kociemba
        kf = tk.Frame(left, bg="#1b2838", padx=10, pady=6,
                      highlightbackground=ORANGE, highlightthickness=1)
        kf.pack(fill="x", pady=4)
        kf.pack_propagate(False)
        kf.configure(height=160)

        tk.Label(kf, text="SOLUTION KOCIEMBA", bg="#1b2838", fg=ORANGE, font=FONT_BIG).pack(anchor="w")
        self.lbl_kociemba_string = tk.Label(kf, text="—", bg="#1b2838", fg="#80cbc4",
                                             font=("Consolas", 9), anchor="w")
        self.lbl_kociemba_string.pack(anchor="w", pady=(2, 0))
        self.lbl_solution = tk.Label(kf, text="En attente du scan...", bg="#1b2838", fg=FG,
                                      font=("Consolas", 11, "bold"), wraplength=380, justify="left")
        self.lbl_solution.pack(anchor="w", pady=2)
        self.lbl_nb_moves = tk.Label(kf, text="", bg="#1b2838", fg=BLUE_L, font=FONT)
        self.lbl_nb_moves.pack(anchor="w")

        # Messages de progression
        self.lbl_progress = tk.Label(left, text="", bg=BG, fg=BLUE_L, font=FONT_B)
        self.lbl_progress.pack(pady=2)
        self.lbl_scan = tk.Label(left, text="", bg=BG, fg=BLUE_L, font=FONT_B)
        self.lbl_scan.pack(pady=2)

        # Zone centrale : caméra
        center = tk.Frame(main, bg=BG)
        center.pack(side="left", fill="both", expand=True, padx=4)

        cam_header = tk.Frame(center, bg=BG)
        cam_header.pack(fill="x")
        tk.Label(cam_header, text="CAMERA EN DIRECT", bg=BG, fg=BLUE_L, font=FONT_BIG).pack(side="left", pady=(4, 2))
        self.lbl_cam_status = tk.Label(cam_header, text="● Inactive", bg=BG, fg=RED, font=FONT_B)
        self.lbl_cam_status.pack(side="right", padx=8)

        self.camera_label = tk.Label(center, bg="#0d1117",
                                      text="Camera en cours d'initialisation..." if PIL_AVAILABLE
                                           else "Installer Pillow :\npip install Pillow",
                                      fg="#555", font=FONT)
        self.camera_label.pack(fill="both", expand=True, pady=2)

        # Zone droite : commandes
        right = tk.Frame(main, bg=BG, width=300)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        tk.Label(right, text="CONTROLES", bg=BG, fg=BLUE_L, font=FONT_BIG).pack(pady=(4, 6))

        self.btn_auto = tk.Button(right, text="🚀  Scanner + Resoudre",
                                   command=self._start_auto,
                                   bg="#00897b", fg="white", font=FONT_B,
                                   bd=0, padx=10, pady=10, width=22)
        self.btn_auto.pack(pady=4)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=4)

        self.btn_solve = tk.Button(right, text="🧩  Resoudre",
                                    command=self._solve_and_send,
                                    bg="#2e7d32", fg="white", font=FONT_B,
                                    bd=0, padx=10, pady=8, width=22)
        self.btn_solve.pack(pady=3)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=4)

        # Boutons robot
        gf = tk.Frame(right, bg=BG)
        gf.pack(pady=3)
        tk.Button(gf, text="✊ Attraper", command=lambda: self._send("GRAB"),
                  bg=ORANGE, fg="black", font=FONT_B, bd=0, padx=10, pady=6,
                  width=10).pack(side="left", padx=3)
        tk.Button(gf, text="🖐 Relacher", command=lambda: self._send("RELEASE"),
                  bg=PURPLE, fg="white", font=FONT_B, bd=0, padx=10, pady=6,
                  width=10).pack(side="left", padx=3)

        ttk.Separator(right, orient="horizontal").pack(fill="x", pady=4)

        # Zone log
        tk.Label(right, text="LOG", bg=BG, fg=FG, font=FONT_B).pack(anchor="w")
        self.log_text = tk.Text(right, height=12, bg="#0d1117", fg="#8b949e",
                                 font=("Consolas", 9), bd=0, wrap="word",
                                 insertbackground=FG)
        self.log_text.pack(fill="both", expand=True, pady=4)

        # Couleurs du texte du log
        self.log_text.tag_configure("tx",      foreground="#ff9100")
        self.log_text.tag_configure("rx",      foreground="#66bb6a")
        self.log_text.tag_configure("info",    foreground="#448aff")
        self.log_text.tag_configure("error",   foreground="#ff1744")
        self.log_text.tag_configure("success", foreground="#00c853")
        self.log_text.tag_configure("solve",   foreground="#80cbc4")

        # Liste des ports disponibles
        self._refresh_ports()

    def _update_camera_tk(self):
        # Mise à jour de l'image caméra dans l'interface
        try:
            if PIL_AVAILABLE and self.cam.is_opened():
                frame_rgb = self.cam.get_frame_rgb()
                if frame_rgb is not None:
                    lw = self.camera_label.winfo_width()
                    lh = self.camera_label.winfo_height()
                    if lw > 10 and lh > 10:
                        h, w = frame_rgb.shape[:2]
                        scale = min(lw / w, lh / h)
                        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
                        img = Image.fromarray(frame_rgb)
                        img = img.resize((nw, nh), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        self.camera_label.config(image=photo, text="")
                        self.camera_label.image = photo
                self.lbl_cam_status.config(text="● Active", fg=GREEN)
            elif not PIL_AVAILABLE:
                self.lbl_cam_status.config(text="● Pillow manquant", fg=ORANGE)
            else:
                self.lbl_cam_status.config(text="● Inactive", fg=RED)
        except Exception:
            pass
        self.root.after(50, self._update_camera_tk)

    def _log(self, msg, tag=None):
        # Ajout d'un message avec heure dans le log
        ts = time.strftime("%H:%M:%S")
        full = "[{}] {}".format(ts, msg)
        print(full)
        self.log_text.insert("end", full + "\n", tag)
        self.log_text.see("end")

    def _refresh_ports(self):
        # Recherche des ports série disponibles
        ports = list_ports()
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)

    def _toggle_connect(self):
        # Connexion ou déconnexion Bluetooth
        if self.bt.is_connected():
            self.bt.disconnect()
            self.btn_connect.config(text="Connecter", bg=GREEN)
            self.lbl_bt.config(text="● Deconnecte", fg=RED)
            self._log("Bluetooth deconnecte", "info")
        else:
            port = self.port_var.get()
            if not port:
                messagebox.showwarning("Port", "Selectionne un port COM")
                return
            try:
                self.bt.connect(port)
                self.btn_connect.config(text="Deconnecter", bg=RED)
                self.lbl_bt.config(text="● Connecte ({})".format(port), fg=GREEN)
                self._log("Bluetooth connecte sur {}".format(port), "success")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
                self._log("Erreur connexion: {}".format(e), "error")

    def _send(self, tag, payload=""):
        # Envoi d'une commande au robot
        try:
            self.bt.send(tag, payload)
            display = payload if len(payload) < 60 else payload[:60] + "..."
            self._log("TX -> {} : {}".format(tag, display), "tx")
        except Exception as e:
            self._log("ERREUR envoi: {}".format(e), "error")

    def _poll_bt(self):
        # Lecture continue des messages reçus
        while not self.bt.rx_queue.empty():
            line, tag, payload = self.bt.rx_queue.get_nowait()
            if tag:
                self._log("RX <- {} : {}".format(tag, payload), "rx")
            self._handle_rx(tag, payload)
        self.root.after(80, self._poll_bt)

    def _handle_rx(self, tag, payload):
        # Traitement des messages reçus du robot
        if tag is None:
            return

        if tag == "PONG":
            self._log("PONG recu — connexion OK", "success")

        elif tag == "AUTH":
            parts = payload.split(",")
            if len(parts) == 2:
                card_id, auth = parts
                self.rfid_id = card_id
                self.rfid_status = auth == "1"
                if self.rfid_status:
                    self.lbl_rfid_icon.config(fg=GREEN)
                    self.lbl_rfid_id.config(text="Badge autorise  ID: {}".format(card_id), fg=GREEN)
                    self._log("RFID Badge autorise — ID: {}".format(card_id), "success")
                else:
                    self.lbl_rfid_icon.config(fg=RED)
                    self.lbl_rfid_id.config(text="Badge refuse  ID: {}".format(card_id), fg=RED)
                    self._log("RFID Badge refuse — ID: {}".format(card_id), "error")

        elif tag == "SCAN_READY":
            face_name = payload.strip()
            self._log("Face {} — capture dans {}s...".format(face_name, AUTO_CAPTURE_DELAY), "info")
            self.lbl_scan.config(text="Face {} — capture dans {}s...".format(face_name, AUTO_CAPTURE_DELAY))
            self.cam._current_face = face_name
            threading.Thread(target=self._capture_face_auto, args=(face_name,), daemon=True).start()

        elif tag == "SCAN_DONE":
            self.scanning = False
            n = len(self.captured_faces)
            self.lbl_scan.config(text="Scan termine — {}/6 faces".format(n))
            self._log("== SCAN TERMINE — {}/6 faces ==".format(n), "success")
            if n == 6:
                try:
                    kstr = build_kociemba_string(self.captured_faces)
                    self.lbl_kociemba_string.config(text="Cube string : {}".format(kstr))
                    self._log("Chaine Kociemba : {}".format(kstr), "solve")
                except Exception as e:
                    self._log("Erreur construction chaine: {}".format(e), "error")
            self.cam._status_text = "RESOLUTION EN COURS"
            self.root.after(500, self._solve_and_send)

        elif tag == "AUTO_START":
            self._log("Bouton physique presse -> demarrage auto", "info")
            self._start_auto()

        elif tag == "PROG":
            parts = payload.split("/")
            if len(parts) == 2:
                try:
                    idx = int(parts[0]) - 1
                    total = int(parts[1])
                    if 0 <= idx < len(self.solution_moves):
                        mvt = self.solution_moves[idx]
                        self.cube_state.apply_move(mvt)
                        self._refresh_cube_view()
                        self.move_index = idx + 1
                        self.lbl_progress.config(
                            text="Mouvement {}/{} : {}".format(idx + 1, total, mvt))
                        self._log("Mouvement {}/{} : {} OK".format(idx + 1, total, mvt), "info")
                        self.cam._status_text = "RESOLUTION {}/{} - {}".format(idx + 1, total, mvt)
                except Exception:
                    pass

        elif tag == "DONE":
            self.solving = False
            self._stop_timer()
            self.cam._status_text = "TERMINE - Resolu en {:.1f}s".format(self.timer_elapsed)
            self.lbl_progress.config(text="Resolution terminee !")
            self.lbl_scan.config(text="")
            self._log("== RESOLU en {:.1f}s ==".format(self.timer_elapsed), "success")
            self._enable_buttons()

        elif tag == "ERR":
            self._log("ERREUR robot: {}".format(payload), "error")
            self.lbl_scan.config(text="Erreur: {}".format(payload), fg=RED)
            self.scanning = False
            self.cam._status_text = "En attente"
            self._enable_buttons()

        elif tag == "OK":
            self._log("OK: {}".format(payload), "success")

        elif tag == "LOG":
            self._log("Pico: {}".format(payload), "rx")

    def _start_auto(self):
        # Début du scan automatique
        if not self.bt.is_connected():
            messagebox.showwarning("Bluetooth", "Connecte-toi au robot d'abord.")
            return
        if not self.cam.is_opened():
            if not self.cam.open():
                messagebox.showerror("Camera", "Impossible d'ouvrir la camera.")
                return

        self._log("== DEMARRAGE SCAN AUTOMATIQUE ==", "info")
        self.captured_faces = {}
        self.cam.reset_scan()
        self.cube_view.reset()
        self.scanning = True
        self.lbl_scan.config(text="Scan auto en cours...")
        self.lbl_solution.config(text="En attente du scan...", fg=FG)
        self.lbl_kociemba_string.config(text="—")
        self.lbl_nb_moves.config(text="")
        self.lbl_progress.config(text="")
        self.timer_elapsed = 0.0
        self._disable_buttons()
        self._send("START_SCAN")

    def _capture_face_auto(self, face_name):
        # Compte à rebours puis capture de la face
        for i in range(AUTO_CAPTURE_DELAY, 0, -1):
            self.root.after(0, lambda n=i, fn=face_name: self.lbl_scan.config(
                text="Face {} — capture dans {}s...".format(fn, n)))
            time.sleep(1)

        colors = self.cam.snapshot_face(face_name)

        if colors and "?" not in colors:
            self.captured_faces[face_name] = list(colors)
            self.root.after(0, lambda fn=face_name, c=list(colors): self._on_face_scanned(fn, c))
            self._send("SCAN_ACK", face_name)
            self._log("Face {} capturee : {}".format(face_name, colors), "success")
        else:
            self._log("Face {} — echec detection, nouvelle tentative...".format(face_name), "error")
            time.sleep(1)
            colors = self.cam.snapshot_face(face_name)
            if colors:
                self.captured_faces[face_name] = list(colors)
                self.root.after(0, lambda fn=face_name, c=list(colors): self._on_face_scanned(fn, c))
            else:
                self.root.after(0, lambda fn=face_name: self.lbl_scan.config(
                    text="Face {} — detection echouee, corrigez manuellement".format(fn)))
            self._send("SCAN_ACK", face_name)

    def _on_sticker_edit(self, face_name, idx, new_color):
        # Correction manuelle d'une case du cube
        if face_name not in self.captured_faces:
            self.captured_faces[face_name] = ["?"] * 9
        self.captured_faces[face_name][idx] = new_color
        self._log("Edition : {} [{}] -> {}".format(face_name, idx, new_color), "info")

    def _on_face_scanned(self, face_name, colors):
        # Mise à jour visuelle après scan d'une face
        self.cube_view.update_face(face_name, colors)
        self.lbl_scan.config(text="Faces scannees : {}/6".format(len(self.captured_faces)))

    def _solve_and_send(self):
        # Calcul de la solution puis envoi au robot
        if len(self.captured_faces) < 6:
            self.lbl_solution.config(
                text="Il manque des faces ({}/6).\nCorrigez les couleurs et reessayez.".format(
                    len(self.captured_faces)), fg=ORANGE)
            self._enable_buttons()
            return
        if not self.bt.is_connected():
            messagebox.showwarning("Bluetooth", "Connecte-toi au robot.")
            self._enable_buttons()
            return

        self._log("Calcul de la solution Kociemba...", "info")
        try:
            cube_string, solution = solve(self.captured_faces)
            self.solution_str = solution
            self.solution_moves = solution.strip().split()
            self.move_index = 0
            nb = len(self.solution_moves)

            self.lbl_kociemba_string.config(text="Cube string : {}".format(cube_string))
            self.lbl_solution.config(text=solution, fg=FG)
            self.lbl_nb_moves.config(text="{} mouvements".format(nb))
            self.lbl_progress.config(text="0/{}".format(nb))

            self._log("CUBE STRING  : {}".format(cube_string), "solve")
            self._log("SOLUTION     : {}".format(solution), "solve")
            self._log("NB MOUVEMENTS: {}".format(nb), "solve")

            self.cube_state.set_faces(self.captured_faces)
            self._refresh_cube_view()

            self.solving = True
            self._disable_buttons()
            self._start_timer()
            self._log("Envoi des mouvements au robot...", "info")
            self._send("MOVE", solution)

        except Exception as e:
            self._log("ERREUR Kociemba: {}".format(e), "error")
            self.lbl_solution.config(
                text="Scan invalide — Cliquez sur les cases pour corriger\npuis appuyez sur Resoudre",
                fg=RED)
            self.lbl_nb_moves.config(text="")
            self.cam._status_text = "En attente"
            self._enable_buttons()

    def _start_timer(self):
        # Démarre le chronomètre
        self.timer_start = time.time()
        self.timer_running = True

    def _stop_timer(self):
        # Arrête le chronomètre
        self.timer_running = False
        self.timer_elapsed = time.time() - self.timer_start

    def _update_timer_display(self):
        # Affichage du temps en continu
        elapsed = time.time() - self.timer_start if self.timer_running else self.timer_elapsed
        mins = int(elapsed // 60)
        secs = elapsed % 60
        self.lbl_timer.config(text="{:02d}:{:04.1f}".format(mins, secs))
        self.root.after(100, self._update_timer_display)

    def _refresh_cube_view(self):
        # Met à jour la vue du cube avec l'état actuel
        for fn in FACE_ORDER:
            self.cube_view.update_face(fn, self.cube_state.faces[fn])

    def _disable_buttons(self):
        # Bloque les boutons pendant une action importante
        for b in (self.btn_auto, self.btn_solve):
            b.config(state="disabled")

    def _enable_buttons(self):
        # Réactive les boutons
        for b in (self.btn_auto, self.btn_solve):
            b.config(state="normal")


class WelcomePage:
    # Couleurs de l'écran d'accueil
    BG_DARK  = "#0a0a18"
    FG_TITLE = "#ffffff"
    FG_SUB   = "#9090b0"
    FG_HINT  = "#3a3a5c"
    BTN_BG   = "#00897b"
    BTN_HOV  = "#00695c"
    CUBE_COLORS = ["#ffffff", "#ff1744", "#00c853", "#ffd600", "#ff9100", "#448aff"]

    def __init__(self, root, on_launch):
        self.root = root
        self.on_launch = on_launch
        self._build()

    def _build(self):
        # Fond de la page d'accueil
        f = tk.Frame(self.root, bg=self.BG_DARK)
        f.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._frame = f

        # Bande colorée en haut
        bar = tk.Frame(f, height=10, bg=self.BG_DARK)
        bar.pack(fill="x", side="top")
        for c in self.CUBE_COLORS:
            tk.Frame(bar, bg=c, height=10).pack(side="left", fill="x", expand=True)

        # Bande colorée en bas
        bot = tk.Frame(f, height=6, bg=self.BG_DARK)
        bot.pack(fill="x", side="bottom")
        for c in reversed(self.CUBE_COLORS):
            tk.Frame(bot, bg=c, height=6).pack(side="left", fill="x", expand=True)

        # Contenu centré
        center = tk.Frame(f, bg=self.BG_DARK)
        center.place(relx=0.5, rely=0.5, anchor="center")

        # Petit dessin du cube
        cube_frame = tk.Frame(center, bg=self.BG_DARK)
        cube_frame.pack(pady=(0, 20))
        MINI = [
            ["#ff1744","#ff9100","#ffd600"],
            ["#00c853","#ffffff","#448aff"],
            ["#448aff","#ffd600","#ff1744"],
        ]
        for row in MINI:
            r = tk.Frame(cube_frame, bg=self.BG_DARK)
            r.pack()
            for color in row:
                tk.Frame(r, bg=color, width=28, height=28,
                         highlightbackground="#0a0a18",
                         highlightthickness=2).pack(side="left")

        tk.Label(center, text="ROBOT RUBIK'S CUBE",
                 bg=self.BG_DARK, fg=self.FG_TITLE,
                 font=("Segoe UI", 40, "bold")).pack(pady=(12, 4))

        tk.Label(center, text="Systeme de resolution automatique",
                 bg=self.BG_DARK, fg=self.FG_SUB,
                 font=("Segoe UI", 16)).pack()

        sep = tk.Frame(center, bg=self.BG_DARK)
        sep.pack(pady=20)
        for c in self.CUBE_COLORS:
            tk.Frame(sep, bg=c, width=60, height=4).pack(side="left", padx=3)

        # Bouton de lancement
        btn = tk.Button(center,
                        text="   🚀   LANCER L'APPLICATION   ",
                        command=self._launch,
                        bg=self.BTN_BG, fg="white",
                        font=("Segoe UI", 18, "bold"),
                        bd=0, padx=28, pady=18,
                        cursor="hand2",
                        activebackground=self.BTN_HOV,
                        activeforeground="white",
                        relief="flat")
        btn.pack(pady=10)
        btn.bind("<Enter>", lambda e: btn.config(bg=self.BTN_HOV))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.BTN_BG))

        tk.Label(center, text="HC-05 Bluetooth  •  MicroPython",
                 bg=self.BG_DARK, fg=self.FG_HINT,
                 font=("Segoe UI", 11)).pack(pady=(18, 0))

        tk.Label(f, text="v6.0  •  2026", bg=self.BG_DARK, fg=self.FG_HINT,
                 font=("Segoe UI", 10)).place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-16)

    def _launch(self):
        # Ouvre la page principale
        self._frame.destroy()
        self.on_launch()


def run_app():
    # Démarrage de la fenêtre principale
    root = tk.Tk()
    root.title("Robot Rubik's Cube")
    root.configure(bg="#0a0a18")
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry("{}x{}+0+0".format(sw, sh))
    root.state("zoomed")
    WelcomePage(root, on_launch=lambda: App(root))
    root.mainloop()


if __name__ == "__main__":
    run_app()