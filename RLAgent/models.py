# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# models.py
"""
Data models for the Warehouse Picker Environment.

The agent navigates a grid warehouse, picks items from shelves,
and delivers them to a dispatch zone.
"""

from typing import List, Tuple
from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class WarehouseAction(Action):
    """
    Action for the Warehouse Picker environment.

    0 = move up
    1 = move down
    2 = move left
    3 = move right
    4 = pick  (pick item at current or adjacent shelf cell)
    5 = deliver (deposit held item at dispatch zone)
    """

    action: int = Field(
        ...,
        ge=0,
        le=5,
        description="Action ID: 0=up, 1=down, 2=left, 3=right, 4=pick, 5=deliver",
    )


class WarehouseObservation(Observation):
    """Observation from the Warehouse Picker environment."""

    # Agent position on the grid
    agent_x: int = Field(default=0, description="Agent column position")
    agent_y: int = Field(default=0, description="Agent row position")

    # Order state — list of (x, y) for each item still needed
    remaining_items: List[Tuple[int, int]] = Field(
        default_factory=list,
        description="Grid positions of items not yet picked",
    )

    # Whether the agent is currently holding a picked item
    holding_item: bool = Field(
        default=False,
        description="True if the agent has picked an item and not yet delivered it",
    )

    # Dispatch zone location (so agent can learn to navigate there)
    dispatch_x: int = Field(default=0, description="Dispatch zone column")
    dispatch_y: int = Field(default=0, description="Dispatch zone row")

    # Progress counters
    items_delivered: int = Field(default=0, description="Number of items delivered so far")
    total_items: int = Field(default=0, description="Total items in this episode's order")
    steps_elapsed: int = Field(default=0, description="Steps taken so far this episode")
    max_steps: int = Field(default=100, description="Step budget for this episode")

    # Grid structure — shelf positions the agent cannot walk through
    shelf_positions: List[Tuple[int, int]] = Field(
        default_factory=list,
        description="Grid positions of impassable shelf cells",
    )

    # Standard OpenEnv fields
    done: bool = Field(default=False, description="True if the episode has ended")
    reward: float = Field(default=0.0, description="Reward received for the last action")