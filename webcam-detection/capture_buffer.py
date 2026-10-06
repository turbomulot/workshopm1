"""One-slot mailbox: slow analysis skips old captures instead of queuing them."""

import threading


class CaptureBuffer:
    def __init__(self):
        self.condition = threading.Condition()
        self.sequence = 0
        self.generation = 0
        self.packet = None

    def put(self, image, captured_at, capture_ms):
        with self.condition:
            self.sequence += 1
            self.packet = (self.sequence, self.generation, image, captured_at, capture_ms)
            self.condition.notify_all()

    def invalidate(self):
        with self.condition:
            self.generation += 1
            self.packet = None
            self.condition.notify_all()

    def read(self, after_sequence, stop):
        with self.condition:
            self.condition.wait_for(lambda: stop.is_set() or (self.packet is not None and self.sequence > after_sequence), timeout=0.25)
            return self.packet if not stop.is_set() and self.packet is not None and self.sequence > after_sequence else None

    def current(self, generation):
        with self.condition:
            return self.packet is not None and self.generation == generation
