import json
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


@retry(stop=stop_after_attempt(10), reraise=True)
def validate_task(task_config, task_class):
    """Validates a task with a given configuration"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        task = task_class(fixed_config=task_config)
        task.setup(page=page)
        chat_messages = []
        task.cheat(page=page, chat_messages=chat_messages)
        task_successful = task.validate(page, chat_messages)[1]
        task.teardown()
        browser.close()

        return task_successful, task_config


def validate_configs(task_class, config_path) -> list[dict]:
    with open(config_path, "r") as f:
        all_configs = json.load(f)

    failed_tasks = []
    with tqdm(
        total=len(all_configs), desc=f"Validating {task_class.__name__} configs", ncols=150
    ) as pbar:
        for task_config in all_configs:
            try:
                success, task_config = validate_task(task_config, task_class)
                print(f"success: {success}")
                if not success:
                    failed_tasks.append(task_config)
            except Exception as e:
                failed_tasks.append(task_config)
                print(f"Exception")
            pbar.update(1)
    # Save failed tasks to a JSON file
    with open(f"failed_{task_class.__name__}.json", "w") as f:
        json.dump(failed_tasks, f)


if __name__ == "__main__":
    with multiprocessing.Pool() as pool:
        tasks_and_paths = list(task_to_config_path_mapping.items())
        pool.starmap(validate_configs, tasks_and_paths)
