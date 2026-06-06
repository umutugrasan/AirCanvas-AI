import os
import time
import cv2
import numpy as np


class CanvasManager:
    """Sanal tuval, sürüklenen notlar ve screenshot katmanını yönetir."""

    def __init__(self, width=640, height=480, save_dir="screenshots"):
        self.width = width
        self.height = height
        self.canvas = np.zeros((height, width, 3), dtype=np.uint8)

        self.brush_color = (255, 0, 0)  # BGR -> mavi
        self.brush_thickness = 6
        self.eraser_thickness = 40

        self.prev_point = None
        self.notes = []  # [{ "text": str, "pos": (x, y), "color": (b,g,r) }]
        self.dragging_note_idx = None

        # Tüm tuvalin pinch ile sürüklenmesi için snapshot ve başlangıç noktası
        self._canvas_drag_anchor = None
        self._canvas_snapshot = None

        self.frozen_background = None  # screenshot modunda kullanılır
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def set_brush(self, color_bgr, thickness):
        self.brush_color = color_bgr
        self.brush_thickness = int(thickness)

    def draw_to(self, point):
        if self.prev_point is None:
            self.prev_point = point
            return
        cv2.line(
            self.canvas,
            self.prev_point,
            point,
            self.brush_color,
            self.brush_thickness,
            lineType=cv2.LINE_AA,
        )
        self.prev_point = point

    def erase_at(self, point):
        cv2.circle(self.canvas, point, self.eraser_thickness // 2, (0, 0, 0), -1)
        self.prev_point = None

    def reset_pen(self):
        self.prev_point = None

    def clear_all(self):
        self.canvas[:] = 0
        self.notes.clear()
        self.frozen_background = None
        self.prev_point = None

    def add_note(self, text, position):
        self.notes.append(
            {"text": text, "pos": position, "color": self.brush_color}
        )

    def pick_note_at(self, point):
        """Sürüklenebilecek bir nota dokunulduysa indexini döndürür."""
        for i, note in enumerate(self.notes):
            nx, ny = note["pos"]
            (w, h), _ = cv2.getTextSize(note["text"], cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            if nx - 10 <= point[0] <= nx + w + 10 and ny - h - 10 <= point[1] <= ny + 10:
                return i
        return None

    def drag(self, point):
        """PINCH sırasında her karede çağrılır.

        Parmak ucunda bir not varsa onu, yoksa tüm tuvalin (çizdiklerinin)
        bir bütün halinde taşınmasını sağlar.
        """
        # Sürükleme türü henüz belirlenmediyse: not mu, tuval mi?
        if self.dragging_note_idx is None and self._canvas_drag_anchor is None:
            picked = self.pick_note_at(point)
            if picked is not None:
                self.dragging_note_idx = picked
            else:
                self._canvas_drag_anchor = point
                self._canvas_snapshot = self.canvas.copy()

        if self.dragging_note_idx is not None:
            self.notes[self.dragging_note_idx]["pos"] = point
        elif self._canvas_drag_anchor is not None:
            dx = point[0] - self._canvas_drag_anchor[0]
            dy = point[1] - self._canvas_drag_anchor[1]
            translation = np.float32([[1, 0, dx], [0, 1, dy]])
            self.canvas = cv2.warpAffine(
                self._canvas_snapshot,
                translation,
                (self.width, self.height),
                borderValue=(0, 0, 0),
            )

    def release_drag(self):
        self.dragging_note_idx = None
        self._canvas_drag_anchor = None
        self._canvas_snapshot = None

    def freeze_background(self, frame):
        """Mevcut kare bir "not altlığı" haline gelir; canvas üzerine yazılır."""
        self.frozen_background = frame.copy()

    def save_screenshot(self, composed_frame):
        filename = os.path.join(
            self.save_dir, f"aircanvas_{int(time.time())}.png"
        )
        cv2.imwrite(filename, composed_frame)
        return filename

    def compose(self, frame):
        """Canvas + notlar + (varsa) dondurulmuş arkaplanı tek bir kareye basar."""
        if self.frozen_background is not None:
            base = self.frozen_background.copy()
            # Frozen background varken hafif beyazlatarak "kağıt" hissi ver
            base = cv2.addWeighted(base, 0.6, np.full_like(base, 255), 0.4, 0)
        else:
            base = frame.copy()

        # Canvas'ı baseye karıştır (siyah pikseller şeffaf kabul edilir)
        gray = cv2.cvtColor(self.canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
        mask_inv = cv2.bitwise_not(mask)
        bg = cv2.bitwise_and(base, base, mask=mask_inv)
        fg = cv2.bitwise_and(self.canvas, self.canvas, mask=mask)
        composed = cv2.add(bg, fg)

        # Notları üst katmana yaz
        for note in self.notes:
            cv2.putText(
                composed,
                note["text"],
                note["pos"],
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                note["color"],
                2,
                cv2.LINE_AA,
            )
        return composed
