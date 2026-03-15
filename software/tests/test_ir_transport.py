from io import StringIO

from smartblaster.ir.command import MideaIrCommand, MideaMode
from smartblaster.ir.transport import Esp32IrBridgeClient


class FakeDuplexStream(StringIO):
    """Simple in-memory stream: captures writes and serves prepared reads."""

    def __init__(self, read_lines: list[str]) -> None:
        super().__init__()
        self._read_lines = read_lines

    def readline(self, size: int = -1) -> str:
        if not self._read_lines:
            return ""
        return self._read_lines.pop(0)



def test_send_command_and_ack_roundtrip() -> None:
    stream = FakeDuplexStream(['{"v":1,"topic":"midea_ir.ack","request_id":"req-42","ok":true}\n'])
    client = Esp32IrBridgeClient(stream)

    cmd = MideaIrCommand(mode=MideaMode.COOL, temperature_c=24)
    ack = client.send_command(cmd, request_id="req-42")

    written = stream.getvalue()
    assert '"topic":"midea_ir.command"' in written
    assert '"request_id":"req-42"' in written
    assert ack["ok"] is True


def test_wait_for_ack_skips_other_request_ids() -> None:
    stream = FakeDuplexStream(
        [
            '{"v":1,"topic":"midea_ir.ack","request_id":"req-other","ok":true}\n',
            '{"v":1,"topic":"midea_ir.ack","request_id":"req-99","ok":true}\n',
        ]
    )
    client = Esp32IrBridgeClient(stream)

    ack = client.wait_for_ack(request_id="req-99", timeout_s=0.2)
    assert ack["request_id"] == "req-99"
