"""Application entrypoint."""

from smartblaster.services.runtime import SmartBlasterRuntime


def main() -> int:
    import sys
    print("[TRACE] Entering smartblaster.main.main()", file=sys.stderr)
    try:
        runtime = SmartBlasterRuntime.from_env()
        print("[TRACE] SmartBlasterRuntime created", file=sys.stderr)
        runtime.run_forever()
        print("[TRACE] run_forever() exited", file=sys.stderr)
        return 0
    except Exception as e:
        import traceback
        print("[ERROR] Exception in smartblaster.main.main():", file=sys.stderr)
        traceback.print_exc()
        return 1
