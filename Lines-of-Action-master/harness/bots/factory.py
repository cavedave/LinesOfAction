import json
from pathlib import Path

from LOA.heuristic_weights import HeuristicWeights

from .minimax import MinimaxBot
from .random_bot import RandomBot

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "registry.json"


def load_registry():
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def make_bot(bot_id: str, dim: int):
    reg = load_registry()
    if bot_id not in reg:
        raise KeyError(f"Unknown bot id {bot_id!r}; see harness/registry.json")
    spec = reg[bot_id]
    if "alias" in spec:
        return make_bot(spec["alias"], dim)
    t = spec["type"]
    if t == "minimax":
        weights = HeuristicWeights.from_mapping(spec.get("heuristic"))
        depth = int(spec.get("depth", 3))
        depth_deep = int(spec.get("depth_deep", depth + 1))
        adaptive = bool(spec.get("adaptive_depth", False))
        return MinimaxBot(
            dim,
            depth=depth,
            weights=weights,
            depth_deep=depth_deep,
            adaptive_depth=adaptive,
        )
    if t == "random":
        return RandomBot(dim, seed=int(spec.get("seed", 0)))
    raise ValueError(f"Unsupported bot type {t!r}")
