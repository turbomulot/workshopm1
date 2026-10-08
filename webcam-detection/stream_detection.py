"""Single camera owner: person detection, QR validation, face recognition and local Flask API."""

import copy
import functools
import json
import os
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

# Must precede the torch import: idle OpenMP workers otherwise spin between
# YOLO frames and starve the main loop and the face thread.
os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
os.environ.setdefault("KMP_BLOCKTIME", "0")

import cv2
import paho.mqtt.client as mqtt
import torch
from flask import Flask, Response, jsonify
from ultralytics import YOLO

from badges import BadgeStore, create_badge_api, require_admin
from capture_buffer import CaptureBuffer
from faces import FaceRecognizer, annotate_faces, authenticated_people, create_face_api
from qr_vision import QRVision, associate_codes

ROOT = Path(__file__).resolve().parent
# AVFoundation n'existe que sur Mac ; sous Windows DirectShow ouvre la caméra
# de façon fiable ; ailleurs on laisse OpenCV choisir.
CAMERA_BACKEND = {"darwin": cv2.CAP_AVFOUNDATION, "win32": cv2.CAP_DSHOW}.get(sys.platform, cv2.CAP_ANY)
MAX_CAMERAS = 6
RENDER_FPS = float(os.environ.get("RENDER_FPS", "20"))

# Link with the ESP8266 box: its PIR (<base>/sensors, field "pir") wakes the camera,
# and a passed face check turns its LED green (<base>/vision).
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_BASE_TOPIC = os.environ.get("MQTT_BASE_TOPIC", "sentinel").rstrip("/")
# Camera released after this long without PIR motion or person seen; 0 keeps it always on.
STANDBY_SECONDS = float(os.environ.get("CAMERA_STANDBY_S", "30"))
# The box forgets a recognition when its presence ends: repeated while it lasts.
RECOGNISED_REPEAT = 5.0
# The box's OLED drops the face check after 2.5 s without news: repeated every second.
CHECK_REPEAT = 1.0


def check_message(view):
    """Face check as the box's OLED shows it: the current step, then the result."""
    if not view:
        return None
    if view["state"] == "running":
        return {"verification": view["steps"][view["step"] - 1]["key"], "etape": view["step"],
                "total": view["total"], "restant": view["remaining_s"]}
    return {"verification": view["state"]}


@functools.lru_cache(maxsize=None)
def placeholder(text):
    import numpy as np
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(image, text, (25, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    return cv2.imencode(".jpg", image)[1].tobytes()


def camera_names():
    """DirectShow names, in the same order as OpenCV indexes; None if unknown."""
    if sys.platform != "win32":
        return None
    try:
        import comtypes
        from pygrabber.dshow_graph import FilterGraph
    except ImportError:
        return None
    # Flask answers in worker threads, where COM is not initialised by default.
    comtypes.CoInitialize()
    try:
        return FilterGraph().get_input_devices()[:MAX_CAMERAS]
    except Exception:
        return None
    finally:
        comtypes.CoUninitialize()


class VisionRuntime:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.camera_file = store.directory / "camera.txt"
        saved = self.camera_file.read_text(encoding="utf-8").strip() if self.camera_file.exists() else ""
        self.camera_index = int(saved) if saved.isdigit() else int(os.environ.get("CAMERA_INDEX", "0"))
        self.camera_switch = threading.Event()
        self.frame = None
        self.overlay = None   # latest analysis drawn by render(): boxes, badges, YOLO latency
        self.last_frame_at = 0.0
        self.output_sequence = 0
        self.output_changed = threading.Condition(self.lock)
        self.capture_buffer = CaptureBuffer()
        self.log_id = 0
        self.logs = deque(maxlen=50)
        self.state = {"detection": False, "personnes": 0, "latence_ms": 0,
                      "traitement_ms": 0, "heure": "", "camera_connected": False,
                      "timestamp": None, "badges": [], "error": None, "fps": 0.0,
                      "analyse_ms": 0, "age_image_ms": 0, "confiance": None, "veille": False}
        self.faces = FaceRecognizer(store, self.log)
        self.last_presence = None  # monotonic time of the last PIR motion or person seen
        self.mqtt = None
        self.mqtt_connected = False

    def snapshot(self, private=False):
        with self.lock:
            state = copy.deepcopy(self.state)
            stale = state["camera_connected"] and time.monotonic() - self.last_frame_at > 3
            if stale:
                state.update(camera_connected=False, detection=False, personnes=0, badges=[],
                             error="Analyse caméra interrompue : image périmée.", timestamp=None, fps=0.0)
        state.update(self.faces.snapshot())
        if stale or not state["camera_connected"]:
            state["faces"] = []
        # Names (badges, faces, check result) only through the supervisor route.
        return state if private else {k: v for k, v in state.items() if k not in ("badges", "faces", "face_check")}

    def log(self, level, message):
        with self.lock:
            self.log_id += 1
            line = {"id": self.log_id, "heure": datetime.now().strftime("%H:%M:%S"),
                    "niveau": level, "message": message}
            self.logs.append(line)
        print(f"[{line['heure']}] {level} : {message}", flush=True)

    def start_mqtt(self):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = self.on_mqtt_connect
        client.on_disconnect = lambda *args: setattr(self, "mqtt_connected", False)
        client.on_message = self.on_mqtt_message
        # Connection and reconnections happen in paho's own thread.
        client.connect_async(MQTT_HOST, MQTT_PORT)
        client.loop_start()
        self.mqtt = client

    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            return
        client.subscribe(f"{MQTT_BASE_TOPIC}/sensors")
        self.mqtt_connected = True
        self.log("INFO", f"Broker MQTT connecté ({MQTT_HOST}:{MQTT_PORT}) : caméra pilotée par le PIR")

    def on_mqtt_message(self, client, userdata, message):
        try:
            measure = json.loads(message.payload)
        except ValueError:
            return
        if isinstance(measure, dict) and measure.get("pir") == 1:
            self.last_presence = time.monotonic()

    def camera_wanted(self):
        """Without the broker, or with standby disabled, the camera stays on as before."""
        if STANDBY_SECONDS <= 0 or not self.mqtt_connected:
            return True
        return self.last_presence is not None and time.monotonic() - self.last_presence < STANDBY_SECONDS

    def report_to_box(self):
        """Sends the box the face check steps (OLED) and whether the face in front of the
        camera passed a check in the last 30 min (green LED) or not (red). No name is sent."""
        last_recognised, was_recognised = 0.0, None
        last_check, last_check_at = None, 0.0
        while not self.stop.wait(0.2):
            if not self.mqtt_connected:
                continue
            now = time.monotonic()
            # None (no face in view, e.g. head turned) keeps the box's last answer.
            recognised = self.faces.main_face_authenticated()
            if recognised is not None and (recognised != was_recognised or now - last_recognised >= RECOGNISED_REPEAT):
                self.publish_vision({"reconnu": recognised})
                last_recognised, was_recognised = now, recognised
            check = check_message(self.faces.snapshot()["face_check"])
            if check and (check != last_check or now - last_check_at >= CHECK_REPEAT):
                self.publish_vision(check)
                last_check_at = now
            last_check = check

    def publish_vision(self, message):
        self.mqtt.publish(f"{MQTT_BASE_TOPIC}/vision", json.dumps(message))

    def unavailable(self, message):
        with self.lock:
            self.frame = None
            self.output_sequence += 1
            self.state.update(camera_connected=False, detection=False, personnes=0,
                              badges=[], error=message, timestamp=None, heure="", confiance=None,
                              latence_ms=0, traitement_ms=0, fps=0.0, analyse_ms=0, age_image_ms=0)
            self.output_changed.notify_all()

    def cameras(self):
        with self.lock:
            current = self.camera_index
        names = camera_names()
        if names is not None:
            found = list(enumerate(names))
        else:
            # No device list on this system: probe the indexes, except the one in use.
            found = []
            for index in range(MAX_CAMERAS):
                probe = None if index == current else cv2.VideoCapture(index, CAMERA_BACKEND)
                if probe is None or probe.isOpened():
                    found.append((index, f"Caméra {index + 1}"))
                if probe is not None:
                    probe.release()
        cameras = [{"index": index, "name": name, "current": index == current} for index, name in found]
        if not any(camera["current"] for camera in cameras):
            cameras.append({"index": current, "name": f"Caméra {current + 1} (non détectée)", "current": True})
        return cameras

    def select_camera(self, index):
        with self.lock:
            changed = index != self.camera_index
            self.camera_index = index
        self.camera_file.write_text(str(index), encoding="utf-8")
        if changed:
            self.log("INFO", f"Changement de caméra : caméra {index + 1}")
            self.unavailable("Changement de caméra en cours.")
            self.camera_switch.set()

    def capture(self):
        """This thread alone owns VideoCapture, including release/reconnection."""
        camera = None
        asleep = False
        try:
            while not self.stop.is_set():
                if not self.camera_wanted():
                    if not asleep:
                        if camera is not None:
                            camera.release()
                            camera = None
                            self.log("INFO", f"Caméra en veille ({STANDBY_SECONDS:.0f} s sans présence)")
                        self.capture_buffer.invalidate()
                        self.unavailable("Caméra en veille : aucune présence détectée.")
                        with self.lock:
                            self.state["veille"] = True
                        asleep = True
                    # Not camera_switch.wait: a pending switch would make it return at once.
                    self.stop.wait(0.2)
                    continue
                if asleep:
                    asleep = False
                    with self.lock:
                        self.state["veille"] = False
                    self.log("INFO", "Mouvement détecté : caméra allumée")
                if self.camera_switch.is_set():
                    self.camera_switch.clear()
                    if camera is not None:
                        camera.release()
                        camera = None
                    self.capture_buffer.invalidate()
                if camera is None:
                    with self.lock:
                        index = self.camera_index
                    camera = cv2.VideoCapture(index, CAMERA_BACKEND)
                    # Compressed MJPG keeps 1280x720 at full rate on USB webcams (YUY2 often drops to 5-10 fps).
                    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    camera.set(cv2.CAP_PROP_FPS, 30)
                    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # May be ignored by the device/backend.
                    if not camera.isOpened():
                        camera.release()
                        camera = None
                        self.capture_buffer.invalidate()
                        self.unavailable(f"Caméra {index + 1} indisponible. Nouvelle tentative dans 3 secondes.")
                        self.camera_switch.wait(3)
                        continue
                    self.log("INFO", f"Caméra {index + 1} connectée ; acquisition continue de la dernière image")
                start = time.perf_counter()
                ok, original = camera.read()
                captured_at = time.monotonic()
                if not ok:
                    self.log("ERREUR", "Caméra déconnectée ; reconnexion en cours")
                    self.capture_buffer.invalidate()
                    self.unavailable("Plus d'image caméra. Reconnexion en cours.")
                    camera.release()
                    camera = None
                    self.camera_switch.wait(3)
                    continue
                self.capture_buffer.put(original, captured_at, (time.perf_counter() - start) * 1000)
        except Exception as error:
            self.capture_buffer.invalidate()
            self.unavailable(f"Erreur capture : {error}")
            self.log("ERREUR", str(error))
        finally:
            if camera is not None:
                camera.release()

    def render(self, reader):
        """Publishes every camera frame at once, drawn with the latest analysis.

        Analysis (YOLO, QR, faces) runs at its own pace: boxes may trail a moving
        person by one analysis, but the video itself is no longer delayed by it.
        """
        sequence, generation, sent_at = 0, -1, 0.0
        published = deque()
        while not self.stop.is_set():
            packet = self.capture_buffer.read(sequence, self.stop)
            if packet is None:
                continue
            sequence, packet_generation, original, captured_at, _ = packet
            if packet_generation != generation:
                generation = packet_generation
                published.clear()
            if time.monotonic() - sent_at < 1 / RENDER_FPS:
                continue
            with self.lock:
                overlay = self.overlay
            fresh = overlay and overlay["generation"] == generation and time.monotonic() - overlay["at"] < 1.0
            boxes, observations = (overlay["boxes"], overlay["observations"]) if fresh else ([], [])
            image = cv2.resize(original, (640, 480))
            faces, check = self.faces.overlay(generation)
            scale = (640 / original.shape[1], 480 / original.shape[0])
            image = reader.annotate(image, boxes, observations, authenticated_people(boxes, faces, scale))
            image = annotate_faces(image, faces, check, scale, reader.font)
            if fresh:
                cv2.putText(image, f"Personnes : {len(boxes)} | YOLO : {overlay['latency']:.0f} ms", (10, 470),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            encoded, jpeg = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not encoded:
                continue
            with self.lock:
                if self.stop.is_set() or not self.capture_buffer.current(generation):
                    continue
                sent_at = self.last_frame_at = time.monotonic()
                self.frame = jpeg.tobytes()
                self.output_sequence += 1
                published.append(sent_at)
                while published and sent_at - published[0] > 2:
                    published.popleft()
                fps = (len(published) - 1) / (published[-1] - published[0]) if len(published) > 1 else 0.0
                self.state.update(fps=round(fps, 1), age_image_ms=round((sent_at - captured_at) * 1000))
                self.output_changed.notify_all()

    def run(self):
        capture_thread = face_thread = render_thread = report_thread = None
        try:
            self.start_mqtt()
            os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT.parent / ".venv" / "yolo-config"))
            # torch defaults to one thread per core; with the face thread beside it,
            # 4 is faster on hybrid laptop CPUs (YOLO 140 -> 65 ms on a Core Ultra 7 155U).
            torch.set_num_threads(int(os.environ.get("YOLO_THREADS", "4")))
            model = YOLO(str(ROOT / "yolov8n.pt"))
            reader = QRVision()
            capture_thread = threading.Thread(target=self.capture, daemon=True)
            capture_thread.start()
            face_thread = threading.Thread(target=self.faces.run, args=(self.capture_buffer, self.stop), daemon=True)
            face_thread.start()
            render_thread = threading.Thread(target=self.render, args=(reader,), daemon=True)
            render_thread.start()
            report_thread = threading.Thread(target=self.report_to_box, daemon=True)
            report_thread.start()
            sequence = 0
            generation = -1
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
                if self.stop.is_set() or not self.capture_buffer.current(generation):
                    continue
                detected = bool(boxes)
                clock = time.monotonic()
                if detected:
                    self.last_presence = clock
                if detected != had_person and clock - last_presence_event >= 2:
                    self.log("INFO", "Présence détectée" if detected else "Zone libre")
                    last_presence_event = clock
                    had_person = detected
                with self.lock:
                    # A disconnect must not be undone by an in-flight analysis.
                    if not self.capture_buffer.current(generation):
                        continue
                    self.overlay = {"generation": generation, "at": time.monotonic(), "boxes": boxes,
                                    "observations": observations, "latency": latency}
                    analysis_ms = (time.perf_counter() - start) * 1000
                    self.state.update(detection=detected, personnes=len(boxes), latence_ms=round(latency),
                                      traitement_ms=round(capture_ms + analysis_ms), analyse_ms=round(analysis_ms),
                                      heure=datetime.now().strftime("%H:%M:%S"),
                                      timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
                                      camera_connected=True, badges=observations, error=None,
                                      confiance=confidence)
        except Exception as error:
            self.unavailable(f"Erreur vision : {error}")
            self.log("ERREUR", str(error))
        finally:
            self.stop.set()
            if self.mqtt is not None:
                self.mqtt.loop_stop()
            for thread in (capture_thread, face_thread, render_thread, report_thread):
                if thread is not None:
                    thread.join(timeout=5)
            if self.stop.is_set():
                with self.lock:
                    error = self.state.get("error")
                self.unavailable(error or "Service vision arrêté.")

    def images(self):
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
                asleep = self.state["veille"]
            if frame is None:
                frame = placeholder("Camera en veille - en attente du PIR" if asleep
                                    else "Camera indisponible - reconnexion...")
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
    app.register_blueprint(create_face_api(store, runtime.faces))

    @app.after_request
    def cors(response):
        from flask import request
        origins = os.environ.get("FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if request.headers.get("Origin") in origins:
            response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="Requête trop volumineuse. Photo de 2 Mo maximum."), 413

    protected = require_admin(store)

    @app.get("/api/v1/cameras")
    @protected
    def list_cameras():
        return jsonify(runtime.cameras())

    @app.put("/api/v1/camera")
    @protected
    def select_camera():
        from flask import request
        body = request.get_json(silent=True)
        index = body.get("index") if isinstance(body, dict) else None
        if type(index) is not int or not 0 <= index < MAX_CAMERAS:
            return jsonify(error=f"Champ index entier de 0 à {MAX_CAMERAS - 1} attendu."), 400
        runtime.select_camera(index)
        return jsonify(runtime.cameras())

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
