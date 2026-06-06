import os
import time
import cv2
import numpy as np


class CanvasManager:
    """Sanal tuval, sürüklenen notlar, screenshot, geçmiş ve şekil düzeltme katmanı."""

    HISTORY_LIMIT = 30

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

        # Pinch ile tuvalin tamamını taşımak için
        self._canvas_drag_anchor = None
        self._canvas_snapshot = None

        # Mevcut çizilen stroke'u (şekil düzeltme için) kaydet
        self._stroke_points = []
        self.shape_correction = False

        # Geri al / yinele yığınları
        self._history = []
        self._redo = []

        # Arka plan (yüklenmiş resim veya screenshot dondurması)
        self.background = None
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    # ---------------------------------------------------------------- ayarlar
    def set_brush(self, color_bgr, thickness):
        self.brush_color = tuple(int(c) for c in color_bgr)
        self.brush_thickness = int(thickness)

    def set_background(self, image_bgr):
        """Yüklenen resmi tuval boyutuna ölçekleyip arka plan yap."""
        if image_bgr is None:
            self.background = None
            return
        resized = cv2.resize(image_bgr, (self.width, self.height))
        self.background = resized

    # ----------------------------------------------------------- çizim aksiyonları
    def draw_to(self, point):
        if self.prev_point is None:
            self.prev_point = point
            self._stroke_points = [point]
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
        self._stroke_points.append(point)

    def erase_at(self, point):
        cv2.circle(self.canvas, point, self.eraser_thickness // 2, (0, 0, 0), -1)
        self.prev_point = None
        self._stroke_points = []

    def reset_pen(self):
        # Çizim biterse, gerekirse şekil düzeltmeyi uygula
        if self.shape_correction and len(self._stroke_points) >= 12:
            self._correct_stroke_in_place()
        self.prev_point = None
        self._stroke_points = []

    def clear_all(self):
        self.canvas[:] = 0
        self.notes.clear()
        self.background = None
        self.prev_point = None
        self._stroke_points = []
        self._history.clear()
        self._redo.clear()

    # -------------------------------------------------------------------- notlar
    def add_note(self, text, position):
        self.notes.append(
            {"text": text, "pos": position, "color": self.brush_color}
        )

    def pick_note_at(self, point):
        for i, note in enumerate(self.notes):
            nx, ny = note["pos"]
            (w, h), _ = cv2.getTextSize(note["text"], cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            if nx - 10 <= point[0] <= nx + w + 10 and ny - h - 10 <= point[1] <= ny + 10:
                return i
        return None

    # -------------------------------------------------------------- drag (pinch)
    def drag(self, point):
        """PINCH sırasında her karede çağrılır.

        Parmak ucunda not varsa onu, yoksa tüm tuvalin (çizgilerin) bir
        bütün halinde taşınmasını sağlar.
        """
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

    # ------------------------------------------------------------------- history
    def push_history(self):
        """Bir değiştirici jest başlamadan ÖNCE çağır."""
        snapshot = {
            "canvas": self.canvas.copy(),
            "notes": [dict(n) for n in self.notes],
        }
        self._history.append(snapshot)
        if len(self._history) > self.HISTORY_LIMIT:
            self._history.pop(0)
        self._redo.clear()

    def undo(self):
        if not self._history:
            return False
        current = {
            "canvas": self.canvas.copy(),
            "notes": [dict(n) for n in self.notes],
        }
        self._redo.append(current)
        last = self._history.pop()
        self.canvas = last["canvas"]
        self.notes = last["notes"]
        self.reset_pen()
        return True

    def redo(self):
        if not self._redo:
            return False
        current = {
            "canvas": self.canvas.copy(),
            "notes": [dict(n) for n in self.notes],
        }
        self._history.append(current)
        nxt = self._redo.pop()
        self.canvas = nxt["canvas"]
        self.notes = nxt["notes"]
        self.reset_pen()
        return True

    # -------------------------------------------------------- şekil düzeltme
    def _correct_stroke_in_place(self):
        """Son çizilen stroke'u analiz et: kapalı şekle → elips, doğrusal → çizgi."""
        pts = np.array(self._stroke_points, dtype=np.int32)
        if len(pts) < 12:
            return

        # Stroke uzunluğu
        diffs = np.diff(pts, axis=0)
        seg_lens = np.sqrt((diffs ** 2).sum(axis=1))
        total_len = float(seg_lens.sum())
        if total_len < 60:
            return

        chord = float(np.linalg.norm(pts[-1] - pts[0]))
        closed_ratio = chord / total_len

        # Stroke'u önce sil (tuvalden temizle), sonra düzgün şekli çiz
        # Son stroke'un yaklaşık bounding-box'ında siyah bir maske ile silelim
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        cv2.polylines(mask, [pts], isClosed=False, color=255,
                      thickness=self.brush_thickness + 4)
        # Maskeyle eşleşen pikselleri sıfırla
        self.canvas[mask > 0] = 0

        if closed_ratio < 0.18 and len(pts) >= 20:
            # Kapalı şekil → elips fit
            try:
                (cx, cy), (MA, ma), angle = cv2.fitEllipse(pts)
                cv2.ellipse(
                    self.canvas,
                    (int(cx), int(cy)),
                    (int(MA / 2), int(ma / 2)),
                    angle,
                    0,
                    360,
                    self.brush_color,
                    self.brush_thickness,
                    cv2.LINE_AA,
                )
                return
            except cv2.error:
                pass

        # Doğrusallık ölç: noktaların başlangıç-bitiş çizgisine ortalama uzaklığı
        start, end = pts[0].astype(np.float32), pts[-1].astype(np.float32)
        line_vec = end - start
        line_len = np.linalg.norm(line_vec)
        if line_len > 1:
            normal = np.array([-line_vec[1], line_vec[0]]) / line_len
            rel = pts.astype(np.float32) - start
            distances = np.abs(rel @ normal)
            mean_dev = float(distances.mean())
            if mean_dev < max(8.0, self.brush_thickness * 1.2):
                cv2.line(
                    self.canvas,
                    tuple(pts[0]),
                    tuple(pts[-1]),
                    self.brush_color,
                    self.brush_thickness,
                    cv2.LINE_AA,
                )
                return

        # Düzeltilemedi → orjinal stroke'u geri çiz
        for i in range(1, len(pts)):
            cv2.line(
                self.canvas,
                tuple(pts[i - 1]),
                tuple(pts[i]),
                self.brush_color,
                self.brush_thickness,
                cv2.LINE_AA,
            )

    # --------------------------------------------------------------- screenshot
    def save_screenshot(self, composed_frame):
        filename = os.path.join(
            self.save_dir, f"aircanvas_{int(time.time())}.png"
        )
        cv2.imwrite(filename, composed_frame)
        return filename

    # ---------------------------------------------------------------- composing
    def compose(self, frame, pip_frame=None):
        """Canvas + notlar + arka plan + (opsiyonel) PIP webcam'i birleştirir."""
        if self.background is not None:
            base = self.background.copy()
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

        # PIP webcam (sağ alt köşe)
        if pip_frame is not None:
            pip_w, pip_h = 160, 120
            pip = cv2.resize(pip_frame, (pip_w, pip_h))
            x2, y2 = self.width - 10, self.height - 10
            x1, y1 = x2 - pip_w, y2 - pip_h
            # Beyaz çerçeve + gölge
            cv2.rectangle(composed, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (255, 255, 255), 2)
            composed[y1:y2, x1:x2] = pip

        return composed
