import argparse, random
from typing import Dict, Tuple, List
from grader import grade, grade_all, GradeResult

MOVE_UP=0; MOVE_DOWN=1; MOVE_LEFT=2; MOVE_RIGHT=3; PICK=4; DELIVER=5

def _manhattan(a, b): return abs(a[0]-b[0]) + abs(a[1]-p[1])

def greedy_agent(obs: dict) -> int:
    ax, ay = obs["agent_x"], obs["agent_y"]
    holding = obs["holding_item"]
    dispatch = (obs["dispatch_x"], obs["dispatch_y"])
    remaining = obs["remaining_items"]
    W = obs["dispatch_x"]  # rightmost open column

    if holding:
        tx, ty = dispatch
    elif remaining:
        nearest = min(remaining, key=lambda p: abs(ax-p[0])+abs(ay-p[1]))
        tx, ty = nearest[0], nearest[1]
    else:
        tx, ty = dispatch

    if (ax, ay) == (tx, ty):
        if holding: return DELIVER
        if any(p[0]==ax and p[1]==ay for p in remaining): return PICK
        return MOVE_RIGHT

    # Check if a shelf row blocks the vertical path
    shelf_rows = list(range(2, 20, 2))
    blocked = any(min(ay,ty) < r < max(ay,ty) or (ay==r and r!=ty) for r in shelf_rows)

    if blocked:
        if ax != W:
            # Step 1: go to open column first
            return MOVE_RIGHT if ax < W else MOVE_LEFT
        else:
            # Step 2: at open column — finish vertical movement first
            if ay != ty:
                return MOVE_DOWN if ay < ty else MOVE_UP
            # Step 3: then go horizontal to target
            return MOVE_LEFT if ax > tx else MOVE_RIGHT

    # No shelf blocking — horizontal first then vertical
    if ax != tx: return MOVE_RIGHT if ax < tx else MOVE_LEFT
    if ay != ty: return MOVE_DOWN if ay < ty else MOVE_UP
    return MOVE_RIGHT

def print_summary(results):
    print("\n" + "="*52)
    print("  WarehousePicker-v0 — Baseline Results")
    print("="*52)
    for task, r in results.items():
        bar = "█"*int(r.score*20) + "░"*(20-int(r.score*20))
        print(f"\n  {task}")
        print(f"  [{bar}] {r.score:.3f}")
        print(f"  Items: {r.items_delivered}/{r.total_items}  Steps: {r.steps_used}/{r.max_steps}  Completed: {r.completed}")
        print(f"  Breakdown → completion: {r.completion_score:.2f}  efficiency: {r.efficiency_score:.2f}  bonus: {r.bonus_score:.2f}")
    avg = sum(r.score for r in results.values()) / len(results)
    print(f"\n{'─'*52}\n  Average score : {avg:.3f}\n{'='*52}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["single_item_fetch","multi_item_order","rush_order","all"], default="all")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    random.seed(args.seed)
    if args.task == "all":
        results = grade_all(greedy_agent, seed=args.seed, verbose=args.verbose)
    else:
        results = {args.task: grade(args.task, greedy_agent, seed=args.seed, verbose=args.verbose)}
    print_summary(results)

if __name__ == "__main__":
    main()
