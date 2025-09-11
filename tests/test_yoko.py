#!/usr/bin/env python3
import json
import logging
import multiprocessing
import argparse
import traceback
import os
import time
import random

# ---- Instance credentials (env) ----
os.environ["SNOW_INSTANCE_URL"] = "https://myarena25demo.service-now.com/"
os.environ["SNOW_INSTANCE_UNAME"] = "admin"
os.environ["SNOW_INSTANCE_PWD"] = r"Snow@456"

from browsergym.workarena.config import (
    # navigation tasks
    ALL_MENU_PATH,
    IMPERSONATION_CONFIG_PATH,
    # form tasks
    CREATE_CHANGE_REQUEST_CONFIG_PATH,
    CREATE_HARDWARE_CONFIG_PATH,
    CREATE_INCIDENT_CONFIG_PATH,
    CREATE_PROBLEM_CONFIG_PATH,
    CREATE_USER_CONFIG_PATH,
    # list tasks
    FILTER_ASSET_LIST_CONFIG_PATH,
    FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH,
    FILTER_HARDWARE_LIST_CONFIG_PATH,
    FILTER_INCIDENT_LIST_CONFIG_PATH,
    FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
    FILTER_USER_LIST_CONFIG_PATH,
    SORT_ASSET_LIST_CONFIG_PATH,
    SORT_CHANGE_REQUEST_LIST_CONFIG_PATH,
    SORT_HARDWARE_LIST_CONFIG_PATH,
    SORT_INCIDENT_LIST_CONFIG_PATH,
    SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
    SORT_USER_LIST_CONFIG_PATH,
    # knowledge tasks
    KB_CONFIG_PATH,
    # Service Catalog tasks
    ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH,
    ORDER_IPAD_MINI_TASK_CONFIG_PATH,
    ORDER_IPAD_PRO_TASK_CONFIG_PATH,
    ORDER_SALES_LAPTOP_TASK_CONFIG_PATH,
    ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH,
    ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
    ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH,
    ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH,
)
from browsergym.workarena.tasks.form import (
    CreateChangeRequestTask,
    CreateHardwareAssetTask,
    CreateIncidentTask,
    CreateProblemTask,
    CreateUserTask,
)
from browsergym.workarena.tasks.knowledge import KnowledgeBaseSearchTask
from browsergym.workarena.tasks.list import (
    FilterAssetListTask,
    FilterChangeRequestListTask,
    FilterHardwareListTask,
    FilterIncidentListTask,
    FilterServiceCatalogItemListTask,
    FilterUserListTask,
    SortAssetListTask,
    SortChangeRequestListTask,
    SortHardwareListTask,
    SortIncidentListTask,
    SortServiceCatalogItemListTask,
    SortUserListTask,
)
from browsergym.workarena.tasks.navigation import AllMenuTask, ImpersonationTask
from browsergym.workarena.tasks.service_catalog import (
    OrderDeveloperLaptopTask,
    OrderIpadMiniTask,
    OrderIpadProTask,
    OrderSalesLaptopTask,
    OrderStandardLaptopTask,
    OrderAppleWatchTask,
    OrderAppleMacBookPro15Task,
    OrderDevelopmentLaptopPCTask,
    OrderLoanerLaptopTask,
)

from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt
from tqdm import tqdm


task_to_config_path_mapping = {
    AllMenuTask: ALL_MENU_PATH,
    ImpersonationTask: IMPERSONATION_CONFIG_PATH,
    OrderDeveloperLaptopTask: ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH,
    OrderIpadMiniTask: ORDER_IPAD_MINI_TASK_CONFIG_PATH,
    OrderIpadProTask: ORDER_IPAD_PRO_TASK_CONFIG_PATH,
    OrderSalesLaptopTask: ORDER_SALES_LAPTOP_TASK_CONFIG_PATH,
    OrderStandardLaptopTask: ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH,
    OrderAppleWatchTask: ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
    OrderAppleMacBookPro15Task: ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    OrderDevelopmentLaptopPCTask: ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH,
    OrderLoanerLaptopTask: ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH,
    CreateChangeRequestTask: CREATE_CHANGE_REQUEST_CONFIG_PATH,
    CreateHardwareAssetTask: CREATE_HARDWARE_CONFIG_PATH,
    CreateIncidentTask: CREATE_INCIDENT_CONFIG_PATH,
    CreateProblemTask: CREATE_PROBLEM_CONFIG_PATH,
    CreateUserTask: CREATE_USER_CONFIG_PATH,
    KnowledgeBaseSearchTask: KB_CONFIG_PATH,
    FilterAssetListTask: FILTER_ASSET_LIST_CONFIG_PATH,
    FilterChangeRequestListTask: FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH,
    FilterHardwareListTask: FILTER_HARDWARE_LIST_CONFIG_PATH,
    FilterIncidentListTask: FILTER_INCIDENT_LIST_CONFIG_PATH,
    FilterServiceCatalogItemListTask: FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
    FilterUserListTask: FILTER_USER_LIST_CONFIG_PATH,
    SortAssetListTask: SORT_ASSET_LIST_CONFIG_PATH,
    SortChangeRequestListTask: SORT_CHANGE_REQUEST_LIST_CONFIG_PATH,
    SortHardwareListTask: SORT_HARDWARE_LIST_CONFIG_PATH,
    SortIncidentListTask: SORT_INCIDENT_LIST_CONFIG_PATH,
    SortServiceCatalogItemListTask: SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH,
    SortUserListTask: SORT_USER_LIST_CONFIG_PATH,
}


@retry(stop=stop_after_attempt(3), reraise=True)
def validate_task(task_config, task_class, page=None):
    """Validates a task with a given configuration"""
    num_attempts = 4
    tries = 0
    while tries < num_attempts:
        if page is None:
            # To run validation
            with sync_playwright() as p:
                browser = p.chromium.launch(slow_mo=1000)
                context = browser.new_context()
                page = context.new_page()
                cheat_passed, task_done, reward = validate_on_page(task_class, task_config, page)
        else:
            # For testing purposes
            cheat_passed, task_done, reward = validate_on_page(task_class, task_config, page)
        tries += 1
        task_successful = task_done is True and reward == 1.0
        if task_successful:
            break
        else:
            logging.warning(
                f"Task {task_class.__name__} was not successful ({tries} / {num_attempts})"
            )

    return task_done, reward, task_config, cheat_passed


def validate_on_page(task_class, task_config, page):
    """Validate a configuration on a given page"""
    cheat_passed = False
    task_done = False
    reward = 0.0
    task = task_class(seed=1, fixed_config=task_config)
    task.setup(page=page)
    chat_messages = []
    task.cheat(page=page, chat_messages=chat_messages)
    cheat_passed = True
    page.wait_for_timeout(2000)
    reward, task_done, _, _ = task.validate(page, chat_messages)
    task.teardown()

    return cheat_passed, task_done, reward


def validate_configs(
    task_class,
    config_path,
    num_tasks: int = None,        # legacy; if provided, overrides sample_size
    save_failed_tasks: bool = True,
    page=None,
    output_dir: str = ".",
    sample_size: int = 100,       # <- new: sample this many per task, with seed=0
    sleep_sec: float = 10.0,      # <- new: sleep after each config
) -> list[dict]:
    """
    Validate that the configs are working. Saves failing configs to json so they can be tested.
    """
    with open(config_path, "r") as f:
        all_configs = json.load(f)

    # Determine how many to run
    target_n = num_tasks if num_tasks is not None else sample_size
    target_n = min(target_n, len(all_configs))

    # Deterministic sampling with seed=0
    rng = random.Random(0)
    if target_n < len(all_configs):
        selected_configs = rng.sample(all_configs, target_n)
    else:
        selected_configs = all_configs

    failed_tasks = {"cheat": [], "no_reward": [], "exception": [], "not_done": []}

    # Ensure output dir exists and compute path
    os.makedirs(output_dir, exist_ok=True)
    failed_tasks_path = os.path.join(output_dir, f"failed_{task_class.__name__}.json")

    # Overwrite the file at the beginning of the validation for a clean slate
    if save_failed_tasks:
        with open(failed_tasks_path, "w") as f:
            json.dump(failed_tasks, f)

    with tqdm(
        total=len(selected_configs),
        desc=f"Validating {task_class.__name__} configs (n={len(selected_configs)})",
        ncols=150,
    ) as pbar:
        for task_config in selected_configs:
            has_failed = False
            try:
                task_done, reward, task_config, cheat_passed = validate_task(
                    task_config, task_class, page
                )
                success = task_done and reward == 1.0
                if not cheat_passed:
                    failed_tasks["cheat"].append(task_config)
                    has_failed = True
                elif not task_done:
                    failed_tasks["not_done"].append(task_config)
                    has_failed = True
                elif reward == 0:
                    failed_tasks["no_reward"].append(task_config)
                    has_failed = True

                print(f"Success: {success}")
            except Exception as e:
                failed_tasks["exception"].append(
                    {"config": task_config, "reason": traceback.format_exc()}
                )
                has_failed = True
                print(f"Exception {e}")

            # Persist incremental failures
            if has_failed and save_failed_tasks:
                with open(failed_tasks_path, "w") as f:
                    json.dump(failed_tasks, f)

            pbar.update(1)

            # --- Throttle to avoid server overload ---
            try:
                time.sleep(sleep_sec)
            except KeyboardInterrupt:
                raise
            except Exception:
                pass

    return failed_tasks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate WorkArena tasks.")
    parser.add_argument(
        "--sequential",
        action="store_true",
        default=False,
        help="Run validation sequentially instead of in parallel.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/Users/dheeraj.vattikonda/Desktop/WORKARENA_2/TEST_new/",
        help="Directory where failed task JSONs will be saved.",
    )
    parser.add_argument(
        "--sample_size",
        type=int,
        default=1000,
        help="Random sample size per task (seed=0).",
    )
    parser.add_argument(
        "--sleep_sec",
        type=float,
        default=10.0,
        help="Seconds to sleep after each config.",
    )
    args = parser.parse_args()

    tasks_and_paths = list(task_to_config_path_mapping.items())

    if args.sequential:
        for task_class, config_path in tasks_and_paths:
            validate_configs(
                task_class,
                config_path,
                output_dir=args.output_dir,
                sample_size=args.sample_size,
                sleep_sec=args.sleep_sec,
            )
    else:
        with multiprocessing.Pool(15) as pool:
            pool.starmap(
                validate_configs,
                [
                    (
                        task_class,
                        config_path,
                        None,          # num_tasks
                        True,          # save_failed_tasks
                        None,          # page
                        args.output_dir,
                        args.sample_size,
                        args.sleep_sec,
                    )
                    for task_class, config_path in tasks_and_paths
                ],
            )
