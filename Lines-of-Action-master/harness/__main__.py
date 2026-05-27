"""Run: ``cd Lines-of-Action-master && python -m harness --a minimax_d1 --b random --games 4``

Or championship-style::

    python -m harness compare --champion minimax_d3 --challenger minimax_d4_bbox12 --rounds 100 --dim 8

``a_wins`` in JSON counts wins for ``--champion``.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()

from harness.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
