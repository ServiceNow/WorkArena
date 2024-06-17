from importlib import resources

from ..workarena import data_files
from ..workarena.tasks import utils

# ServiceNow configuration
SNOW_DATA_LOOKBACK_MINUTES = 5
SNOW_BROWSER_TIMEOUT = 30000  # Milliseconds
SNOW_JS_UTILS_FILEPATH = str(resources.files(utils).joinpath("js_utils.js"))
SNOW_SUPPORTED_RELEASES = ["washingtondc"]

# Path to the Menu navigation task configuration
ALL_MENU_PATH = str(resources.files(data_files).joinpath("task_configs/all_menu.json"))

# Path to the dashboard/report retrieval task configurations
DASHBOARD_RETRIEVAL_MINMAX_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/dashboard_retrieval_minmax_task.json")
)
DASHBOARD_RETRIEVAL_VALUE_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/dashboard_retrieval_value_task.json")
)
REPORT_RETRIEVAL_MINMAX_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/report_retrieval_minmax_task.json")
)
REPORT_RETRIEVAL_VALUE_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/report_retrieval_value_task.json")
)

# Path to knowledge base task configurations
KB_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/knowledge_base_configs.json")
)
# Path to the Impersonation task configuration
IMPERSONATION_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/impersonation_users.json")
)
# Path to the service catalog configs
ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_developer_laptop_task.json")
)
ORDER_IPAD_MINI_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_ipad_mini_task.json")
)
ORDER_IPAD_PRO_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_ipad_pro_task.json")
)
ORDER_SALES_LAPTOP_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_sales_laptop_task.json")
)
ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_standard_laptop_task.json")
)
ORDER_APPLE_WATCH_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_apple_watch_task.json")
)
ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_apple_mac_book_pro15_task.json")
)
ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_development_laptop_pc_task.json")
)
ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_loaner_laptop_task.json")
)

# Knowledge base that is included with the benchmark
KB_NAME = "General Knowledge"
KB_FILEPATH = str(resources.files(data_files).joinpath("setup_files/knowledge/knowledge_base.json"))
PROTOCOL_KB_NAME = "Company Protocols"
PROTOCOL_KB_FILEPATH = str(
    resources.files(data_files).joinpath("setup_files/knowledge/protocols.json")
)

# Form tasks
CREATE_CHANGE_REQUEST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_change_request_task.json")
)
CREATE_HARDWARE_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_hardware_asset_task.json")
)
CREATE_INCIDENT_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_incident_task.json")
)
CREATE_PROBLEM_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_problem_task.json")
)
CREATE_USER_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_user_task.json")
)
# List tasks
FILTER_ASSET_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/filter_asset_list_task.json")
)
FILTER_CHANGE_REQUEST_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/filter_change_request_list_task.json")
)
FILTER_HARDWARE_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/filter_hardware_list_task.json")
)
FILTER_INCIDENT_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/filter_incident_list_task.json")
)
FILTER_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/filter_service_catalog_item_list_task.json")
)
FILTER_USER_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/filter_user_list_task.json")
)
SORT_ASSET_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/sort_asset_list_task.json")
)
SORT_CHANGE_REQUEST_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/sort_change_request_list_task.json")
)
SORT_HARDWARE_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/sort_hardware_list_task.json")
)
SORT_INCIDENT_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/sort_incident_list_task.json")
)
SORT_SERVICE_CATALOG_ITEM_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/sort_service_catalog_item_list_task.json")
)
SORT_USER_LIST_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/sort_user_list_task.json")
)


# Custom workflows that are included with the benchmark
WORKFLOWS = {
    "kb_publish": {
        "name": "WorkArena Auto-Publish",
        "update_set": str(
            resources.files(data_files).joinpath(
                "setup_files/knowledge/kb_autopublish_workflow.xml"
            )
        ),
    }
}


# Custom UI Themes
UI_THEMES_UPDATE_SET = {
    "name": "WorkArena UI Themes",
    "update_set": str(
        resources.files(data_files).joinpath("setup_files/ui_themes/workarena_themes.xml")
    ),
    "variants": [
        "Astranova",
        "Charlies",
        "Great pasta",
        "Mighty capital",
        "Speedy tires",
        "Skyward",
        "Turbobots",
        "Ultrashoes",
        "Vitasphere",
        "Workarena",
    ],
}


# Expected columns for list tasks; used in setup
EXPECTED_ASSET_LIST_COLUMNS_PATH = str(
    resources.files(data_files).joinpath("setup_files/lists/expected_asset_list_columns.json")
)
EXPECTED_CHANGE_REQUEST_COLUMNS_PATH = str(
    resources.files(data_files).joinpath(
        "setup_files/lists/expected_change_request_list_columns.json"
    )
)
EXPECTED_EXPENSE_LINE_COLUMNS_PATH = str(
    resources.files(data_files).joinpath(
        "setup_files/lists/expected_expense_line_list_columns.json"
    )
)
EXPECTED_HARDWARE_COLUMNS_PATH = str(
    resources.files(data_files).joinpath("setup_files/lists/expected_hardware_list_columns.json")
)
EXPECTED_INCIDENT_COLUMNS_PATH = str(
    resources.files(data_files).joinpath("setup_files/lists/expected_incident_list_columns.json")
)
EXPECTED_PROBLEM_COLUMNS_PATH = str(
    resources.files(data_files).joinpath("setup_files/lists/expected_problem_list_columns.json")
)
EXPECTED_REQUESTED_ITEMS_COLUMNS_PATH = str(
    resources.files(data_files).joinpath(
        "setup_files/lists/expected_requested_items_list_columns.json"
    )
)
EXPECTED_SERVICE_CATALOG_COLUMNS_PATH = str(
    resources.files(data_files).joinpath(
        "setup_files/lists/expected_service_catalog_list_columns.json"
    )
)
EXPECTED_USER_COLUMNS_PATH = str(
    resources.files(data_files).joinpath("setup_files/lists/expected_user_list_columns.json")
)
# Expected form fields for form tasks; used in setup
EXPECTED_ASSET_FORM_FIELDS_PATH = str(
    resources.files(data_files).joinpath("setup_files/forms/expected_asset_form_fields.json")
)
EXPECTED_CHANGE_REQUEST_FORM_FIELDS_PATH = str(
    resources.files(data_files).joinpath(
        "setup_files/forms/expected_change_request_form_fields.json"
    )
)

EXPECTED_HARDWARE_FORM_FIELDS_PATH = str(
    resources.files(data_files).joinpath("setup_files/forms/expected_hardware_form_fields.json")
)
EXPECTED_INCIDENT_FORM_FIELDS_PATH = str(
    resources.files(data_files).joinpath("setup_files/forms/expected_incident_form_fields.json")
)
EXPECTED_PROBLEM_FORM_FIELDS_PATH = str(
    resources.files(data_files).joinpath("setup_files/forms/expected_problem_form_fields.json")
)
EXPECTED_USER_FORM_FIELDS_PATH = str(
    resources.files(data_files).joinpath("setup_files/forms/expected_user_form_fields.json")
)
EXPECTED_REQUEST_ITEM_FORM_FIELDS_PATH = str(
    resources.files(data_files).joinpath("setup_files/forms/expected_request_item_form_fields.json")
)

# Report date filter patch flag
REPORT_PATCH_FLAG = "WORKARENA_DATE_FILTER_PATCH"
REPORT_DATE_FILTER = "2024-04-01"
