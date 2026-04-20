from machine import UART, Pin


class Bluetooth:
    def __init__(self, uart_id=0, baudrate=38400, tx_pin=12, rx_pin=13):
        self.uart = UART(uart_id, baudrate=baudrate,
                         tx=Pin(tx_pin), rx=Pin(rx_pin))

    def send(self, tag, payload=""):
        msg = "START:{}:{}:END\n".format(tag, payload)
        try:
            self.uart.write(msg)
        except:
            pass

    def log(self, text):
        self.send("LOG", text)

    def ok(self, tag):
        self.send("OK", tag)

    def err(self, reason):
        self.send("ERR", reason)

    def readline(self):
        if self.uart.any():
            raw = self.uart.readline()
            if raw:
                try:
                    return raw.decode().strip()
                except:
                    return None
        return None

    def parse(self, line):
        if not line:
            return None, None
        line = line.strip()
        if line.startswith("START:") and line.endswith(":END"):
            body = line[6:-4]
            if ":" in body:
                tag, payload = body.split(":", 1)
                return tag.strip(), payload.strip()
        return None, None