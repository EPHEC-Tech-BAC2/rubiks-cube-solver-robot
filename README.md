# Rubik's Cube Solver Robot

Projet réalisé à l'EPHEC-Tech (A2073 — Robotique Part 2, classe 2AU, 2025-2026), en équipe de trois : **EL YAZAMI Yassine**, **MAZID Mohamed**, **ELHAMAYDA Amer**.

## Le projet

Conception et réalisation d'un robot autonome capable de scanner, résoudre et exécuter physiquement la solution d'un Rubik's Cube, sans intervention humaine. Le système combine trois domaines : électronique, mécanique et développement logiciel.

Le robot scanne les 6 faces du cube via une caméra, calcule la solution optimale avec l'algorithme de Kociemba, puis l'exécute grâce à 4 bras motorisés pilotés par un Raspberry Pi Pico W.

## Partie électronique

PCB sur mesure conçu sous **EasyEDA** et fabriqué via **JLCPCB** (81,15 × 88,14 mm, 21 composants, 2 couches de cuivre, 141 pastilles traversantes, 6 vias).

| Composant | Référence | Rôle |
|---|---|---|
| Raspberry Pi Pico W | RP2040 | Microcontrôleur principal (firmware MicroPython) |
| Module Bluetooth | HC-05 | Communication sans fil PC ↔ Pico (UART, 38400 bauds) |
| Lecteur RFID | MFRC522 | Identification par badge, autorisation d'accès |
| Écran OLED | SSD1306 0,96" | Affichage état du robot, face scannée, progression |
| LED RGB | TJ-L5FCMXHTCSLCRGB | Indicateur visuel (rouge = bloqué, vert = prêt, bleu = actif) |
| Servomoteurs | MG90S x8 | 4 rotations + 4 pinces, PWM 50 Hz |
| Bouton | TS665CJ | Appui court = toggle pinces, appui long = scan auto |

L'alimentation des servomoteurs est séparée de celle du Pico pour éviter les chutes de tension lors des mouvements simultanés.

## Partie mécanique

Structure organisée autour d'une base centrale (découpée au laser) sur laquelle se fixent 4 bras en croix (Front, Back, Left, Right), chacun composé d'un servomoteur de rotation et d'un servomoteur de pince. Toutes les pièces ont été modélisées sous **Fusion 360** et imprimées en PLA :

- Platine principale (support servomoteur de rotation)
- Colonne verticale (support servomoteur de pince)
- Pince en U (saisie des faces du cube)
- Support de caméra
- Engrenage et cadre structural en U

Plusieurs itérations d'impression ont été nécessaires pour ajuster les tolérances dimensionnelles et obtenir des mouvements précis. Chaque bras dispose de son propre calibrage (ROT_CENTER, GRIP_HOLD) pour compenser les asymétries mécaniques.

## Partie programmation

Architecture logicielle en deux blocs communiquant en Bluetooth :

- **Firmware Pico (MicroPython)** : gestion des 8 servomoteurs, lecture RFID, affichage OLED, machine à états (IDLE/MOVING/SCAN)
- **Application PC (Python 3, Tkinter)** : capture caméra, détection des couleurs (OpenCV/HSV), interface graphique, résolution Kociemba

Protocole de communication maison : `START:TAG:PAYLOAD:END\n`, avec des tags dédiés (MOVE, GRAB/RELEASE, START_SCAN, PROG, DONE, AUTH...).

**Détection des couleurs** : analyse HSV par patch, vote majoritaire sur 7 captures par face pour plus de robustesse (l'orange est testé avant le rouge, leurs plages HSV étant adjacentes).

**Résolution** : algorithme de Kociemba embarqué localement (hors ligne), garantissant une solution en 20 mouvements maximum.

## Difficultés rencontrées

- Précision des angles de servomoteurs → calibrage individuel par bras
- Confusion orange/rouge en détection HSV → ordre de test + fallback par distance circulaire
- Instabilité de la détection couleur → vote majoritaire sur 7 captures
- Bruit d'initialisation du HC-05 → parsing basé sur la recherche du pattern `START:`
- Chutes de tension lors des mouvements simultanés → alimentation séparée + séquencement
- Tolérances d'impression 3D → révisions dimensionnelles successives

## Contenu du dépôt

- `Partie électronique/` : fichier PCB et export Gerber
- `Partie mécanique/` : fichiers STL de toutes les pièces imprimées + fichier DWG du support du robot
- `Partie programmation/` : firmware MicroPython (dossier `PICO/`) et application de contrôle (dossier `PC/`)
- `Présentation/` : support PowerPoint de la présentation finale
- `Rapport/` : rapport complet du projet (DOCX + PDF)