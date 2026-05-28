"""Run: ``cd Lines-of-Action-master && python -m harness --a best --b random --games 4``

Or championship-style::

    python -m harness compare --champion best --challenger minimax_d4_bbox12 --rounds 100 --dim 8

Mobility weight sweep (classic vs each ``minimax_d3_mobN``)::

    python -m harness sweep-mobility --games 100 --random-opening --opening-seed 42 --dim 8

``a_wins`` in JSON counts wins for ``--champion``.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()

from harness.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
