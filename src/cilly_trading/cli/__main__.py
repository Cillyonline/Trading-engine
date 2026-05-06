"""Allow ``python -m cilly_trading.cli`` to invoke the admin CLI (issue #1140)."""

from __future__ import annotations

import sys

from cilly_trading.cli.admin import main


if __name__ == "__main__":
    sys.exit(main())
