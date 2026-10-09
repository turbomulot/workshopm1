"""Access sequence started by the ESP8266 PIR: face positions, then badge, then alert.

    motion -> "visage" (3 positions x 6 s) -> "badge" (15 s) -> "alerte" -> standby once the person has left the camera field
                 \\____________________________\\_____________\\__ recognised -> "reconnu" (20 s) -> standby
"""

import math
import os

BADGE_SECONDS = float(os.environ.get("ACCESS_BADGE_S", "15"))
# Safety net if the face check never answers (camera slow to start, no face enrolled...).
FACE_MAX_SECONDS = float(os.environ.get("ACCESS_FACE_MAX_S", "25"))
RECOGNISED_SECONDS = float(os.environ.get("ACCESS_RECOGNISED_S", "20"))  # camera kept on, then standby
RESULT_DISPLAY_SECONDS = 5.0
WAITING = ("visage", "badge", "alerte")


class AccessSession:
    def __init__(self):
        self.phase = None        # None = standby, or "visage", "badge", "alerte", "reconnu"
        self.changed = 0.0       # time of the last phase change
        self.alerted = False     # this session ended in an alert

    def active(self):
        return self.phase is not None

    def update(self, now, motion, recognised, presence, face_failed=False):
        """motion: new PIR motion; recognised: face check passed or valid badge;
        presence: person still in the camera field (ends an alert); face_failed: the face check ended
        without success. Returns the new phase on a change ("veille" for standby), else None."""
        previous = self.phase
        if self.phase is None:
            if motion:
                self.phase, self.alerted = "visage", False
        elif self.phase in WAITING and recognised:
            self.phase = "reconnu"
        elif self.phase == "visage" and (face_failed or now - self.changed >= FACE_MAX_SECONDS):
            self.phase = "badge"
        elif self.phase == "badge" and now - self.changed >= BADGE_SECONDS:
            self.phase, self.alerted = "alerte", True
        elif self.phase == "alerte" and not presence:
            self.phase = None
        elif self.phase == "reconnu" and now - self.changed >= RECOGNISED_SECONDS:
            self.phase = None
        if self.phase == previous:
            return None
        self.changed = now
        return self.phase or "veille"

    def screen(self, now, check):
        """Message for the box's OLED, or None to let it show the sensors.
        check: the face check view (faces.FaceRecognizer.check_view)."""
        if self.phase == "visage":
            if check and check["state"] == "running":
                return {"verification": check["steps"][check["step"] - 1]["key"], "etape": check["step"],
                        "total": check["total"], "restant": check["remaining_s"]}
            return {"verification": "face"}
        if self.phase == "badge":
            return {"verification": "badge", "restant": math.ceil(BADGE_SECONDS - (now - self.changed))}
        if self.phase == "alerte":
            # Shown until the person has left the camera field, which ends the phase.
            return {"verification": "alerte"}
        if self.phase == "reconnu" and now - self.changed < RESULT_DISPLAY_SECONDS:
            return {"verification": "valid"}
        return None
