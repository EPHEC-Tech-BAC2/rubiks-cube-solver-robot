from machine import UART, Pin


class Bluetooth:
    def __init__(self, uart_id=0, baudrate=38400, tx_pin=12, rx_pin=13):
        # Initialisation de l'UART pour communiquer avec le module Bluetooth
        # rxbuf=512 pour accepter les messages longs
        self.uart = UART(
            uart_id,
            baudrate=baudrate,
            tx=Pin(tx_pin),
            rx=Pin(rx_pin),
            rxbuf=512
        )
        self._buf = ""  # Buffer pour stocker les données reçues

    def send(self, tag, payload=""):
        # Crée un message avec un format simple et lisible
        msg = "START:{}:{}:END\n".format(tag, payload)
        try:
            self.uart.write(msg.encode())
        except Exception as e:
            print("[BT] send erreur:", e)

    def readline(self):
        # Lit les données disponibles sur l'UART
        try:
            n = self.uart.any()
            if n > 0:
                chunk = self.uart.read(n)
                if chunk:
                    self._buf += chunk.decode("utf-8", "ignore")
        except Exception as e:
            print("[BT] read erreur:", e)
            return None

        # Garde seulement la partie utile du message
        if "START:" in self._buf:
            idx = self._buf.index("START:")
            if idx > 0:
                self._buf = self._buf[idx:]

        # Retourne une ligne complète si elle existe
        if "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            return line.strip()

        return None

    def parse(self, line):
        # Analyse un message reçu et récupère le tag + le contenu
        if not line:
            return None, None

        if "START:" in line:
            line = line[line.index("START:"):]

        if line.startswith("START:") and line.endswith(":END"):
            body = line[6:-4]
            if ":" in body:
                tag, payload = body.split(":", 1)
                return tag.strip(), payload.strip()

        return None, None