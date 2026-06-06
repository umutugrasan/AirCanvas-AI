import math
import time


class GestureDetector:
    """Parmak durumlarından soyut jestleri (Action) çıkarır.

    Tanımlı jestler:
        DRAW       -> sadece işaret parmağı açık (başparmak kapalı = kalem yerde)
        PEN_UP     -> işaret + başparmak ikisi de açık (kalem havada, çizmez)
        ERASE      -> işaret + orta parmak açık
        PINCH      -> başparmak ucu ile işaret ucu birbirine değer
        CLEAR_ALL  -> beş parmak da açık
        SCREENSHOT -> yumruktan (0 parmak) ani 5 parmak açılışına geçiş
    """

    PINCH_THRESHOLD = 40  # piksel
    FIST_TO_OPEN_WINDOW = 0.6  # saniye

    def __init__(self):
        self._fist_seen_at = None
        self._last_screenshot_at = 0.0
        self._screenshot_cooldown = 1.2

    @staticmethod
    def _distance(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def detect(self, landmarks, fingers):
        """Tek bir karedeki landmark + parmak durumundan jest etiketi döndürür."""
        if landmarks is None:
            self._fist_seen_at = None
            return "NONE"

        thumb_tip, index_tip = landmarks[4], landmarks[8]
        pinch_dist = self._distance(thumb_tip, index_tip)

        total_open = sum(fingers)
        now = time.time()

        # Yumruk -> açık el geçişi (screenshot)
        if total_open <= 1 and fingers[1] == 0:
            self._fist_seen_at = now

        if (
            total_open == 5
            and self._fist_seen_at is not None
            and (now - self._fist_seen_at) <= self.FIST_TO_OPEN_WINDOW
            and (now - self._last_screenshot_at) > self._screenshot_cooldown
        ):
            self._fist_seen_at = None
            self._last_screenshot_at = now
            return "SCREENSHOT"

        # Pinch: ucları birbirine değiyor, diğer parmaklar da kapalı değil
        if pinch_dist < self.PINCH_THRESHOLD and fingers[2] == 0:
            return "PINCH"

        # Tüm ekranı temizle
        if total_open == 5:
            return "CLEAR_ALL"

        # Silgi: işaret + orta
        if fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0:
            return "ERASE"

        # Kalem havada: işaret + başparmak açık, gerisi kapalı
        # (harfler arası boşluk bırakmak için imleci taşı, ama çizme)
        if fingers[0] == 1 and fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            return "PEN_UP"

        # Çizim: sadece işaret (başparmak kapalı = kalem yerde)
        if fingers[0] == 0 and fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 0:
            return "DRAW"

        return "HOVER"
