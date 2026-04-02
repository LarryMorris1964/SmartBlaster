"""Camera abstraction layer."""

from __future__ import annotations

from io import BytesIO



import threading
import time

class CameraService:
    def __init__(self) -> None:
        self._camera = None
        self._is_usb = False
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._camera is not None:
            return
        # Try USB camera (OpenCV) first — this project uses a telephoto USB camera.
        try:
            import cv2
            cam = cv2.VideoCapture(0)
            if cam.isOpened():
                cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                cam.set(cv2.CAP_PROP_FPS, 30)
                # Test grab to confirm camera is usable
                ret, frame = cam.read()
                if ret:
                    self._camera = cam
                    self._is_usb = True
                    return
                else:
                    cam.release()
        except ImportError:
            pass
        # Fallback: try Pi camera (Picamera2)
        try:
            from picamera2 import Picamera2  # type: ignore
            camera = Picamera2()
            config = camera.create_still_configuration()
            camera.configure(config)
            camera.start()
            self._camera = camera
            self._is_usb = False
        except ImportError:
            self._camera = None
            self._is_usb = False

    def capture_frame(self) -> bytes | None:
        if self._camera is None:
            return None
        with self._lock:
            if self._is_usb:
                import cv2
                ret, frame = self._camera.read()
                if not ret or frame is None:
                    return None
                # Encode as JPEG
                ret, buf = cv2.imencode('.jpg', frame)
                if not ret:
                    return None
                return buf.tobytes()
            else:
                buffer = BytesIO()
                self._camera.capture_file(buffer, format="jpeg")
                return buffer.getvalue()

    def stop(self) -> None:
        if self._camera is None:
            return
        with self._lock:
            if self._is_usb:
                self._camera.release()
            else:
                self._camera.stop()
                self._camera.close()
            self._camera = None
            self._is_usb = False


class NoCameraService(CameraService):
    """Null camera implementation for IR-only operation."""

    def start(self) -> None:
        print("camera=disabled (IR-only mode)")

    def capture_frame(self) -> bytes | None:
        return None

    def stop(self) -> None:
        return
