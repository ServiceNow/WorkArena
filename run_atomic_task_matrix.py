#!/usr/bin/env python
import argparse
import concurrent.futures
import json
import logging
import os
import random
import traceback
from collections import defaultdict
from typing import Any, Dict, List, Tuple

import browsergym.core
from browsergym.workarena import ATOMIC_TASKS
from browsergym.workarena.instance import SNowInstance, fetch_instances
import pandas as pd
from playwright.sync_api import sync_playwright
from tenacity import retry, retry_if_exception_type, stop_after_attempt

TaskJob = Tuple[str, int, Dict[str, str]]
TASKS_BY_ID = {task.get_task_id(): task for task in ATOMIC_TASKS}


def _serialize_config(config: Any) -> Any:
    if config is None:
        return None
    try:
        return json.loads(json.dumps(config, default=str))
    except Exception:
        return repr(config)


def _run_task_attempt(
    task_id: str,
    seed: int,
    instance_entry: Dict[str, str],
    headless: bool,
    config_holder: Dict[str, Any] | None = None,
):
    """Run a single task attempt, mirroring tests/test_task_general.py."""
    pw = sync_playwright().start()
    browsergym.core._set_global_playwright(pw)
    browser = None
    page = None
    browser = pw.chromium.launch(headless=headless)
    page = browser.new_page()
    task = None
    task_config = None
    try:
        instance = SNowInstance(
            snow_url=instance_entry["url"],
            snow_credentials=("admin", instance_entry["password"]),
        )
        task_cls = TASKS_BY_ID[task_id]
        task = task_cls(seed=seed, instance=instance)
        task.setup(page=page)
        task_config = _serialize_config(task.__dict__)
        chat_messages: List[Dict[str, Any]] = []
        reward, done, message, info = task.validate(page, chat_messages)
        if done or reward != 0.0:
            raise AssertionError(
                f"Pre-cheat validation failed for {task_id} seed {seed} on {instance_entry['url']} "
                f"(reward={reward}, done={done})"
            )
        if not isinstance(message, str) or not isinstance(info, dict):
            raise AssertionError(
                f"Validation outputs unexpected types for {task_id} seed {seed} on {instance_entry['url']}"
            )
        task.cheat(page=page, chat_messages=chat_messages)
        reward, done, _, _ = task.validate(page, chat_messages)
        if not done or reward != 1.0:
            raise AssertionError(
                f"Post-cheat validation failed for {task_id} seed {seed} on {instance_entry['url']} "
                f"(reward={reward}, done={done})"
            )
    finally:
        if task:
            try:
                task.teardown()
            except Exception:
                logging.exception(
                    "Teardown failed for %s seed %s on %s", task_id, seed, instance_entry["url"]
                )
        if page:
            page.close()
        if browser:
            browser.close()
        pw.stop()
        if config_holder is not None:
            config_holder["config"] = task_config
    return task_config


def _run_task(task_id: str, seed: int, instance_entry: Dict[str, str], headless: bool) -> Dict[str, Any]:
    config_holder: Dict[str, Any] = {"config": None}

    @retry(
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _attempt():
        return _run_task_attempt(task_id, seed, instance_entry, headless, config_holder=config_holder)

    try:
        config = _attempt()
        return {
            "ok": True,
            "task_id": task_id,
            "seed": seed,
            "instance_url": instance_entry["url"],
            "config": config,
        }
    except Exception as exc:
        return {
            "ok": False,
            "task_id": task_id,
            "seed": seed,
            "instance_url": instance_entry["url"],
            "error": repr(exc),
            "traceback": traceback.format_exc(),
            "config": config_holder.get("config"),
        }


def build_jobs(task_ids: List[str], seeds: List[int], instances: List[Dict[str, str]]) -> List[TaskJob]:
    jobs: List[TaskJob] = []
    for task_id in task_ids:
        for seed in seeds:
            for instance_entry in instances:
                jobs.append((task_id, seed, instance_entry))
    return jobs


def main():
    parser = argparse.ArgumentParser(description="Run cheat/validate checks over all atomic tasks.")
    parser.add_argument(
        "--task-id",
        type=str,
        default=None,
        help="Run only this task id (default: all atomic tasks).",
    )
    parser.add_argument(
        "--seed-count",
        type=int,
        default=1,
        help="Number of random seeds to run (default: 1). Ignored if --seeds is provided.",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=None,
        help="Explicit list of seeds to run (overrides --seed-count).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        help="Number of worker processes for parallel runs (default: CPU count).",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Playwright in headed mode (default: headless).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    instances = fetch_instances()
    if not instances:
        raise SystemExit("No ServiceNow instances available.")

    if args.task_id:
        if args.task_id not in TASKS_BY_ID:
            raise SystemExit(f"Unknown task id: {args.task_id}")
        task_ids = [args.task_id]
    else:
        task_ids = list(TASKS_BY_ID.keys())

    if args.seeds is not None:
        seeds = args.seeds
    else:
        seeds_set = set()
        # Generate unique random seeds to avoid clustered runs.
        while len(seeds_set) < args.seed_count:
            seeds_set.add(random.randint(0, 2**31 - 1))
        seeds = sorted(seeds_set)

    jobs = build_jobs(task_ids, seeds, instances)
    total_jobs = len(jobs)
    logging.info(
        "Starting %s runs across %s instances, %s task(s), %s seed(s) with %s workers.",
        total_jobs,
        len(instances),
        len(task_ids),
        len(seeds),
        args.workers,
    )

    results: List[Dict[str, Any]] = []
    config_by_task_seed: dict[Tuple[str, int], Any] = {}
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(_run_task, job[0], job[1], job[2], not args.headed): job for job in jobs}
        for idx, future in enumerate(concurrent.futures.as_completed(future_map), start=1):
            res = future.result()
            results.append(res)
            key = (res["task_id"], res["seed"])
            if key not in config_by_task_seed and res.get("config") is not None:
                config_by_task_seed[key] = res["config"]
            if res["ok"]:
                logging.info(
                    "[%s/%s] OK %s seed=%s instance=%s",
                    idx,
                    total_jobs,
                    res["task_id"],
                    res["seed"],
                    res["instance_url"],
                )
            else:
                logging.error(
                    "[%s/%s] FAIL %s seed=%s instance=%s error=%s",
                    idx,
                    total_jobs,
                    res["task_id"],
                    res["seed"],
                    res["instance_url"],
                    res["error"],
                )

    failures = [r for r in results if not r["ok"]]
    logging.info("Completed runs: %s success / %s failed.", len(results) - len(failures), len(failures))

    if not failures:
        print("All runs succeeded.")
        return

    instance_failures: defaultdict[str, int] = defaultdict(int)
    task_seed_failures: defaultdict[Tuple[str, int], int] = defaultdict(int)
    for res in failures:
        instance_failures[res["instance_url"]] += 1
        task_seed_failures[(res["task_id"], res["seed"])] += 1

    runs_per_instance = len(task_ids) * len(seeds)
    runs_per_task_seed = len(instances)

    # Task failure ranking
    task_failure_rows = []
    for (task_id, seed), fail_count in task_seed_failures.items():
        failure_rate = fail_count / runs_per_task_seed
        if fail_count == runs_per_task_seed:
            status = "confirmed_broken"
            status_rank = 3
        elif fail_count > runs_per_task_seed / 2:
            status = "likely_broken"
            status_rank = 2
        else:
            status = "unlikely_broken"
            status_rank = 1
        task_failure_rows.append(
            {
                "task_id": task_id,
                "seed": seed,
                "failures": fail_count,
                "total_instances": runs_per_task_seed,
                "failure_rate": round(failure_rate, 3),
                "status": status,
                "config": config_by_task_seed.get((task_id, seed)),
                "status_rank": status_rank,
            }
        )

    if task_failure_rows:
        df = pd.DataFrame(task_failure_rows)
        df = df.sort_values(by=["status_rank", "failures"], ascending=[False, False])
        df = df.drop(columns=["status_rank"])
        df_print = df.drop(columns=["config"], errors="ignore")
        print("\nTask failure ranking (sorted):")
        print(df_print.to_string(index=False))
        df.to_csv("task_failure_ranking.csv", index=False)
        print("Saved task failure ranking to task_failure_ranking.csv")
    else:
        print("\nNo task failures recorded.")

    # Instance failure flagging
    confirmed_broken_count = sum(1 for row in task_failure_rows if row["status"] == "confirmed_broken")
    instance_rows = []
    for instance_url, count in instance_failures.items():
        failure_rate = count / runs_per_instance if runs_per_instance else 0.0
        flagged = count > confirmed_broken_count
        instance_rows.append(
            {
                "instance_url": instance_url,
                "failures": count,
                "total_runs": runs_per_instance,
                "failure_rate": round(failure_rate, 3),
                "flagged": flagged,
            }
        )

    if instance_rows:
        df_instances = pd.DataFrame(instance_rows)
        df_instances = df_instances.sort_values(by=["flagged", "failures"], ascending=[False, False])
        print("\nInstance failures (pandas view):")
        print(df_instances.to_string(index=False))
        df_instances.to_csv("instance_failures.csv", index=False)
        print("Saved instance failures to instance_failures.csv")
    else:
        print("\nNo instance failures recorded.")


if __name__ == "__main__":
    main()
