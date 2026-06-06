"""AirCanvas AI - Bağımsız OpenCV sürümü.

Webcam penceresi açar, MediaPipe ile el iskeletini takip eder ve PDF'te tanımlı
beş jeste göre çizim/silme/screenshot işlemlerini gerçekleştirir.

Klavye kısayolları:
    q  -> çık
    c  -> tuvali temizle
    n  -> mevcut konuma örnek not ekle
    1/2/3/4 -> fırça rengi (mavi/yeşil/kırmızı/sarı)
    +/- -> fırça kalınlığını değiştir
"""

import cv2

from canvas_manager import CanvasManager
from gesture_detector import GestureDetector
from hand_tracker import HandTracker


COLORS = {
    ord("1"): (255, 0, 0),     # mavi
    ord("2"): (0, 255, 0),     # yeşil
    ord("3"): (0, 0, 255),     # kırmızı
    ord("4"): (0, 255, 255),   # sarı
}


def overlay_hud(frame, gesture, brush_color, brush_thickness):
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (30, 30, 30), -1)
    cv2.putText(
        frame,
        f"Jest: {gesture}",
        (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
    )
    cv2.circle(frame, (frame.shape[1] - 60, 20), 12, brush_color, -1)
    cv2.putText(
        frame,
        f"{brush_thickness}px",
        (frame.shape[1] - 40, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        raise RuntimeError("Webcam acilamadi. Kameranin baska bir uygulama tarafindan kullanilmadigindan emin olun.")

    tracker = HandTracker()
    detector = GestureDetector()
    canvas = CanvasManager(width=640, height=480)

    window = "AirCanvas AI"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        landmarks, handedness = tracker.find_landmarks(frame, draw=True)
        fingers = tracker.fingers_up(landmarks, handedness or "Right")
        gesture = detector.detect(landmarks, fingers)

        if landmarks is not None:
            index_tip = landmarks[8]
            middle_tip = landmarks[12]
            eraser_point = (
                (index_tip[0] + middle_tip[0]) // 2,
                (index_tip[1] + middle_tip[1]) // 2,
            )

            if gesture == "DRAW":
                canvas.draw_to(index_tip)
                canvas.release_drag()
            elif gesture == "PEN_UP":
                canvas.reset_pen()
                canvas.release_drag()
            elif gesture == "ERASE":
                canvas.erase_at(eraser_point)
                canvas.release_drag()
            elif gesture == "PINCH":
                canvas.drag(index_tip)
                canvas.reset_pen()
            elif gesture == "CLEAR_ALL":
                canvas.clear_all()
            elif gesture == "SCREENSHOT":
                canvas.freeze_background(frame)
            else:
                canvas.reset_pen()
                canvas.release_drag()

            # Görsel imleç / geri bildirim
            if gesture == "ERASE":
                cv2.circle(frame, eraser_point, canvas.eraser_thickness // 2, (200, 200, 200), 2)
            elif gesture == "PEN_UP":
                cv2.circle(frame, index_tip, 14, (0, 255, 255), 2)
                cv2.circle(frame, index_tip, 2, (0, 255, 255), -1)
            elif gesture == "DRAW":
                cv2.circle(frame, index_tip, 8, canvas.brush_color, -1)
            elif gesture == "PINCH":
                cv2.line(frame, landmarks[4], landmarks[8], (0, 255, 0), 2)
                cv2.circle(frame, index_tip, 10, (0, 255, 0), 2)

        composed = canvas.compose(frame)
        overlay_hud(composed, gesture, canvas.brush_color, canvas.brush_thickness)

        cv2.imshow(window, composed)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("c"):
            canvas.clear_all()
        elif key == ord("n"):
            if landmarks is not None:
                canvas.add_note("AirCanvas AI", landmarks[8])
        elif key in COLORS:
            canvas.set_brush(COLORS[key], canvas.brush_thickness)
        elif key == ord("+") or key == ord("="):
            canvas.set_brush(canvas.brush_color, min(canvas.brush_thickness + 2, 40))
        elif key == ord("-"):
            canvas.set_brush(canvas.brush_color, max(canvas.brush_thickness - 2, 2))
        elif gesture == "SCREENSHOT":
            saved = canvas.save_screenshot(composed)
            print(f"[screenshot] kaydedildi -> {saved}")

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()


if __name__ == "__main__":
    main()
