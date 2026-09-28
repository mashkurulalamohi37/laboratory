"""Write the OpenAPI document to a file (input for the generated TypeScript client).

python -m app.scripts.export_openapi ../../packages/api-client/openapi.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    # The schema does not depend on secrets; placeholders let this run without a .env.
    os.environ.setdefault("JWT_SECRET", "openapi-export-placeholder-secret-0000000000")
    os.environ.setdefault("OTP_HMAC_SECRET", "openapi-export-placeholder-secret-0000000000")
    from app.main import create_app

    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    target.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(f"wrote {target}\n")


if __name__ == "__main__":
    main()
