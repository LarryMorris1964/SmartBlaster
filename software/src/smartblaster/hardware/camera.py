"""Camera abstraction layer."""

from __future__ import annotations


class CameraService:
    def start(self) -> None:
        # TODO: initialize picamera2 pipeline
        pass

    def capture_frame(self) -> bytes | None:
        # TODO: return encoded frame or structured data
        return None

    def stop(self) -> None:
        pass


class NoCameraService(CameraService):
    """Null camera implementation for IR-only operation."""

    def start(self) -> None:
        print("camera=disabled (IR-only mode)")

    def capture_frame(self) -> bytes | None:
        return None

    def stop(self) -> None:
        return
