import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from openspiel_loa.benchmark import main

if __name__ == "__main__":
    main()
