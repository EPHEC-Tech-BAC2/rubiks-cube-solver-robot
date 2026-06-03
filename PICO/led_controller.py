# controle la LED RGB du robot via PWM
# rouge = pas de badge, vert = autorise + Bluetooth actif, bleu = lecture badge

from machine import Pin, PWM


class LEDController:
    # pins = broches GPIO pour rouge, vert, bleu
    def __init__(self, pins=(27, 26, 28)):
        self.pwms = [PWM(Pin(p)) for p in pins]
        for p in self.pwms:
            # frequence 1kHz pour eviter le scintillement visible
            p.freq(1000)
        self.set(0, 0, 100)

    # allume la LED avec les intensites r, g, b de 0 a 255
    def set(self, r, g, b):
        for pwm, val in zip(self.pwms, [r, g, b]):
            # LED commune anode : inverser le rapport cyclique (65535 = eteint)
            pwm.duty_u16(max(0, min(65535, 65535 - val * 257)))

    def off(self):
        self.set(0, 0, 0)