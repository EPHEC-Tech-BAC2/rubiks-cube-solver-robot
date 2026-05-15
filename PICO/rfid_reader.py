from mfrc522 import MFRC522

class RFIDReader:
    def __init__(self, sck=18, mosi=19, miso=0, rst=10, cs=17, spi_id=0):
        self.reader = MFRC522(sck=sck, mosi=mosi, miso=miso,
                              rst=rst, cs=cs, spi_id=spi_id)
        self.allowed_tags = []

    def set_allowed(self, tags):
        self.allowed_tags = tags

    def scan_once(self):
        try:
            self.reader.init()
            stat, tag_type = self.reader.request(self.reader.REQIDL)
            if stat == self.reader.OK:
                stat, uid = self.reader.SelectTagSN()
                if stat == self.reader.OK:
                    card = int.from_bytes(bytes(uid), "little", False)
                    allowed = (not self.allowed_tags) or (card in self.allowed_tags)
                    return card, allowed
        except:
            pass
        return None
