#!/usr/bin/env python
"""
Count how many users were created recently on each ServiceNow instance in the pool.

This reuses the instance loader and table API helper from the codebase.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

WAND_ENTITY = "alexdrouin"
WAND_PROJECT = "workarena-monitoring"
RUN_VERSION = "v3"  # Increment if you need to recreate runs after deletion

from browsergym.workarena.api.utils import table_api_call
from browsergym.workarena.instance import SNowInstance, fetch_instances


def _time_window(hours: int = 24) -> Tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    ts_format = "%Y-%m-%d %H:%M:%S"
    return start.strftime(ts_format), end.strftime(ts_format)


def _fetch_user_creations(
    instance: SNowInstance, start_ts: str, end_ts: str
) -> List[Dict[str, str]]:
    # Query the audit log directly so deleted users are still counted.
    page_size = 10000  # avoid the default 100-row limit
    offset = 0
    seen: Dict[str, Dict[str, str]] = {}
    while True:
        params = {
            "sysparm_query": f"tablename=sys_user^sys_created_on>={start_ts}^sys_created_on<{end_ts}",
            "sysparm_fields": "documentkey,sys_created_on,user,fieldname,newvalue",
            "sysparm_limit": page_size,
            "sysparm_offset": offset,
        }
        response = table_api_call(instance=instance, table="sys_audit", params=params)
        batch = response.get("result", [])
        for audit in batch:
            doc = audit.get("documentkey")
            if not doc:
                continue
            # Keep the earliest audit entry per user record.
            if doc not in seen or audit.get("sys_created_on", "") < seen[doc].get(
                "sys_created_on", ""
            ):
                seen[doc] = audit
        if len(batch) < page_size:
            break
        offset += page_size
    return list(seen.values())


def _parse_sys_created(ts: str | None) -> datetime | None:
    if not ts:
        return None
    ts = ts.replace("Z", "+00:00")
    # Try ISO parsing with timezone if provided
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        dt = None
    if dt is None:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(ts, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hourly_counts(records: List[Dict[str, str]]) -> Dict[datetime, int]:
    buckets: Dict[datetime, int] = defaultdict(int)
    for record in records:
        ts = _parse_sys_created(record.get("sys_created_on"))
        if ts is None:
            continue
        bucket = ts.replace(minute=0, second=0, microsecond=0)
        buckets[bucket] += 1
    return buckets


def _daily_counts(records: List[Dict[str, str]]) -> Dict[datetime, int]:
    buckets: Dict[datetime, int] = defaultdict(int)
    for record in records:
        ts = _parse_sys_created(record.get("sys_created_on"))
        if ts is None:
            continue
        bucket = ts.replace(hour=0, minute=0, second=0, microsecond=0)
        buckets[bucket] += 1
    return buckets


def _init_wandb(instance_name: str | None = None):
    try:
        import wandb
    except ImportError as exc:
        raise SystemExit(
            "wandb is required for logging; install it to enable W&B logging."
        ) from exc

    # Use instance name or "total" as the display name
    display_name = instance_name or "total"
    # Add version suffix to run ID to avoid conflicts with deleted runs
    run_id = f"{display_name}-{RUN_VERSION}"

    run = wandb.init(
        project=WAND_PROJECT,
        entity=WAND_ENTITY,
        name=display_name,  # Clean name for display
        mode="online",
        id=run_id,  # Versioned ID for persistence
        resume="allow",
        settings=wandb.Settings(init_timeout=180),
        config={
            "hours": 24,
            "instance": display_name,
        },
    )
    return run


def _log_time_series_to_wandb(
    run,
    hourly_data: Dict[datetime, int],
    daily_data: Dict[datetime, int],
):
    """Log time series data to a W&B run, ensuring chronological order."""
    if run is None:
        return

    import wandb

    # Define metrics to allow out-of-order logging based on timestamp
    run.define_metric("daily_tasks_run", step_metric="timestamp", summary="last")
    run.define_metric("hourly_tasks_run", step_metric="timestamp", summary="last")
    run.define_metric("date", step_metric="timestamp")

    # Combine all timestamps and sort them chronologically
    all_data = []

    # Add daily data points
    for bucket, count in daily_data.items():
        all_data.append((bucket, "daily_tasks_run", count))

    # Add hourly data points
    for bucket, count in hourly_data.items():
        all_data.append((bucket, "hourly_tasks_run", count))

    # Sort by timestamp
    all_data.sort(key=lambda x: x[0])

    # Log in chronological order with human-readable date
    for bucket, metric_name, count in all_data:
        run.log(
            {
                "timestamp": int(bucket.timestamp()),
                metric_name: count,
                "date": bucket,  # Pass datetime object directly for W&B to format
            }
        )

    run.finish()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    start_ts, end_ts = _time_window()
    logging.info("Checking user creations between %s and %s (UTC)", start_ts, end_ts)

    instances = fetch_instances()
    if not instances:
        raise SystemExit("No ServiceNow instances available.")

    summaries: List[Tuple[str, int]] = []
    hourly_totals: Dict[datetime, int] = defaultdict(int)
    hourly_per_instance: Dict[str, Dict[datetime, int]] = {}
    daily_totals: Dict[datetime, int] = defaultdict(int)
    daily_per_instance: Dict[str, Dict[datetime, int]] = {}

    # Fetch data from all instances
    for entry in instances:
        url = entry["url"]
        logging.info("Querying %s", url)
        try:
            instance = SNowInstance(snow_url=url, snow_credentials=("admin", entry["password"]))
            creations = _fetch_user_creations(instance=instance, start_ts=start_ts, end_ts=end_ts)
            summaries.append((url, len(creations)))
            hourly = _hourly_counts(creations)
            for bucket, count in hourly.items():
                hourly_totals[bucket] += count
            hourly_per_instance[url] = hourly
            daily = _daily_counts(creations)
            for bucket, count in daily.items():
                daily_totals[bucket] += count
            daily_per_instance[url] = daily
            logging.info("...found %s tasks run", len(creations))
        except Exception:
            logging.exception("Failed to fetch data for %s", url)

    # Log total data to a separate W&B run
    logging.info("Logging total usage to W&B")
    total_run = _init_wandb(instance_name=None)
    _log_time_series_to_wandb(total_run, hourly_totals, daily_totals)

    # Log each instance's data to separate W&B runs
    for url, hourly_data in hourly_per_instance.items():
        instance_name = url.split("//")[-1].replace(".service-now.com", "")
        logging.info(f"Logging {instance_name} usage to W&B")

        instance_run = _init_wandb(instance_name=instance_name)
        daily_data = daily_per_instance[url]
        _log_time_series_to_wandb(instance_run, hourly_data, daily_data)

    # Print summary
    total_created = sum(count for _, count in summaries)
    print(f"\nTotal tasks run across instances: {total_created}")

    for url, count in summaries:
        print(f"{url}: {count} task(s) run")

    if daily_totals:
        print("\nDaily task runs (UTC):")
        for bucket in sorted(daily_totals.keys()):
            ts_str = bucket.strftime("%Y-%m-%d")
            print(f"{ts_str}: {daily_totals[bucket]}")

    if hourly_totals:
        print("\nHourly task runs (UTC):")
        for bucket in sorted(hourly_totals.keys()):
            ts_str = bucket.strftime("%Y-%m-%d %H:%M")
            print(f"{ts_str}: {hourly_totals[bucket]}")


if __name__ == "__main__":
    main()
