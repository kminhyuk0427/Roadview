# Flask 기반 경량 MJPEG 스트리밍 서버 (백그라운드 전용)

from flask import Flask, Response
import cv2
import threading
import time
import sys

try:
    from config import RTSP_URL, RTSP_CAMERAS, VIDEO_DISPLAY_WIDTH, VIDEO_DISPLAY_HEIGHT
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    RTSP_URL = "rtsp://localhost:8554/stream"
    RTSP_CAMERAS = []
    VIDEO_DISPLAY_WIDTH = 800
    VIDEO_DISPLAY_HEIGHT = 450

app = Flask(__name__)


# 스트림 관리 클래스
class RTSPStreamManager:
    def __init__(self, rtsp_url, stream_id, width=800, height=450, fps=15):
        self.rtsp_url = rtsp_url
        self.stream_id = stream_id
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_interval = 1.0 / fps

        self.current_frame = None
        self.is_running = False
        self.is_connected = False
        self.lock = threading.Lock()
        self.thread = None
        self.cap = None
        self.last_frame_time = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    def connect(self):
        try:
            if self.cap is not None:
                self.cap.release()
                time.sleep(0.2)

            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    self.reconnect_attempts = 0
                    return True

            self.is_connected = False
            self.reconnect_attempts += 1
            return False

        except Exception as e:
            self.is_connected = False
            self.reconnect_attempts += 1
            return False

    def _capture_loop(self):
        reconnect_delay = 5
        last_reconnect = time.time()

        while self.is_running:
            if not self.is_connected:
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    time.sleep(10)
                    self.reconnect_attempts = 0

                if time.time() - last_reconnect > reconnect_delay:
                    self.connect()
                    last_reconnect = time.time()

                time.sleep(1)
                continue

            try:
                elapsed = time.time() - self.last_frame_time
                if elapsed < self.frame_interval:
                    time.sleep(self.frame_interval - elapsed)

                for _ in range(2):
                    self.cap.grab()

                ret, frame = self.cap.retrieve()

                if ret and frame is not None:
                    resized = cv2.resize(
                        frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR
                    )

                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                    _, buffer = cv2.imencode(".jpg", resized, encode_param)

                    with self.lock:
                        self.current_frame = buffer.tobytes()
                        self.last_frame_time = time.time()
                else:
                    self.is_connected = False

            except Exception as e:
                self.is_connected = False
                time.sleep(1)

    def start(self):
        if self.is_running:
            return

        self.is_running = True

        for attempt in range(3):
            if self.connect():
                break
            time.sleep(2)

        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

        if self.thread:
            self.thread.join(timeout=3)

        if self.cap:
            self.cap.release()

        self.is_connected = False

    def get_frame(self):
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame
        return None


# 전역 스트림 매니저
stream_managers = {}


def init_streams():
    if CONFIG_AVAILABLE and RTSP_URL:
        manager = RTSPStreamManager(
            RTSP_URL,
            "main",
            width=VIDEO_DISPLAY_WIDTH,
            height=VIDEO_DISPLAY_HEIGHT,
            fps=15,
        )
        manager.start()
        stream_managers["main"] = manager

    if CONFIG_AVAILABLE and RTSP_CAMERAS:
        for idx, camera in enumerate(RTSP_CAMERAS):
            stream_id = f"camera_{idx}"
            manager = RTSPStreamManager(
                camera["url"],
                stream_id,
                width=VIDEO_DISPLAY_WIDTH,
                height=VIDEO_DISPLAY_HEIGHT,
                fps=15,
            )
            manager.start()
            stream_managers[stream_id] = manager


def generate_mjpeg(stream_id):
    manager = stream_managers.get(stream_id)

    if not manager:
        import numpy as np
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            error_frame,
            "Stream Not Found",
            (50, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        _, buffer = cv2.imencode(".jpg", error_frame)

        while True:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
            time.sleep(1)
        return

    while True:
        frame = manager.get_frame()

        if frame is None:
            import numpy as np
            waiting_frame = np.zeros((manager.height, manager.width, 3), dtype=np.uint8)
            status = (
                "Connecting..."
                if manager.reconnect_attempts < manager.max_reconnect_attempts
                else "Connection Failed"
            )
            cv2.putText(
                waiting_frame,
                status,
                (50, manager.height // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
            _, buffer = cv2.imencode(".jpg", waiting_frame)
            frame = buffer.tobytes()

        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.033)


@app.route("/stream/<stream_id>")
def stream(stream_id):
    return Response(
        generate_mjpeg(stream_id), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/health")
def health():
    return "OK", 200


def main():
    init_streams()

    if not stream_managers:
        sys.exit(1)

    try:
        app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        pass
    finally:
        for manager in stream_managers.values():
            manager.stop()


if __name__ == "__main__":
    main()