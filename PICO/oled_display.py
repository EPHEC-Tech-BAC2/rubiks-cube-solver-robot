import ssd1306
from machine import I2C, Pin


class OLED:
    def __init__(self, i2c_id=0, sda=20, scl=21, w=128, h=64):
        # Initialisation de l'écran OLED en I2C
        i2c = I2C(i2c_id, sda=Pin(sda), scl=Pin(scl))
        self.d = ssd1306.SSD1306_I2C(w, h, i2c)

    def show(self, line1, line2="", line3="", line4=""):
        # Efface l'écran
        self.d.fill(0)

        # Affiche jusqu'à 4 lignes de texte
        for i, txt in enumerate([line1, line2, line3, line4]):
            if txt:
                self.d.text(txt[:16], 0, i * 14)

        # Met à jour l'affichage
        self.d.show()