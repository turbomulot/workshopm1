"""Face recognition linked to employee records, with a step-by-step liveness check.

Ported from the face_app.py prototype (InsightFace buffalo_l). Runs in its own
thread on the shared capture buffer so YOLO and the video stream keep their pace.
"""

import math
import os
import threading
import time

import cv2
import numpy as np
from flask import Blueprint, jsonify
from PIL import Image, ImageDraw

from badges import require_admin

# buffalo_s: ~30 ms per face on a laptop CPU next to YOLO; buffalo_l (the
# prototype's pack) is more accurate but ~400 ms. Changing it requires re-enrolment.
MODEL = os.environ.get("FACE_MODEL", "buffalo_s")
THRESHOLD = float(os.environ.get("FACE_THRESHOLD", "0.45"))
YAW_SIGN = int(os.environ.get("FACE_YAW_SIGN", "1"))  # -1 if left and right are swapped
DET_SIZE = int(os.environ.get("FACE_DET_SIZE", "320"))
YAW_THRESHOLD = 0.20     # head turn, as a fraction of the distance between the eyes
# Chin up, as a fraction of the eyes-to-mouth height. Blinks were dropped: below
# 10 analysed frames/s and with landmarks smoothing the eyelids, they went unseen.
PITCH_THRESHOLD = float(os.environ.get("FACE_PITCH_THRESHOLD", "0.08"))
STABLE_NEEDED = 3        # consecutive recognitions before the gestures start
BASELINE_FRAMES = 3      # frontal poses averaged as the reference for the gestures
HOLD_FRAMES = 2          # a gesture must hold on consecutive analyses (landmark noise)
SEARCH_TIMEOUT = 10.0
CHALLENGE_TIMEOUT = 8.0
VERIFY_TIMEOUT = 5.0
LOST_TIMEOUT = 1.5
RESULT_SECONDS = 5.0
IDLE_PERIOD = 0.25       # outside a check, 4 analyses per second are enough
CHECK_PERIOD = 0.08      # during a check, ~12 per second still catch a slow blink
# onnxruntime defaults to one thread per core and then starves YOLO (torch) on
# laptop hybrid CPUs: measured 100 ms -> 18 s per YOLO frame on a Core Ultra 7 155U.
THREADS = int(os.environ.get("FACE_THREADS", "2"))
# A stably recognised, active employee starts the liveness check by themselves;
# its success authenticates them without a badge.
AUTO_CHECK = os.environ.get("FACE_AUTO_CHECK", "1") != "0"
RETRY_COOLDOWN = 10.0    # no automatic check for this employee after a failure
AUTH_GRACE = 5.0         # authentication lost when the face is out of view this long
AUTH_MAX = 120.0         # and in any case after this long: a new check is needed
ANALYSIS_WIDTH = 640
FRESH_SECONDS = 1.0

# (key, checklist label, instruction). A flat photo, even tilted, keeps the nose
# at the same place relative to the eyes and mouth: it cannot pass the gestures.
STEPS = [
    ("face", "Reconnaissance de face", "Placez-vous seul face à la caméra et regardez-la"),
    ("left", "Tête à gauche", "Tournez la tête vers votre gauche"),
    ("right", "Tête à droite", "Tournez la tête vers votre droite"),
    ("up", "Menton levé", "Levez nettement le menton, comme pour regarder le plafond"),
    ("verify", "Confirmation de face", "Revenez de face pour confirmer"),
]
GESTURES = {"left", "right", "up"}
TIMEOUTS = {"face": SEARCH_TIMEOUT, "verify": VERIFY_TIMEOUT}


class FaceError(Exception):
    def __init__(self, message, status=409):
        super().__init__(message)
        self.status = status


def best_match(embedding, gallery):
    """(employee_id, cosine score) of the closest enrolled face."""
    best_id, best_score = None, -1.0
    for employee_id, (*_, embeddings) in gallery.items():
        score = float(np.max(embeddings @ embedding))
        if score > best_score:
            best_id, best_score = employee_id, score
    return best_id, best_score


def analyse(model, image, modules):
    """FaceAnalysis.get restricted to the given modules."""
    from insightface.app.common import Face

    bboxes, kpss = model.det_model.detect(image, max_num=0, metric="default")
    faces = []
    for index in range(bboxes.shape[0]):
        face = Face(bbox=bboxes[index, 0:4], kps=None if kpss is None else kpss[index], det_score=bboxes[index, 4])
        for name in modules:
            model.models[name].get(image, face)
        faces.append(face)
    return faces


def head_ratio(face):
    """Nose offset from the middle of the eyes (0 = facing the camera)."""
    kps = face.kps
    eye_mid = (kps[0] + kps[1]) / 2
    eye_dist = np.linalg.norm(kps[0] - kps[1]) + 1e-6
    return float((kps[2][0] - eye_mid[0]) / eye_dist)


def pitch_ratio(face):
    """Nose height between the eyes (0) and the mouth (1); decreases chin up."""
    kps = face.kps
    eye_y = (kps[0][1] + kps[1][1]) / 2
    mouth_y = (kps[3][1] + kps[4][1]) / 2
    return float((kps[2][1] - eye_y) / (mouth_y - eye_y + 1e-6))


def pose(face):
    return head_ratio(face), pitch_ratio(face)


def gesture_done(key, current, baseline):
    yaw = (current[0] - baseline[0]) * YAW_SIGN
    if key == "left":
        return yaw > YAW_THRESHOLD
    if key == "right":
        return yaw < -YAW_THRESHOLD
    return current[1] - baseline[1] < -PITCH_THRESHOLD


class FaceRecognizer:
    def __init__(self, store, log):
        self.store = store
        store.face_model = MODEL
        self.log = log
        self.lock = threading.Lock()
        self.engine = {"state": "starting", "message": "Démarrage de la reconnaissance faciale…"}
        self.gallery = {}
        self.latest = None       # (analysed_at, [normed embeddings]) used for enrolment
        self.faces = []          # [{bbox, employee_id, name, active, score}] in original pixels
        self.faces_at = 0.0
        self.faces_generation = -1
        self.check = None
        self.result = None
        self.stable = (None, 0)  # (employee_id, consecutive recognitions) outside a check
        self.cooldown = {}       # employee_id -> no automatic check before this time
        self.authenticated = {}  # employee_id -> {"since", "seen"}

    def set_engine(self, state, message):
        with self.lock:
            self.engine = {"state": state, "message": message}

    def reload(self):
        gallery = self.store.face_gallery()
        with self.lock:
            self.gallery = gallery

    # ------------------------------------------------------------ API side
    def snapshot(self):
        now = time.monotonic()
        with self.lock:
            faces = self.faces if now - self.faces_at <= FRESH_SECONDS else []
            return {"face_engine": dict(self.engine, auto_check=AUTO_CHECK),
                    "faces": [{"authenticated": False, **{k: v for k, v in face.items() if k != "bbox"}} for face in faces],
                    "face_check": self.check_view(now)}

    def overlay(self, generation):
        now = time.monotonic()
        with self.lock:
            fresh = self.faces_generation == generation and now - self.faces_at <= FRESH_SECONDS
            return (list(self.faces) if fresh else []), self.check_view(now)

    def ready(self):
        if self.engine["state"] != "ready":
            raise FaceError(self.engine["message"], 503)

    def start_check(self):
        with self.lock:
            self.ready()
            if self.check:
                raise FaceError("Une vérification est déjà en cours.")
            if not self.gallery:
                raise FaceError("Aucun visage enregistré : enregistrer d'abord le visage d'un employé.")
            self.new_check(time.monotonic())
        self.log("INFO", "Vérification faciale démarrée")

    def new_check(self, now, target=None, stable=0, sample=None, auto=False):
        """Under the lock: start at the first step."""
        self.check = {"index": 0, "started": now, "step_started": now, "seen": now, "target": target,
                      "stable": stable, "samples": [sample] if sample else [], "baseline": None,
                      "hits": 0, "auto": auto}
        self.result = None

    def enroll(self, employee_id):
        with self.lock:
            self.ready()
            latest, gallery = self.latest, self.gallery
        if latest is None or time.monotonic() - latest[0] > FRESH_SECONDS:
            raise FaceError("Aucune image caméra récente.")
        if len(latest[1]) != 1:
            raise FaceError("Aucun visage détecté." if not latest[1] else "Une seule personne doit être face à la caméra.")
        embedding = latest[1][0]
        other, score = best_match(embedding, {k: v for k, v in gallery.items() if k != employee_id})
        if other and score >= THRESHOLD:
            first, last = gallery[other][:2]
            raise FaceError(f"Ce visage correspond déjà à la fiche de {first} {last}.")
        employee = self.store.add_face(employee_id, embedding)
        if employee:
            self.reload()
        return employee

    def erase(self, employee_id):
        employee = self.store.clear_faces(employee_id)
        if employee:
            self.reload()
        return employee

    # ------------------------------------------------------------ analysis thread
    def run(self, capture_buffer, stop):
        if os.environ.get("FACE_RECOGNITION", "1") == "0":
            self.set_engine("disabled", "Reconnaissance faciale désactivée (FACE_RECOGNITION=0).")
            return
        self.set_engine("loading", "Chargement du modèle de reconnaissance faciale…")
        try:
            from insightface.app import FaceAnalysis
        except ImportError:
            self.set_engine("unavailable", "InsightFace non installé : pip install insightface onnxruntime")
            return
        try:
            import onnxruntime

            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = THREADS
            options.inter_op_num_threads = 1
            # Idle ORT threads busy-wait by default, burning cores YOLO needs between analyses.
            options.add_session_config_entry("session.intra_op.allow_spinning", "0")
            model = FaceAnalysis(name=MODEL, allowed_modules=["detection", "recognition"],
                                 providers=["CPUExecutionProvider"], sess_options=options)
            model.prepare(ctx_id=-1, det_size=(DET_SIZE, DET_SIZE))
            self.reload()
        except Exception as error:
            self.set_engine("error", f"Modèle facial indisponible : {error}")
            self.log("ERREUR", f"Modèle facial indisponible : {error}")
            return
        self.set_engine("ready", "Reconnaissance faciale active.")
        self.log("INFO", "Reconnaissance faciale prête")
        sequence, last_run, reloaded = 0, 0.0, time.monotonic()
        while not stop.is_set():
            with self.lock:
                checking = self.check is not None
                modules = self.modules()
            # Polling the period, so a check that just started speeds up at once.
            if time.monotonic() < last_run + (CHECK_PERIOD if checking else IDLE_PERIOD):
                stop.wait(0.02)
                continue
            packet = capture_buffer.read(sequence, stop)
            if packet is None:
                self.publish([], None, 1.0, -1)
                continue
            sequence, generation, original, captured_at, _ = packet
            if time.monotonic() - captured_at > 0.5:
                continue
            last_run = time.monotonic()
            if time.monotonic() - reloaded > 2:
                self.reload()
                reloaded = time.monotonic()
            factor = min(1.0, ANALYSIS_WIDTH / original.shape[1])
            image = cv2.resize(original, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA) if factor < 1 else original
            try:
                detected = analyse(model, image, modules)
            except Exception as error:
                self.log("ERREUR", f"Analyse faciale : {error}")
                stop.wait(1)
                continue
            self.publish(detected, image, factor, generation)

    def gesture_step(self):
        return bool(self.check) and STEPS[self.check["index"]][0] in GESTURES

    def modules(self):
        """Only what the current step needs: gestures use the detector's 5 points."""
        return () if self.gesture_step() else ("recognition",)

    def publish(self, detected, image, factor, generation):
        now = time.monotonic()
        with self.lock:
            gallery = self.gallery
            target = self.check["target"] if self.gesture_step() else None
        faces = []
        for face in detected:
            employee_id, score = (None, 0.0)
            if face.embedding is not None and gallery:
                employee_id, score = best_match(face.normed_embedding, gallery)
            known = employee_id is not None and score >= THRESHOLD
            first, last, active = gallery[employee_id][:3] if known else (None, None, False)
            faces.append({"bbox": (face.bbox / factor).tolist(), "employee_id": employee_id if known else None,
                          "name": f"{first} {last}" if known else None, "active": active,
                          "score": round(score, 2), "raw": face})
        area = lambda f: (f["bbox"][2] - f["bbox"][0]) * (f["bbox"][3] - f["bbox"][1])
        main = max(faces, key=area, default=None)
        if target in gallery:
            # No recognition during a challenge: show only the face being checked.
            first, last, active = gallery[target][:3]
            faces = [dict(main, employee_id=target, name=f"{first} {last}", active=active, score=0.0)] if main else []
        started = False
        with self.lock:
            self.refresh_authenticated(faces if target is None else [], now)
            if image is not None:
                self.faces = [{k: v for k, v in face.items() if k != "raw"} for face in faces]
                self.faces_at, self.faces_generation = now, generation
                if all(face.embedding is not None for face in detected):
                    self.latest = (now, [face.normed_embedding for face in detected])
                started = target is None and self.auto_start(main, now)
            finished = self.advance(main, now)
        if started:
            self.log("INFO", "Vérification faciale démarrée automatiquement")
        if finished:
            employee_id, result, message = finished
            self.store.record(employee_id, result, "face")
            self.log("INFO", {"valid": "Vérification faciale : accès accepté",
                              "disabled": "Vérification faciale : fiche désactivée"}.get(result, "Vérification faciale refusée"))

    def refresh_authenticated(self, faces, now):
        """Under the lock: keep authentications whose face is still in view, flag those faces."""
        for face in faces:
            entry = self.authenticated.get(face["employee_id"])
            face["authenticated"] = bool(entry) and face["active"]
            if face["authenticated"]:
                entry["seen"] = now
        for employee_id, entry in list(self.authenticated.items()):
            active = self.gallery.get(employee_id, (None, None, False))[2]
            if not active or now - entry["seen"] > AUTH_GRACE or now - entry["since"] > AUTH_MAX:
                del self.authenticated[employee_id]

    def auto_start(self, main, now):
        """Under the lock: start the check once an active, unauthenticated employee is stably recognised."""
        if not AUTO_CHECK or self.check or self.engine["state"] != "ready":
            self.stable = (None, 0)
            return False
        employee_id = main["employee_id"] if main and main["active"] else None
        if employee_id is None or employee_id in self.authenticated or now < self.cooldown.get(employee_id, 0):
            self.stable = (None, 0)
            return False
        count = self.stable[1] + 1 if self.stable[0] == employee_id else 1
        self.stable = (employee_id, count)
        if count < STABLE_NEEDED:
            return False
        self.new_check(now, employee_id, count, pose(main["raw"]), auto=True)
        self.stable = (None, 0)
        return True

    def advance(self, main, now):
        """Liveness state machine; called under the lock. Returns a finished check."""
        check = self.check
        if not check:
            return None
        if main:
            check["seen"] = now
        key, label, _ = STEPS[check["index"]]
        timed_out = now - check["step_started"] > TIMEOUTS.get(key, CHALLENGE_TIMEOUT)
        if key == "face":
            if main and main["employee_id"]:
                if main["employee_id"] != check["target"]:
                    check.update(target=main["employee_id"], stable=0, samples=[])
                check["stable"] += 1
                check["samples"].append(pose(main["raw"]))
            elif main:
                check.update(target=None, stable=0, samples=[])
            if check["stable"] >= STABLE_NEEDED and len(check["samples"]) >= BASELINE_FRAMES:
                check["baseline"] = tuple(np.median(check["samples"][-BASELINE_FRAMES:], axis=0))
                self.next_step(check, now)
            elif timed_out:
                return self.finish(check["target"], "refused", "Aucun visage enregistré reconnu.", now)
        elif key in GESTURES:
            if main:
                done = gesture_done(key, pose(main["raw"]), check["baseline"])
                check["hits"] = check["hits"] + 1 if done else 0
            if check["hits"] >= HOLD_FRAMES:
                self.next_step(check, now)
            elif now - check["seen"] > LOST_TIMEOUT:
                return self.finish(check["target"], "refused", f"Visage perdu à l'étape « {label} ».", now)
            elif timed_out:
                return self.finish(check["target"], "refused", f"Délai dépassé à l'étape « {label} ».", now)
        else:
            if main and main["employee_id"] == check["target"]:
                check["hits"] += 1
            if check["hits"] >= 2:
                first, last, active = self.gallery.get(check["target"], ("?", "?", False))[:3]
                if active:
                    return self.finish(check["target"], "valid", f"Accès accepté : {first} {last}", now)
                return self.finish(check["target"], "disabled", f"Visage reconnu, fiche désactivée : {first} {last}", now)
            if timed_out:
                return self.finish(check["target"], "refused", "Identité non confirmée de face.", now)
        return None

    @staticmethod
    def next_step(check, now):
        check.update(index=check["index"] + 1, step_started=now, hits=0)

    @staticmethod
    def steps_view(index, outcome=None):
        """Checklist: done / current / pending, the current one 'failed' on refusal."""
        def state(position):
            if outcome == "valid" or position < index:
                return "done"
            if position == index:
                return "failed" if outcome == "refused" else "current"
            return "pending"
        return [{"key": key, "label": label, "state": state(position)} for position, (key, label, _) in enumerate(STEPS)]

    def finish(self, employee_id, result, message, now):
        outcome = "valid" if result in ("valid", "disabled") else "refused"
        steps = self.steps_view(self.check["index"], outcome) if self.check else []
        self.check = None
        self.result = {"state": result, "message": message, "until": now + RESULT_SECONDS, "steps": steps}
        if employee_id and result == "valid":
            self.authenticated[employee_id] = {"since": now, "seen": now}
        elif employee_id:
            self.cooldown[employee_id] = now + RETRY_COOLDOWN
        return employee_id, result, message

    def check_view(self, now):
        check = self.check
        if check:
            index = check["index"]
            key, _, instruction = STEPS[index]
            limit = TIMEOUTS.get(key, CHALLENGE_TIMEOUT)
            return {"state": "running", "auto": check["auto"], "step": index + 1, "total": len(STEPS),
                    "steps": self.steps_view(index), "instruction": instruction,
                    "remaining_s": math.ceil(max(0, limit - (now - check["step_started"])))}
        if self.result and now < self.result["until"]:
            return {key: self.result[key] for key in ("state", "message", "steps")}
        return None


COLORS = {"valid": "#2fb344", "disabled": "#e5484d", "refused": "#e5484d"}


def authenticated_people(boxes, faces, scale):
    """{person index: name} for person boxes holding exactly one authenticated face,
    and only if that face is inside exactly one person box (same caution as badges)."""
    sx, sy = scale
    people = {}
    claimed = {}
    for face in faces:
        if not face.get("authenticated"):
            continue
        x1, y1, x2, y2 = face["bbox"]
        cx, cy = (x1 + x2) / 2 * sx, (y1 + y2) / 2 * sy
        inside = [i for i, (bx1, by1, bx2, by2) in enumerate(boxes) if bx1 <= cx <= bx2 and by1 <= cy <= by2]
        if len(inside) == 1:
            claimed[inside[0]] = claimed.get(inside[0], 0) + 1
            people[inside[0]] = face["name"]
    return {index: name for index, name in people.items() if claimed[index] == 1}


def annotate_faces(image, faces, check, scale, font):
    """Draw face boxes (original pixels, scaled to the stream) and the check banner."""
    if not faces and not check:
        return image
    canvas = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(canvas)
    sx, sy = scale
    for face in faces:
        x1, y1, x2, y2 = face["bbox"]
        box = (x1 * sx, y1 * sy, x2 * sx, y2 * sy)
        if face.get("authenticated"):
            color, label = "#2fb344", f"Visage authentifié : {face['name']}"
        elif face["name"]:
            color = "#4cc2ff" if face["active"] else "#e5484d"
            label = f"Visage : {face['name']} ({face['score']:.2f})"
        else:
            color, label = "#fab219", "Visage inconnu"
        draw.rectangle(box, outline=color, width=2)
        width = draw.textbbox((0, 0), label, font=font)[2] + 10
        left = max(0, min(int(box[0]), canvas.width - width))
        top = min(canvas.height - 24, int(box[3]) + 2)
        draw.rectangle((left, top, left + width, top + 24), fill="#121924")
        draw.text((left + 5, top + 2), label, font=font, fill=color)
    if check:
        text = check.get("message") or check["instruction"]
        if check["state"] == "running":
            text = f"Étape {check['step']}/{check['total']} : {text} ({check['remaining_s']} s)"
        color = COLORS.get(check["state"], "#fab219")
        draw.rectangle((0, 0, canvas.width, 32), fill="#121924")
        draw.text((10, 7), text, font=font, fill=color)
    return cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)


def create_face_api(store, recognizer):
    api = Blueprint("faces", __name__)
    protected = require_admin(store)

    @api.post("/api/v1/employees/<employee_id>/faces")
    @protected
    def enroll(employee_id):
        try:
            employee = recognizer.enroll(employee_id)
        except FaceError as error:
            return jsonify(error=str(error)), error.status
        return (jsonify(employee), 201) if employee else (jsonify(error="Employé introuvable."), 404)

    @api.delete("/api/v1/employees/<employee_id>/faces")
    @protected
    def erase(employee_id):
        employee = recognizer.erase(employee_id)
        return (jsonify(employee), 200) if employee else (jsonify(error="Employé introuvable."), 404)

    @api.post("/api/v1/faces/check")
    @protected
    def check():
        try:
            recognizer.start_check()
        except FaceError as error:
            return jsonify(error=str(error)), error.status
        return jsonify(recognizer.snapshot()["face_check"]), 202

    @api.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    return api
