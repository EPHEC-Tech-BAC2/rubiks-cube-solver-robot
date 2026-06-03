# PC/solver/cube_solver.py
# Résolution du cube via kociemba

import kociemba
from vision.color_detection import build_kociemba_string


def solve(faces):
    """
    faces : dict {U: [9 noms couleur], R: [...], ...}
    retourne (cube_string, solution_str)
    """
    cube_string = build_kociemba_string(faces)
    solution = kociemba.solve(cube_string)
    return cube_string, solution.strip()