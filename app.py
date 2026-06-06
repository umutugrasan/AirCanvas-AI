"""AirCanvas AI - Streamlit web sürümü.

Tarayıcıda webcam akışını streamlit-webrtc üzerinden alır ve aynı jest motorunu
kullanır. Yan panelden fırça rengi/kalınlığı ayarlanır, tuval sıfırlanır.

Çalıştırma:
    streamlit run app.py
"""

import av
import cv2
import numpy as np
import streamlit as st
from streamlit_webrtc import VideoProcessorBase, webrtc_streamer, RTCConfiguration

from canvas_manager import CanvasManager
from gesture_detector import GestureDetector
from hand_tracker import HandTracker


st.set_page_config(
    page_title="AirCanvas AI",
    page_icon=":art:",
    layout="wide",
)


PRESET_COLORS = {
    "Mavi": (255, 0, 0),
    "Yesil": (0, 255, 0),
    "Kirmizi": (0, 0, 255),
    "Sari": (0, 255, 255),
    "Beyaz": (255, 255, 255),
}


class AirCanvasProcessor(VideoProcessorBase):
    def __init__(self):
        self.tracker = HandTracker()
        self.detector = GestureDetector()
        self.canvas = CanvasManager(width=640, height=480)
        self.brush_color = (255, 0, 0)
        self.brush_thickness = 6
        self.clear_flag = False
        self.add_note_flag = False
        self.note_text = "Not"
        self.last_gesture = "NONE"

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        img = cv2.resize(img, (640, 480))
        img = cv2.flip(img, 1)

        self.canvas.set_brush(self.brush_color, self.brush_thickness)
        if self.clear_flag:
            self.canvas.clear_all()
            self.clear_flag = False

        landmarks, handedness = self.tracker.find_landmarks(img, draw=True)
        fingers = self.tracker.fingers_up(landmarks, handedness or "Right")
        gesture = self.detector.detect(landmarks, fingers)
        self.last_gesture = gesture

        if landmarks is not None:
            index_tip = landmarks[8]
            middle_tip = landmarks[12]
            eraser_point = (
                (index_tip[0] + middle_tip[0]) // 2,
                (index_tip[1] + middle_tip[1]) // 2,
            )

            # Sidebar'dan tetiklenen not ekleme (parmak ucu konumuna)
            if self.add_note_flag:
                self.canvas.add_note(self.note_text, index_tip)
                self.add_note_flag = False

            if gesture == "DRAW":
                self.canvas.draw_to(index_tip)
                self.canvas.release_drag()
            elif gesture == "PEN_UP":
                # Kalem havada: çizme, sadece imleci göster
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
                self.canvas.freeze_background(img)
            else:
                self.canvas.reset_pen()
                self.canvas.release_drag()

            # Görsel imleç / geri bildirim
            if gesture == "ERASE":
                cv2.circle(img, eraser_point, self.canvas.eraser_thickness // 2, (200, 200, 200), 2)
            elif gesture == "PEN_UP":
                # Boş halka = kalem havada
                cv2.circle(img, index_tip, 14, (0, 255, 255), 2)
                cv2.circle(img, index_tip, 2, (0, 255, 255), -1)
            elif gesture == "DRAW":
                # Dolu daire = kalem yerde
                cv2.circle(img, index_tip, 8, self.brush_color, -1)
            elif gesture == "PINCH":
                cv2.line(img, landmarks[4], landmarks[8], (0, 255, 0), 2)
                cv2.circle(img, index_tip, 10, (0, 255, 0), 2)

        composed = self.canvas.compose(img)

        # HUD
        cv2.rectangle(composed, (0, 0), (composed.shape[1], 40), (30, 30, 30), -1)
        cv2.putText(
            composed,
            f"Jest: {gesture}",
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.circle(composed, (composed.shape[1] - 60, 20), 12, self.brush_color, -1)
        cv2.putText(
            composed,
            f"{self.brush_thickness}px",
            (composed.shape[1] - 40, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )

        return av.VideoFrame.from_ndarray(composed, format="bgr24")


def render_sidebar():
    st.sidebar.title("AirCanvas AI")
    st.sidebar.caption("Jest kontrollu cizim ve not platformu")

    color_name = st.sidebar.selectbox("Firca rengi", list(PRESET_COLORS.keys()), index=0)
    thickness = st.sidebar.slider("Firca kalinligi", 2, 30, 6)
    clear = st.sidebar.button("Tuvali temizle")

    st.sidebar.divider()
    st.sidebar.subheader("Not")
    note_text = st.sidebar.text_input("Not metni", value="AirCanvas")
    add_note = st.sidebar.button("Not ekle (parmak ucuna)")

    with st.sidebar.expander("Jest rehberi", expanded=True):
        st.markdown(
            """
- **Cizim**: sadece isaret parmagi acik (basparmak kapali)
- **Kalem havada**: isaret + basparmak ikisi de acik
  (cizmez, sadece imleci tasir — harfler arasi bosluk icin)
- **Silgi**: isaret + orta parmak acik
- **Tutma/Tasi**: basparmak ucu + isaret ucu birbirine deger (pinch)
- **Screenshot**: yumruk -> ani 5 parmak acilis
- **Tum tuval temizle**: avuc tamamen acik (5 parmak)
            """
        )

    return PRESET_COLORS[color_name], thickness, clear, add_note, note_text


def main():
    st.markdown(
        "<h1 style='text-align:center'>AirCanvas AI</h1>"
        "<p style='text-align:center; color:#888'>"
        "OpenCV + MediaPipe + Streamlit ile jest kontrollu sanal tuval"
        "</p>",
        unsafe_allow_html=True,
    )

    color, thickness, clear, add_note, note_text = render_sidebar()

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
        ctx.video_processor.brush_color = color
        ctx.video_processor.brush_thickness = thickness
        ctx.video_processor.note_text = note_text
        if clear:
            ctx.video_processor.clear_flag = True
        if add_note:
            ctx.video_processor.add_note_flag = True


if __name__ == "__main__":
    main()
