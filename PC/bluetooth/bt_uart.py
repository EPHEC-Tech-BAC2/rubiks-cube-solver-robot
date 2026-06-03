import serial
import serial.tools.list_ports
import threading
import queue
import time


def list_ports():
    return [p.device for p in serial.tools.list_ports.comports()]


def make_msg(tag, payload=""):
    return "START:{}:{}:END\n".format(tag, payload)


def parse_msg(line):
    line = line.strip()
    if line.startswith("START:") and line.endswith(":END"):
        body = line[6:-4]
        if ":" in body:
            tag, payload = body.split(":", 1)
            return tag.strip(), payload.strip()
    return None, None


class BTUart:
    def __init__(self):
        self.ser = None
        self._thread = None
        self._alive = False
        self.rx_queue = queue.Queue()
        self.on_receive = None  # callback(tag, payload)

    def connect(self, port, baud=38400):
        self.disconnect()
        self.ser = serial.Serial(port, baudrate=baud, timeout=1)
        self._alive = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def disconnect(self):
        self._alive = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    def send(self, tag, payload=""):
        if not self.is_connected():
            raise RuntimeError("Non connecté")
        self.ser.write(make_msg(tag, payload).encode())

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def _reader(self):
        while self._alive and self.ser:
            try:
                raw = self.ser.readline()
                if not raw:
                    continue
                line = raw.decode(errors="ignore").strip()
                if not line:
                    continue
                tag, payload = parse_msg(line)
                self.rx_queue.put((line, tag, payload))
                if self.on_receive and tag:
                    try:
                        self.on_receive(tag, payload)
                    except Exception:
                        pass
            except Exception:
                time.sleep(0.1)