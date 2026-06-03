# algorithme Kociemba deux phases : resout n importe quel cube en moins de 20 mouvements
import kociemba
from vision.color_detection import build_kociemba_string


# prend les couleurs detectees, construit la chaine Kociemba et retourne la solution
def solve(faces):
    # convertit les noms de couleurs en chaine de 54 lettres (ex: UUUUUUUUURRRRRR...)
    cube_string = build_kociemba_string(faces)
    # Kociemba calcule la sequence de mouvements optimale
    solution = kociemba.solve(cube_string)
    return cube_string, solution.strip()
