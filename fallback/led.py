# led.py
# Contrôle de la LED d'authentification (GPIO Raspberry Pi)
# Fallback console si testé sur PC (pas de GPIO disponible)

import threading
import time

from config import LED_PIN

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO_DISPONIBLE = True
except (ImportError, RuntimeError):
    GPIO_DISPONIBLE = False
    print("[LED] GPIO non disponible — mode simulation console activé.")

_clignotement_actif = False
_thread_led = None


def _set_led(etat):
    """Allume (True) ou éteint (False) la LED — physique ou console."""
    if GPIO_DISPONIBLE:
        GPIO.output(LED_PIN, GPIO.HIGH if etat else GPIO.LOW)
    else:
        print(f"[LED] {'🔵 ON ' if etat else '⚫ OFF'}", end="\r")


def _boucle_clignotement():
    """Fait clignoter la LED tant que _clignotement_actif est True."""
    etat = False
    while _clignotement_actif:
        etat = not etat
        _set_led(etat)
        time.sleep(0.5)


def demarrer_clignotement():
    """Démarre le clignotement en arrière-plan (recherche en cours)."""
    global _clignotement_actif, _thread_led
    _clignotement_actif = True
    _thread_led = threading.Thread(target=_boucle_clignotement, daemon=True)
    _thread_led.start()


def arreter_clignotement():
    """Arrête le clignotement avant de passer en fixe ou éteint."""
    global _clignotement_actif
    _clignotement_actif = False
    if _thread_led is not None:
        _thread_led.join(timeout=1)


def allumer_fixe():
    """LED fixe — authentification réussie."""
    arreter_clignotement()
    _set_led(True)
    print("\n[LED] 🔵 Fixe — Conducteur authentifié.")


def eteindre():
    """Éteint la LED — échec ou arrêt du module."""
    arreter_clignotement()
    _set_led(False)
    print("\n[LED] ⚫ Éteinte.")


def nettoyer():
    """À appeler en fin de programme pour libérer le GPIO proprement."""
    eteindre()
    if GPIO_DISPONIBLE:
        GPIO.cleanup()
