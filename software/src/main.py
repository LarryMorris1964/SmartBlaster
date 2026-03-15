"""Backward-compatible script entrypoint.

Prefer running `python -m smartblaster` from the software directory.
"""

from smartblaster.main import main


if __name__ == "__main__":
    raise SystemExit(main())
