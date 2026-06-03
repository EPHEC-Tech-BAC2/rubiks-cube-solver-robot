from bluetooth import Bluetooth
from servo_controller import RobotController, TEMPS_SCAN
from led_controller import LEDController
from oled_display import OLED
from rfid_reader import RFIDReader
from machine import Pin
import utime

# communication Bluetooth avec le PC (HC-05)
bt    = Bluetooth(uart_id=0, baudrate=38400, tx_pin=12, rx_pin=13)
# controle des 4 bras du robot
robot = RobotController()
# LED RGB pour montrer l etat du robot
led   = LEDController(pins=(26,27,2))
# ecran OLED pour afficher les messages
oled  = OLED()
# lecteur de badge RFID
rfid  = RFIDReader(sck=18, mosi=19, miso=0, rst=10, cs=17)

# seul ce badge est autorise a utiliser le robot
ALLOWED_TAGS = [54206395]
rfid.set_allowed(ALLOWED_TAGS)

rfid_authorized = False
rfid_card_id    = None

# bouton physique sur le robot
btn_start = Pin(22, Pin.IN, Pin.PULL_UP)

_btn_last       = 1
_btn_press_time = 0
_grab_state     = False
# appui long = plus de 800ms = lancer le scan
LONG_PRESS_MS   = 800

_last_bt_ms   = 0
# si pas de message Bluetooth depuis 30s, on considere la connexion perdue
BT_TIMEOUT_MS = 30000


# rouge = pas de badge, vert = badge ok + BT actif
def led_etat():
    if not rfid_authorized:
        led.set(200, 0, 0)
    elif utime.ticks_diff(utime.ticks_ms(), _last_bt_ms) < BT_TIMEOUT_MS:
        led.set(0, 200, 0)
    else:
        led.set(200, 0, 0)


def _oled_attente_badge():
    oled.show("Scannez votre", "badge pour", "continuer...", "")


def log(msg):
    bt.send("LOG", msg)


# verifie si un badge est pose sur le lecteur
def handle_rfid():
    global rfid_authorized, rfid_card_id

    res = rfid.scan_once()
    if not res:
        return

    card, allowed = res
    rfid_card_id = card
    status = "1" if allowed else "0"
    # envoie l id et le resultat au PC
    bt.send("AUTH", "{},{}".format(card, status))

    card_str = str(card)
    # bleu pendant la lecture du badge
    led.set(0, 0, 200)

    if allowed:
        rfid_authorized = True
        oled.show("BIENVENU!", card_str[:8], "Autorise", "")
        log("RFID autorise: {}".format(card))
        utime.sleep_ms(1500)
        led_etat()
        oled.show("Robot pret", "Commandes OK", "", "")
    else:
        rfid_authorized = False
        oled.show("Badge refuse", card_str[:8], "Non autorise", "")
        log("RFID refuse: {}".format(card))
        # 3 clignotements rouges pour signaler le refus
        for _ in range(3):
            led.set(0, 0, 0)
            utime.sleep_ms(100)
            led.set(200, 0, 0)
            utime.sleep_ms(100)
        utime.sleep_ms(1000)
        _oled_attente_badge()


# bloque toute commande si pas de badge valide
def _bloquer(raison=""):
    log("BLOQUE badge requis" + (" (" + raison + ")" if raison else ""))
    led.set(200, 0, 0)
    oled.show("Scannez votre", "badge pour", "continuer...", "")
    bt.send("ERR", "NOT_AUTHORIZED")


# ferme les 4 pinces (attrape le cube)
def _do_grab():
    global _grab_state
    if not rfid_authorized:
        _bloquer("GRAB bouton")
        return
    _grab_state = True
    robot.tout_serrer()
    bt.send("OK", "GRAB")
    oled.show("Pinces", "Serrees", "", "")
    led.set(200, 100, 0)
    utime.sleep_ms(300)
    led_etat()


# ouvre les 4 pinces (lache le cube)
def _do_release():
    global _grab_state
    if not rfid_authorized:
        _bloquer("RELEASE bouton")
        return
    _grab_state = False
    robot.tout_lacher()
    bt.send("OK", "RELEASE")
    oled.show("Pinces", "Lachees", "", "")
    led_etat()


# gere l appui sur le bouton physique
def check_button():
    global _btn_last, _btn_press_time

    val = btn_start.value()

    if _btn_last == 1 and val == 0:
        _btn_press_time = utime.ticks_ms()

    elif _btn_last == 0 and val == 1:
        duration = utime.ticks_diff(utime.ticks_ms(), _btn_press_time)

        if duration >= LONG_PRESS_MS:
            if not rfid_authorized:
                _bloquer("bouton long")
                return
            # appui long = demarre le scan automatique
            bt.send("AUTO_START", "")
            oled.show("Demarrage", "Scan auto...", "", "")
            led.set(0, 150, 200)
        else:
            # appui court = ouvre/ferme les pinces
            if _grab_state:
                _do_release()
            else:
                _do_grab()

    _btn_last = val


# attend que le PC confirme la capture d une face (SCAN_ACK)
def wait_ack(face_name, timeout_ms=60000):
    t0 = utime.ticks_ms()
    while utime.ticks_diff(utime.ticks_ms(), t0) < timeout_ms:
        line = bt.readline()
        tag, payload = bt.parse(line)
        if tag == "SCAN_ACK" and payload == face_name:
            return True
        utime.sleep_ms(50)
    return False


# place le cube pour scanner une face, puis attend la confirmation du PC
def expose_and_capture(face_name, step_num):
    oled.show("Scan {}/6".format(step_num), "Face " + face_name, "", "")
    utime.sleep_ms(1000)
    bt.send("SCAN_READY", face_name)

    if not wait_ack(face_name):
        oled.show("ERREUR", "Timeout " + face_name, "", "")
        bt.send("ERR", "SCAN_TIMEOUT_" + face_name)
        return False

    led.set(0, 200, 0)
    utime.sleep_ms(200)
    led.set(0, 150, 200)
    return True


# sequence complete de scan des 6 faces : U R F D L B
def auto_scan():
    led.set(0, 150, 200)
    oled.show("Scan auto", "Debut...", "", "")
    S = TEMPS_SCAN
    W = 1500

    # face U : position initiale (blanc en haut)
    robot.position_scan(S); utime.sleep_ms(W)
    if not expose_and_capture("U", 1):
        robot.fin_scan(S); led_etat(); return False
    robot.fin_scan(S); utime.sleep_ms(W)

    # aller vers face verte pour servir de reference
    robot.basculer_arriere(S); utime.sleep_ms(W)

    # face R : depuis vert, tourner vers rouge
    robot.basculer_gauche(S); utime.sleep_ms(W)
    robot.position_scan(S);   utime.sleep_ms(W)
    if not expose_and_capture("R", 2):
        robot.fin_scan(S); led_etat(); return False
    robot.fin_scan(S); utime.sleep_ms(W)

    # retour face verte
    robot.basculer_droite(S); utime.sleep_ms(W)

    # face F : vert deja en haut
    robot.position_scan(S); utime.sleep_ms(W)
    if not expose_and_capture("F", 3):
        robot.fin_scan(S); led_etat(); return False
    robot.fin_scan(S); utime.sleep_ms(W)

    # face D : descendre vers jaune
    robot.basculer_arriere(S); utime.sleep_ms(W)
    robot.position_scan(S);    utime.sleep_ms(W)
    if not expose_and_capture("D", 4):
        robot.fin_scan(S); led_etat(); return False
    robot.fin_scan(S); utime.sleep_ms(W)

    # retour face verte
    robot.basculer_avant(S); utime.sleep_ms(W)

    # face L : depuis vert, tourner vers orange
    robot.basculer_droite(S); utime.sleep_ms(W)
    robot.position_scan(S);   utime.sleep_ms(W)
    if not expose_and_capture("L", 5):
        robot.fin_scan(S); led_etat(); return False
    robot.fin_scan(S); utime.sleep_ms(W)

    # face B : depuis orange, tourner vers bleu
    robot.basculer_droite(S); utime.sleep_ms(W)
    robot.position_scan(S);   utime.sleep_ms(W)
    if not expose_and_capture("B", 6):
        robot.fin_scan(S); led_etat(); return False
    robot.fin_scan(S); utime.sleep_ms(W)

    # retour position initiale (blanc en haut)
    robot.basculer_gauche(S); utime.sleep_ms(W)
    robot.basculer_gauche(S); utime.sleep_ms(W)
    robot.basculer_avant(S);  utime.sleep_ms(W)

    oled.show("Scan OK!", "6/6 faces", "", "")
    bt.send("SCAN_DONE", "OK")
    led.set(0, 200, 0)
    utime.sleep_ms(1000)
    led_etat()
    return True


# execute la liste de mouvements envoyes par le PC (algorithme Kociemba)
def execute_moves(payload):
    led.set(200, 100, 0)
    moves = payload.split()
    total = len(moves)

    for i, mvt in enumerate(moves, 1):
        oled.show("Move {}/{}".format(i, total), mvt, "", "")
        robot.executer_mouvement_rubiks(mvt)
        # envoie la progression au PC pour mettre a jour l interface
        bt.send("PROG", "{}/{}".format(i, total))

    bt.send("DONE", "MOVE")
    led.set(0, 200, 0)
    oled.show("Felicitations!", "Resolu!", str(total) + " moves", "")
    utime.sleep_ms(3000)
    led_etat()
    oled.show("Robot pret", "Commandes OK", "", "")


# initialisation du robot au demarrage
robot.initialiser()
led.set(200, 0, 0)
_oled_attente_badge()
bt.send("LOG", "PICO_READY")

last_rfid = 0

# boucle principale : ecoute Bluetooth + verifie badge + verifie bouton
while True:
    now = utime.ticks_ms()

    # scan RFID toutes les 500ms
    if utime.ticks_diff(now, last_rfid) > 500:
        handle_rfid()
        last_rfid = utime.ticks_ms()

    check_button()

    line = bt.readline()
    tag, payload = bt.parse(line)

    if tag is None:
        utime.sleep_ms(20)
        continue

    # une commande recue = Bluetooth toujours actif
    _last_bt_ms = utime.ticks_ms()

    if tag == "PING":
        bt.send("PONG")
        led_etat()

    elif tag == "SCAN":
        handle_rfid()

    elif not rfid_authorized:
        _bloquer(tag)

    elif tag == "MOVE":
        execute_moves(payload)

    elif tag == "GRAB":
        _do_grab()

    elif tag == "RELEASE":
        _do_release()

    elif tag == "START_SCAN":
        auto_scan()

    elif tag == "AUTO_START":
        auto_scan()

    utime.sleep_ms(20)
