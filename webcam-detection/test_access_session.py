import unittest

from access_session import BADGE_SECONDS, FACE_MAX_SECONDS, RECOGNISED_SECONDS, AccessSession

RUNNING = {"state": "running", "step": 2, "total": 3, "remaining_s": 4,
           "steps": [{"key": "down"}, {"key": "left"}, {"key": "up"}]}


class AccessSessionTest(unittest.TestCase):
    def setUp(self):
        self.session = AccessSession()

    def step(self, now, motion=False, recognised=False, presence=True, face_failed=False):
        return self.session.update(now, motion, recognised, presence, face_failed)

    def test_waits_for_motion(self):
        self.assertIsNone(self.step(0))
        self.assertFalse(self.session.active())
        self.assertEqual(self.step(1, motion=True), "visage")
        self.assertTrue(self.session.active())

    def test_positions_then_badge_then_alert(self):
        self.step(0, motion=True)
        self.assertEqual(self.session.screen(1, None), {"verification": "face"})
        self.assertEqual(self.session.screen(9, RUNNING),
                         {"verification": "left", "etape": 2, "total": 3, "restant": 4})
        self.assertIsNone(self.step(17))
        self.assertEqual(self.step(18, face_failed=True), "badge")
        self.assertEqual(self.session.screen(18 + 5, None), {"verification": "badge", "restant": BADGE_SECONDS - 5})
        self.assertIsNone(self.step(18 + BADGE_SECONDS - 0.1))
        self.assertEqual(self.step(18 + BADGE_SECONDS), "alerte")
        self.assertEqual(self.session.screen(18 + BADGE_SECONDS + 1, None), {"verification": "alerte"})
        # The camera keeps watching while someone is there, then goes to standby.
        self.assertIsNone(self.step(60))
        self.assertEqual(self.step(61, presence=False), "veille")

    def test_alert_lasts_until_the_person_leaves_the_camera_field(self):
        self.step(0, motion=True)
        self.step(1, face_failed=True)
        self.assertEqual(self.step(1 + BADGE_SECONDS), "alerte")
        self.assertTrue(self.session.alerted)
        for later in (60, 300):
            self.assertIsNone(self.step(later, presence=True))
            self.assertEqual(self.session.screen(later, None), {"verification": "alerte"})
        self.assertEqual(self.step(301, presence=False), "veille")
        self.assertIsNone(self.session.screen(301, None))
        self.assertEqual(self.step(400, motion=True), "visage")
        self.assertFalse(self.session.alerted)

    def test_badge_even_if_the_face_check_never_answers(self):
        self.step(0, motion=True)
        self.assertIsNone(self.step(FACE_MAX_SECONDS - 0.1))
        self.assertEqual(self.step(FACE_MAX_SECONDS), "badge")

    def test_recognised_by_face_or_badge_then_standby_after_20_s(self):
        for recognised_at in (4, 25):
            session = self.session = AccessSession()
            self.step(0, motion=True)
            self.step(18, face_failed=True)
            self.assertEqual(self.step(recognised_at, recognised=True), "reconnu")
            self.assertEqual(session.screen(recognised_at + 1, None), {"verification": "valid"})
            self.assertIsNone(self.step(recognised_at + RECOGNISED_SECONDS - 0.1))
            self.assertEqual(self.step(recognised_at + RECOGNISED_SECONDS), "veille")

    def test_recognised_after_the_alert(self):
        self.step(0, motion=True)
        self.step(1, face_failed=True)
        self.step(1 + BADGE_SECONDS)
        self.assertEqual(self.step(40, recognised=True), "reconnu")

    def test_motion_during_a_session_is_ignored(self):
        self.step(0, motion=True)
        self.assertIsNone(self.step(5, motion=True))
        self.assertEqual(self.step(6, face_failed=True), "badge")


if __name__ == "__main__":
    unittest.main()
