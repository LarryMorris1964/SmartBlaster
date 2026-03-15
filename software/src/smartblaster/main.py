"""Application entrypoint."""

from smartblaster.services.runtime import SmartBlasterRuntime


def main() -> int:
    runtime = SmartBlasterRuntime.from_env()
    runtime.run_forever()
    return 0
