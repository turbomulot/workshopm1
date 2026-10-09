import sys
import time
import cv2

# Sur Mac, on utilise le backend AVFoundation (le plus fiable).
# Index 0 = webcam intégrée du MacBook Air.
# Si tu as aussi une webcam USB branchée, elle peut être l'index 1.
INDEX_CAMERA = 0

backend_camera = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
camera = cv2.VideoCapture(INDEX_CAMERA, backend_camera)

if not camera.isOpened():
    print("Impossible d'ouvrir la caméra.")
    print("Vérifie : Réglages Système > Confidentialité et sécurité > Caméra")
    print("et coche ton terminal (ou VS Code), puis relance-le.")
    raise SystemExit(1)

print("Caméra ouverte. Appuie sur Q dans la fenêtre pour quitter.")

dernier_temps = time.time()

while True:
    ok, image = camera.read()
    if not ok:
        print("Aucune image reçue de la caméra.")
        break

    # Taille imposée par le sujet pour garder un traitement rapide
    image = cv2.resize(image, (640, 480))

    # Calcul des images par seconde (FPS)
    maintenant = time.time()
    fps = 1 / (maintenant - dernier_temps)
    dernier_temps = maintenant

    cv2.putText(image, f"FPS : {fps:.0f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Test webcam - Q pour quitter", image)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()
