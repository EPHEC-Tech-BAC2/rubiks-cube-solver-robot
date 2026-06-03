import tkinter as tk
from vision.color_detection import DISPLAY_HEX, FACE_ORDER

# position de chaque face dans la croix (colonne, ligne)
FACE_POSITIONS = {
    "U": (1, 0),  # haut
    "L": (0, 1),  # gauche
    "F": (1, 1),  # avant (face centrale)
    "R": (2, 1),  # droite
    "B": (3, 1),  # arriere
    "D": (1, 2),  # bas
}

# ordre de changement de couleur quand on clique sur une case
COLOR_CYCLE = ["Blanc", "Jaune", "Rouge", "Orange", "Vert", "Bleu"]


# widget canvas qui affiche les 6 faces du cube en forme de croix
# clic gauche sur une case = change la couleur (correction manuelle)
class CubeView(tk.Canvas):
    def __init__(self, master, cell_size=28, on_change=None, **kwargs):
        self.cell = cell_size
        # largeur = 4 faces * 3 cases, hauteur = 3 faces * 3 cases
        w = 4 * 3 * cell_size + 20
        h = 3 * 3 * cell_size + 20
        super().__init__(master, width=w, height=h, bg="#1e1e1e",
                         highlightthickness=0, cursor="hand2", **kwargs)
        # initialise toutes les cases a "?" (inconnu)
        self.faces = {f: ["?"] * 9 for f in FACE_ORDER}
        # callback appele quand une case est modifiee par clic
        self.on_change = on_change
        self._draw_all()

    # met a jour les couleurs d une face et redessine
    def update_face(self, face_name, colors):
        self.faces[face_name] = list(colors)
        self._draw_face(face_name)

    # remet toutes les faces a "?" (avant un nouveau scan)
    def reset(self):
        self.faces = {f: ["?"] * 9 for f in FACE_ORDER}
        self._draw_all()

    def _draw_all(self):
        self.delete("all")
        for face in FACE_ORDER:
            self._draw_face(face)

    # dessine les 9 cases d une face avec leurs couleurs
    def _draw_face(self, face_name):
        col, row = FACE_POSITIONS[face_name]
        ox = 10 + col * 3 * self.cell
        oy = 10 + row * 3 * self.cell
        colors = self.faces[face_name]
        self.delete("face_{}".format(face_name))
        for i in range(9):
            r, c = i // 3, i % 3
            x0 = ox + c * self.cell
            y0 = oy + r * self.cell
            x1 = x0 + self.cell
            y1 = y0 + self.cell
            fill = DISPLAY_HEX.get(colors[i], "#444444")
            tag_cell = "cell_{}_{}".format(face_name, i)
            tag_face = "face_{}".format(face_name)
            self.create_rectangle(x0, y0, x1, y1,
                                   fill=fill, outline="#555555", width=1,
                                   tags=(tag_face, tag_cell))
            # premiere lettre de la couleur au centre de la case
            self.create_text((x0 + x1) // 2, (y0 + y1) // 2,
                              text=colors[i][0] if colors[i] != "?" else "?",
                              fill="black" if colors[i] == "Blanc" else "white",
                              font=("Consolas", 8),
                              tags=(tag_face, tag_cell))
            # clic sur cette case = cycle la couleur
            self.tag_bind(tag_cell, "<Button-1>",
                          lambda e, f=face_name, idx=i: self._cycle_color(f, idx))

    # change la couleur d une case au clic (passe a la suivante dans le cycle)
    def _cycle_color(self, face_name, idx):
        current = self.faces[face_name][idx]
        try:
            next_idx = (COLOR_CYCLE.index(current) + 1) % len(COLOR_CYCLE)
        except ValueError:
            next_idx = 0
        new_color = COLOR_CYCLE[next_idx]
        self.faces[face_name][idx] = new_color
        self._draw_face(face_name)
        # previent l interface que la couleur a change
        if self.on_change:
            self.on_change(face_name, idx, new_color)
