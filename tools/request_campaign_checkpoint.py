#!/usr/bin/env python3
"""Queue a validated one-shot original campaign-save launch request."""

try:
    from .request_tutorial_checkpoint import main
except ImportError:
    from request_tutorial_checkpoint import main


if __name__ == "__main__":
    main()
