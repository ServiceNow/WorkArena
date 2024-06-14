import json
import time
from ...api.utils import table_api_call
from playwright.sync_api import Page


def create_private_task_and_get_sys_id(
    instance,
    page: Page,
    private_task_id: str,
    task_info: str,
    short_description: str,
    user_sys_id: str = None,
) -> None:
    """
    Create a private task in the ServiceNow instance to store the task information. Used for level 3 tasks.
    Sets the sys_id of the private task to the sys_id attribute of the task.
    Returns the sys_id of the private task.
    Parameters:
    ----------
    instance: SNowInstance
        The instance to use.
    page: Page
        playwright page
    private_task_id: str
        ID of the private task to be created.
    task_info: str
        The information needed to complete the task, written in the private task description.
    short_description: str
        A short description of the task, written in the private task short description.
    user_sys_id: str
        The sys_id of the user to assign the task to. If None, the task will be assigned to the admin user.
    """
    page.wait_for_load_state("networkidle")
    if user_sys_id is None:
        # Get the user sys_id; if the page is blank, use the admin user
        if page.url == "about:blank":
            user_sys_id = table_api_call(
                instance=instance,
                table="sys_user",
                params={"sysparm_query": "user_name=admin"},
            )["result"][0]["sys_id"]
        else:
            user_sys_id = page.evaluate("() => NOW.user.userID")
    # Create private task containing the information needed to complete the task
    result = table_api_call(
        instance=instance,
        table="vtb_task",
        data=json.dumps(
            {
                "number": f"{private_task_id}",
                "description": f"{task_info}",
                "short_description": f"{short_description}",
                "assigned_to": f"{user_sys_id}",
            }
        ),
        method="POST",
    )["result"]
    sys_id = result["sys_id"]

    assert result, "Failed to create private task"

    return sys_id
