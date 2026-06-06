"""AirCanvas AI - Streamlit web sürümü.

Tarayıcıda webcam akışını streamlit-webrtc üzerinden alır ve aynı jest motorunu
kullanır. Yan panelden fırça rengi/kalınlığı, arka plan resmi, undo/redo,
şekil düzeltme ve PNG indirme kontrol edilir.

Çalıştırma:
    streamlit run app.py
"""

import io

import av
import cv2
import numpy as np
import streamlit as st
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer, RTCConfiguration

from canvas_manager import CanvasManager
from gesture_detector import GestureDetector
from hand_tracker import HandTracker
from overlay import (
    PALETTE_COLORS,
    draw_hud,
    draw_palette,
    hit_test_palette,
    palette_cells,
)


st.set_page_config(
    page_title="AirCanvas AI",
    page_icon=":art:",
    layout="wide",
)


class AirCanvasProcessor(VideoProcessorBase):
    def __init__(self):
        self.tracker = HandTracker()
        self.detector = GestureDetector()
        self.canvas = CanvasManager(width=640, height=480)
        self.brush_color = (255, 0, 0)
        self.brush_thickness = 6
        self.note_text = "Not"

        # Sidebar tetikleyici bayrakları
        self.clear_flag = False
        self.add_note_flag = False
        self.undo_flag = False
        self.redo_flag = False
        self.background_image = None  # numpy BGR
        self.shape_correction = False
        self.show_pip = True

        # Palette hover dwell-time (anlık dokunuş seçmesin)
        self._palette_hover_color = None
        self._palette_hover_frames = 0
        self._palette_dwell_required = 5

        # Gesture transition
        self._prev_gesture = "NONE"
        self.last_composed = None

    def _maybe_push_history(self, gesture):
        # Yeni bir değiştirici jest başladıysa snapshot al
        modifying = {"DRAW", "ERASE", "PINCH", "CLEAR_ALL", "SCREENSHOT"}
        if gesture in modifying and self._prev_gesture not in modifying:
            self.canvas.push_history()

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        img = cv2.resize(img, (640, 480))
        img = cv2.flip(img, 1)
        raw_camera = img.copy()  # PIP için

        self.canvas.set_brush(self.brush_color, self.brush_thickness)
        self.canvas.shape_correction = self.shape_correction

        # Sidebar bayrakları
        if self.background_image is not None:
            self.canvas.set_background(self.background_image)
            self.background_image = None
        if self.clear_flag:
            self.canvas.clear_all()
            self.clear_flag = False
        if self.undo_flag:
            self.canvas.undo()
            self.undo_flag = False
        if self.redo_flag:
            self.canvas.redo()
            self.redo_flag = False

        landmarks, handedness = self.tracker.find_landmarks(img, draw=True)
        fingers = self.tracker.fingers_up(landmarks, handedness or "Right")
        gesture = self.detector.detect(landmarks, fingers)

        # Palette hit-test (sadece DRAW/PEN_UP/HOVER esnasında)
        cells = palette_cells(640)
        if landmarks is not None and gesture in ("DRAW", "PEN_UP", "HOVER"):
            picked = hit_test_palette(landmarks[8], cells)
            if picked is not None:
                if picked == self._palette_hover_color:
                    self._palette_hover_frames += 1
                else:
                    self._palette_hover_color = picked
                    self._palette_hover_frames = 1
                if self._palette_hover_frames >= self._palette_dwell_required:
                    self.brush_color = picked
                    self.canvas.set_brush(picked, self.brush_thickness)
                # Palette alanındayken DRAW'ı süpürelim, oraya çizmesin
                if gesture == "DRAW":
                    gesture = "PEN_UP"
            else:
                self._palette_hover_color = None
                self._palette_hover_frames = 0
        else:
            self._palette_hover_color = None
            self._palette_hover_frames = 0

        self._maybe_push_history(gesture)

        if landmarks is not None:
            index_tip = landmarks[8]
            middle_tip = landmarks[12]
            eraser_point = (
                (index_tip[0] + middle_tip[0]) // 2,
                (index_tip[1] + middle_tip[1]) // 2,
            )

            if self.add_note_flag:
                self.canvas.add_note(self.note_text, index_tip)
                self.add_note_flag = False

            if gesture == "DRAW":
                self.canvas.draw_to(index_tip)
                self.canvas.release_drag()
            elif gesture == "PEN_UP":
                self.canvas.reset_pen()
                self.canvas.release_drag()
            elif gesture == "ERASE":
                self.canvas.erase_at(eraser_point)
                self.canvas.release_drag()
            elif gesture == "PINCH":
                self.canvas.drag(index_tip)
                self.canvas.reset_pen()
            elif gesture == "CLEAR_ALL":
                self.canvas.clear_all()
            elif gesture == "SCREENSHOT":
                self.canvas.set_background(img.copy())
            else:
                self.canvas.reset_pen()
                self.canvas.release_drag()

            # Görsel imleç
            if gesture == "ERASE":
                cv2.circle(img, eraser_point, self.canvas.eraser_thickness // 2, (200, 200, 200), 2)
            elif gesture == "PEN_UP":
                cv2.circle(img, index_tip, 14, (0, 255, 255), 2)
                cv2.circle(img, index_tip, 2, (0, 255, 255), -1)
            elif gesture == "DRAW":
                cv2.circle(img, index_tip, 8, self.brush_color, -1)
            elif gesture == "PINCH":
                cv2.line(img, landmarks[4], landmarks[8], (0, 255, 0), 2)
                cv2.circle(img, index_tip, 10, (0, 255, 0), 2)

        self._prev_gesture = gesture

        composed = self.canvas.compose(img, pip_frame=raw_camera if self.show_pip else None)
        draw_palette(composed, cells, self.brush_color)
        extra = "Sekil duzeltme: ON" if self.shape_correction else None
        draw_hud(composed, gesture, self.brush_color, self.brush_thickness, extra_info=extra)

        self.last_composed = composed.copy()
        return av.VideoFrame.from_ndarray(composed, format="bgr24")


def _load_uploaded_image(uploaded):
    if uploaded is None:
        return None
    data = uploaded.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def render_sidebar():
    st.sidebar.title("AirCanvas AI")
    st.sidebar.caption("Jest kontrollu cizim ve not platformu")

    color_names = [n for n, _ in PALETTE_COLORS]
    color_lookup = dict(PALETTE_COLORS)
    color_name = st.sidebar.selectbox("Firca rengi", color_names, index=0)
    thickness = st.sidebar.slider("Firca kalinligi", 2, 30, 6)

    col_undo, col_redo = st.sidebar.columns(2)
    undo = col_undo.button("Geri al")
    redo = col_redo.button("Yinele")
    clear = st.sidebar.button("Tuvali temizle")

    st.sidebar.divider()
    st.sidebar.subheader("Arka plan")
    uploaded = st.sidebar.file_uploader("Resim yukle", type=["png", "jpg", "jpeg", "bmp"])

    st.sidebar.divider()
    st.sidebar.subheader("Not")
    note_text = st.sidebar.text_input("Not metni", value="AirCanvas")
    add_note = st.sidebar.button("Not ekle (parmak ucuna)")

    st.sidebar.divider()
    show_pip = st.sidebar.checkbox("Sag altta PIP webcam", value=True)
    shape_correction = st.sidebar.checkbox(
        "Sekil duzeltme (cember/cizgi auto-fix)", value=False,
        help="DRAW jesti bitince stroke kapaliysa elipse, dogrusalsa cizgiye snap eder."
    )

    with st.sidebar.expander("Jest rehberi", expanded=False):
        st.markdown(
            """
- **Cizim**: sadece isaret parmagi acik (basparmak kapali)
- **Kalem havada**: isaret + basparmak ikisi de acik
- **Silgi**: isaret + orta parmak acik
- **Tutma/Tasi**: basparmak ucu + isaret ucu birbirine deger (pinch)
  - Parmak altinda not varsa onu, yoksa tum tuvali tasir
- **Screenshot**: yumruk -> ani 5 parmak acilis
- **Tum tuval temizle**: avuc tamamen acik (5 parmak)
- **Renk paleti**: imleci ust palet seridine getir, ~5 kare bekle
            """
        )

    return {
        "color": color_lookup[color_name],
        "thickness": thickness,
        "clear": clear,
        "undo": undo,
        "redo": redo,
        "add_note": add_note,
        "note_text": note_text,
        "shape_correction": shape_correction,
        "show_pip": show_pip,
        "uploaded": uploaded,
    }


def render_download(ctx):
    st.sidebar.divider()
    st.sidebar.subheader("Indir")
    if ctx and ctx.video_processor and ctx.video_processor.last_composed is not None:
        ok, buf = cv2.imencode(".png", ctx.video_processor.last_composed)
        if ok:
            st.sidebar.download_button(
                label="Tuvali PNG olarak indir",
                data=io.BytesIO(buf.tobytes()),
                file_name="aircanvas.png",
                mime="image/png",
            )
    else:
        st.sidebar.caption("Yayini baslat, sonra indirebilirsin.")


def main():
    st.markdown(
        "<h1 style='text-align:center'>AirCanvas AI</h1>"
        "<p style='text-align:center; color:#888'>"
        "OpenCV + MediaPipe + Streamlit ile jest kontrollu sanal tuval"
        "</p>",
        unsafe_allow_html=True,
    )

    controls = render_sidebar()

    rtc_config = RTCConfiguration(
        {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    ctx = webrtc_streamer(
        key="aircanvas",
        video_processor_factory=AirCanvasProcessor,
        rtc_configuration=rtc_config,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
    )

    if ctx.video_processor:
        vp = ctx.video_processor
        vp.brush_color = controls["color"]
        vp.brush_thickness = controls["thickness"]
        vp.note_text = controls["note_text"]
        vp.shape_correction = controls["shape_correction"]
        vp.show_pip = controls["show_pip"]
        if controls["clear"]:
            vp.clear_flag = True
        if controls["undo"]:
            vp.undo_flag = True
        if controls["redo"]:
            vp.redo_flag = True
        if controls["add_note"]:
            vp.add_note_flag = True
        if controls["uploaded"] is not None:
            img = _load_uploaded_image(controls["uploaded"])
            if img is not None:
                vp.background_image = img

    render_download(ctx)


if __name__ == "__main__":
    main()
