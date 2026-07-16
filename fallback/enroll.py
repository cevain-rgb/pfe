# enroll.py
# Script d'inscription de conducteurs pour les tests du système
#
# Lancement :
#   python enroll.py
#
# Ce script permet de :
#   1. Lister les conducteurs déjà enregistrés
#   2. Inscrire un nouveau conducteur via la webcam
#   3. Supprimer un conducteur
#   4. Tester l'authentification en temps réel

import json
import time

import cv2
import db_context  # ⚠️ DOIT être importé en premier — active le contexte Flask/SQLAlchemy
from extensions import db
from models import Driver
from recognition import calculer_embedding, identifier_conducteur

# ── Helpers ──────────────────────────────────────────

def lister_conducteurs():
    conducteurs = Driver.query.all()
    if not conducteurs:
        print("\n  (aucun conducteur enregistré)\n")
        return
    print(f"\n  {'ID':<5} {'Nom':<20} {'Source':<10} {'Enregistré le'}")
    print("  " + "-" * 55)
    for d in conducteurs:
        print(f"  {d.id:<5} {d.nom:<20} {d.source:<10} {d.created_at.strftime('%d/%m/%Y %H:%M')}")
    print()


def inscrire_conducteur():
    nom = input("  Nom du conducteur *: ").strip()
    prenom = input("  Prenom : ").strip()
    if not nom :
        print("  [ERREUR] Nom vide.")
        return

    print(f"\n  Positionnez le visage de {nom} face à la caméra.")
    print("  ESPACE = capturer  |  Q = annuler\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("  [ERREUR] Impossible d'ouvrir la caméra.")
        return

    embedding = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        cv2.putText(frame, f"Inscription : {nom}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(frame, "ESPACE = capturer  |  Q = annuler",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.imshow("Inscription conducteur", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("  [ANNULÉ]")
            break
        elif key == ord(' '):
            print("  Calcul de l'embedding...")
            embedding = calculer_embedding(frame)
            if embedding is None:
                print("  [ERREUR] Aucun visage détecté — réessaie.")
                continue
            print("  ✅ Visage capturé.")
            break

    cap.release()
    cv2.destroyAllWindows()

    if embedding is None:
        return

    driver = Driver(nom=nom, embedding=json.dumps(embedding), source="local")
    db.session.add(driver)
    db.session.commit()
    print(f"  ✅ Conducteur '{nom}' enregistré (ID={driver.id}).\n")


def supprimer_conducteur():
    lister_conducteurs()
    try:
        id_ = int(input("  ID du conducteur à supprimer : "))
    except ValueError:
        print("  [ERREUR] ID invalide.")
        return

    driver = Driver.query.get(id_)
    if not driver:
        print("  [ERREUR] Conducteur introuvable.")
        return

    confirmation = input(f"  Supprimer '{driver.nom}' ? (o/n) : ").strip().lower()
    if confirmation == 'o':
        db.session.delete(driver)
        db.session.commit()
        print(f"  ✅ Conducteur '{driver.nom}' supprimé.\n")
    else:
        print("  [ANNULÉ]")


def tester_authentification():
    print("\n  Test d'authentification en temps réel.")
    print("  Le système essaie de vous reconnaître toutes les 1,5 secondes.")
    print("  Appuyez sur Q pour quitter.\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("  [ERREUR] Impossible d'ouvrir la caméra.")
        return

    derniere_tentative = 0
    resultat_affiche = "En attente..."
    couleur = (200, 200, 200)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        now = time.time()

        if now - derniere_tentative >= 1.5:
            derniere_tentative = now
            nom, distance = identifier_conducteur(frame)
            if nom:
                resultat_affiche = f"✓ {nom} (dist={distance})"
                couleur = (0, 255, 0)
            elif distance is not None:
                resultat_affiche = f"✗ Inconnu (dist={distance})"
                couleur = (0, 0, 255)
            else:
                resultat_affiche = "Aucun visage"
                couleur = (128, 128, 128)

        cv2.rectangle(frame, (0, 0), (400, 70), (30, 30, 30), -1)
        cv2.putText(frame, resultat_affiche,
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, couleur, 2)
        cv2.putText(frame, f"Seuil : {__import__('config').SEUIL_RECONNAISSANCE}  |  Q = quitter",
                    (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        cv2.imshow("Test authentification", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


# ── Menu principal ────────────────────────────────────

def menu():
    while True:
        print("=" * 45)
        print("  GESTION DES CONDUCTEURS — Tests système")
        print("=" * 45)
        print("  1. Lister les conducteurs")
        print("  2. Inscrire un nouveau conducteur")
        print("  3. Supprimer un conducteur")
        print("  4. Tester l'authentification (temps réel)")
        print("  0. Quitter")
        print("-" * 45)
        choix = input("  Choix : ").strip()

        if choix == "1":
            lister_conducteurs()
        elif choix == "2":
            inscrire_conducteur()
        elif choix == "3":
            supprimer_conducteur()
        elif choix == "4":
            tester_authentification()
        elif choix == "0":
            print("  Au revoir.")
            break
        else:
            print("  [ERREUR] Choix invalide.\n")


if __name__ == "__main__":
    menu()