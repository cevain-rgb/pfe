# buzzer.py
# Alerte sonore (EF5) — GPIO Raspberry Pi, fallback console sur PC
# Pattern différent selon le niveau d'alerte (SOMNOLENCE/FATIGUE/DISTRACTION)

import threading
import time

from config import BUZZER_PIN

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO_DISPONIBLE = True
except (ImportError, RuntimeError):
    GPIO_DISPONIBLE = False
    print("[BUZZER] GPIO non disponible — mode simulation console activé.")

_buzzer_actif = False
_thread_buzzer = None

# (durée_on, durée_off) en secondes, répété en séquence
PATTERNS = {
    "SOMNOLENCE":  [(0.15, 0.10)] * 6,   # rapide et répété — urgent
    "FATIGUE":     [(0.30, 0.30)] * 3,   # modéré
    "DISTRACTION": [(0.50, 0.00)],       # un seul bip court
}


def _set_buzzer(etat):
    """Active (True) ou coupe (False) le buzzer — physique ou console."""
    if GPIO_DISPONIBLE:
        GPIO.output(BUZZER_PIN, GPIO.HIGH if etat else GPIO.LOW)
    elif etat:
        print("\a[BUZZER] 🔊 BEEP", end="\r")


def _jouer_pattern(pattern):
    """Joue un pattern de bips, s'arrête si _buzzer_actif passe à False."""
    global _buzzer_actif
    _buzzer_actif = True
    for duree_on, duree_off in pattern:
        if not _buzzer_actif:
            break
        _set_buzzer(True)
        time.sleep(duree_on)
        _set_buzzer(False)
        if duree_off > 0:
            time.sleep(duree_off)
    _buzzer_actif = False


def declencher_alerte(type_alerte):
    """
    Déclenche le buzzer de façon NON bloquante (thread séparé) afin de
    respecter EF5 (<500ms) sans geler la boucle de détection.
    Si un son est déjà en cours, ne superpose pas un nouveau pattern.
    """
    global _thread_buzzer
    if _buzzer_actif:
        return

    pattern = PATTERNS.get(type_alerte, PATTERNS["DISTRACTION"])
    _thread_buzzer = threading.Thread(target=_jouer_pattern, args=(pattern,), daemon=True)
    _thread_buzzer.start()


def arreter():
    """Coupe immédiatement le buzzer (urgence / fin de programme)."""
    global _buzzer_actif
    _buzzer_actif = False
    _set_buzzer(False)


def nettoyer():
    """À appeler en fin de programme pour libérer le GPIO proprement."""
    arreter()
    if GPIO_DISPONIBLE:
        GPIO.cleanup()