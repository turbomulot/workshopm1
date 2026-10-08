"""Spatial badge association, valid only while its QR is visible in this frame."""

from collections import Counter
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def associate_codes(payloads, polygons, boxes, store):
    counts = Counter(payloads)
    observations = []
    candidates = []
    for payload, polygon in zip(payloads, polygons):
        if not payload:
            continue
        observation = store.validate(payload)
        inside = [index for index, (x1, y1, x2, y2) in enumerate(boxes)
                  if all(x1 <= x <= x2 and y1 <= y <= y2 for x, y in polygon)]
        min_x, min_y = np.min(polygon, axis=0)
        max_x, max_y = np.max(polygon, axis=0)
        touching = [i for i, (x1, y1, x2, y2) in enumerate(boxes)
                    if x1 <= max_x and x2 >= min_x and y1 <= max_y and y2 >= min_y]
        candidate = inside[0] if len(inside) == len(touching) == 1 and counts[payload] == 1 else None
        candidates.append(candidate)
        observations.append({**observation, "person_index": candidate, "association": "unassigned"})
    per_person = Counter(index for index in candidates if index is not None)
    for observation in observations:
        index = observation["person_index"]
        if index is not None and per_person[index] == 1:
            observation["association"] = "clear"
        else:
            observation["person_index"] = None
    return observations


class QRVision:
    def __init__(self):
        self.detector = cv2.QRCodeDetector()
        self.next_single_scan = 0.0
        font_paths = [Path("C:/Windows/Fonts/arial.ttf"),
                      Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                      Path("/System/Library/Fonts/Supplemental/Arial.ttf")]
        self.font = next((ImageFont.truetype(str(path), 16) for path in font_paths if path.exists()), ImageFont.load_default())

    def read(self, image):
        # Scan a 960px-wide grayscale preview; periodically retry at full size
        # for small/less readable badges. Return coordinates in original pixels.
        factor = min(1.0, 960 / image.shape[1])
        preview = cv2.resize(image, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA) if factor < 1 else image
        preview = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY)
        found, payloads, polygons, _ = self.detector.detectAndDecodeMulti(preview)
        if found and any(payloads):
            return payloads[:12], polygons[:12] / factor
        # Multi also reads individual codes. Keep the single-code rescue at 2 Hz
        # instead of running two complete scans on every frame with no badge.
        clock = time.monotonic()
        if clock >= self.next_single_scan:
            self.next_single_scan = clock + 0.5
            if factor < 1:
                found, payloads, polygons, _ = self.detector.detectAndDecodeMulti(image)
                if found and any(payloads):
                    return payloads[:12], polygons[:12]
            payload, polygon, _ = self.detector.detectAndDecode(image)
            if payload and polygon is not None:
                return [payload], polygon.reshape(1, 4, 2)
        return [], []

    def annotate(self, image, boxes, observations, face_people=None, badge_people=None):
        """face_people: {person index: name} authenticated by face, which then needs no badge.
        badge_people: {person index: name} authenticated by a badge accepted earlier and put away since."""
        if not len(boxes):
            return image
        canvas = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(canvas)
        labels = {item["person_index"]: item for item in observations if item["association"] == "clear"}
        face_people = face_people or {}
        badge_people = badge_people or {}
        for index, (x1, y1, x2, y2) in enumerate(boxes):
            color = "#fab219"
            label = f"Personne {index + 1} - présence non authentifiée"
            item = labels.get(index)
            if index in face_people:
                label = f"Authentifié (visage) : {face_people[index]}"
                color = "#2fb344"
            elif item:
                if item["result"] == "valid":
                    employee = item["employee"]
                    label = f"Personne authentifiée (badge) : {employee['first_name']} {employee['last_name']}"
                    color = "#2fb344"
                else:
                    label = "Badge désactivé" if item["result"] == "disabled" else "Badge inconnu"
                    color = "#e5484d"
            elif index in badge_people:
                label = f"Personne authentifiée (badge) : {badge_people[index]}"
                color = "#2fb344"
            draw.rectangle((x1, y1, x2, y2), outline=color, width=2)
            while len(label) > 4 and draw.textbbox((0, 0), label, font=self.font)[2] > canvas.width - 12:
                label = label[:-4] + "..."
            width = draw.textbbox((0, 0), label, font=self.font)[2] + 10
            left = max(0, min(int(x1), canvas.width - width))
            top = max(0, int(y1) - 25)
            draw.rectangle((left, top, left + width, top + 24), fill="#121924")
            draw.text((left + 5, top + 2), label, font=self.font, fill=color)
        return cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)
