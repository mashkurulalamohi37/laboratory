"""Create the object-storage buckets if missing (idempotent).

python -m app.scripts.init_storage
"""

from __future__ import annotations

import sys
import time

from app.core.storage import ensure_buckets


def main(retries: int = 20) -> None:
    for attempt in range(1, retries + 1):
        try:
            created = ensure_buckets()
        except Exception as exc:  # storage may still be starting
            if attempt == retries:
                raise
            sys.stdout.write(f"[wait] storage not ready ({type(exc).__name__}), retrying\n")
            time.sleep(2)
            continue
        sys.stdout.write(f"[ok] buckets ready ({len(created)} created)\n")
        return


if __name__ == "__main__":
    main()
