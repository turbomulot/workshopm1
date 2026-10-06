"""Local prototype badge registry. No biometric identification."""

import base64
import hashlib
import io
import secrets
import sqlite3
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import qrcode
from flask import Blueprint, jsonify, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError

PREFIX = "sentinel-x:badge:"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def prepare_photo(value):
    if not value:
        return None
    if not isinstance(value, str) or len(value) > 3_000_000:
        raise ValueError("Photo trop volumineuse (2 Mo maximum).")
    try:
        header, encoded = value.split(",", 1)
        if header not in {"data:image/jpeg;base64", "data:image/png;base64", "data:image/webp;base64"}:
            raise ValueError("Utiliser une photo JPEG, PNG ou WebP.")
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 2_000_000:
            raise ValueError("Photo trop volumineuse (2 Mo maximum).")
        with Image.open(io.BytesIO(raw)) as source:
            if source.width * source.height > 20_000_000:
                raise ValueError("Dimensions de photo trop grandes.")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((512, 512))
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as error:
        raise ValueError("Photo invalide : JPEG, PNG ou WebP, 2 Mo maximum.") from error


class BadgeStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "badges.sqlite3"
        self.lock = threading.RLock()
        self.recent = OrderedDict()
        key_path = self.directory / "admin-token.txt"
        if not key_path.exists():
            key_path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
        self.admin_token = key_path.read_text(encoding="utf-8").strip()
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS employees (
                    id TEXT PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
                    photo TEXT, active INTEGER NOT NULL DEFAULT 1,
                    badge_token TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                    employee_id TEXT, first_name TEXT, last_name TEXT,
                    result TEXT NOT NULL, source TEXT NOT NULL
                );
            """)

    def connect(self):
        # Context manager below closes connections as well as committing/rolling back.
        return Database(self.database)

    @staticmethod
    def public(row):
        return {key: (bool(row[key]) if key == "active" else row[key])
                for key in ("id", "first_name", "last_name", "photo", "active", "created_at")}

    def employees(self):
        with self.lock, self.connect() as db:
            return [self.public(row) for row in db.execute("SELECT * FROM employees ORDER BY created_at DESC, id")]

    def create(self, body):
        names = []
        for key in ("first_name", "last_name"):
            value = body.get(key)
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80 or any(ord(c) < 32 for c in value):
                raise ValueError("Nom et prénom obligatoires, de 1 à 80 caractères.")
            names.append(value.strip())
        employee_id = secrets.token_hex(12)
        photo = prepare_photo(body.get("photo"))
        with self.lock, self.connect() as db:
            db.execute("INSERT INTO employees VALUES (?, ?, ?, ?, 1, ?, ?)",
                       (employee_id, *names, photo, secrets.token_urlsafe(32), now()))
            return self.public(db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone())

    def update(self, employee_id, active=None, rotate=False):
        with self.lock, self.connect() as db:
            if not db.execute("SELECT id FROM employees WHERE id = ?", (employee_id,)).fetchone():
                return None
            if rotate:
                db.execute("UPDATE employees SET badge_token = ? WHERE id = ?", (secrets.token_urlsafe(32), employee_id))
            if active is not None:
                db.execute("UPDATE employees SET active = ? WHERE id = ?", (int(active), employee_id))
            return self.public(db.execute("SELECT * FROM employees WHERE id = ?", (employee_id,)).fetchone())

    def badge(self, employee_id):
        with self.lock, self.connect() as db:
            row = db.execute("SELECT badge_token FROM employees WHERE id = ?", (employee_id,)).fetchone()
            return PREFIX + row[0] if row else None

    def validate(self, payload, source="camera"):
        if not isinstance(payload, str) or len(payload) > 256:
            payload = ""
        token = payload[len(PREFIX):] if payload.startswith(PREFIX) else ""
        with self.lock, self.connect() as db:
            row = db.execute("SELECT * FROM employees WHERE badge_token = ?", (token,)).fetchone() if token else None
            result = "valid" if row and row["active"] else "disabled" if row else "unknown"
            employee = self.public(row) if row else None
            # Keep photo and badge secret out of the camera state/event log.
            if employee:
                employee.pop("photo")
            digest = hashlib.sha256(payload.encode()).hexdigest()
            event_key = (digest, result, source)
            clock = time.monotonic()
            if clock - self.recent.get(event_key, -100) >= 5:
                db.execute("""INSERT INTO events
                    (timestamp, employee_id, first_name, last_name, result, source)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (now(), row["id"] if row else None, row["first_name"] if row else None,
                     row["last_name"] if row else None, result, source))
                db.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 1000)")
                self.recent[event_key] = clock
                self.recent.move_to_end(event_key)
                if len(self.recent) > 256:
                    self.recent.popitem(last=False)
            return {"result": result, "employee": employee}

    def events(self):
        with self.lock, self.connect() as db:
            return [dict(row) for row in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")]


class Database:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row

    def __enter__(self):
        return self.db

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                self.db.commit()
            else:
                self.db.rollback()
        finally:
            self.db.close()


def create_badge_api(store, camera_status):
    api = Blueprint("badges", __name__)

    def protected(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if not token or not secrets.compare_digest(token.encode(), store.admin_token.encode()):
                return jsonify(error="Clé superviseur invalide ou absente."), 401
            return function(*args, **kwargs)
        return wrapper

    @api.get("/api/v1/employees")
    @protected
    def list_employees():
        return jsonify(store.employees())

    @api.post("/api/v1/employees")
    @protected
    def add_employee():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify(error="Objet JSON attendu."), 400
        try:
            return jsonify(store.create(body)), 201
        except ValueError as error:
            return jsonify(error=str(error)), 400

    @api.patch("/api/v1/employees/<employee_id>")
    @protected
    def set_active(employee_id):
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or type(body.get("active")) is not bool:
            return jsonify(error="Champ active booléen obligatoire."), 400
        employee = store.update(employee_id, active=body["active"])
        return (jsonify(employee), 200) if employee else (jsonify(error="Employé introuvable."), 404)

    @api.post("/api/v1/employees/<employee_id>/badge/rotate")
    @protected
    def rotate(employee_id):
        employee = store.update(employee_id, rotate=True)
        return (jsonify(employee), 200) if employee else (jsonify(error="Employé introuvable."), 404)

    @api.get("/api/v1/employees/<employee_id>/badge.png")
    @protected
    def download_badge(employee_id):
        payload = store.badge(employee_id)
        if not payload:
            return jsonify(error="Employé introuvable."), 404
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
        qr.add_data(payload)
        qr.make(fit=True)
        output = io.BytesIO()
        qr.make_image(fill_color="black", back_color="white").save(output, format="PNG")
        output.seek(0)
        return send_file(output, mimetype="image/png", as_attachment=True, download_name=f"badge-{employee_id}.png")

    @api.get("/api/v1/access/events")
    @protected
    def events():
        return jsonify(store.events())

    @api.get("/api/v1/access/status")
    @protected
    def status():
        return jsonify(camera_status())

    # Explicit manual test; never attaches a name to a person in the camera image.
    @api.post("/api/v1/badges/validate")
    @protected
    def validate():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or not isinstance(body.get("payload"), str) or len(body["payload"]) > 256:
            return jsonify(error="Champ payload texte attendu (256 caractères maximum)."), 400
        return jsonify(store.validate(body["payload"], source="manual"))

    @api.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"
        return response

    return api
