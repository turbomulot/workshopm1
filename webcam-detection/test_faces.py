"""Run: ..\\.venv\\Scripts\\python.exe -m unittest test_faces -v

Synthetic faces only: no model, camera or real biometric data.
"""

import tempfile
import time
import unittest
from unittest import mock

import numpy as np

import faces
from qr_vision import QRVision
from stream_detection import create_app


def embedding(seed):
    vector = np.random.default_rng(seed).normal(size=512).astype(np.float32)
    return vector / np.linalg.norm(vector)


class FakeFace:
    """Same attributes as insightface's Face for what faces.py reads.
    turn > 0 = head turned to the person's left; chin > 0 = chin up."""

    def __init__(self, seed, turn=0.0, chin=0.0, left=100):
        self.embedding = self.normed_embedding = embedding(seed)
        self.bbox = np.array([left, 80, left + 60, 160], dtype=np.float32)
        self.kps = np.array([[100, 100], [140, 100], [120 + turn * 40, 120 - chin * 40], [105, 140], [135, 140]],
                            dtype=np.float32)


FRONT = FakeFace(1)
GESTURES = [FakeFace(1, turn=0.3)] * 2 + [FakeFace(1, turn=-0.3)] * 2 + [FakeFace(1, chin=0.15)] * 2
# After an automatic start one more frontal frame completes the reference pose.
LIVE = [FRONT] + GESTURES + [FRONT] * 2


class FaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = create_app(self.tmp.name)
        self.store = self.app.extensions["badge_store"]
        self.faces = self.app.extensions["vision"].faces
        self.faces.set_engine("ready", "Reconnaissance faciale active.")
        self.client = self.app.test_client()
        self.headers = {"Authorization": f"Bearer {self.store.admin_token}"}

    def employee(self, first="Camille", last="Démo"):
        return self.client.post("/api/v1/employees", headers=self.headers,
                                json={"first_name": first, "last_name": last}).json

    def show(self, *visible):
        self.faces.publish(list(visible), np.zeros((360, 640, 3), np.uint8), 1.0, 0)

    def enroll(self, employee, seed):
        self.show(FakeFace(seed))
        return self.client.post(f"/api/v1/employees/{employee['id']}/faces", headers=self.headers)

    def status(self):
        return self.client.get("/api/v1/access/status", headers=self.headers).json

    def test_routes_are_protected_and_public_status_hides_names(self):
        for method, path in [("POST", "/api/v1/employees/x/faces"), ("DELETE", "/api/v1/employees/x/faces"),
                             ("POST", "/api/v1/faces/check")]:
            self.assertEqual(self.client.open(path, method=method).status_code, 401)
        camille = self.employee()
        self.enroll(camille, 1)
        self.show(FakeFace(1))
        public = self.client.get("/status").json
        self.assertNotIn("faces", public)
        self.assertNotIn("face_check", public)
        self.assertEqual(public["face_engine"]["state"], "ready")

    def test_enrol_requires_one_fresh_face_and_refuses_another_employee_face(self):
        camille, alex = self.employee(), self.employee("Alex", "Exemple")
        url = f"/api/v1/employees/{camille['id']}/faces"
        self.assertEqual(self.client.post(url, headers=self.headers).status_code, 409)
        self.show()
        self.assertIn("Aucun visage", self.client.post(url, headers=self.headers).json["error"])
        self.show(FakeFace(1), FakeFace(2, left=300))
        self.assertIn("seule personne", self.client.post(url, headers=self.headers).json["error"])
        response = self.enroll(camille, 1)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["faces"], 1)
        refused = self.enroll(alex, 1)
        self.assertEqual(refused.status_code, 409)
        self.assertIn("Camille Démo", refused.json["error"])
        self.assertEqual(self.enroll({"id": "missing"}, 3).status_code, 404)
        self.faces.latest = (time.monotonic() - 5, [embedding(4)])
        self.assertIn("récente", self.client.post(f"/api/v1/employees/{alex['id']}/faces", headers=self.headers).json["error"])

    def test_engine_not_ready_and_erase(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.assertEqual(self.store.employees()[0]["faces"], 1)
        erased = self.client.delete(f"/api/v1/employees/{camille['id']}/faces", headers=self.headers)
        self.assertEqual(erased.json["faces"], 0)
        self.assertEqual(self.store.face_gallery(), {})
        self.faces.set_engine("unavailable", "InsightFace non installé")
        self.assertEqual(self.enroll(camille, 1).status_code, 503)
        self.assertEqual(self.client.post("/api/v1/faces/check", headers=self.headers).status_code, 503)

    def test_embeddings_of_another_pack_are_ignored(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.store.face_model = "buffalo_l"
        self.assertEqual(self.store.face_gallery(), {})
        self.assertEqual(self.store.employees()[0]["faces"], 0)

    def start_manual_check(self):
        self.assertEqual(self.client.post("/api/v1/faces/check", headers=self.headers).status_code, 202)
        for _ in range(faces.STABLE_NEEDED):
            self.show(FRONT)
        return self.faces.snapshot()["face_check"]

    def test_steps_run_in_order_with_checklist_then_access_granted(self):
        camille = self.employee()
        self.enroll(camille, 1)
        check = self.start_manual_check()
        self.assertEqual(self.client.post("/api/v1/faces/check", headers=self.headers).status_code, 409)
        self.assertEqual((check["state"], check["step"], check["total"]), ("running", 2, len(faces.STEPS)))
        self.assertEqual([step["state"] for step in check["steps"]], ["done", "current", "pending", "pending", "pending"])
        # Out of order: chin up and right turn do nothing during the left-turn step.
        for face in [FakeFace(1, chin=0.15)] * 2 + [FakeFace(1, turn=-0.3)] * 2:
            self.show(face)
        self.assertEqual(self.faces.snapshot()["face_check"]["step"], 2)
        # One frame is not enough: the gesture must hold.
        self.show(FakeFace(1, turn=0.3))
        self.show(FRONT)
        self.assertEqual(self.faces.snapshot()["face_check"]["step"], 2)
        for face in GESTURES:
            self.show(face)
        check = self.faces.snapshot()["face_check"]
        self.assertEqual((check["step"], check["instruction"]), (5, faces.STEPS[4][2]))
        self.show(FRONT)
        self.show(FRONT)
        result = self.status()["face_check"]
        self.assertEqual(result["state"], "valid")
        self.assertIn("Camille Démo", result["message"])
        self.assertTrue(all(step["state"] == "done" for step in result["steps"]))
        event = self.store.events()[0]
        self.assertEqual((event["source"], event["result"], event["employee_id"]), ("face", "valid", camille["id"]))

    def test_disabled_employee_is_not_granted(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.client.patch(f"/api/v1/employees/{camille['id']}", headers=self.headers, json={"active": False})
        self.faces.reload()
        self.start_manual_check()
        for face in GESTURES + [FRONT] * 2:
            self.show(face)
        self.assertEqual(self.status()["face_check"]["state"], "disabled")

    def test_still_photo_fails_at_the_first_gesture(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.start_manual_check()
        for _ in range(10):
            self.show(FRONT)
        with self.faces.lock:
            finished = self.faces.advance(None, time.monotonic() + faces.CHALLENGE_TIMEOUT + 1)
        self.assertEqual(finished[1], "refused")
        self.assertIn("Tête à gauche", finished[2])
        result = self.faces.snapshot()["face_check"]
        self.assertEqual(result["state"], "refused")
        self.assertEqual([step["state"] for step in result["steps"]], ["done", "failed", "pending", "pending", "pending"])

    def test_tilted_photo_does_not_count_as_a_head_turn(self):
        # A flat photo shifted or scaled keeps every ratio: still the frontal pose.
        tilted = FakeFace(1)
        tilted.kps = tilted.kps * (0.7, 1.0) + (40, 10)
        self.assertFalse(faces.gesture_done("left", faces.pose(tilted), faces.pose(FRONT)))
        self.assertFalse(faces.gesture_done("up", faces.pose(tilted), faces.pose(FRONT)))

    def test_unknown_face_is_refused_after_search_timeout(self):
        self.enroll(self.employee(), 1)
        self.client.post("/api/v1/faces/check", headers=self.headers)
        self.show(FakeFace(99))
        with self.faces.lock:
            finished = self.faces.advance(None, time.monotonic() + faces.SEARCH_TIMEOUT + 1)
        self.assertEqual(finished, (None, "refused", "Aucun visage enregistré reconnu."))

    def auto_start(self, seed=1):
        for _ in range(faces.STABLE_NEEDED):
            self.show(FakeFace(seed))
        return self.faces.snapshot()["face_check"]

    def test_recognised_face_starts_check_and_authenticates_without_badge(self):
        camille = self.employee()
        self.enroll(camille, 1)
        for _ in range(faces.STABLE_NEEDED - 1):
            self.show(FakeFace(1))
        self.assertIsNone(self.faces.snapshot()["face_check"])
        self.faces.stable = (None, 0)
        check = self.auto_start()
        self.assertEqual((check["state"], check["auto"]), ("running", True))
        for face in LIVE:
            self.show(face)
        self.assertEqual(self.status()["face_check"]["state"], "valid")
        self.assertEqual(self.store.events()[0]["source"], "face")
        self.show(FakeFace(1), FakeFace(99, left=300))
        self.assertEqual([face["authenticated"] for face in self.faces.snapshot()["faces"]], [True, False])
        # No new check while authenticated.
        self.auto_start()
        self.assertEqual(self.faces.snapshot()["face_check"]["state"], "valid")
        people = faces.authenticated_people([[0, 0, 250, 400], [280, 0, 400, 400]], self.faces.faces, (1, 1))
        self.assertEqual(people, {0: "Camille Démo"})
        image = QRVision().annotate(np.zeros((480, 640, 3), np.uint8), [[0, 0, 250, 400]], [], people)
        self.assertEqual(image.shape, (480, 640, 3))

    def test_authentication_expires_and_needs_a_new_liveness_check(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.auto_start()
        for face in LIVE:
            self.show(face)
        # Out of view, the authentication holds: the same face is recognised without gestures.
        self.show()
        self.show(FakeFace(1))
        self.assertTrue(self.faces.main_face_authenticated())
        self.faces.authenticated[camille["id"]]["since"] -= faces.AUTH_MAX + 1
        self.show()
        self.assertEqual(self.faces.authenticated, {})
        self.faces.result = None
        self.show(FakeFace(1))
        self.assertFalse(self.faces.snapshot()["faces"][0]["authenticated"])
        self.faces.stable = (None, 0)
        self.assertEqual(self.auto_start()["state"], "running")

    def test_other_person_is_not_green_and_needs_their_own_check(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.auto_start()
        for face in LIVE:
            self.show(face)
        self.faces.result = None
        self.show(FakeFace(1))
        self.assertTrue(self.faces.main_face_authenticated())
        self.show()
        self.assertIsNone(self.faces.main_face_authenticated())
        self.show(FakeFace(99))
        self.assertFalse(self.faces.main_face_authenticated())
        alex = self.employee("Alex", "Test")
        self.enroll(alex, 2)
        self.faces.stable = (None, 0)
        self.assertFalse(self.faces.main_face_authenticated())
        self.assertEqual(self.auto_start(seed=2)["state"], "running")

    def test_failed_auto_check_waits_for_cooldown(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.auto_start()
        self.show(FRONT)
        with self.faces.lock:
            finished = self.faces.advance(None, time.monotonic() + faces.LOST_TIMEOUT + 1)
        self.assertEqual(finished[1], "refused")
        self.assertNotIn(camille["id"], self.faces.authenticated)
        self.assertEqual(self.auto_start()["state"], "refused")
        self.faces.cooldown[camille["id"]] = time.monotonic() - 1
        self.assertEqual(self.auto_start()["state"], "running")

    def test_no_auto_check_for_disabled_unknown_or_when_turned_off(self):
        camille = self.employee()
        self.enroll(camille, 1)
        self.assertIsNone(self.auto_start(99))
        with mock.patch("faces.AUTO_CHECK", False):
            self.assertIsNone(self.auto_start())
        self.client.patch(f"/api/v1/employees/{camille['id']}", headers=self.headers, json={"active": False})
        self.faces.reload()
        self.assertIsNone(self.auto_start())
        self.assertEqual(self.store.events(), [])


if __name__ == "__main__":
    unittest.main()
