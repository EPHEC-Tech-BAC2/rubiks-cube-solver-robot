# A2073 - Robotique part2 - 2025-2026
## Robot Solveur Rubik's Cube 3x3x3

**Groupe : B2**
- NOM Prénom (Matricule)
- EL YAZAMI Yassine (HE305212)
- ELHAMAYDA Amer (HE305196)
- MAZID Mohamed (HE305165)

**Objectifs :**  
Initialisation du projet et mise en place des bases logicielles et matérielles (Pico W, Bluetooth, librairies Python)  

**État actuel :**  
- Structure du projet créée 
- Librairies MicroPython (ssd1306, servo, mfrc522)  
- Dépendances Python ajoutées (numpy, opencv-python, pyserial, kociemba)  
- Début de la conception mécanique et du PCB  
- Test pour vérifier la communication Bluetooth entre le Pico et le PC avant l’intégration dans le projet
- Lancer l'interface et se connecter au Pico
- Les boutons Attraper/Relâcher envoient au Pico, le RFID s'affiche, le chrono tourne.
- Camera dans l'interface + cube mis a jour apres chaque capture
- Capturer 6 faces, resoudre, envoyer au pico, voir la progression en direct