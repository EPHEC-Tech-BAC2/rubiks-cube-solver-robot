from mfrc522 import MFRC522


class RFIDReader:
    def __init__(self, sck=18, mosi=19, miso=0, rst=10, cs=17, spi_id=0):
        # Initialisation du lecteur RFID
        self.reader = MFRC522(
            spi_id=spi_id, sck=sck, mosi=mosi,
            miso=miso, cs=cs, rst=rst
        )

        # Liste des badges autorisés
        self.allowed_tags = []

        print("[RFID] Init OK — sck={} mosi={} miso={} cs={} rst={}".format(
            sck, mosi, miso, cs, rst))

    def set_allowed(self, tags):
        # Définit les badges autorisés
        self.allowed_tags = tags

    def scan_once(self):
        # Lit un badge une seule fois
        try:
            self.reader.init()

            # Vérifie si un badge est présent
            stat, _ = self.reader.request(self.reader.REQIDL)
            if stat != self.reader.OK:
                return None

            # Récupère l'identifiant du badge
            stat, uid = self.reader.SelectTagSN()
            if stat != self.reader.OK:
                return None

            # Conversion de l'UID en entier
            card = int.from_bytes(bytes(uid), "little")

            # Vérifie si le badge est autorisé
            allowed = (not self.allowed_tags) or (card in self.allowed_tags)

            return card, allowed

        except Exception as e:
            print("[RFID] Erreur:", e)
            return None