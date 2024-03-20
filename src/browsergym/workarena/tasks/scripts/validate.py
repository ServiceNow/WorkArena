import json
import logging
import multiprocessing

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
            # For testing pusposes
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
    task = task_class(fixed_config=task_config)
    task.setup(page=page, seed=1)
    chat_messages = []
    task.cheat(page=page, chat_messages=chat_messages)
    cheat_passed = True
    page.wait_for_timeout(2000)
    reward, task_done, _, _ = task.validate(page, chat_messages)
    task.teardown()

    return cheat_passed, task_done, reward


def validate_configs(
    task_class, config_path, num_tasks: int = None, save_failed_tasks: bool = True, page=None
) -> list[dict]:
    """Validate that the configs are working. Saves failing configs to json so they can be tested."""
    with open(config_path, "r") as f:
        all_configs = json.load(f)

    if num_tasks is not None:
        all_configs = all_configs[:num_tasks]

    failed_tasks = {"cheat": [], "no_reward": [], "exception": [], "not_done": []}
    with tqdm(
        total=len(all_configs), desc=f"Validating {task_class.__name__} configs", ncols=150
    ) as pbar:
        for task_config in all_configs:
            try:
                task_done, reward, task_config, cheat_passed = validate_task(
                    task_config, task_class, page
                )
                success = task_done and reward == 1.0
                if not cheat_passed:
                    failed_tasks["cheat"].append(task_config)
                elif not task_done:
                    failed_tasks["not_done"].append(task_config)
                elif reward == 0:
                    failed_tasks["no_reward"].append(task_config)

                print(success)
            except Exception as e:
                failed_tasks["exception"].append(task_config)
                print(f"Exception {e}")
            pbar.update(1)
    if save_failed_tasks:
        # Save failed tasks to a JSON file
        with open(f"failed_{task_class.__name__}.json", "w") as f:
            json.dump(failed_tasks, f)

    return failed_tasks


if __name__ == "__main__":
    with multiprocessing.Pool() as pool:
        tasks_and_paths = list(task_to_config_path_mapping.items())
        pool.starmap(validate_configs, tasks_and_paths)
