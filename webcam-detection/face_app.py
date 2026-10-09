"""
Prototype de reconnaissance faciale 100 % local (webcam + InsightFace)
avec vérification de vivacité (anti-photo) par défis aléatoires.

Installation :
    pip install insightface onnxruntime opencv-python numpy

Utilisation :
    # Mode enregistrement : prendre des photos de "Nabil" avec la webcam
    python face_app.py enroll --name Nabil

    # Mode reconnaissance en temps réel (avec vérification de vivacité)
    python face_app.py recognize

    # Reconnaissance seule, sans défis (comportement de la version précédente)
    python face_app.py recognize --no-liveness

    # Voir les personnes enregistrées
    python face_app.py list

Déroulement de la reconnaissance avec vivacité :
    1. Le visage est reconnu de façon stable (score >= seuil).
    2. Le programme tire 2 défis au hasard parmi : tourner la tête à gauche,
       tourner la tête à droite, cligner des yeux.
    3. Une fois les défis réussis, il re-vérifie l'identité de face.
    4. Seulement alors : "ACCES OK : <nom>".
"""

import argparse
import pickle
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from insightface.app import FaceAnalysis

DB_PATH = Path("embeddings.pkl")

# --- Réglages de la vérification de vivacité
YAW_SIGN = 1             # mettre -1 si "gauche" et "droite" sont inversés chez toi
YAW_THRESHOLD = 0.20     # rotation de tête minimale (en fraction de la distance entre les yeux)
BLINK_RATIO = 0.70       # un clignement = ouverture de l'oeil < 70 % de l'ouverture normale
STABLE_NEEDED = 3        # nb de détections consécutives avant de lancer les défis
CHALLENGE_TIMEOUT = 8.0  # secondes par défi
VERIFY_TIMEOUT = 4.0     # secondes pour la re-vérification finale
LOST_TIMEOUT = 1.5       # secondes sans visage avant d'abandonner

CHALLENGES = {
    "left": "Tourne la tete vers TA gauche",
    "right": "Tourne la tete vers TA droite",
    "blink": "Cligne des yeux",
}

GREEN, RED, YELLOW = (0, 200, 0), (0, 0, 255), (0, 255, 255)


# ---------------------------------------------------------------- stockage
def load_db() -> dict:
    """Retourne {nom: tableau (N, 512) d'embeddings}."""
    if DB_PATH.exists():
        with open(DB_PATH, "rb") as f:
            return pickle.load(f)
    return {}


def save_db(db: dict) -> None:
    with open(DB_PATH, "wb") as f:
        pickle.dump(db, f)


# ---------------------------------------------------------------- outils
def open_camera(index: int) -> cv2.VideoCapture:
    backend = cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
    cam = cv2.VideoCapture(index, backend)
    if not cam.isOpened():
        sys.exit("Impossible d'ouvrir la caméra (vérifie l'autorisation caméra et l'index).")
    return cam


def load_model(det_size: int) -> FaceAnalysis:
    # On ne charge que ce dont on a besoin (plus rapide) :
    # détection + embedding + repères 3D (pour clignement et rotation de tête)
    app = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection", "recognition", "landmark_3d_68"],
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_size=(det_size, det_size))
    return app


def draw_text(img, text, org, color=(255, 255, 255), scale=0.6):
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def face_area(face) -> float:
    x1, y1, x2, y2 = face.bbox
    return float((x2 - x1) * (y2 - y1))


# ---------------------------------------------------------------- mode enregistrement
def enroll(args):
    app = load_model(args.det_size)
    db = load_db()
    new_embeddings = []

    cam = open_camera(args.camera)
    print("ESPACE = prendre une photo | Q = terminer et sauvegarder")
    print("Conseil : varie les angles, l'expression, les lunettes, l'éclairage.")

    while True:
        ok, frame = cam.read()
        if not ok:
            break

        faces = app.get(frame)
        display = frame.copy()

        for f in faces:
            x1, y1, x2, y2 = f.bbox.astype(int)
            color = (0, 255, 0) if len(faces) == 1 else (0, 0, 255)
            cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

        if len(faces) == 1:
            status = "Visage OK - ESPACE pour capturer"
        elif len(faces) == 0:
            status = "Aucun visage detecte"
        else:
            status = "Plusieurs visages : une seule personne a la fois"

        draw_text(display, f"Enregistrement : {args.name}", (10, 25))
        draw_text(display, f"Photos prises : {len(new_embeddings)}", (10, 50))
        draw_text(display, status, (10, 75), color=YELLOW)
        cv2.imshow("Enregistrement", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(" ") and len(faces) == 1:
            new_embeddings.append(faces[0].normed_embedding)
            print(f"Photo {len(new_embeddings)} enregistrée")
        elif key == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()

    if not new_embeddings:
        print("Aucune photo prise, rien n'a été sauvegardé.")
        return

    new_embeddings = np.array(new_embeddings)
    if args.name in db:
        db[args.name] = np.vstack([db[args.name], new_embeddings])
    else:
        db[args.name] = new_embeddings
    save_db(db)
    print(f"{len(new_embeddings)} embeddings ajoutés pour {args.name} "
          f"(total : {len(db[args.name])}). Fichier : {DB_PATH}")


# ---------------------------------------------------------------- comparaison
def best_match(embedding, db, strategy):
    """Retourne (nom, score) de la personne la plus proche."""
    best_name, best_score = None, -1.0
    for name, embs in db.items():
        if strategy == "mean":
            ref = embs.mean(axis=0)
            ref = ref / np.linalg.norm(ref)
            score = float(np.dot(ref, embedding))
        else:  # "best"
            score = float(np.max(embs @ embedding))
        if score > best_score:
            best_name, best_score = name, score
    return best_name, best_score


# ---------------------------------------------------------------- vivacité
def head_ratio(face) -> float:
    """Position du nez par rapport au milieu des yeux (0 = de face).
    Avec l'image non miroir : tourner la tête vers SA droite => valeur négative."""
    kps = face.kps  # 5 points : oeil, oeil, nez, bouche, bouche
    eye_mid = (kps[0] + kps[1]) / 2
    eye_dist = np.linalg.norm(kps[0] - kps[1]) + 1e-6
    return float((kps[2][0] - eye_mid[0]) / eye_dist)


def eye_aspect_ratio(face) -> float:
    """Ouverture moyenne des yeux (EAR), à partir des 68 repères standards."""
    lm = face.landmark_3d_68[:, :2]

    def ear(p):
        vertical = np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4])
        horizontal = 2 * np.linalg.norm(p[0] - p[3]) + 1e-6
        return vertical / horizontal

    return float((ear(lm[36:42]) + ear(lm[42:48])) / 2)


class Challenge:
    """Un défi de vivacité : 'left', 'right' ou 'blink'."""

    def __init__(self, kind: str):
        self.kind = kind
        self.start = time.time()
        self.samples = []
        self.baseline = None

    def update(self, face) -> bool:
        """Retourne True quand le défi est réussi."""
        value = eye_aspect_ratio(face) if self.kind == "blink" else head_ratio(face)

        # Les premières images servent de référence ("normal")
        need = 8 if self.kind == "blink" else 5
        if self.baseline is None:
            self.samples.append(value)
            if len(self.samples) >= need:
                self.baseline = float(np.median(self.samples))
            return False

        if self.kind == "blink":
            return value < BLINK_RATIO * self.baseline

        delta = (value - self.baseline) * YAW_SIGN
        if self.kind == "right":
            return delta < -YAW_THRESHOLD
        return delta > YAW_THRESHOLD  # "left"


# ---------------------------------------------------------------- mode reconnaissance
def recognize(args):
    db = load_db()
    if not db:
        sys.exit("Base vide : lance d'abord `python face_app.py enroll --name TonNom`.")

    app = load_model(args.det_size)
    cam = open_camera(args.camera)
    print("Q = quitter")

    state = "recognizing"  # recognizing -> challenge -> verify -> result
    frame_count = 0
    results = []           # (bbox, label, score, face)
    target_name, stable = None, 0
    queue, idx = [], 0
    last_seen = time.time()
    verify_start, verify_ok = 0.0, 0
    banner_text, banner_color, banner_until = "", GREEN, 0.0

    def fail(message):
        nonlocal state, banner_text, banner_color, banner_until, stable, target_name
        state = "result"
        banner_text, banner_color = f"ECHEC : {message}", RED
        banner_until = time.time() + 3.0
        stable, target_name = 0, None

    while True:
        ok, frame = cam.read()
        if not ok:
            break
        now = time.time()

        # ---------- 1. reconnaissance simple
        if state == "recognizing":
            if frame_count % args.every == 0:
                results = []
                for f in app.get(frame):
                    name, score = best_match(f.normed_embedding, db, args.strategy)
                    label = name if score >= args.threshold else "Inconnu"
                    results.append((f.bbox.astype(int), label, score, f))

                if args.liveness:
                    if results:
                        main = max(results, key=lambda r: (r[0][2] - r[0][0]) * (r[0][3] - r[0][1]))
                        label = main[1]
                        if label == "Inconnu":
                            target_name, stable = None, 0
                        elif label == target_name:
                            stable += 1
                        else:
                            target_name, stable = label, 1
                    else:
                        target_name, stable = None, 0

                    if stable >= STABLE_NEEDED:
                        kinds = random.sample(list(CHALLENGES), 2)
                        queue = [Challenge(k) for k in kinds]
                        idx = 0
                        queue[0].start = now
                        last_seen = now
                        state = "challenge"

        # ---------- 2. défis de vivacité
        elif state == "challenge":
            faces = app.get(frame)
            results = []
            if faces:
                last_seen = now
                f = max(faces, key=face_area)
                results = [(f.bbox.astype(int), target_name, 0.0, f)]
                if queue[idx].update(f):
                    idx += 1
                    if idx >= len(queue):
                        state = "verify"
                        verify_start, verify_ok = now, 0
                    else:
                        queue[idx].start = now

            if state == "challenge":
                if now - last_seen > LOST_TIMEOUT:
                    fail("visage perdu")
                elif now - queue[idx].start > CHALLENGE_TIMEOUT:
                    fail("delai depasse")

        # ---------- 3. re-vérification de l'identité, de face
        elif state == "verify":
            faces = app.get(frame)
            results = []
            if faces:
                f = max(faces, key=face_area)
                name, score = best_match(f.normed_embedding, db, args.strategy)
                label = name if score >= args.threshold else "Inconnu"
                results = [(f.bbox.astype(int), label, score, f)]
                if name == target_name and score >= args.threshold:
                    verify_ok += 1

            if verify_ok >= 2:
                state = "result"
                banner_text, banner_color = f"ACCES OK : {target_name}", GREEN
                banner_until = now + 4.0
            elif now - verify_start > VERIFY_TIMEOUT:
                fail("identite non confirmee")

        # ---------- 4. affichage du résultat, puis retour au début
        elif state == "result":
            if now > banner_until:
                state, results = "recognizing", []
                stable, target_name, frame_count = 0, None, 0

        # ---------- dessin
        for (x1, y1, x2, y2), label, score, _ in results:
            known = label not in ("Inconnu", None)
            color = (0, 255, 0) if known else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            text = f"{label} ({score:.2f})" if score else f"{label}"
            draw_text(frame, text, (x1, max(y1 - 10, 20)), color=color)

        h, w = frame.shape[:2]
        if state == "recognizing":
            mode = "vivacite ON" if args.liveness else "vivacite OFF"
            draw_text(frame, f"Seuil : {args.threshold} | {args.strategy} | {mode}", (10, 25))
        elif state == "challenge":
            left = max(0.0, CHALLENGE_TIMEOUT - (now - queue[idx].start))
            draw_text(frame, f"Epreuve {idx + 1}/{len(queue)} ({left:.0f}s)", (10, 30), YELLOW, 0.8)
            draw_text(frame, CHALLENGES[queue[idx].kind], (10, 65), YELLOW, 0.9)
        elif state == "verify":
            draw_text(frame, "Regarde la camera, de face", (10, 30), YELLOW, 0.8)
        elif state == "result":
            cv2.rectangle(frame, (0, h // 2 - 40), (w, h // 2 + 40), banner_color, -1)
            draw_text(frame, banner_text, (20, h // 2 + 10), (255, 255, 255), 1.0)

        cv2.imshow("Reconnaissance", frame)
        frame_count += 1

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()


# ---------------------------------------------------------------- liste
def list_people(_args):
    db = load_db()
    if not db:
        print("Aucune personne enregistrée.")
    for name, embs in db.items():
        print(f"- {name} : {len(embs)} embeddings")


# ---------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description="Reconnaissance faciale locale")
    parser.add_argument("--camera", type=int, default=0, help="index de la webcam")
    parser.add_argument("--det-size", type=int, default=480,
                        help="taille de détection (plus petit = plus rapide)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_enroll = sub.add_parser("enroll", help="prendre des photos avec la webcam")
    p_enroll.add_argument("--name", required=True, help="nom de la personne")
    p_enroll.set_defaults(func=enroll)

    p_rec = sub.add_parser("recognize", help="reconnaissance en temps réel")
    p_rec.add_argument("--threshold", type=float, default=0.45,
                       help="score minimum pour accepter une personne (à calibrer)")
    p_rec.add_argument("--strategy", choices=["best", "mean"], default="best",
                       help="best = meilleur score, mean = moyenne des embeddings")
    p_rec.add_argument("--every", type=int, default=2,
                       help="détection toutes les N frames (hors défis)")
    p_rec.add_argument("--no-liveness", dest="liveness", action="store_false",
                       help="désactive la vérification de vivacité (défis)")
    p_rec.set_defaults(func=recognize, liveness=True)

    p_list = sub.add_parser("list", help="lister les personnes enregistrées")
    p_list.set_defaults(func=list_people)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()