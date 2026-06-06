"""Renk paleti ve HUD katmanı yardımcıları (app.py + aircanvas.py paylaşır)."""

import cv2


PALETTE_COLORS = [
    ("Mavi", (255, 0, 0)),
    ("Yesil", (0, 255, 0)),
    ("Kirmizi", (0, 0, 255)),
    ("Sari", (0, 255, 255)),
    ("Pembe", (255, 0, 255)),
    ("Beyaz", (255, 255, 255)),
]

PALETTE_TOP = 45
PALETTE_BOTTOM = 95
CELL_WIDTH = 70


def palette_cells(frame_w):
    """Palette hücrelerinin x,y,w,h dikdörtgenlerini ve renklerini döndürür."""
    total = len(PALETTE_COLORS) * CELL_WIDTH
    start_x = max(10, (frame_w - total) // 2)
    cells = []
    for i, (name, color) in enumerate(PALETTE_COLORS):
        x = start_x + i * CELL_WIDTH
        cells.append({
            "name": name,
            "color": color,
            "rect": (x, PALETTE_TOP, CELL_WIDTH - 6, PALETTE_BOTTOM - PALETTE_TOP),
        })
    return cells


def hit_test_palette(point, cells):
    """Bir noktanın palette üzerinde olup olmadığını döndürür → seçilen renk veya None."""
    if point is None:
        return None
    px, py = point
    for cell in cells:
        x, y, w, h = cell["rect"]
        if x <= px <= x + w and y <= py <= y + h:
            return cell["color"]
    return None


def draw_palette(frame, cells, active_color):
    for cell in cells:
        x, y, w, h = cell["rect"]
        cv2.rectangle(frame, (x, y), (x + w, y + h), cell["color"], -1)
        # Aktif renge çerçeve
        border = (255, 255, 255) if cell["color"] != (255, 255, 255) else (0, 0, 0)
        thickness = 3 if tuple(cell["color"]) == tuple(active_color) else 1
        cv2.rectangle(frame, (x, y), (x + w, y + h), border, thickness)


def draw_hud(frame, gesture, brush_color, brush_thickness, extra_info=None):
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
    if extra_info:
        cv2.putText(
            frame,
            extra_info,
            (180, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (180, 220, 180),
            1,
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
