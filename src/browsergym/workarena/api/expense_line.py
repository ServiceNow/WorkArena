import json
import time

from faker import Faker

fake = Faker()

from .cost_center import get_cost_center_sysid
from .utils import table_api_call

from ..instance import SNowInstance


def create_expense_line(
    instance: SNowInstance,
    amount: float,
    number: str,
    date: str,
    short_description: str = None,
    expense_hashtag: str = "",
    task_sys_id: str = None,
    cost_center_sys_id: str = None,
    summary_type: str = "run_business",
    user_sys_id: str = None,
):
    """Create a hardware asset -computer model- and assign it to a user
    Args:
    --------
    instance (SNowInstance):
        The instance to create the hardware asset in
    amount (float):
        The amount of the expense line
    number (str):
        The number of the expense line
    date (str):
        The date of the expense line
    short_description (str):
        The short description of the expense line; if None, a random one will be generated
    expense_hashtag (str):
        The hashtag of the expense line (added to the short description)
    task_sys_id (str):
        The sys id of the task to file the expense line under
    cost_center_sys_id (str):
        The sys id of the cost center to file the expense line under
    summary_type (str):
        The summary type of the expense line (choice of "run_business", "grow_business", "transform_business")
    user_sys_id (str):
        The sys_id of the user to assign the hardware asset to. If None, the hardware asset is not assigned to any user
    Returns:
    --------
    sys_id (str):
        The sys_id of the created expense_line
    expense_line_number (str):
        The number of the created expense_line
    """
    if cost_center_sys_id is None:
        # sys_id of the engineering cost center
        cost_center_sys_id = table_api_call(
            instance=instance,
            table="cmn_cost_center",
            params={"sysparm_query": "name=Engineering"},
        )["result"][0]["sys_id"]

    if short_description is None:
        short_description = fake.sentence(4)

    expense_cfg = {
        "date": date,
        "base_expense": "",
        "short_description": short_description + " " + expense_hashtag,
        "summary_type": summary_type,
        "summary_type": "run_business",
        "type": "one-time",
        "number": f"{number}",
        "task": f"{task_sys_id}",
        "state": "processed",
        "amount": f"{amount}",
        "cost_center": f"{cost_center_sys_id}",
        "user": f"{user_sys_id}",
    }

    result = table_api_call(
        instance=instance,
        table="fm_expense_line",
        json=expense_cfg,
        method="POST",
    )["result"]

    return result["sys_id"], result["number"]
