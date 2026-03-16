"""Camera abstraction layer."""

from __future__ import annotations

from io import BytesIO


class CameraService:
    def __init__(self) -> None:
        self._camera = None

    def start(self) -> None:
        if self._camera is not None:
            return
        try:
            from picamera2 import Picamera2  # type: ignore
        except ImportError:
            self._camera = None
            return

        camera = Picamera2()
        config = camera.create_still_configuration()
        camera.configure(config)
        camera.start()
        self._camera = camera

    def capture_frame(self) -> bytes | None:
        if self._camera is None:
            return None

        buffer = BytesIO()
        self._camera.capture_file(buffer, format="jpeg")
        return buffer.getvalue()

    def stop(self) -> None:
        if self._camera is None:
            return
        self._camera.stop()
        self._camera.close()
        self._camera = None


class NoCameraService(CameraService):
    """Null camera implementation for IR-only operation."""

    def start(self) -> None:
        print("camera=disabled (IR-only mode)")

    def capture_frame(self) -> bytes | None:
        return None

    def stop(self) -> None:
        return
