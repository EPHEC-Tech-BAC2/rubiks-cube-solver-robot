# Importation des bibliothèques nécessaires
import serial                  # Communication série (UART/Bluetooth)
import serial.tools.list_ports # Détection des ports COM disponibles
import threading               # Exécution en parallèle (multithreading)
import queue                   # File d'attente pour stocker les messages reçus
import time                    # Gestion du temps et des pauses


# Liste tous les ports série disponibles sur l'ordinateur
def list_ports():
    return [p.device for p in serial.tools.list_ports.comports()]


# Création d'un message au format :
# START:TAG:DONNEE:END
def make_msg(tag, payload=""):
    return "START:{}:{}:END\n".format(tag, payload)


# Analyse un message reçu
# Retourne le tag et la donnée (payload)
def parse_msg(line):
    line = line.strip()

    # Vérification du format du message
    if line.startswith("START:") and line.endswith(":END"):
        body = line[6:-4]

        # Séparation du tag et des données
        if ":" in body:
            tag, payload = body.split(":", 1)
            return tag.strip(), payload.strip()

    return None, None


# Classe principale pour gérer la communication Bluetooth/UART
class BTUart:

    # Constructeur
    def __init__(self):
        self.ser = None              # Objet port série
        self._thread = None          # Thread de lecture
        self._alive = False          # État de fonctionnement
        self.rx_queue = queue.Queue()# Stockage des messages reçus
        self.on_receive = None       # Fonction appelée à la réception

    # Connexion au port série
    def connect(self, port, baud=38400):
        self.disconnect()  # Ferme une ancienne connexion

        # Ouverture du port série
        self.ser = serial.Serial(port, baudrate=baud, timeout=1)

        # Activation du thread de lecture
        self._alive = True
        self._thread = threading.Thread(
            target=self._reader,
            daemon=True
        )
        self._thread.start()

    # Déconnexion du port série
    def disconnect(self):
        self._alive = False

        # Arrêt du thread
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)

        # Fermeture du port
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass

        self.ser = None

    # Envoi d'un message
    def send(self, tag, payload=""):

        # Vérifie que la connexion existe
        if not self.is_connected():
            raise RuntimeError("Non connecté")

        # Envoi du message formaté
        self.ser.write(make_msg(tag, payload).encode())

    # Vérifie si le port est connecté
    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    # Fonction exécutée dans un thread
    # Lecture continue des données reçues
    def _reader(self):

        while self._alive and self.ser:
            try:
                # Lecture d'une ligne
                raw = self.ser.readline()

                if not raw:
                    continue

                # Conversion en texte
                line = raw.decode(errors="ignore").strip()

                if not line:
                    continue

                # Analyse du message
                tag, payload = parse_msg(line)

                # Stockage dans la file d'attente
                self.rx_queue.put((line, tag, payload))

                # Appel du callback si défini
                if self.on_receive and tag:
                    try:
                        self.on_receive(tag, payload)
                    except Exception:
                        pass

            except Exception:
                # Pause en cas d'erreur
                time.sleep(0.1)