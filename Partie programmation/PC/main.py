import sys
import os

# Ajoute le dossier actuel au chemin d'import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Lance l'interface principale
from ui.interface import run_app

# Point d'entrée du programme
if __name__ == "__main__":
    run_app()