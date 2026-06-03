# classe generique pour controler un servomoteur via PWM sur le Pico
# un servomoteur recoit un signal PWM a 50Hz, la largeur d impulsion definit l angle

from machine import Pin, PWM

class Servo:
    # frequence du signal PWM : 50Hz = periode de 20ms (standard pour les servos)
    __servo_pwm_freq = 50
    # valeur minimale du rapport cyclique (correspond a 0 degres)
    __min_u16_duty = 1802
    # valeur maximale du rapport cyclique (correspond a 180 degres)
    __max_u16_duty = 7864
    min_angle = 0
    max_angle = 180
    current_angle = 0.001

    def __init__(self, pin):
        self.__initialise(pin)

    # permet de recalibrer le servo avec des valeurs differentes
    def update_settings(self, servo_pwm_freq, min_u16_duty, max_u16_duty, min_angle, max_angle, pin):
        self.__servo_pwm_freq = servo_pwm_freq
        self.__min_u16_duty = min_u16_duty
        self.__max_u16_duty = max_u16_duty
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.__initialise(pin)

    # deplace le servo a l angle demande (en degres)
    def move(self, angle):
        # arrondit pour eviter des micro-corrections inutiles
        angle = round(angle, 2)
        # ne bouge pas si on est deja a cet angle
        if angle == self.current_angle:
            return
        self.current_angle = angle
        # convertit l angle en signal PWM et l envoie au servo
        duty_u16 = self.__angle_to_u16_duty(angle)
        self.__motor.duty_u16(duty_u16)

    # arrete le signal PWM (servo se relache)
    def stop(self):
        self.__motor.deinit()

    def get_current_angle(self):
        return self.current_angle

    # formule de conversion : angle -> valeur du rapport cyclique (16 bits)
    def __angle_to_u16_duty(self, angle):
        return int((angle - self.min_angle) * self.__angle_conversion_factor) + self.__min_u16_duty

    # initialise le PWM sur la broche et calcule le facteur de conversion
    def __initialise(self, pin):
        self.current_angle = -0.001
        # facteur = plage de duty / plage d angles
        self.__angle_conversion_factor = (self.__max_u16_duty - self.__min_u16_duty) / (self.max_angle - self.min_angle)
        self.__motor = PWM(Pin(pin))
        self.__motor.freq(self.__servo_pwm_freq)
