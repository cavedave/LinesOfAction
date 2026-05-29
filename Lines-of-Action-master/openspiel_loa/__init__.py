"""OpenSpiel bridge for Lines of Action (teacher bot, state export, benchmarks)."""

from .bridge import (
    action_to_grid_move,
    grid_move_to_action,
    observation_to_grid,
    record_step,
    state_to_record,
)
from .teacher import LoaTeacherBot, default_teacher_weights

__all__ = [
    "LoaTeacherBot",
    "default_teacher_weights",
    "observation_to_grid",
    "action_to_grid_move",
    "grid_move_to_action",
    "record_step",
    "state_to_record",
]
