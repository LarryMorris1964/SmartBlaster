"""Backward-compatible script entrypoint.

Prefer running `python -m smartblaster` from the software directory.
"""

from smartblaster.main import main


if __name__ == "__main__":
    import sys
    print("[TRACE] Entering main.py", file=sys.stderr)
    try:
        result = main()
        print(f"[TRACE] main() returned {result}", file=sys.stderr)
        raise SystemExit(result)
    except Exception as e:
        import traceback
        print("[ERROR] Exception in main.py:", file=sys.stderr)
        traceback.print_exc()
        raise SystemExit(1)
