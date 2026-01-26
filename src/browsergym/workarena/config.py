from importlib import resources
from json import load as json_load
from os.path import exists

from ..workarena import data_files
from ..workarena.tasks import utils

# ServiceNow configuration
SNOW_DATA_LOOKBACK_MINUTES = 5
SNOW_BROWSER_TIMEOUT = 30000  # Milliseconds
SNOW_JS_UTILS_FILEPATH = str(resources.files(utils).joinpath("js_utils.js"))
SNOW_SUPPORTED_RELEASES = ["washingtondc"]

# Hugging Face dataset containing available instances
INSTANCE_REPO_ID = "ServiceNow/WorkArena-Instances"
INSTANCE_REPO_FILENAME = "instances_v2.json"
INSTANCE_REPO_TYPE = "dataset"
INSTANCE_XOR_SEED = "x3!+-9mi#nhlo%a02$9hna{]"

# Path to the Menu navigation task configuration
ALL_MENU_PATH = str(resources.files(data_files).joinpath("task_configs/all_menu.json"))
ALL_MENU_CUSTOM_GOAL_PATH = str(resources.files(data_files).joinpath("task_configs/go_to_page.json"))

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
REPORT_FILTER_PROPERTY = "workarena.report.filter.config"


# Case tasks
GET_CASE_STATUS_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/get_case_status.json")
)
GET_CASE_RESOLUTION_NOTES_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/get_case_resnotes.json")
)
CLOSE_CASE_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/close_case.json")
)
FIND_ASSET_UNDER_ACCOUNT_CREATE_CASE_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/find_asset_under_account_create_case.json")
)

# Role tasks
ASSIGN_ROLE_TO_USER_ADMIN_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/assign_role_to_user_admin.json")
)
ASSIGN_ROLES_TO_USER_EXPLICIT_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/assign_roles_to_user_explicit.json")
)
ASSIGN_ROLES_TO_USER_IMPLICIT_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/assign_roles_to_user_implicit.json")
)

## License tasks
GET_NUMBER_LICENSES_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/get_number_licenses.json")
)

## Change Request tasks
CHANGE_CHANGE_REQUEST_APPROVER_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/change_chg_approver.json")
)

## Incident tasks
ADD_ADDITIONAL_ASSIGNEE_TO_INCIDENT_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/add_additional_assignee_to_incident.json")
)
RESOLVE_INCIDENT_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/resolve_incident.json")
)
UPDATE_INCIDENT_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/update_incident.json")
)

## Request Item tasks
CHANGE_RITM_STATUS_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/change_ritm_status.json")
)
UPDATE_RITM_QUANTITY_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/update_ritm_quantity.json")
)

## Interaction tasks
CREATE_INTERACTION_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_interaction.json")
)

## Customer account tasks
FIND_CUSTOMER_ACCOUNT_MANAGER_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/find_customer_account_manager.json")
)

## User group tasks
DEACTIVATE_USER_GROUP_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/deactivate_user_group.json")
)
CREATE_USER_GROUP_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_user_group.json")
)
CREATE_USER_GROUP_ADD_USERS_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/create_user_group_add_users.json")
)

# service catalog tasks (dynamic guidance)
ORDER_IPHONE_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_iphone.json")
)
ORDER_MOBILE_PHONE_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_mobile_phone.json")
)
ORDER_MISC_HARDWARE_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_misc_hardware.json")
)
ORDER_MISC_HARDWARE_WITH_BUSINESS_JUSTIFICATION_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_misc_hardware_with_business_justification.json")
)
ORDER_PACKAGING_AND_SHIPPING_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_packaging_and_shipping.json")
)
ORDER_RESET_PASSWORD_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_reset_password.json")
)
ORDER_PAPER_SUPPLIES_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_paper_and_supplies.json")
)
ORDER_SOFTWARE_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_software.json")
)
ORDER_SOFTWARE_ACCESS_TASK_CONFIG_PATH = str(
    resources.files(data_files).joinpath("task_configs/order_software_access.json")
)
