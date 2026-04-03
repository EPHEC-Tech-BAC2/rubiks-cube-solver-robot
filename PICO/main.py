# Gère la réception BT et répond au PING avec la LED comme feedback
from machine import UART, Pin, PWM
import utime

uart = UART(0, baudrate=38400, tx=Pin(0), rx=Pin(1))

# LED RGB sur GP11 (R), GP13 (G), GP12 (B)
def set_led(r, g, b):
    for pin, val in zip([11, 13, 12], [r, g, b]):
        pwm = PWM(Pin(pin))
        pwm.freq(1000)
        pwm.duty_u16(65535 - val * 257)

def send(tag, payload=""):
    uart.write("START:{}:{}:END\n".format(tag, payload))

def parse(line):
    line = line.strip()
    if line.startswith("START:") and line.endswith(":END"):
        body = line[6:-4]
        if ":" in body:
            tag, payload = body.split(":", 1)
            return tag.strip(), payload.strip()
    return None, None

# bleu au démarrage, le Pico est prêt
set_led(0, 0, 100)
send("LOG", "PICO_READY")

while True:
    if uart.any():
        raw = uart.readline()
        if raw:
            try:
                line = raw.decode().strip()
            except:
                continue

            tag, payload = parse(line)

            if tag == "PING":
                send("PONG")
                set_led(0, 100, 0)
                utime.sleep_ms(200)
                set_led(0, 0, 100)

    utime.sleep_ms(20)