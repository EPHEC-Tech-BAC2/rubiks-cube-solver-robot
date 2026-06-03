import numpy as np

# ordre des faces pour la chaine Kociemba
FACE_ORDER = ["U", "R", "F", "D", "L", "B"]

# couleurs BGR pour OpenCV (affichage sur l image camera)
DISPLAY_BGR = {
    "Blanc":  (240, 240, 240),
    "Rouge":  (0,   0,   220),
    "Vert":   (0,   200,  0 ),
    "Jaune":  (0,   220, 220),
    "Orange": (0,   120, 255),
    "Bleu":   (210,  0,   0 ),
}

# couleurs hex pour Tkinter (affichage dans l interface)
DISPLAY_HEX = {
    "Blanc":  "#f0f0f0",
    "Rouge":  "#dc0000",
    "Vert":   "#00c800",
    "Jaune":  "#dcdc00",
    "Orange": "#ff7800",
    "Bleu":   "#0000dc",
    "?":      "#444444",
}

# mettre True pour afficher les valeurs HSV dans la console (debug)
DEBUG_HSV = False


# distance entre deux teintes sur le cercle chromatique (H de 0 a 180 en OpenCV)
def circular_hue_distance(h1, h2):
    d = abs(h1 - h2)
    return min(d, 180 - d)


# detecte la couleur d un pixel a partir de ses valeurs HSV
# orange est verifie AVANT rouge pour eviter les confusions
def detect_color(h, s, v):
    # blanc : peu de saturation et bien lumineux
    if s < 60 and v > 170:
        return "Blanc"

    # orange : teinte entre 6 et 22
    if 6 <= h <= 22 and s > 100 and v > 80:
        return "Orange"

    # jaune : teinte entre 23 et 38
    if 23 <= h <= 38 and s > 80 and v > 80:
        return "Jaune"

    # vert : teinte entre 39 et 85
    if 39 <= h <= 85 and s > 70 and v > 50:
        return "Vert"

    # bleu : teinte entre 95 et 135
    if 95 <= h <= 135 and s > 70 and v > 50:
        return "Bleu"

    # rouge : teinte tres basse ou tres haute (entoure le 0/180)
    if ((0 <= h <= 5) or (170 <= h <= 179)) and s > 90 and v > 50:
        return "Rouge"

    # si rien ne correspond, prend la couleur la plus proche par distance de teinte
    centres = {
        "Rouge":  0,
        "Orange": 14,
        "Jaune":  30,
        "Vert":   60,
        "Bleu":   115,
    }
    best = min(centres, key=lambda n: circular_hue_distance(h, centres[n]))

    if DEBUG_HSV:
        print("[FALLBACK] H={} S={} V={} -> {}".format(h, s, v, best))

    return best


# detecte les 9 couleurs d une face a partir de l image HSV
def detect_face_colors(frame_hsv, centers, face_name="?"):
    h_img, w_img = frame_hsv.shape[:2]
    result = []

    if DEBUG_HSV:
        print("\n--- Detection face {} ---".format(face_name))

    for idx, (px, py) in enumerate(centers):
        # echantillon de 8x8 pixels autour du centre de chaque case
        x0, x1 = max(0, px - 8), min(w_img, px + 9)
        y0, y1 = max(0, py - 8), min(h_img, py + 9)
        patch = frame_hsv[y0:y1, x0:x1]

        if patch.size == 0:
            result.append("?")
            continue

        # prend la valeur mediane pour ignorer les pixels parasites
        h = int(np.median(patch[:, :, 0]))
        s = int(np.median(patch[:, :, 1]))
        v = int(np.median(patch[:, :, 2]))

        color = detect_color(h, s, v)
        result.append(color)

        if DEBUG_HSV:
            pos = ["TL", "TM", "TR", "ML", "CC", "MR", "BL", "BM", "BR"]
            tag = pos[idx] if idx < 9 else str(idx)
            marker = " <<<" if color in ("Rouge", "Orange") else ""
            print("  [{}] H={:3d}  S={:3d}  V={:3d}  -> {:7s}{}".format(
                tag, h, s, v, color, marker))

    return result


# construit la chaine de 54 caracteres pour l algorithme Kociemba
# chaque lettre correspond a une face (U R F D L B)
def build_kociemba_string(faces):
    # les centres des faces definissent quelle couleur = quelle face
    color_to_face = {faces[f][4]: f for f in FACE_ORDER}
    cube_string = ""
    for face_name in FACE_ORDER:
        stickers = faces[face_name]
        if len(stickers) != 9:
            raise ValueError("La face {} n'a pas 9 cases".format(face_name))
        for color in stickers:
            if color not in color_to_face:
                raise ValueError("Couleur inconnue : {}".format(color))
            cube_string += color_to_face[color]
    if len(cube_string) != 54:
        raise ValueError("Chaine de {} caracteres au lieu de 54".format(len(cube_string)))
    return cube_string
