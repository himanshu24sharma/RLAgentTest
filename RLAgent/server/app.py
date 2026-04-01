# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
"""
FastAPI application for the Warehouse Picker Environment.

Endpoints:
    - POST /reset: Reset the environment (accepts optional task= param)
    - POST /step: Execute an action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - GET /health: Health check endpoint
    - WS /ws: WebSocket endpoint for persistent sessions

Usage:
    uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
"""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError(
        "openenv is required. Install dependencies with '\n    uv sync\n'"
    ) from e

try:
    from models import WarehouseAction, WarehouseObservation
    from .RLAgent_environment import WarehouseEnvironment
except ModuleNotFoundError:
    from models import WarehouseAction, WarehouseObservation
    from server.RLAgent_environment import WarehouseEnvironment


app = create_app(
    WarehouseEnvironment,
    WarehouseAction,
    WarehouseObservation,
    env_name="WarehousePicker",
    max_concurrent_envs=4,
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "env": "WarehousePicker-v0"}


@app.get("/tasks")
async def list_tasks():
    """List available tasks and their configurations."""
    return {
        "tasks": {
            "single_item_fetch": {
                "difficulty": "easy",
                "grid": "6x5",
                "items": 1,
                "max_steps": 30,
            },
            "multi_item_order": {
                "difficulty": "medium",
                "grid": "10x8",
                "items": 3,
                "max_steps": 100,
            },
            "rush_order": {
                "difficulty": "hard",
                "grid": "12x10",
                "items": 5,
                "max_steps": 150,
            },
        }
    }


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)