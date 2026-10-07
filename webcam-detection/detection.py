import json
import sys
import time
from collections import deque
from datetime import datetime

import cv2
from ultralytics import YOLO

DELAI_ENTRE_ALERTES = 5   # secondes : pas plus d'une alerte toutes les 5 s

modele = YOLO("yolov8n.pt")
backend_camera = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
camera = cv2.VideoCapture(0, backend_camera)

dernieres_latences = deque(maxlen=30)   # garde les 30 dernières mesures
derniere_alerte = 0                     # heure de la dernière alerte envoyée

while True:
    ok, image = camera.read()
    if not ok:
        break

    image = cv2.resize(image, (640, 480))

    debut = time.time()
    resultats = modele(image, classes=[0], conf=0.5, verbose=False)
    latence_ms = (time.time() - debut) * 1000
    dernieres_latences.append(latence_ms)
    latence_moyenne = sum(dernieres_latences) / len(dernieres_latences)

    boxes = resultats[0].boxes
    nb_personnes = len(boxes)

    # --- Création de l'alerte ---
    maintenant = time.time()
    if nb_personnes > 0 and (maintenant - derniere_alerte) > DELAI_ENTRE_ALERTES:
        alerte = {
            "source": "camera",
            "type": "intrusion",
            "score": round(float(boxes.conf.max()), 2),   # meilleure confiance
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        print(json.dumps(alerte))      # pour l'instant on affiche seulement
        derniere_alerte = maintenant

    # --- Affichage ---
    image = resultats[0].plot()
    cv2.putText(image, f"Personnes : {nb_personnes}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(image, f"Latence moy. : {latence_moyenne:.0f} ms", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    cv2.imshow("Detection - Q pour quitter", image)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
