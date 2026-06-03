# Fichier : PC/vision/face_capture.py
# Membre 3 - branch : vision-solver
# Capture les 6 faces du cube et envoie le résultat au solveur Kociemba

import cv2
import numpy as np
import sys
from pathlib import Path

# Permet d'importer PC/solver/cube_solver.py
sys.path.append(str(Path(__file__).resolve().parents[1]))

from solver.cube_solver import solve_from_faces 

# --------- Réglages caméra ----------
CAMERA_INDEX = 1   # change en 0, 1, 2 ou 3 si besoin

# --------- Zone de
# 
# lecture 3x3 ----------
X1, Y1, X2, Y2 = 160, 80, 400, 320
SQ = (X2 - X1) // 3

# --------- Ordre demandé par Kociemba ----------
FACE_ORDER = ["U", "R", "F", "D", "L", "B"]
FACE_LABELS = {
    "U": "Up / Haut",
    "R": "Right / Droite",
    "F": "Front / Avant",
    "D": "Down / Bas",
    "L": "Left / Gauche",
    "B": "Back / Arriere",
}

# Couleurs d'affichage (BGR pour OpenCV)
DISPLAY = {
    "Blanc":  (240, 240, 240),
    "Rouge":  (0,   0,   220),
    "Vert":   (0,   200,  0),
    "Jaune":  (0,   220, 220),
    "Orange": (0,   120, 255),
    "Bleu":   (220,  0,   0),
}

def grid_centers():
    pts = []
    for r in range(3):
        for c in range(3):
            cx = X1 + c * SQ + SQ // 2
            cy = Y1 + r * SQ + SQ // 2
            pts.append((cx, cy))
    return pts

def circular_hue_distance(h1, h2):
    d = abs(h1 - h2)
    return min(d, 180 - d)

def detect_color_hsv(hsv_pixel):
    h, s, v = int(hsv_pixel[0]), int(hsv_pixel[1]), int(hsv_pixel[2])

    # Blanc
    if s < 60 and v > 170:
        return "Blanc"

    # Orange
    if 6 <= h <= 22 and s > 100 and v > 80:
        return "Orange"

    # Jaune
    if 23 <= h <= 38 and s > 80 and v > 80:
        return "Jaune"

    # Vert
    if 39 <= h <= 85 and s > 70 and v > 50:
        return "Vert"

    # Bleu
    if 95 <= h <= 135 and s > 70 and v > 50:
        return "Bleu"

    # Rouge
    if ((0 <= h <= 5) or (170 <= h <= 179)) and s > 90 and v > 50:
        return "Rouge"

    # fallback
    centres = {
        "Rouge": 0,
        "Orange": 14,
        "Jaune": 30,
        "Vert": 60,
        "Bleu": 115,
    }

    best_name = "Blanc"
    best_dist = 999

    for name, hc in centres.items():
        d = circular_hue_distance(h, hc)
        if d < best_dist:
            best_dist = d
            best_name = name

    return best_name

def detect_face_hsv(frame_hsv, centers):
    h_img, w_img = frame_hsv.shape[:2]
    result = []

    for (px, py) in centers:
        x0 = max(0, px - 8)
        x1 = min(w_img, px + 9)
        y0 = max(0, py - 8)
        y1 = min(h_img, py + 9)

        patch = frame_hsv[y0:y1, x0:x1]

        if patch.size == 0:
            result.append("?")
            continue

        med_h = int(np.median(patch[:, :, 0]))
        med_s = int(np.median(patch[:, :, 1]))
        med_v = int(np.median(patch[:, :, 2]))

        color_name = detect_color_hsv((med_h, med_s, med_v))
        result.append(color_name)

    return result

def draw_grid(frame, centers, colors):
    cv2.rectangle(frame, (X1, Y1), (X2, Y2), (0, 255, 150), 2)

    for idx, (px, py) in enumerate(centers):
        c = idx % 3
        r = idx // 3
        rx0, ry0 = X1 + c * SQ, Y1 + r * SQ
        rx1, ry1 = rx0 + SQ, ry0 + SQ

        name = colors[idx] if idx < len(colors) else "?"
        fill = DISPLAY.get(name, (100, 100, 100))

        overlay = frame.copy()
        cv2.rectangle(overlay, (rx0, ry0), (rx1, ry1), fill, -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        cv2.rectangle(frame, (rx0, ry0), (rx1, ry1), (200, 200, 200), 1)
        cv2.circle(frame, (px, py), 4, (255, 255, 255), -1)

        cv2.putText(
            frame,
            name[:3],
            (rx0 + 4, ry0 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

    return frame

def is_face_valid(colors):
    if len(colors) != 9:
        return False
    if "?" in colors:
        return False
    return True

def save_faces_to_file(faces, filename="faces_result.txt"):
    with open(filename, "w", encoding="utf-8") as f:
        for face_name in FACE_ORDER:
            f.write(f"{face_name}: {faces[face_name]}\n")

def main():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Caméra introuvable. Essaie CAMERA_INDEX = 0, 1, 2 ou 3.")
        return

    centers = grid_centers()
    faces = {}
    current_face_index = 0

    print("Ordre de capture : U, R, F, D, L, B")
    print("C = capturer la face courante")
    print("R = recommencer toutes les faces")
    print("Q = quitter")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Impossible de lire l'image caméra.")
            break

        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        colors = detect_face_hsv(frame_hsv, centers)

        display_frame = frame.copy()
        display_frame = draw_grid(display_frame, centers, colors)

        if current_face_index < len(FACE_ORDER):
            current_face_name = FACE_ORDER[current_face_index]
            current_face_label = FACE_LABELS[current_face_name]
            info_text = f"Face a capturer : {current_face_name} ({current_face_label})"
        else:
            info_text = "Toutes les faces sont capturees"

        cv2.putText(
            display_frame,
            info_text,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 150),
            2
        )

        cv2.putText(
            display_frame,
            "C=capturer  R=reset  Q=quitter",
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 150),
            1
        )

        y_text = 80
        for face_name in FACE_ORDER:
            status = "OK" if face_name in faces else "--"
            cv2.putText(
                display_frame,
                f"{face_name}: {status}",
                (10, y_text),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1
            )
            y_text += 20

        cv2.imshow("Face Capture HSV", display_frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break

        if key == ord('r'):
            faces = {}
            current_face_index = 0
            print("Toutes les captures ont ete reinitialisees.")

        if key == ord('c'):
            if current_face_index >= len(FACE_ORDER):
                print("Les 6 faces sont deja capturees. Appuie sur R pour recommencer.")
                continue

            if not is_face_valid(colors):
                print("Face invalide. Detection incomplete.")
                continue

            face_name = FACE_ORDER[current_face_index]
            faces[face_name] = colors.copy()

            print(f"Face {face_name} capturee : {faces[face_name]}")
            current_face_index += 1

            if current_face_index == len(FACE_ORDER):
                print("\nToutes les faces ont ete capturees.")
                save_faces_to_file(faces)

                try:
                    cube_string, solution = solve_from_faces(faces)

                    print("Cube string :", cube_string)
                    print("Solution :", solution)

                    with open("cube_solution.txt", "w", encoding="utf-8") as f:
                        f.write("Faces capturees :\n")
                        for fn in FACE_ORDER:
                            f.write(f"{fn}: {faces[fn]}\n")
                        f.write("\n")
                        f.write(f"Cube string : {cube_string}\n")
                        f.write(f"Solution : {solution}\n")

                    print("Resultat sauvegarde dans cube_solution.txt")

                except Exception as e:
                    print("Erreur solveur :", e)
                    print("Verifie l'ordre des faces et les couleurs detectees.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()