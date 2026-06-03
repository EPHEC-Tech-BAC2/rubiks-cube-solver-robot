# Importation de la bibliothèque Tkinter pour créer l'interface graphique
import tkinter as tk

# Importation du dictionnaire des couleurs et de l'ordre des faces du cube
from vision.color_detection import DISPLAY_HEX, FACE_ORDER

# Position de chaque face du cube dans l'affichage 2D
FACE_POSITIONS = {
    "U": (1, 0),  # Face Up (haut)
    "L": (0, 1),  # Face Left (gauche)
    "F": (1, 1),  # Face Front (avant)
    "R": (2, 1),  # Face Right (droite)
    "B": (3, 1),  # Face Back (arrière)
    "D": (1, 2),  # Face Down (bas)
}

# Liste des couleurs utilisées pour le changement manuel des cases
COLOR_CYCLE = ["Blanc", "Jaune", "Rouge", "Orange", "Vert", "Bleu"]


# Classe représentant la vue graphique du cube
class CubeView(tk.Canvas):

    # Constructeur de la classe
    def __init__(self, master, cell_size=28, on_change=None, **kwargs):

        # Taille d'une case du cube
        self.cell = cell_size

        # Calcul de la largeur totale du canvas
        w = 4 * 3 * cell_size + 20

        # Calcul de la hauteur totale du canvas
        h = 3 * 3 * cell_size + 20

        # Initialisation du Canvas Tkinter
        super().__init__(master, width=w, height=h, bg="#1e1e1e",
                         highlightthickness=0, cursor="hand2", **kwargs)

        # Création d'un dictionnaire contenant les 6 faces du cube
        # Chaque face contient 9 cases initialisées à "?"
        self.faces = {f: ["?"] * 9 for f in FACE_ORDER}

        # Fonction callback appelée lorsqu'une couleur change
        self.on_change = on_change

        # Dessine toutes les faces du cube
        self._draw_all()

    # Met à jour une face complète avec une nouvelle liste de couleurs
    def update_face(self, face_name, colors):

        # Copie les couleurs reçues dans la face concernée
        self.faces[face_name] = list(colors)

        # Redessine uniquement cette face
        self._draw_face(face_name)

    # Réinitialise complètement le cube
    def reset(self):

        # Remet toutes les cases à "?"
        self.faces = {f: ["?"] * 9 for f in FACE_ORDER}

        # Redessine tout le cube
        self._draw_all()

    # Dessine toutes les faces du cube
    def _draw_all(self):

        # Efface tous les éléments du canvas
        self.delete("all")

        # Parcourt toutes les faces dans l'ordre défini
        for face in FACE_ORDER:

            # Dessine chaque face
            self._draw_face(face)

    # Dessine une face spécifique
    def _draw_face(self, face_name):

        # Récupère la position de la face dans la grille d'affichage
        col, row = FACE_POSITIONS[face_name]

        # Calcul de la coordonnée X d'origine
        ox = 10 + col * 3 * self.cell

        # Calcul de la coordonnée Y d'origine
        oy = 10 + row * 3 * self.cell

        # Récupération des couleurs de la face
        colors = self.faces[face_name]

        # Supprime l'ancien dessin de cette face
        self.delete("face_{}".format(face_name))

        # Boucle sur les 9 cases de la face
        for i in range(9):

            # Calcul de la ligne et de la colonne de la case
            r, c = i // 3, i % 3

            # Coordonnée X du coin supérieur gauche
            x0 = ox + c * self.cell

            # Coordonnée Y du coin supérieur gauche
            y0 = oy + r * self.cell

            # Coordonnée X du coin inférieur droit
            x1 = x0 + self.cell

            # Coordonnée Y du coin inférieur droit
            y1 = y0 + self.cell

            # Récupère la couleur hexadécimale associée
            fill = DISPLAY_HEX.get(colors[i], "#444444")

            # Tag unique de la cellule
            tag_cell = "cell_{}_{}".format(face_name, i)

            # Tag commun à toute la face
            tag_face = "face_{}".format(face_name)

            # Dessine le rectangle représentant la case
            self.create_rectangle(x0, y0, x1, y1,
                                   fill=fill, outline="#555555", width=1,
                                   tags=(tag_face, tag_cell))

            # Dessine la première lettre de la couleur au centre de la case
            self.create_text((x0 + x1) // 2, (y0 + y1) // 2,
                              text=colors[i][0] if colors[i] != "?" else "?",
                              fill="black" if colors[i] == "Blanc" else "white",
                              font=("Consolas", 8),
                              tags=(tag_face, tag_cell))

            # Associe un clic gauche à la fonction de changement de couleur
            self.tag_bind(tag_cell, "<Button-1>",
                          lambda e, f=face_name, idx=i: self._cycle_color(f, idx))

    # Change la couleur d'une case en passant à la suivante dans COLOR_CYCLE
    def _cycle_color(self, face_name, idx):

        # Récupère la couleur actuelle
        current = self.faces[face_name][idx]

        try:
            # Recherche l'index de la couleur actuelle puis passe à la suivante
            next_idx = (COLOR_CYCLE.index(current) + 1) % len(COLOR_CYCLE)

        # Si la couleur actuelle n'existe pas dans COLOR_CYCLE
        except ValueError:

            # Commence à la première couleur
            next_idx = 0

        # Récupère la nouvelle couleur
        new_color = COLOR_CYCLE[next_idx]

        # Met à jour la couleur dans le tableau
        self.faces[face_name][idx] = new_color

        # Redessine la face concernée
        self._draw_face(face_name)

        # Si une fonction callback existe
        if self.on_change:

            # Informe le programme que la couleur a changé
            self.on_change(face_name, idx, new_color)