# Importation de la bibliothèque NumPy pour les calculs sur les tableaux/images
import numpy as np

# Ordre officiel des faces utilisé dans tout le programme
FACE_ORDER = ["U", "R", "F", "D", "L", "B"]

# Couleurs BGR utilisées pour l'affichage OpenCV
DISPLAY_BGR = {
    "Blanc":  (240, 240, 240),  # Blanc
    "Rouge":  (0,   0,   220),  # Rouge
    "Vert":   (0,   200,  0 ),  # Vert
    "Jaune":  (0,   220, 220),  # Jaune
    "Orange": (0,   120, 255),  # Orange
    "Bleu":   (210,  0,   0 ),  # Bleu
}

# Couleurs HEX utilisées pour l'affichage Tkinter
DISPLAY_HEX = {
    "Blanc":  "#f0f0f0",  # Blanc
    "Rouge":  "#dc0000",  # Rouge
    "Vert":   "#00c800",  # Vert
    "Jaune":  "#dcdc00",  # Jaune
    "Orange": "#ff7800",  # Orange
    "Bleu":   "#0000dc",  # Bleu
    "?":      "#444444",  # Inconnu
}

# Active ou désactive l'affichage des informations HSV
DEBUG_HSV = False


# Calcule la distance circulaire entre deux teintes HSV
def circular_hue_distance(h1, h2):

    # Documentation de la fonction
    """Distance circulaire entre deux teintes (H va de 0 à 180 en OpenCV)."""

    # Différence absolue entre les deux teintes
    d = abs(h1 - h2)

    # Retourne la plus courte distance sur le cercle HSV
    return min(d, 180 - d)


# Détecte la couleur à partir des valeurs HSV
def detect_color(h, s, v):

    # Documentation de la fonction
    """
    Détection de couleur — logique de face_capture.py.
    L'ordre est important : Orange est testé AVANT Rouge.
    """

    # Détection du blanc
    if s < 60 and v > 170:
        return "Blanc"

    # Détection de l'orange
    # Testé avant le rouge pour éviter les erreurs
    if 6 <= h <= 22 and s > 100 and v > 80:
        return "Orange"

    # Détection du jaune
    if 23 <= h <= 38 and s > 80 and v > 80:
        return "Jaune"

    # Détection du vert
    if 39 <= h <= 85 and s > 70 and v > 50:
        return "Vert"

    # Détection du bleu
    if 95 <= h <= 135 and s > 70 and v > 50:
        return "Bleu"

    # Détection du rouge
    # Rouge est situé aux extrémités du cercle HSV
    if ((0 <= h <= 5) or (170 <= h <= 179)) and s > 90 and v > 50:
        return "Rouge"

    # Si aucune couleur n'est détectée clairement
    # Recherche de la couleur la plus proche
    centres = {
        "Rouge":  0,
        "Orange": 14,
        "Jaune":  30,
        "Vert":   60,
        "Bleu":   115,
    }

    # Recherche de la couleur dont la teinte est la plus proche
    best = min(centres, key=lambda n: circular_hue_distance(h, centres[n]))

    # Affichage debug si activé
    if DEBUG_HSV:
        print("[FALLBACK] H={} S={} V={} → {}".format(h, s, v, best))

    # Retourne la couleur la plus proche
    return best


# Détecte les 9 couleurs d'une face du cube
def detect_face_colors(frame_hsv, centers, face_name="?"):

    # Documentation
    """Détecte les 9 couleurs d'une face."""

    # Récupération de la taille de l'image HSV
    h_img, w_img = frame_hsv.shape[:2]

    # Liste qui contiendra les 9 couleurs détectées
    result = []

    # Affichage debug
    if DEBUG_HSV:
        print("\n--- Detection face {} ---".format(face_name))

    # Parcours des 9 positions du cube
    for idx, (px, py) in enumerate(centers):

        # Limites de la zone d'analyse autour du centre
        x0, x1 = max(0, px - 8), min(w_img, px + 9)
        y0, y1 = max(0, py - 8), min(h_img, py + 9)

        # Extraction de la zone à analyser
        patch = frame_hsv[y0:y1, x0:x1]

        # Si la zone est vide
        if patch.size == 0:

            # Couleur inconnue
            result.append("?")

            # Passe au sticker suivant
            continue

        # Calcul de la médiane de H
        h = int(np.median(patch[:, :, 0]))

        # Calcul de la médiane de S
        s = int(np.median(patch[:, :, 1]))

        # Calcul de la médiane de V
        v = int(np.median(patch[:, :, 2]))

        # Détection de la couleur
        color = detect_color(h, s, v)

        # Ajout dans le résultat final
        result.append(color)

        # Affichage debug
        if DEBUG_HSV:

            # Nom des positions du cube
            pos = ["TL", "TM", "TR", "ML", "CC", "MR", "BL", "BM", "BR"]

            # Nom de la position actuelle
            tag = pos[idx] if idx < 9 else str(idx)

            # Marqueur spécial pour rouge et orange
            marker = " <<<" if color in ("Rouge", "Orange") else ""

            # Affichage des valeurs HSV
            print("  [{}] H={:3d}  S={:3d}  V={:3d}  -> {:7s}{}".format(
                tag, h, s, v, color, marker))

    # Retourne la liste des 9 couleurs détectées
    return result


# Construit la chaîne de 54 caractères utilisée par Kociemba
def build_kociemba_string(faces):

    # Documentation
    """
    faces : dict {U: [9 noms], R: [...], ...}
    retourne la chaîne 54 caractères pour kociemba
    """

    # Création du dictionnaire couleur -> face centrale
    color_to_face = {faces[f][4]: f for f in FACE_ORDER}

    # Chaîne finale du cube
    cube_string = ""

    # Parcours des faces dans l'ordre officiel
    for face_name in FACE_ORDER:

        # Récupération des stickers de la face
        stickers = faces[face_name]

        # Vérifie qu'il y a bien 9 stickers
        if len(stickers) != 9:
            raise ValueError("La face {} n'a pas 9 cases".format(face_name))

        # Parcours de chaque sticker
        for color in stickers:

            # Vérifie que la couleur existe
            if color not in color_to_face:
                raise ValueError("Couleur inconnue : {}".format(color))

            # Ajoute la lettre de la face correspondante
            cube_string += color_to_face[color]

    # Vérifie que la chaîne contient bien 54 caractères
    if len(cube_string) != 54:
        raise ValueError(
            "Chaine de {} caracteres au lieu de 54".format(len(cube_string))
        )

    # Retourne la chaîne compatible Kociemba
    return cube_string