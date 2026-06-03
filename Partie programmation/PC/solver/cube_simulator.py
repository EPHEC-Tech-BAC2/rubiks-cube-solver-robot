# PC/solver/cube_simulator.py
# Simule l'état du cube et applique les mouvements pour la visualisation en direct

FACE_ORDER = ["U", "R", "F", "D", "L", "B"]

# Chaque face a 9 stickers indexés 0-8 :
#   0 1 2
#   3 4 5
#   6 7 8

def _rotate_face_cw(face):
    """Rotation horaire des 9 stickers d'une face."""
    return [face[6], face[3], face[0],
            face[7], face[4], face[1],
            face[8], face[5], face[2]]

def _rotate_face_ccw(face):
    return [face[2], face[5], face[8],
            face[1], face[4], face[7],
            face[0], face[3], face[6]]


class CubeState:
    """Représente l'état du cube avec 6 faces de 9 couleurs chacune."""

    def __init__(self, faces=None):
        if faces:
            self.faces = {f: list(faces[f]) for f in FACE_ORDER}
        else:
            self.faces = {f: [f] * 9 for f in FACE_ORDER}

    def copy(self):
        return CubeState(self.faces)

    def set_faces(self, faces_dict):
        """faces_dict : {U: [9 noms couleur], ...}"""
        self.faces = {f: list(faces_dict[f]) for f in FACE_ORDER}

    def apply_move(self, move_str):
        """Applique un mouvement standard (R, R', R2, U, U', etc.)."""
        if not move_str:
            return
        face = move_str[0]
        if len(move_str) > 1 and move_str[1] == "'":
            self._do_move(face, -1)
        elif len(move_str) > 1 and move_str[1] == "2":
            self._do_move(face, 1)
            self._do_move(face, 1)
        else:
            self._do_move(face, 1)

    def apply_sequence(self, seq_str):
        """Applique une séquence de mouvements séparés par des espaces."""
        for m in seq_str.strip().split():
            self.apply_move(m)

    def _do_move(self, face, direction):
        """direction=1 pour CW, -1 pour CCW."""
        f = self.faces
        if direction == 1:
            f[face] = _rotate_face_cw(f[face])
        else:
            f[face] = _rotate_face_ccw(f[face])

        # Cycle des bandes adjacentes
        if face == "R":
            self._cycle_strips(
                ("F", [2, 5, 8]), ("U", [2, 5, 8]),
                ("B", [6, 3, 0]), ("D", [2, 5, 8]), direction)
        elif face == "L":
            self._cycle_strips(
                ("F", [0, 3, 6]), ("D", [0, 3, 6]),
                ("B", [8, 5, 2]), ("U", [0, 3, 6]), direction)
        elif face == "U":
            self._cycle_strips(
                ("F", [0, 1, 2]), ("L", [0, 1, 2]),
                ("B", [0, 1, 2]), ("R", [0, 1, 2]), direction)
        elif face == "D":
            self._cycle_strips(
                ("F", [6, 7, 8]), ("R", [6, 7, 8]),
                ("B", [6, 7, 8]), ("L", [6, 7, 8]), direction)
        elif face == "F":
            self._cycle_strips(
                ("U", [6, 7, 8]), ("R", [0, 3, 6]),
                ("D", [2, 1, 0]), ("L", [8, 5, 2]), direction)
        elif face == "B":
            self._cycle_strips(
                ("U", [2, 1, 0]), ("L", [0, 3, 6]),
                ("D", [6, 7, 8]), ("R", [8, 5, 2]), direction)

    def _cycle_strips(self, s1, s2, s3, s4, direction):
        """Fait cycler 4 bandes de 3 stickers (CW ou CCW)."""
        f = self.faces
        if direction == 1:
            order = [s1, s2, s3, s4]
        else:
            order = [s4, s3, s2, s1]
        tmp = [f[order[3][0]][i] for i in order[3][1]]
        for k in range(3, 0, -1):
            src_face, src_idx = order[k - 1]
            dst_face, dst_idx = order[k]
            for j in range(3):
                f[dst_face][dst_idx[j]] = f[src_face][src_idx[j]]
        dst_face, dst_idx = order[0]
        for j in range(3):
            f[dst_face][dst_idx[j]] = tmp[j]
