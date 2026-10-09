"""Run: ..\\.venv\\Scripts\\python.exe -m unittest test_badges -v

All records and images are synthetic and use temporary storage.
"""

import base64
import io
import tempfile
import time
import threading
import unittest
from unittest import mock

import cv2
import numpy as np
from PIL import Image

from badges import BadgeStore, PREFIX
from capture_buffer import CaptureBuffer
from qr_vision import QRVision, associate_codes
from stream_detection import create_app


class BadgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = create_app(self.tmp.name)
        self.store = self.app.extensions["badge_store"]
        self.client = self.app.test_client()
        self.headers = {"Authorization": f"Bearer {self.store.admin_token}"}

    def employee(self, first="Camille", last="Démo", **extra):
        response = self.client.post("/api/v1/employees", headers=self.headers,
                                    json={"first_name": first, "last_name": last, **extra})
        self.assertEqual(response.status_code, 201)
        return response.json

    def test_api_auth_validation_and_no_secret_in_registry(self):
        for method, path in [("GET", "/api/v1/employees"), ("POST", "/api/v1/employees"),
                             ("GET", "/api/v1/access/events"), ("GET", "/api/v1/access/status"),
                             ("POST", "/api/v1/badges/validate"), ("GET", "/api/v1/employees/no/badge.png")]:
            self.assertEqual(self.client.open(path, method=method).status_code, 401)
        self.assertEqual(self.client.post("/api/v1/employees", headers=self.headers, json=[]).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/employees", headers=self.headers,
                                         json={"first_name": " ", "last_name": "Test"}).status_code, 400)
        employee = self.employee()
        self.assertNotIn("badge_token", employee)
        self.assertNotIn("badge_token", self.client.get("/api/v1/employees", headers=self.headers).json[0])
        self.assertEqual(self.client.patch(f"/api/v1/employees/{employee['id']}", headers=self.headers,
                                          json={"active": "false"}).status_code, 400)
        self.assertEqual(self.client.patch("/api/v1/employees/missing", headers=self.headers,
                                          json={"active": False}).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/employees/missing/badge.png", headers=self.headers).status_code, 404)

    def test_revoke_rotate_deduplicate_and_persist(self):
        employee = self.employee()
        payload = self.store.badge(employee["id"])
        self.assertTrue(payload.startswith(PREFIX))
        self.assertEqual(self.store.validate(payload)["result"], "valid")
        self.store.validate(payload)
        self.assertEqual(len(self.store.events()), 1)
        self.client.patch(f"/api/v1/employees/{employee['id']}", headers=self.headers, json={"active": False})
        self.assertEqual(self.store.validate(payload)["result"], "disabled")
        self.client.patch(f"/api/v1/employees/{employee['id']}", headers=self.headers, json={"active": True})
        self.client.post(f"/api/v1/employees/{employee['id']}/badge/rotate", headers=self.headers)
        self.assertEqual(self.store.validate(payload)["result"], "unknown")
        new = self.store.badge(employee["id"])
        self.assertNotEqual(payload, new)
        self.assertEqual(self.store.validate(new)["result"], "valid")
        reopened = BadgeStore(self.tmp.name)
        self.assertEqual(reopened.admin_token, self.store.admin_token)
        self.assertEqual(reopened.badge(employee["id"]), new)
        self.assertEqual(len(reopened.employees()), 1)
        self.assertNotIn(new, str(reopened.events()))

    def test_photo_normalization_and_bad_input(self):
        buffer = io.BytesIO()
        Image.new("RGB", (800, 600), "blue").save(buffer, "PNG")
        photo = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
        employee = self.employee(photo=photo)
        self.assertTrue(employee["photo"].startswith("data:image/jpeg;base64,"))
        image = Image.open(io.BytesIO(base64.b64decode(employee["photo"].split(",")[1])))
        self.assertLessEqual(max(image.size), 512)
        self.assertEqual(self.client.post("/api/v1/employees", headers=self.headers,
                                         json={"first_name": "Test", "last_name": "Test", "photo": "bad"}).status_code, 400)

    def test_generated_qr_can_be_decoded_and_validated(self):
        employee = self.employee()
        response = self.client.get(f"/api/v1/employees/{employee['id']}/badge.png", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        image = cv2.imdecode(np.frombuffer(response.data, np.uint8), cv2.IMREAD_COLOR)
        payloads, points = QRVision().read(image)
        self.assertEqual(list(payloads), [self.store.badge(employee["id"])])
        result = self.client.post("/api/v1/badges/validate", headers=self.headers, json={"payload": payloads[0]})
        self.assertEqual(result.json["result"], "valid")
        self.assertEqual(self.store.events()[0]["source"], "manual")

    def test_two_people_overlap_duplicates_and_disappearance(self):
        a, b = self.employee(), self.employee("Alex", "Exemple")
        payloads = [self.store.badge(a["id"]), self.store.badge(b["id"])]
        points = np.array([[[20, 20], [40, 20], [40, 40], [20, 40]],
                           [[220, 20], [240, 20], [240, 40], [220, 40]]])
        boxes = [[0, 0, 100, 200], [200, 0, 300, 200]]
        result = associate_codes(payloads, points, boxes, self.store)
        self.assertEqual([item["person_index"] for item in result], [0, 1])
        overlap = associate_codes([payloads[0]], points[:1], [[0, 0, 100, 200], [35, 0, 200, 200]], self.store)
        self.assertEqual(overlap[0]["association"], "unassigned")
        copies = associate_codes([payloads[0]] * 2, points, boxes, self.store)
        self.assertTrue(all(item["person_index"] is None for item in copies))
        both_one_person = associate_codes(payloads, points, [[0, 0, 400, 300]], self.store)
        self.assertTrue(all(item["person_index"] is None for item in both_one_person))
        self.assertEqual(associate_codes([], [], boxes, self.store), [])
        rendered = QRVision().annotate(np.zeros((480, 640, 3), np.uint8), boxes, result)
        self.assertEqual(rendered.shape, (480, 640, 3))

    def test_multiple_qr_in_one_frame(self):
        a, b = self.employee(), self.employee("Alex", "Exemple")
        images = []
        for employee in (a, b):
            png = self.client.get(f"/api/v1/employees/{employee['id']}/badge.png", headers=self.headers).data
            image = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
            images.append(cv2.resize(image, (350, 350), interpolation=cv2.INTER_NEAREST))
        canvas = np.full((700, 1400, 3), 255, np.uint8)
        canvas[175:525, 100:450], canvas[175:525, 950:1300] = images
        decoded, polygons = QRVision().read(canvas)
        self.assertEqual(set(decoded), {self.store.badge(a["id"]), self.store.badge(b["id"])})
        # Preview scanning must return original-space geometry for attribution.
        centers = sorted(np.mean(points, axis=0)[0] for points in polygons)
        self.assertAlmostEqual(centers[0], 275, delta=10)
        self.assertAlmostEqual(centers[1], 1125, delta=10)

    def test_camera_state_is_reset_and_import_does_not_open_camera(self):
        runtime = self.app.extensions["vision"]
        self.assertFalse(runtime.snapshot()["camera_connected"])
        runtime.state.update(camera_connected=True, personnes=2, detection=True, badges=[{"result": "valid"}])
        runtime.frame = b"old-frame"
        runtime.unavailable("Test panne")
        public = self.client.get("/status").json
        self.assertFalse(public["camera_connected"])
        self.assertFalse(public["detection"])
        self.assertNotIn("badges", public)
        self.assertEqual(runtime.snapshot(private=True)["badges"], [])
        self.assertIsNone(runtime.frame)

    def test_stalled_camera_does_not_report_old_badge_as_current(self):
        runtime = self.app.extensions["vision"]
        runtime.state.update(camera_connected=True, personnes=1, detection=True, badges=[{"result": "valid"}])
        runtime.last_frame_at = time.monotonic() - 10
        status = runtime.snapshot(private=True)
        self.assertFalse(status["camera_connected"])
        self.assertEqual(status["badges"], [])

    def test_capture_skips_backlog_and_invalidates_previous_connection(self):
        buffer = CaptureBuffer()
        stop = threading.Event()
        buffer.put("old-image", time.monotonic(), 5)
        first = buffer.read(0, stop)
        buffer.put("middle-image", time.monotonic(), 5)
        buffer.put("latest-image", time.monotonic(), 5)
        latest = buffer.read(first[0], stop)
        self.assertEqual(latest[2], "latest-image")
        self.assertGreater(latest[0], first[0] + 1)
        buffer.invalidate()
        self.assertFalse(buffer.current(latest[1]))
        buffer.put("reconnected-image", time.monotonic(), 5)
        renewed = buffer.read(latest[0], stop)
        self.assertNotEqual(renewed[1], latest[1])
        self.assertTrue(buffer.current(renewed[1]))
        stop.set()
        self.assertIsNone(buffer.read(0, stop))

    def test_camera_selection_is_protected_validated_and_saved(self):
        self.assertEqual(self.client.get("/api/v1/cameras").status_code, 401)
        self.assertEqual(self.client.put("/api/v1/camera", json={"index": 1}).status_code, 401)
        runtime = self.app.extensions["vision"]
        with mock.patch("stream_detection.camera_names", return_value=["HP 5MP Camera", "USB Camera"]):
            cameras = self.client.get("/api/v1/cameras", headers=self.headers).json
            self.assertEqual([(c["name"], c["current"]) for c in cameras], [("HP 5MP Camera", True), ("USB Camera", False)])
            for bad in ({"index": "1"}, {"index": -1}, {"index": 99}, {"index": True}, []):
                self.assertEqual(self.client.put("/api/v1/camera", headers=self.headers, json=bad).status_code, 400)
            self.assertFalse(runtime.camera_switch.is_set())
            cameras = self.client.put("/api/v1/camera", headers=self.headers, json={"index": 1}).json
            self.assertTrue(cameras[1]["current"])
            self.assertTrue(runtime.camera_switch.is_set())
            self.assertFalse(runtime.snapshot()["camera_connected"])
        self.assertEqual(create_app(self.tmp.name).extensions["vision"].camera_index, 1)

    def test_stream_yields_new_frame_without_100ms_sleep(self):
        runtime = self.app.extensions["vision"]
        runtime.frame = b"first-jpeg"
        runtime.last_frame_at = time.monotonic()
        stream = runtime.images()
        self.addCleanup(stream.close)
        self.assertIn(b"first-jpeg", next(stream))
        with runtime.output_changed:
            runtime.frame = b"next-jpeg"
            runtime.last_frame_at = time.monotonic()
            runtime.output_sequence += 1
            runtime.output_changed.notify_all()
        start = time.perf_counter()
        self.assertIn(b"next-jpeg", next(stream))
        # One stream interval is ~33 ms. A 100 ms cap would fail this regression.
        self.assertLess(time.perf_counter() - start, 0.09)


if __name__ == "__main__":
    unittest.main()
