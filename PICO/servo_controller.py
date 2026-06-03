from machine import Pin, PWM
import time

# position neutre calibree pour chaque bras (centre du servo)
ROT_CENTER = {"L": 86, "R": 90, "F": 90, "B": 94}
# amplitude de rotation depuis le centre (centre+step = position max)
ROT_STEP   = {"L": 90, "R": 90, "F": 90, "B": 90}
ROT_SIGN   = {"L": 1,  "R": 1,  "F": 1,  "B": 1}

# angle de serrage de la pince
GRIP_HOLD  = {"L": 20, "R": 18, "F": 30, "B": 35}
# angle d ouverture de la pince
GRIP_OPEN  = {"L": 100, "R": 100, "F": 100, "B": 100}
GRIP_BACK  = {"L": 100, "R": 100, "F": 100, "B": 100}

# delai entre chaque mouvement pendant la resolution
TEMPS_MVT  = 0.12
# delai pendant le scan (plus lent pour pas lacher le cube)
TEMPS_SCAN = 0.30


class Bras:
    def __init__(self, nom, pin_rot, pin_pince):
        self.nom = nom
        # servo de rotation du bras
        self.rot   = PWM(Pin(pin_rot));   self.rot.freq(50)
        # servo de la pince
        self.pince = PWM(Pin(pin_pince)); self.pince.freq(50)
        self.center   = ROT_CENTER[nom]
        self.step     = ROT_STEP[nom]
        self.sign     = ROT_SIGN[nom]
        self.hold_ang = GRIP_HOLD[nom]
        self.open_ang = GRIP_OPEN[nom]
        self.back_ang = GRIP_BACK[nom]

    # convertit un angle en signal PWM pour le servo de rotation
    def _angle_rot(self, pwm, angle):
        duty = int(1638 + (8192 - 1638) * (angle / 180.0))
        pwm.duty_u16(min(max(duty, 0), 65535))

    # convertit un angle en signal PWM pour la pince
    def _angle_grip(self, pwm, angle):
        duty = int(1638 + (8192 - 1638) * (angle / 180.0))
        pwm.duty_u16(min(max(duty, 0), 65535))

    def serrer(self):
        self._angle_grip(self.pince, self.hold_ang)

    def lacher(self):
        self._angle_grip(self.pince, self.open_ang)

    def recul(self):
        self._angle_grip(self.pince, self.back_ang)

    # revient a la position neutre
    def rot_centre(self):
        self._angle_rot(self.rot, self.center)

    # tourne dans le sens horaire
    def rot_cw(self):
        angle = max(0, min(180, self.center + self.step * self.sign))
        self._angle_rot(self.rot, angle)

    # tourne dans le sens anti-horaire
    def rot_ccw(self):
        angle = max(0, min(180, self.center - self.step * self.sign))
        self._angle_rot(self.rot, angle)


class RobotController:
    def __init__(self):
        # creation des 4 bras : Front, Back, Right, Left
        self.F = Bras("F", pin_rot=5, pin_pince=6)
        self.B = Bras("B", pin_rot=1, pin_pince=2)
        self.R = Bras("R", pin_rot=3, pin_pince=4)
        self.L = Bras("L", pin_rot=7, pin_pince=8)
        self.bras = {'F': self.F, 'B': self.B, 'R': self.R, 'L': self.L}

    # au demarrage : centre tous les bras puis serre
    def initialiser(self):
        for b in self.bras.values():
            b.rot_centre()
            b.lacher()
        time.sleep(1)
        for b in self.bras.values():
            b.serrer()
        time.sleep(0.5)

    def tout_serrer(self):
        for b in self.bras.values():
            b.serrer()

    # position pour scanner une face : L et R tiennent, F et B s ecartent
    def position_scan(self, d=TEMPS_MVT):
        self.L.lacher()
        self.R.lacher()
        time.sleep(d)
        self.L.rot_cw()
        self.R.rot_cw()
        time.sleep(d)
        self.L.serrer()
        self.R.serrer()
        time.sleep(d)
        self.F.lacher()
        self.B.lacher()
        time.sleep(d)
        self.F.rot_cw()
        self.B.rot_cw()
        time.sleep(d)

    # apres le scan : remet les 4 bras en position normale
    def fin_scan(self, d=TEMPS_MVT):
        self.F.rot_centre()
        self.B.rot_centre()
        time.sleep(d)
        self.F.serrer()
        self.B.serrer()
        time.sleep(d)
        self.L.lacher()
        self.R.lacher()
        time.sleep(d)
        self.L.rot_centre()
        self.R.rot_centre()
        time.sleep(d)
        self.L.serrer()
        self.R.serrer()
        time.sleep(d)

    def tout_lacher(self):
        for b in self.bras.values():
            b.lacher()

    # tourne une face du cube (CW = sens horaire, CCW = anti-horaire, 2 = 180 degres)
    def _tourner(self, face, direction):
        b = self.bras[face]
        if direction == "2":
            self._tourner(face, "CW")
            self._tourner(face, "CW")
            return
        b.rot_cw() if direction == "CW" else b.rot_ccw()
        time.sleep(TEMPS_MVT)
        b.lacher()
        time.sleep(TEMPS_MVT)
        b.rot_centre()
        time.sleep(TEMPS_MVT)
        b.serrer()
        time.sleep(TEMPS_MVT)

    # bascule le cube vers l avant (L et R font pivoter)
    def basculer_avant(self, d=TEMPS_MVT):
        self.F.lacher();  self.B.lacher();  time.sleep(d)
        self.L.rot_cw();  self.R.rot_ccw(); time.sleep(d)
        self.F.serrer();  self.B.serrer();  time.sleep(d)
        self.L.lacher();  self.R.lacher();  time.sleep(d)
        self.L.rot_centre(); self.R.rot_centre(); time.sleep(d)
        self.L.serrer();  self.R.serrer();  time.sleep(d)

    # bascule le cube vers l arriere
    def basculer_arriere(self, d=TEMPS_MVT):
        self.F.lacher();  self.B.lacher();  time.sleep(d)
        self.L.rot_ccw(); self.R.rot_cw();  time.sleep(d)
        self.F.serrer();  self.B.serrer();  time.sleep(d)
        self.L.lacher();  self.R.lacher();  time.sleep(d)
        self.L.rot_centre(); self.R.rot_centre(); time.sleep(d)
        self.L.serrer();  self.R.serrer();  time.sleep(d)

    # bascule le cube vers la droite (F et B font pivoter)
    def basculer_droite(self, d=TEMPS_MVT):
        self.L.lacher();  self.R.lacher();  time.sleep(d)
        self.F.rot_cw();  self.B.rot_ccw(); time.sleep(d)
        self.L.serrer();  self.R.serrer();  time.sleep(d)
        self.F.lacher();  self.B.lacher();  time.sleep(d)
        self.F.rot_centre(); self.B.rot_centre(); time.sleep(d)
        self.F.serrer();  self.B.serrer();  time.sleep(d)

    # bascule le cube vers la gauche
    def basculer_gauche(self, d=TEMPS_MVT):
        self.L.lacher();  self.R.lacher();  time.sleep(d)
        self.F.rot_ccw(); self.B.rot_cw();  time.sleep(d)
        self.L.serrer();  self.R.serrer();  time.sleep(d)
        self.F.lacher();  self.B.lacher();  time.sleep(d)
        self.F.rot_centre(); self.B.rot_centre(); time.sleep(d)
        self.F.serrer();  self.B.serrer();  time.sleep(d)

    # execute un mouvement Kociemba (ex: R, L', F2, U, D')
    def executer_mouvement_rubiks(self, commande):
        face = commande[0]
        direction = "CW"
        if len(commande) > 1:
            if commande[1] == "'": direction = "CCW"
            elif commande[1] == "2": direction = "2"

        if face in self.bras:
            self._tourner(face, direction)
        elif face == 'U':
            # U et D : on bascule d abord pour amener la face a portee du bras
            self.basculer_avant()
            self._tourner('F', direction)
            self.basculer_arriere()
        elif face == 'D':
            self.basculer_avant()
            self._tourner('B', direction)
            self.basculer_arriere()
