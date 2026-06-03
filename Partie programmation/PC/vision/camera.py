import cv2
import threading
import time as _time
from vision.color_detection import detect_face_colors, DISPLAY_BGR, FACE_ORDER

# index de la webcam (1 = camera USB externe)
CAMERA_INDEX = 1

# zone de detection dans l image (rectangle autour du cube)
X1, Y1, X2, Y2 = 160, 80, 400, 320
SQ = (X2 - X1) // 3

# noms des faces pour l affichage a l ecran
FACE_LABELS = {
    "U": "Haut (blanc)",
    "R": "Droite (rouge)",
    "F": "Avant (vert)",
    "D": "Bas (jaune)",
    "L": "Gauche (orange)",
    "B": "Arriere (bleu)",
}


# calcule les centres des 9 cases du cube dans l image
def grid_centers():
    pts = []
    for r in range(3):
        for c in range(3):
            cx = X1 + c * SQ + SQ // 2
            cy = Y1 + r * SQ + SQ // 2
            pts.append((cx, cy))
    return pts


# dessine la grille avec les couleurs detectees sur l image
def draw_grid(frame, centers, colors):
    cv2.rectangle(frame, (X1, Y1), (X2, Y2), (0, 255, 150), 2)
    for idx, _ in enumerate(centers):
        c, r = idx % 3, idx // 3
        rx0, ry0 = X1 + c * SQ, Y1 + r * SQ
        rx1, ry1 = rx0 + SQ, ry0 + SQ
        name = colors[idx] if idx < len(colors) else "?"
        fill = DISPLAY_BGR.get(name, (100, 100, 100))
        # colorie la case avec transparence
        overlay = frame.copy()
        cv2.rectangle(overlay, (rx0, ry0), (rx1, ry1), fill, -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
        cv2.rectangle(frame, (rx0, ry0), (rx1, ry1), (200, 200, 200), 1)
        # affiche les 3 premieres lettres de la couleur
        cv2.putText(frame, name[:3], (rx0 + 4, ry0 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return frame


class OverheadCamera:

    def __init__(self, index=CAMERA_INDEX):
        self.index = index
        self.cap = None
        self.centers = grid_centers()

        self._current_face = ""
        self._faces_done = {}
        self._status_text = "Camera inactive"
        self._stable_count = 0
        self._last_colors = []

        # buffer partage entre le thread de lecture et l interface
        self._frame_buf = None
        self._frame_hsv_buf = None
        self._buf_lock = threading.Lock()
        self._reader_thread = None
        self._reading = False

    # ouvre la webcam et demarre le thread de lecture
    def open(self):
        if self.cap and self.cap.isOpened():
            return True
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            self.cap = None
            return False
        self._reading = True
        self._status_text = "En attente"
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        return True

    def close(self):
        self._reading = False
        if self.cap:
            self.cap.release()
            self.cap = None
        with self._buf_lock:
            self._frame_buf = None
            self._frame_hsv_buf = None
        self._status_text = "Camera inactive"

    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()

    # thread qui lit les images en continu sans bloquer l interface
    def _reader_loop(self):
        while self._reading:
            if not (self.cap and self.cap.isOpened()):
                _time.sleep(0.05)
                continue
            ret, frame = self.cap.read()
            if ret:
                # retourne l image (camera montee a l envers)
                frame = cv2.flip(frame, -1)
                # conversion BGR -> HSV pour la detection des couleurs
                frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                with self._buf_lock:
                    self._frame_buf = frame
                    self._frame_hsv_buf = frame_hsv
            else:
                _time.sleep(0.01)

    # retourne une copie de la derniere image lue
    def _get_frame_copy(self):
        with self._buf_lock:
            if self._frame_buf is None:
                return None, None
            return self._frame_buf.copy(), self._frame_hsv_buf.copy()

    # retourne l image annotee en RGB pour l affichage Tkinter
    def get_frame_rgb(self):
        frame, frame_hsv = self._get_frame_copy()
        if frame is None:
            return None

        is_solving = ("SOLUTION" in self._status_text.upper() or
                      "TERMIN" in self._status_text.upper())

        if not is_solving:
            face = self._current_face if self._current_face else None
            colors = detect_face_colors(frame_hsv, self.centers, face)
            frame = draw_grid(frame, self.centers, colors)

            if self._current_face:
                cv2.putText(frame,
                            "Face {} - {}".format(self._current_face,
                                                   FACE_LABELS.get(self._current_face, "")),
                            (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 150), 2)
            else:
                cv2.putText(frame, self._status_text, (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 150), 2)
        else:
            cv2.putText(frame, self._status_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 150), 2)

        # affiche l etat de chaque face sur le cote droit
        for i, fn in enumerate(FACE_ORDER):
            if fn in self._faces_done:
                txt, col = "{}: OK".format(fn), (0, 255, 0)
            elif fn == self._current_face:
                txt, col = "{}: ...".format(fn), (0, 200, 255)
            else:
                txt, col = "{}: --".format(fn), (150, 150, 150)
            cv2.putText(frame, txt, (520, 30 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)

        # conversion BGR -> RGB pour Tkinter
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # capture une face en faisant un vote sur 7 images (plus fiable qu une seule)
    def snapshot_face(self, face_name, n_samples=7):
        self._current_face = face_name
        samples = []
        for _ in range(n_samples):
            _, frame_hsv = self._get_frame_copy()
            if frame_hsv is not None:
                colors = detect_face_colors(frame_hsv, self.centers, face_name)
                if "?" not in colors:
                    samples.append(colors)
            _time.sleep(0.04)
        self._current_face = ""
        if not samples:
            return None
        # pour chaque case, prend la couleur la plus souvent detectee
        result = []
        for i in range(9):
            votes = {}
            for s in samples:
                votes[s[i]] = votes.get(s[i], 0) + 1
            result.append(max(votes, key=lambda c: votes[c]))
        self._faces_done[face_name] = result
        self._status_text = "Face {} capturee !".format(face_name)
        return result

    def reset_scan(self):
        self._faces_done = {}
        self._current_face = ""
        self._status_text = "En attente"
        self._stable_count = 0
        self._last_colors = []

    def update_preview(self):
        pass
