import os
import sys
import threading
import time
from collections import deque
from datetime import datetime

import cv2
from flask import Flask, Response, jsonify, request
from ultralytics import YOLO

app = Flask(__name__)
modele = YOLO("yolov8n.pt")

# AVFoundation n'existe que sur Mac : sous Windows on passe par DirectShow,
# ailleurs on laisse OpenCV choisir.
BACKENDS_CAMERA = {"darwin": cv2.CAP_AVFOUNDATION, "win32": cv2.CAP_DSHOW}
camera = cv2.VideoCapture(0, BACKENDS_CAMERA.get(sys.platform, cv2.CAP_ANY))

# --- Réglages ---
DELAI_LOG = 5            # secondes entre deux logs tant que quelqu'un est présent

# --- Sécurité (voir security/docs/matrice-securite.md) ---
# Par défaut, le service n'écoute que sur ce PC : depuis le réseau, on passe
# par la porte HTTPS avec mot de passe (Caddy, https://<serveur>/ai/...).
# VISION_HOST=0.0.0.0 pour revenir à l'ancien comportement (déconseillé).
HOTE = os.environ.get("VISION_HOST", "127.0.0.1")
# Seuls ces sites peuvent lire /status et /logs depuis un navigateur (CORS).
ORIGINES_AUTORISEES = {
    origine.strip()
    for origine in os.environ.get(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origine.strip()
}

# --- Ce que le gardien met à jour, et que le serveur web lit ---
etat = {"detection": False, "personnes": 0, "latence_ms": 0, "heure": ""}
logs = deque(maxlen=50)          # le journal : garde les 50 derniers événements
derniere_image = None            # la dernière image JPEG prête à être envoyée
verrou = threading.Lock()        # évite que deux threads touchent l'image en même temps
derniere_ecriture = 0            # heure du dernier log de présence


def ecrire_log(niveau, message):
    """Ajoute une ligne au journal et l'affiche aussi dans le terminal."""
    ligne = {
        "id": (logs[-1]["id"] + 1) if logs else 1,
        "heure": datetime.now().strftime("%H:%M:%S"),
        "niveau": niveau,
        "message": message,
    }
    logs.append(ligne)
    print(f"[{ligne['heure']}] {niveau} : {message}")


def gardien():
    """Tourne en continu, même si personne ne regarde la vidéo."""
    global derniere_image, derniere_ecriture
    ecrire_log("INFO", "Surveillance démarrée")
    etait_detecte = False

    while True:
        ok, image = camera.read()
        if not ok:
            ecrire_log("ERREUR", "Caméra : plus d'image reçue")
            break

        image = cv2.resize(image, (640, 480))

        debut = time.time()
        resultats = modele(image, classes=[0], conf=0.5, verbose=False)
        latence_ms = (time.time() - debut) * 1000

        boxes = resultats[0].boxes
        nb_personnes = len(boxes)
        detecte = nb_personnes > 0

        # Le journal : à l'arrivée, puis toutes les 5 s de présence, puis au départ
        maintenant = time.time()
        if detecte and not etait_detecte:
            score = float(boxes.conf.max())
            ecrire_log("ALERTE", f"Intrusion détectée ({nb_personnes} personne(s), confiance {score:.2f})")
            derniere_ecriture = maintenant
        elif detecte and (maintenant - derniere_ecriture) > DELAI_LOG:
            score = float(boxes.conf.max())
            ecrire_log("INFO", f"Présence toujours détectée ({nb_personnes} personne(s), confiance {score:.2f})")
            derniere_ecriture = maintenant
        elif not detecte and etait_detecte:
            ecrire_log("INFO", "Zone libre")
        etait_detecte = detecte

        # La fiche d'état
        etat["detection"] = detecte
        etat["personnes"] = nb_personnes
        etat["latence_ms"] = round(latence_ms)
        etat["heure"] = datetime.now().strftime("%H:%M:%S")

        # L'image à montrer
        image = resultats[0].plot()
        cv2.putText(image, f"Personnes : {nb_personnes}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(image, f"Latence : {latence_ms:.0f} ms", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        ok, jpeg = cv2.imencode(".jpg", image)
        with verrou:
            derniere_image = jpeg.tobytes()


@app.after_request
def autoriser_le_frontend(reponse):
    # Avant : "*" (n'importe quel site web pouvait lire la détection et le journal).
    origine = request.headers.get("Origin")
    if origine in ORIGINES_AUTORISEES:
        reponse.headers["Access-Control-Allow-Origin"] = origine
        reponse.headers["Vary"] = "Origin"
    return reponse


def generer_images():
    """Envoie au navigateur la dernière image du gardien."""
    while True:
        with verrou:
            image = derniere_image
        if image is not None:
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + image + b"\r\n")
        time.sleep(0.03)     # environ 30 images par seconde


@app.route("/")
def accueil():
    """Page d'accueil : liste les routes disponibles (évite le 404 sur '/')."""
    return jsonify({
        "service": "Sentinel-X - vision",
        "routes": ["/video", "/status", "/logs"],
    })


@app.route("/video")
def video():
    return Response(generer_images(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/status")
def status():
    return jsonify(etat)


@app.route("/logs")
def liste_logs():
    return jsonify(list(logs))


# On lance le gardien en arrière-plan, puis le serveur web
threading.Thread(target=gardien, daemon=True).start()
app.run(host=HOTE, port=5001)