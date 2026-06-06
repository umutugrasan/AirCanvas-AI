import cv2
import mediapipe as mp


class HandTracker:
    """MediaPipe Hands tabanlı tek el takip modülü.

    21 eklem noktasını (X, Y, Z) sağlar ve isteğe bağlı olarak görüntü üzerine
    iskeleti çizer.
    """

    TIP_IDS = [4, 8, 12, 16, 20]  # thumb, index, middle, ring, pinky tips

    def __init__(self, max_hands=1, detection_conf=0.7, tracking_conf=0.5, model_complexity=0):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles
        # model_complexity=0 → "Lite" model, CPU'da ~2x hızlı, doğruluk küçük düşer
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            model_complexity=model_complexity,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )

    def find_landmarks(self, frame_bgr, draw=True):
        """Karedeki eli işler, piksel koordinatlarını döndürür.

        Returns:
            landmarks: [(x_px, y_px), ...] uzunluğu 21 olan liste ya da None
            handedness: "Left" / "Right" / None
        """
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            return None, None

        hand_lms = results.multi_hand_landmarks[0]
        handedness = None
        if results.multi_handedness:
            handedness = results.multi_handedness[0].classification[0].label

        h, w = frame_bgr.shape[:2]
        landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in hand_lms.landmark]

        if draw:
            self.mp_draw.draw_landmarks(
                frame_bgr,
                hand_lms,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style(),
            )
        return landmarks, handedness

    def fingers_up(self, landmarks, handedness="Right"):
        """Hangi parmakların açık olduğunu döndürür.

        Returns:
            [thumb, index, middle, ring, pinky] -> 1 açık, 0 kapalı
        """
        if landmarks is None:
            return [0, 0, 0, 0, 0]

        fingers = []

        # Başparmak: yatay karşılaştırma. Görüntü flip edildiğinden, kameradaki
        # "Right" el aslında ayna görüntüsünde sol tarafta görünür.
        if handedness == "Right":
            fingers.append(1 if landmarks[4][0] < landmarks[3][0] else 0)
        else:
            fingers.append(1 if landmarks[4][0] > landmarks[3][0] else 0)

        # Diğer 4 parmak: parmak ucu, PIP ekleminden yukarıda mı?
        for tip in self.TIP_IDS[1:]:
            fingers.append(1 if landmarks[tip][1] < landmarks[tip - 2][1] else 0)

        return fingers

    def close(self):
        self.hands.close()
