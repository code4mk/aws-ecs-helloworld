"""Container health check that needs no curl/wget in the image.

Usage: python -m app.healthcheck   (exit 0 = healthy, 1 = unhealthy)
"""

import os
import sys
import urllib.request


def main() -> int:
    port = os.getenv("PORT", "8080")
    path = os.getenv("HEALTHCHECK_PATH", "/health")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as response:
            return 0 if response.status == 200 else 1
    except Exception as exc:
        print(f"healthcheck failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
