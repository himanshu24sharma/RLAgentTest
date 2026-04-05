# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
# client.py
# client.py
"""Warehouse Picker Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import WarehouseAction, WarehouseObservation


class RlagentEnv(EnvClient[WarehouseAction, WarehouseObservation, State]):
    """
    Client for the WarehousePicker-v0 Environment.

    Example:
        >>> with RlagentEnv(base_url="http://localhost:8000").sync() as client:
        ...     obs = client.reset()
        ...     obs = client.step(WarehouseAction(action=3))  # move right
        ...     print(obs.observation.agent_x, obs.observation.reward)
    """

    def _step_payload(self, action: WarehouseAction) -> Dict:
        # Server expects {"action": {"action": <int>}}
        return {"action": action.action}

    def _parse_result(self, payload: Dict) -> StepResult[WarehouseObservation]:
        obs_data = payload.get("observation", {})
        # done and reward are at the TOP LEVEL of the payload, not inside observation
        done   = payload.get("done", False)
        reward = payload.get("reward", 0.0)

        observation = WarehouseObservation(
            agent_x=obs_data.get("agent_x", 0),
            agent_y=obs_data.get("agent_y", 0),
            remaining_items=obs_data.get("remaining_items", []),
            holding_item=obs_data.get("holding_item", False),
            dispatch_x=obs_data.get("dispatch_x", 0),
            dispatch_y=obs_data.get("dispatch_y", 0),
            items_delivered=obs_data.get("items_delivered", 0),
            total_items=obs_data.get("total_items", 0),
            steps_elapsed=obs_data.get("steps_elapsed", 0),
            max_steps=obs_data.get("max_steps", 100),
            shelf_positions=obs_data.get("shelf_positions", []), 
            done=done,
            reward=reward,
        )
        return StepResult(
            observation=observation,
            reward=reward,
            done=done,
        )

    def _parse_state(self, payload: Dict) -> State:
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )