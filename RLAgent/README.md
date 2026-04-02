---
title: Warehouse Picker Environment
emoji: 📦
colorFrom: yellow
colorTo: green
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - reinforcement-learning
  - warehouse
---

# 📦 WarehousePicker-v0

A grid-based reinforcement learning environment simulating a **warehouse order fulfillment agent**.

The agent must:
- Navigate warehouse aisles on a 2D grid
- Pick items from shelf-adjacent floor cells
- Deliver them one at a time to a dispatch zone

The objective is to **complete all deliveries in the fewest steps possible**.

---

## Quick Start

### 1. Clone and build

```bash
git clone <your-repo-url>
cd RLAgentTest/RLAgent
docker build -t rlagent -f server/Dockerfile .
```

### 2. Run the container

```bash
docker run -p 8000:8000 -p 8888:8888 rlagent
```

### 3. Install Jupyter (one time)

```bash
docker exec -it <container_id> /app/.venv/bin/pip install jupyterlab --quiet
```

### 4. Launch Jupyter

```bash
docker exec -it <container_id> /app/.venv/bin/jupyter lab \
  --ip=0.0.0.0 --port=8888 --no-browser --allow-root
```

Open the URL printed in the terminal (e.g. `http://127.0.0.1:8888/lab?token=...`), then open `script.ipynb` and run all cells.

---

## Verify the environment

Run the test suite inside the container:

```bash
docker exec -it <container_id> bash
cd /app/env
python test.py
```

Expected output:
```
ALL TESTS PASSED — environment is ready
```

Run the baseline agent to reproduce scores:

```bash
python baseline.py
```

Expected output:
```
  single_item_fetch   [█████████████████░░░] 0.870
  multi_item_order    [████████████████░░░░] 0.814
  rush_order          [████████████████░░░░] 0.804
  Average score : 0.829
```

---

## Environment Details

### Action space

Discrete — 6 actions:

| ID | Action | Description |
|----|--------|-------------|
| 0 | Move up | Move agent one cell north |
| 1 | Move down | Move agent one cell south |
| 2 | Move left | Move agent one cell west |
| 3 | Move right | Move agent one cell east |
| 4 | Pick | Pick item at current cell |
| 5 | Deliver | Deposit held item at dispatch zone |

### Observation space

| Field | Type | Description |
|-------|------|-------------|
| agent_x, agent_y | int | Agent position on the grid |
| remaining_items | list | (x, y) positions of items not yet picked |
| holding_item | bool | Whether the agent is carrying an item |
| dispatch_x, dispatch_y | int | Dispatch zone position |
| items_delivered | int | Items delivered so far |
| total_items | int | Total items in this order |
| steps_elapsed | int | Steps taken this episode |
| max_steps | int | Step budget for this episode |
| done | bool | Whether the episode has ended |
| reward | float | Reward from last action |

### Reward function

| Event | Reward |
|-------|--------|
| Successful pick | +1.0 |
| Successful delivery | +2.0 |
| All items delivered | +5.0 bonus |
| Each step taken | −0.01 |
| Invalid action | −0.2 |
| Collision with wall/shelf | −0.1 |

---

## Tasks

Three difficulty levels, each graded 0.0–1.0:

| Task | Difficulty | Grid | Items | Max Steps | Passing Threshold |
|------|-----------|------|-------|-----------|-------------------|
| single_item_fetch | Easy | 6×5 | 1 | 30 | 0.8 |
| multi_item_order | Medium | 10×8 | 3 | 100 | 0.6 |
| rush_order | Hard | 12×10 | 5 | 150 | 0.5 |

### Scoring formula

```
score = (items_delivered / total_items) * 0.6
      + max(0, 1 - steps_used / max_steps) * 0.3
      + (0.1 if completed else 0.0)
```

---

## Baseline scores (seed=42, greedy heuristic agent)

| Task | Score | Items | Steps | Completed |
|------|-------|-------|-------|-----------|
| single_item_fetch | 0.870 | 1/1 | 13/30 | Yes |
| multi_item_order | 0.814 | 3/3 | 62/100 | Yes |
| rush_order | 0.804 | 5/5 | 98/150 | Yes |
| **Average** | **0.829** | | | |

---

## Deploying to Hugging Face Spaces

```bash
# From the RLAgent directory
openenv push

# Or with options
openenv push --repo-id my-org/warehouse-picker --private
```

After deployment your space will have:
- **Web Interface** at `/web` — interactive UI
- **API Docs** at `/docs` — Swagger interface
- **Health Check** at `/health`
- **WebSocket** at `/ws` — persistent low-latency sessions

---

## Project structure

```
RLAgent/
├── __init__.py                 # Module exports (WarehouseEnv, WarehouseAction)
├── client.py                   # HTTP/WebSocket client
├── models.py                   # WarehouseAction & WarehouseObservation
├── grader.py                   # Task scorer (0.0 → 1.0)
├── baseline.py                 # Greedy heuristic baseline agent
├── test.py                     # Environment verification suite
├── script.ipynb                # Interactive notebook demo
├── openenv.yaml                # OpenEnv manifest
├── pyproject.toml              # Project metadata and dependencies
├── README.md                   # This file
└── server/
    ├── RLAgent_environment.py  # Warehouse grid world
    ├── app.py                  # FastAPI server
    ├── __init__.py
    └── Dockerfile
```