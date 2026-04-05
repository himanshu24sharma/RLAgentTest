# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
"""
Warehouse Picker Environment.

A grid-based warehouse where an agent navigates aisles, picks items
from shelves, and delivers them to a dispatch zone.

Grid cell types:
    0 = empty floor
    1 = shelf (impassable, items sit next to shelves)
    2 = dispatch zone
    3 = agent

Tasks:
    single_item_fetch  (easy)   — 1 item,  6x5  grid, 30  steps
    multi_item_order   (medium) — 3 items, 10x8 grid, 100 steps
    rush_order         (hard)   — 5 items, 12x10 grid, 150 steps
"""

import random
from uuid import uuid4
from typing import List, Tuple, Dict, Any

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..models import WarehouseAction, WarehouseObservation
except ImportError:
    from models import WarehouseAction, WarehouseObservation


# ---------------------------------------------------------------------------
# Task configurations
# ---------------------------------------------------------------------------

TASKS: Dict[str, Dict[str, Any]] = {
    "single_item_fetch": {
        "grid_w": 6,
        "grid_h": 5,
        "num_items": 1,
        "max_steps": 30,
    },
    "multi_item_order": {
        "grid_w": 10,
        "grid_h": 8,
        "num_items": 3,
        "max_steps": 100,
    },
    "rush_order": {
        "grid_w": 12,
        "grid_h": 10,
        "num_items": 5,
        "max_steps": 150,
    },
}

DEFAULT_TASK = "single_item_fetch"

# ---------------------------------------------------------------------------
# Reward constants
# ---------------------------------------------------------------------------

R_PICK             =  1.0
R_DELIVER          =  2.0
R_COMPLETION_BONUS =  5.0
R_STEP             = -0.01
R_INVALID          = -0.2
R_COLLISION        = -0.1

# Action constants
MOVE_UP    = 0
MOVE_DOWN  = 1
MOVE_LEFT  = 2
MOVE_RIGHT = 3
PICK       = 4
DELIVER    = 5

DELTAS = {
    MOVE_UP:    (0, -1),
    MOVE_DOWN:  (0,  1),
    MOVE_LEFT:  (-1, 0),
    MOVE_RIGHT: (1,  0),
}


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class WarehouseEnvironment(Environment):
    """
    Warehouse Picker environment.

    The agent must navigate a 2-D grid, pick items from shelf-adjacent
    floor cells, and deliver them one-at-a-time to the dispatch zone.

    Supports three difficulty tasks set via reset(task=...).
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, task: str = DEFAULT_TASK):
        self._task_name = task if task in TASKS else DEFAULT_TASK
        self._cfg = TASKS[self._task_name]

        # Grid dimensions
        self._W: int = self._cfg["grid_w"]
        self._H: int = self._cfg["grid_h"]
        self._max_steps: int = self._cfg["max_steps"]
        self._num_items: int = self._cfg["num_items"]

        # Runtime state (populated in reset)
        self._grid: List[List[int]] = []
        self._agent_pos: Tuple[int, int] = (0, 0)
        self._dispatch_pos: Tuple[int, int] = (0, 0)
        self._item_positions: List[Tuple[int, int]] = []   # all item floor cells
        self._remaining_items: List[Tuple[int, int]] = []  # items not yet picked
        self._holding_item: bool = False
        self._items_delivered: int = 0
        self._done: bool = False

        self._state = State(episode_id=str(uuid4()), step_count=0)
        self.reset()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self, task: str = "") -> WarehouseObservation:
        """Reset the environment, optionally switching task difficulty."""
        if task and task in TASKS:
            self._task_name = task
            self._cfg = TASKS[task]
            self._W = self._cfg["grid_w"]
            self._H = self._cfg["grid_h"]
            self._max_steps = self._cfg["max_steps"]
            self._num_items = self._cfg["num_items"]

        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._holding_item = False
        self._items_delivered = 0
        self._done = False

        self._build_grid()

        return self._make_obs(reward=0.0)

    def step(self, action: WarehouseAction) -> WarehouseObservation:  # type: ignore[override]
        """Execute one action and return the resulting observation."""
        if self._done:
            # Episode already over — return terminal obs with no reward
            return self._make_obs(reward=0.0)

        self._state.step_count += 1
        reward = R_STEP  # small step penalty every tick

        a = action.action

        if a in DELTAS:
            reward += self._handle_move(a)
        elif a == PICK:
            reward += self._handle_pick()
        elif a == DELIVER:
            reward += self._handle_deliver()
        else:
            reward += R_INVALID

        # Check step budget
        if self._state.step_count >= self._max_steps:
            self._done = True

        return self._make_obs(reward=reward)

    @property
    def state(self) -> State:
        return self._state

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _handle_move(self, action: int) -> float:
        dx, dy = DELTAS[action]
        nx, ny = self._agent_pos[0] + dx, self._agent_pos[1] + dy

        if not self._in_bounds(nx, ny):
            return R_COLLISION

        cell = self._grid[ny][nx]
        if cell == 1:  # shelf — impassable
            return R_COLLISION

        self._agent_pos = (nx, ny)
        return 0.0

    def _handle_pick(self) -> float:
        """
        Pick succeeds if the agent is standing on a floor cell that is
        in _remaining_items AND is not already holding something.
        """
        if self._holding_item:
            return R_INVALID  # already carrying

        ax, ay = self._agent_pos
        if (ax, ay) in self._remaining_items:
            self._remaining_items.remove((ax, ay))
            self._holding_item = True
            return R_PICK

        return R_INVALID  # nothing here to pick

    def _handle_deliver(self) -> float:
        """
        Deliver succeeds when the agent is on the dispatch zone
        and is holding an item.
        """
        if not self._holding_item:
            return R_INVALID

        if self._agent_pos == self._dispatch_pos:
            self._holding_item = False
            self._items_delivered += 1

            bonus = 0.0
            if not self._remaining_items and not self._holding_item:
                # All items delivered
                self._done = True
                bonus = R_COMPLETION_BONUS

            return R_DELIVER + bonus

        return R_INVALID  # not at dispatch zone

    # ------------------------------------------------------------------
    # Grid builder
    # ------------------------------------------------------------------

    def _build_grid(self) -> None:
        """
        Build a simple warehouse grid:
          - Dispatch zone at bottom-right corner
          - Shelf rows across the middle
          - Item floor cells randomly chosen adjacent to shelves
          - Agent starts at top-left
        """
        W, H = self._W, self._H

        # Start with all empty floor
        grid = [[0] * W for _ in range(H)]

        # Dispatch zone — bottom-right cell
        dispatch_x, dispatch_y = W - 1, H - 1
        grid[dispatch_y][dispatch_x] = 2
        self._dispatch_pos = (dispatch_x, dispatch_y)

        # Place shelf rows: one row of shelves every 2 rows, leaving
        # floor lanes the agent can walk in.
        shelf_cells: List[Tuple[int, int]] = []
        for row in range(2, H - 1, 2):
            for col in range(1, W - 1):
                grid[row][col] = 1
                shelf_cells.append((col, row))

        # Item pick-up positions are floor cells directly above or below a shelf
        candidate_pick_cells: List[Tuple[int, int]] = []
        for (sx, sy) in shelf_cells:
            for dy in [-1, 1]:
                ny = sy + dy
                if 0 <= ny < H and grid[ny][sx] == 0:
                    candidate_pick_cells.append((sx, ny))

        # Remove duplicates and shuffle
        candidate_pick_cells = list(set(candidate_pick_cells))
        random.shuffle(candidate_pick_cells)

        # Assign item positions (can't place on dispatch or agent start)
        forbidden = {(0, 0), self._dispatch_pos}
        pick_cells = [c for c in candidate_pick_cells if c not in forbidden]
        chosen = pick_cells[: self._num_items]

        # Fallback: if not enough shelf-adjacent cells, place on random floor
        if len(chosen) < self._num_items:
            floor_cells = [
                (x, y)
                for y in range(H)
                for x in range(W)
                if grid[y][x] == 0 and (x, y) not in forbidden and (x, y) not in chosen
            ]
            random.shuffle(floor_cells)
            chosen += floor_cells[: self._num_items - len(chosen)]

        self._item_positions = chosen[:]
        self._remaining_items = chosen[:]

        self._grid = grid
        self._agent_pos = (0, 0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self._W and 0 <= y < self._H

    def _make_obs(self, reward: float) -> WarehouseObservation:
        return WarehouseObservation(
            agent_x=self._agent_pos[0],
            agent_y=self._agent_pos[1],
            remaining_items=list(self._remaining_items),
            holding_item=self._holding_item,
            dispatch_x=self._dispatch_pos[0],
            dispatch_y=self._dispatch_pos[1],
            items_delivered=self._items_delivered,
            total_items=self._num_items,
            steps_elapsed=self._state.step_count,
            max_steps=self._max_steps,
            shelf_positions=[
                (x, y)
                for y in range(self._H)
                for x in range(self._W)
                if self._grid[y][x] == 1
            ],
            done=self._done,
            reward=reward,
        )