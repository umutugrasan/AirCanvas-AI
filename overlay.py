"""Renk paleti, kalınlık şeridi ve HUD katmanı (app.py + aircanvas.py paylaşır)."""

import cv2


MIN_THICKNESS = 2
MAX_THICKNESS = 30
THICKNESS_LEVELS = [3, 8, 14, 22, 30]
THICKNESS_CELL = 55


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


def thickness_cells(frame_w, frame_h):
    """Sağ kenara dikey kalınlık şeridi hücreleri."""
    total_h = len(THICKNESS_LEVELS) * THICKNESS_CELL
    start_y = max(PALETTE_BOTTOM + 15, (frame_h - total_h) // 2)
    x = frame_w - THICKNESS_CELL - 8
    cells = []
    for i, t in enumerate(THICKNESS_LEVELS):
        y = start_y + i * THICKNESS_CELL
        cells.append({
            "thickness": t,
            "rect": (x, y, THICKNESS_CELL - 6, THICKNESS_CELL - 6),
        })
    return cells


def hit_test_thickness(point, cells):
    if point is None:
        return None
    px, py = point
    for cell in cells:
        x, y, w, h = cell["rect"]
        if x <= px <= x + w and y <= py <= y + h:
            return cell["thickness"]
    return None


def draw_thickness_strip(frame, cells, brush_color, active_thickness):
    for cell in cells:
        x, y, w, h = cell["rect"]
        # Yarı şeffaf koyu kart
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)
        # Çerçeve — aktif kalınlığa kalın sarı
        is_active = cell["thickness"] == active_thickness
        border_col = (0, 255, 255) if is_active else (200, 200, 200)
        border_t = 3 if is_active else 1
        cv2.rectangle(frame, (x, y), (x + w, y + h), border_col, border_t)
        # Kalınlığı temsil eden, mevcut fırça renginde dolu daire
        cx = x + w // 2
        cy = y + h // 2
        cv2.circle(frame, (cx, cy), cell["thickness"], brush_color, -1)


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
