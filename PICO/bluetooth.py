from machine import UART, Pin


class Bluetooth:
    def __init__(self, uart_id=0, baudrate=38400, tx_pin=12, rx_pin=13):
        # rxbuf=512 pour les longues solutions Kociemba
        self.uart = UART(uart_id, baudrate=baudrate,
                         tx=Pin(tx_pin), rx=Pin(rx_pin),
                         rxbuf=512)
        self._buf = ""

    def send(self, tag, payload=""):
        msg = "START:{}:{}:END\n".format(tag, payload)
        try:
            self.uart.write(msg.encode())
        except Exception as e:
            print("[BT] send erreur:", e)

    def readline(self):
        try:
            n = self.uart.any()
            if n > 0:
                chunk = self.uart.read(n)
                if chunk:
                    self._buf += chunk.decode("utf-8", "ignore")
        except Exception as e:
            print("[BT] read erreur:", e)
            return None

        if "START:" in self._buf:
            idx = self._buf.index("START:")
            if idx > 0:
                self._buf = self._buf[idx:]

        if "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            return line.strip()

        return None

    def parse(self, line):
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
