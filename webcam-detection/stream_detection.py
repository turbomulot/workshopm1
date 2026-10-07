"""Single camera owner: person detection, QR validation and local Flask API."""

import copy
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
from flask import Flask, Response, jsonify
from ultralytics import YOLO

from badges import BadgeStore, create_badge_api
from capture_buffer import CaptureBuffer
from qr_vision import QRVision, associate_codes

ROOT = Path(__file__).resolve().parent


class VisionRuntime:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.frame = None
        self.last_frame_at = 0.0
        self.output_sequence = 0
        self.output_changed = threading.Condition(self.lock)
        self.capture_buffer = CaptureBuffer()
        self.log_id = 0
        self.logs = deque(maxlen=50)
        self.state = {"detection": False, "personnes": 0, "latence_ms": 0,
                      "traitement_ms": 0, "heure": "", "camera_connected": False,
                      "timestamp": None, "badges": [], "error": None, "fps": 0.0,
                      "analyse_ms": 0, "age_image_ms": 0, "confiance": None}

    def snapshot(self, private=False):
        with self.lock:
            state = copy.deepcopy(self.state)
            if state["camera_connected"] and time.monotonic() - self.last_frame_at > 3:
                state.update(camera_connected=False, detection=False, personnes=0, badges=[],
                             error="Analyse caméra interrompue : image périmée.", timestamp=None, fps=0.0)
            return state if private else {k: v for k, v in state.items() if k != "badges"}

    def log(self, level, message):
        with self.lock:
            self.log_id += 1
            line = {"id": self.log_id, "heure": datetime.now().strftime("%H:%M:%S"),
                    "niveau": level, "message": message}
            self.logs.append(line)
        print(f"[{line['heure']}] {level} : {message}", flush=True)

    def unavailable(self, message):
        with self.lock:
            self.frame = None
            self.output_sequence += 1
            self.state.update(camera_connected=False, detection=False, personnes=0,
                              badges=[], error=message, timestamp=None, heure="", confiance=None,
                              latence_ms=0, traitement_ms=0, fps=0.0, analyse_ms=0, age_image_ms=0)
            self.output_changed.notify_all()

    def capture(self):
        """This thread alone owns VideoCapture, including release/reconnection."""
        camera = None
        try:
            index = int(os.environ.get("CAMERA_INDEX", "0"))
            # AVFoundation n'existe que sur Mac ; sous Windows DirectShow ouvre la caméra
            # de façon fiable ; ailleurs on laisse OpenCV choisir.
            backends = {"darwin": cv2.CAP_AVFOUNDATION, "win32": cv2.CAP_DSHOW}
            backend = backends.get(sys.platform, cv2.CAP_ANY)
            while not self.stop.is_set():
                if camera is None:
                    camera = cv2.VideoCapture(index, backend)
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    camera.set(cv2.CAP_PROP_FPS, 30)
                    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # May be ignored by the device/backend.
                    if not camera.isOpened():
                        camera.release()
                        camera = None
                        self.capture_buffer.invalidate()
                        self.unavailable("Caméra indisponible. Nouvelle tentative dans 3 secondes.")
                        self.stop.wait(3)
                        continue
                    self.log("INFO", "Caméra connectée ; acquisition continue de la dernière image")
                start = time.perf_counter()
                ok, original = camera.read()
                captured_at = time.monotonic()
                if not ok:
                    self.log("ERREUR", "Caméra déconnectée ; reconnexion en cours")
                    self.capture_buffer.invalidate()
                    self.unavailable("Plus d'image caméra. Reconnexion en cours.")
                    camera.release()
                    camera = None
                    self.stop.wait(3)
                    continue
                self.capture_buffer.put(original, captured_at, (time.perf_counter() - start) * 1000)
        except Exception as error:
            self.capture_buffer.invalidate()
            self.unavailable(f"Erreur capture : {error}")
            self.log("ERREUR", str(error))
        finally:
            if camera is not None:
                camera.release()

    def run(self):
        capture_thread = None
        try:
            os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT.parent / ".venv" / "yolo-config"))
            model = YOLO(str(ROOT / "yolov8n.pt"))
            reader = QRVision()
            capture_thread = threading.Thread(target=self.capture, daemon=True)
            capture_thread.start()
            sequence = 0
            generation = -1
            published = deque()
            had_person = False
            last_presence_event = -10.0
            while not self.stop.is_set():
                packet = self.capture_buffer.read(sequence, self.stop)
                if packet is None:
                    continue
                sequence, packet_generation, original, captured_at, capture_ms = packet
                if time.monotonic() - captured_at > 0.5:
                    continue
                if generation != packet_generation:
                    generation = packet_generation
                    had_person = False
                    published.clear()
                start = time.perf_counter()
                image = cv2.resize(original, (640, 480))
                inference_start = time.perf_counter()
                result = model(image, classes=[0], conf=0.5, verbose=False)[0]
                latency = (time.perf_counter() - inference_start) * 1000
                boxes = result.boxes.xyxy.cpu().numpy().tolist()
                # Meilleure confiance de l'image : affichée par le dashboard (niveau de menace).
                confidence = round(float(result.boxes.conf.max()), 2) if boxes else None
                payloads, polygons = reader.read(original)
                if len(polygons):
                    polygons = polygons * (640 / original.shape[1], 480 / original.shape[0])
                observations = associate_codes(payloads, polygons, boxes, self.store)
                image = reader.annotate(image, boxes, observations)
                cv2.putText(image, f"Personnes : {len(boxes)} | YOLO : {latency:.0f} ms", (10, 470),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                encoded, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not encoded:
                    continue
                if self.stop.is_set() or not self.capture_buffer.current(generation):
                    continue
                detected = bool(boxes)
                clock = time.monotonic()
                if detected != had_person and clock - last_presence_event >= 2:
                    self.log("INFO", "Présence détectée" if detected else "Zone libre")
                    last_presence_event = clock
                    had_person = detected
                with self.lock:
                    # A disconnect must not be undone by an in-flight analysis.
                    if not self.capture_buffer.current(generation):
                        continue
                    self.frame = jpeg.tobytes()
                    self.last_frame_at = time.monotonic()
                    self.output_sequence += 1
                    published.append(self.last_frame_at)
                    while published and self.last_frame_at - published[0] > 2:
                        published.popleft()
                    fps = (len(published) - 1) / (published[-1] - published[0]) if len(published) > 1 else 0.0
                    analysis_ms = (time.perf_counter() - start) * 1000
                    self.state.update(detection=detected, personnes=len(boxes), latence_ms=round(latency),
                                      traitement_ms=round(capture_ms + analysis_ms), analyse_ms=round(analysis_ms),
                                      age_image_ms=round((time.monotonic() - captured_at) * 1000), fps=round(fps, 1),
                                      heure=datetime.now().strftime("%H:%M:%S"),
                                      timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
                                      camera_connected=True, badges=observations, error=None,
                                      confiance=confidence)
                    self.output_changed.notify_all()
                # Only fresh analyzed frames are published; no artificial 10 FPS limit.
        except Exception as error:
            self.unavailable(f"Erreur vision : {error}")
            self.log("ERREUR", str(error))
        finally:
            self.stop.set()
            if capture_thread is not None:
                capture_thread.join(timeout=5)
            if self.stop.is_set():
                with self.lock:
                    error = self.state.get("error")
                self.unavailable(error or "Service vision arrêté.")

    def images(self):
        placeholder = None
        sequence = -1
        sent_at = 0.0
        while not self.stop.is_set():
            self.stop.wait(max(0, 1 / 30 - (time.monotonic() - sent_at)))
            with self.output_changed:
                self.output_changed.wait_for(lambda: self.stop.is_set() or self.output_sequence != sequence, timeout=0.5)
                if self.stop.is_set():
                    break
                sequence = self.output_sequence
                frame = self.frame if time.monotonic() - self.last_frame_at <= 3 else None
            if frame is None:
                if placeholder is None:
                    import numpy as np
                    image = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(image, "Camera indisponible - reconnexion...", (25, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                    _, jpeg = cv2.imencode(".jpg", image)
                    placeholder = jpeg.tobytes()
                frame = placeholder
            sent_at = time.monotonic()
            yield (b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode()
                   + b"\r\n\r\n" + frame + b"\r\n")


def create_app(data_directory=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 3_100_000
    store = BadgeStore(data_directory or ROOT / ".data")
    runtime = VisionRuntime(store)
    app.extensions["badge_store"] = store
    app.extensions["vision"] = runtime
    app.register_blueprint(create_badge_api(store, lambda: runtime.snapshot(private=True)))

    @app.after_request
    def cors(response):
        from flask import request
        origins = os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if request.headers.get("Origin") in origins:
            response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        return response

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="Requête trop volumineuse. Photo de 2 Mo maximum."), 413

    @app.get("/video")
    def video():
        response = Response(runtime.images(), mimetype="multipart/x-mixed-replace; boundary=frame")
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Accel-Buffering"] = "no"
        return response

    @app.get("/status")
    def status():
        return jsonify(runtime.snapshot())

    @app.get("/logs")
    def logs():
        with runtime.lock:
            return jsonify(list(runtime.logs))

    return app


if __name__ == "__main__":
    app = create_app()
    runtime = app.extensions["vision"]
    thread = threading.Thread(target=runtime.run, daemon=True)
    thread.start()
    print(f"Clé superviseur : lire {ROOT / '.data' / 'admin-token.txt'} (ne pas partager).", flush=True)
    try:
        app.run(host=os.environ.get("CAMERA_HOST", "127.0.0.1"),
                port=int(os.environ.get("CAMERA_PORT", "5001")), threaded=True, use_reloader=False)
    finally:
        runtime.stop.set()
        thread.join(timeout=5)
