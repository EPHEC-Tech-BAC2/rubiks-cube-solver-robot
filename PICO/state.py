# gestion de l etat global du robot
# permet de savoir si le robot est en train de scanner, de bouger ou d attendre

class State:
    IDLE    = "IDLE"    # robot en attente
    MOVING  = "MOVING"  # robot en train d executer des mouvements
    SCAN    = "SCAN"    # robot en train de scanner les faces

    def __init__(self):
        self.current = self.IDLE

    def set(self, s):
        self.current = s

    def get(self):
        return self.current