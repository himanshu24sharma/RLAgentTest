"""
grader.py — Warehouse Picker task grader.

Scores an agent's episode 0.0–1.0 using:
    60% — item completion  (items delivered / total items)
    30% — step efficiency  (1 - steps_used / max_steps)
    10% — full completion bonus

Usage:
    from grader import grade
    score = grade(task="single_item_fetch", run_episode_fn=my_fn)
"""

from dataclasses import dataclass
from typing import Callable, Dict

try:
    from server.RLAgent_environment import WarehouseEnvironment, TASKS
    from models import WarehouseAction
except ModuleNotFoundError:
    from RLAgent.server.RLAgent_environment import WarehouseEnvironment, TASKS
    from RLAgent.models import WarehouseAction


# ---------------------------------------------------------------------------
# Score dataclass
# ---------------------------------------------------------------------------

@dataclass
class GradeResult:
    task: str
    score: float                  # final 0.0–1.0
    items_delivered: int
    total_items: int
    steps_used: int
    max_steps: int
    completed: bool               # all items delivered before step budget

    # Sub-scores for transparency
    completion_score: float
    efficiency_score: float
    bonus_score: float

    def __str__(self) -> str:
        return (
            f"[{self.task}]\n"
            f"  Score        : {self.score:.3f}\n"
            f"  Items        : {self.items_delivered}/{self.total_items}\n"
            f"  Steps        : {self.steps_used}/{self.max_steps}\n"
            f"  Completed    : {self.completed}\n"
            f"  Breakdown    : completion={self.completion_score:.2f} "
            f"efficiency={self.efficiency_score:.2f} bonus={self.bonus_score:.2f}"
        )


# ---------------------------------------------------------------------------
# Core scoring formula
# ---------------------------------------------------------------------------

def compute_score(
    items_delivered: int,
    total_items: int,
    steps_used: int,
    max_steps: int,
    completed: bool,
) -> GradeResult:
    """
    Score formula:
        completion  = (items_delivered / total_items) * 0.6
        efficiency  = (1 - steps_used / max_steps)   * 0.3
        bonus       = 0.1 if completed else 0.0
        total       = completion + efficiency + bonus
    """
    completion  = (items_delivered / total_items) * 0.6 if total_items > 0 else 0.0
    efficiency  = max(0.0, 1.0 - steps_used / max_steps) * 0.3
    bonus       = 0.1 if completed else 0.0
    total       = round(completion + efficiency + bonus, 4)

    return GradeResult(
        task="",
        score=total,
        items_delivered=items_delivered,
        total_items=total_items,
        steps_used=steps_used,
        max_steps=max_steps,
        completed=completed,
        completion_score=completion,
        efficiency_score=efficiency,
        bonus_score=bonus,
    )


# ---------------------------------------------------------------------------
# Grade a single task by running an agent callable
# ---------------------------------------------------------------------------

def grade(
    task: str,
    agent_fn: Callable[[dict], int],
    seed: int = 42,
    verbose: bool = False,
) -> GradeResult:
    """
    Run one episode and return a GradeResult.

    Args:
        task:      One of "single_item_fetch", "multi_item_order", "rush_order"
        agent_fn:  Callable that receives an observation dict and returns
                   an action int (0-5). This is your agent's policy.
        seed:      Random seed for reproducibility.
        verbose:   Print step-by-step info.

    Returns:
        GradeResult with score and breakdown.

    Example:
        def random_agent(obs): return random.randint(0, 5)
        result = grade("single_item_fetch", random_agent)
        print(result)
    """
    import random
    random.seed(seed)

    if task not in TASKS:
        raise ValueError(f"Unknown task '{task}'. Choose from: {list(TASKS.keys())}")

    env = WarehouseEnvironment(task=task)
    obs = env.reset(task=task)

    while not obs.done:
        obs_dict = obs.model_dump()
        action_id = agent_fn(obs_dict)

        if verbose:
            print(
                f"step={obs.steps_elapsed:3d} | "
                f"pos=({obs.agent_x},{obs.agent_y}) | "
                f"holding={obs.holding_item} | "
                f"remaining={len(obs.remaining_items)} | "
                f"action={action_id} | "
                f"reward={obs.reward:.2f}"
            )

        obs = env.step(WarehouseAction(action=action_id))

    result = compute_score(
        items_delivered=obs.items_delivered,
        total_items=obs.total_items,
        steps_used=obs.steps_elapsed,
        max_steps=obs.max_steps,
        completed=obs.items_delivered == obs.total_items,
    )
    result.task = task

    if verbose:
        print(result)

    return result


# ---------------------------------------------------------------------------
# Grade all three tasks
# ---------------------------------------------------------------------------

def grade_all(
    agent_fn: Callable[[dict], int],
    seed: int = 42,
    verbose: bool = True,
) -> Dict[str, GradeResult]:
    """
    Run all three tasks and return a dict of results.

    Returns:
        {"single_item_fetch": GradeResult, "multi_item_order": ..., "rush_order": ...}
    """
    results = {}
    for task in TASKS:
        results[task] = grade(task, agent_fn, seed=seed, verbose=verbose)

    if verbose:
        avg = sum(r.score for r in results.values()) / len(results)
        print(f"\nAverage score across all tasks: {avg:.3f}")

    return results