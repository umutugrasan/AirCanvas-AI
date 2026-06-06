"""AirCanvas AI - Bağımsız OpenCV sürümü.

Webcam penceresi açar, MediaPipe ile el iskeletini takip eder ve jestlere göre
çizim/silme/tutma/screenshot işlemlerini gerçekleştirir.

Klavye kısayolları:
    q       -> çık
    c       -> tuvali temizle
    n       -> mevcut parmak ucuna örnek not ekle
    1-6     -> palet renkleri (mavi/yeşil/kırmızı/sarı/pembe/beyaz)
    + / -   -> fırça kalınlığı
    z / y   -> geri al / yinele
    s       -> şekil düzeltmeyi aç/kapat
    p       -> tuvali PNG olarak kaydet
    b       -> arka plana son screenshot'ı sabitle / temizle
    h       -> PIP webcam'i aç/kapat
"""

import time

import cv2

from canvas_manager import CanvasManager
from gesture_detector import GestureDetector
from hand_tracker import HandTracker
from overlay import (
    PALETTE_COLORS,
    draw_hud,
    draw_palette,
    draw_thickness_strip,
    hit_test_palette,
    hit_test_thickness,
    palette_cells,
    thickness_cells,
)


COLOR_KEYS = {
    ord(str(i + 1)): color for i, (_, color) in enumerate(PALETTE_COLORS[:6])
}


def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        raise RuntimeError("Webcam acilamadi. Baska bir uygulamanin kullanmadigindan emin olun.")

    tracker = HandTracker()
    detector = GestureDetector()
    canvas = CanvasManager(width=640, height=480)
    p_cells = palette_cells(640)
    t_cells = thickness_cells(640, 480)

    show_pip = True
    last_composed = None
    prev_gesture = "NONE"

    palette_hover_color = None
    palette_hover_frames = 0
    thickness_hover_value = None
    thickness_hover_frames = 0
    hover_dwell = 5

    # Frame-skip cache
    frame_idx = 0
    inference_every = 2
    cached_landmarks = None
    cached_handedness = None

    window = "AirCanvas AI"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    modifying = {"DRAW", "ERASE", "PINCH", "CLEAR_ALL", "SCREENSHOT"}

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        raw_camera = frame.copy()

        frame_idx += 1
        if frame_idx % inference_every == 0:
            landmarks, handedness = tracker.find_landmarks(frame, draw=True)
            cached_landmarks = landmarks
            cached_handedness = handedness
        else:
            landmarks = cached_landmarks
            handedness = cached_handedness

        fingers = tracker.fingers_up(landmarks, handedness or "Right")
        gesture = detector.detect(landmarks, fingers)

        # Palet + kalınlık şeridi hover kontrolü
        over_ui = False
        if landmarks is not None and gesture in ("DRAW", "PEN_UP", "HOVER"):
            picked_color = hit_test_palette(landmarks[8], p_cells)
            picked_thickness = hit_test_thickness(landmarks[8], t_cells)

            if picked_color is not None:
                over_ui = True
                if picked_color == palette_hover_color:
                    palette_hover_frames += 1
                else:
                    palette_hover_color = picked_color
                    palette_hover_frames = 1
                if palette_hover_frames >= hover_dwell:
                    canvas.set_brush(picked_color, canvas.brush_thickness)
            else:
                palette_hover_color = None
                palette_hover_frames = 0

            if picked_thickness is not None:
                over_ui = True
                if picked_thickness == thickness_hover_value:
                    thickness_hover_frames += 1
                else:
                    thickness_hover_value = picked_thickness
                    thickness_hover_frames = 1
                if thickness_hover_frames >= hover_dwell:
                    canvas.set_brush(canvas.brush_color, picked_thickness)
            else:
                thickness_hover_value = None
                thickness_hover_frames = 0

            if over_ui and gesture == "DRAW":
                gesture = "PEN_UP"
        else:
            palette_hover_color = None
            palette_hover_frames = 0
            thickness_hover_value = None
            thickness_hover_frames = 0

        if gesture in modifying and prev_gesture not in modifying:
            canvas.push_history()

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
                canvas.set_background(frame.copy())
            else:
                canvas.reset_pen()
                canvas.release_drag()

            if gesture == "ERASE":
                cv2.circle(frame, eraser_point, canvas.eraser_thickness // 2, (200, 200, 200), 2)
            elif gesture == "PEN_UP":
                cv2.line(frame, landmarks[4], landmarks[8], (0, 255, 255), 1)
                preview_r = max(4, canvas.brush_thickness)
                cv2.circle(frame, index_tip, preview_r, canvas.brush_color, 2)
                cv2.circle(frame, index_tip, 3, (0, 255, 255), -1)
            elif gesture == "DRAW":
                cv2.circle(frame, index_tip, max(4, canvas.brush_thickness // 2 + 2), canvas.brush_color, -1)
            elif gesture == "PINCH":
                cv2.line(frame, landmarks[4], landmarks[8], (0, 255, 0), 2)
                cv2.circle(frame, index_tip, 10, (0, 255, 0), 2)

        prev_gesture = gesture

        composed = canvas.compose(frame, pip_frame=raw_camera if show_pip else None)
        draw_palette(composed, p_cells, canvas.brush_color)
        draw_thickness_strip(composed, t_cells, canvas.brush_color, canvas.brush_thickness)
        extra = "Sekil ON" if canvas.shape_correction else None
        draw_hud(composed, gesture, canvas.brush_color, canvas.brush_thickness, extra_info=extra)
        last_composed = composed

        cv2.imshow(window, composed)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("c"):
            canvas.clear_all()
        elif key == ord("z"):
            canvas.undo()
        elif key == ord("y"):
            canvas.redo()
        elif key == ord("n") and landmarks is not None:
            canvas.add_note("AirCanvas", landmarks[8])
        elif key in COLOR_KEYS:
            canvas.set_brush(COLOR_KEYS[key], canvas.brush_thickness)
        elif key == ord("+") or key == ord("="):
            canvas.set_brush(canvas.brush_color, min(canvas.brush_thickness + 2, 40))
        elif key == ord("-"):
            canvas.set_brush(canvas.brush_color, max(canvas.brush_thickness - 2, 2))
        elif key == ord("s"):
            canvas.shape_correction = not canvas.shape_correction
            print(f"[sekil duzeltme] {'ON' if canvas.shape_correction else 'OFF'}")
        elif key == ord("h"):
            show_pip = not show_pip
        elif key == ord("b"):
            canvas.background = None
        elif key == ord("p") and last_composed is not None:
            fname = canvas.save_screenshot(last_composed)
            print(f"[png] kaydedildi -> {fname}")

    cap.release()
    cv2.destroyAllWindows()
    tracker.close()


if __name__ == "__main__":
    main()
