# PC/solver/cube_simulator.py

# Simule l'état du cube et applique les mouvements pour la visualisation en direct

# Ordre des faces utilisé dans tout le programme
FACE_ORDER = ["U", "R", "F", "D", "L", "B"]

# Chaque face a 9 stickers indexés ainsi :
#   0 1 2
#   3 4 5
#   6 7 8

# Fonction qui effectue une rotation horaire (CW) d'une face
def _rotate_face_cw(face):
    """Rotation horaire des 9 stickers d'une face."""

    # Retourne une nouvelle liste avec les stickers déplacés
    return [face[6], face[3], face[0],
            face[7], face[4], face[1],
            face[8], face[5], face[2]]

# Fonction qui effectue une rotation antihoraire (CCW) d'une face
def _rotate_face_ccw(face):

    # Retourne une nouvelle liste avec les stickers déplacés
    return [face[2], face[5], face[8],
            face[1], face[4], face[7],
            face[0], face[3], face[6]]


# Classe représentant l'état complet du Rubik's Cube
class CubeState:

    # Documentation de la classe
    """Représente l'état du cube avec 6 faces de 9 couleurs chacune."""

    # Constructeur
    def __init__(self, faces=None):

        # Si un état de cube est fourni
        if faces:

            # Copie les faces reçues
            self.faces = {f: list(faces[f]) for f in FACE_ORDER}

        # Sinon crée un cube résolu
        else:

            # Chaque face contient sa propre lettre
            self.faces = {f: [f] * 9 for f in FACE_ORDER}

    # Retourne une copie complète du cube
    def copy(self):

        # Crée un nouvel objet CubeState identique
        return CubeState(self.faces)

    # Remplace complètement l'état du cube
    def set_faces(self, faces_dict):

        # Documentation
        """faces_dict : {U: [9 noms couleur], ...}"""

        # Copie toutes les faces reçues
        self.faces = {f: list(faces_dict[f]) for f in FACE_ORDER}

    # Applique un mouvement unique
    def apply_move(self, move_str):

        # Documentation
        """Applique un mouvement standard (R, R', R2, U, U', etc.)."""

        # Si chaîne vide
        if not move_str:

            # Ne rien faire
            return

        # Première lettre = face à tourner
        face = move_str[0]

        # Si mouvement inverse (ex : R')
        if len(move_str) > 1 and move_str[1] == "'":

            # Rotation antihoraire
            self._do_move(face, -1)

        # Si mouvement double (ex : R2)
        elif len(move_str) > 1 and move_str[1] == "2":

            # Première rotation
            self._do_move(face, 1)

            # Deuxième rotation
            self._do_move(face, 1)

        # Rotation normale
        else:

            # Rotation horaire
            self._do_move(face, 1)

    # Applique une séquence de mouvements
    def apply_sequence(self, seq_str):

        # Documentation
        """Applique une séquence de mouvements séparés par des espaces."""

        # Parcourt chaque mouvement de la chaîne
        for m in seq_str.strip().split():

            # Applique le mouvement
            self.apply_move(m)

    # Exécute réellement un mouvement
    def _do_move(self, face, direction):

        # Documentation
        """direction=1 pour CW, -1 pour CCW."""

        # Raccourci vers les faces du cube
        f = self.faces

        # Si rotation horaire
        if direction == 1:

            # Rotation de la face
            f[face] = _rotate_face_cw(f[face])

        # Sinon rotation antihoraire
        else:

            # Rotation de la face
            f[face] = _rotate_face_ccw(f[face])

        # Gestion des bandes adjacentes

        # Rotation de la face droite
        if face == "R":

            # Fait tourner les bandes concernées
            self._cycle_strips(
                ("F", [2, 5, 8]), ("U", [2, 5, 8]),
                ("B", [6, 3, 0]), ("D", [2, 5, 8]), direction)

        # Rotation de la face gauche
        elif face == "L":

            # Fait tourner les bandes concernées
            self._cycle_strips(
                ("F", [0, 3, 6]), ("D", [0, 3, 6]),
                ("B", [8, 5, 2]), ("U", [0, 3, 6]), direction)

        # Rotation de la face du haut
        elif face == "U":

            # Fait tourner les bandes concernées
            self._cycle_strips(
                ("F", [0, 1, 2]), ("L", [0, 1, 2]),
                ("B", [0, 1, 2]), ("R", [0, 1, 2]), direction)

        # Rotation de la face du bas
        elif face == "D":

            # Fait tourner les bandes concernées
            self._cycle_strips(
                ("F", [6, 7, 8]), ("R", [6, 7, 8]),
                ("B", [6, 7, 8]), ("L", [6, 7, 8]), direction)

        # Rotation de la face avant
        elif face == "F":

            # Fait tourner les bandes concernées
            self._cycle_strips(
                ("U", [6, 7, 8]), ("R", [0, 3, 6]),
                ("D", [2, 1, 0]), ("L", [8, 5, 2]), direction)

        # Rotation de la face arrière
        elif face == "B":

            # Fait tourner les bandes concernées
            self._cycle_strips(
                ("U", [2, 1, 0]), ("L", [0, 3, 6]),
                ("D", [6, 7, 8]), ("R", [8, 5, 2]), direction)

    # Fait tourner les bandes entre quatre faces
    def _cycle_strips(self, s1, s2, s3, s4, direction):

        # Documentation
        """Fait cycler 4 bandes de 3 stickers (CW ou CCW)."""

        # Raccourci vers les faces
        f = self.faces

        # Rotation horaire
        if direction == 1:

            # Ordre normal
            order = [s1, s2, s3, s4]

        # Rotation antihoraire
        else:

            # Ordre inversé
            order = [s4, s3, s2, s1]

        # Sauvegarde temporaire de la dernière bande
        tmp = [f[order[3][0]][i] for i in order[3][1]]

        # Décale les bandes
        for k in range(3, 0, -1):

            # Face source et indices source
            src_face, src_idx = order[k - 1]

            # Face destination et indices destination
            dst_face, dst_idx = order[k]

            # Copie les trois stickers
            for j in range(3):

                # Déplacement du sticker
                f[dst_face][dst_idx[j]] = f[src_face][src_idx[j]]

        # Récupère la première bande
        dst_face, dst_idx = order[0]

        # Remet les valeurs sauvegardées
        for j in range(3):

            # Recopie depuis tmp
            f[dst_face][dst_idx[j]] = tmp[j]