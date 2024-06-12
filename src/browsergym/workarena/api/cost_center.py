import warnings
from faker import Faker

fake = Faker()

from .utils import table_api_call

from ..instance import SNowInstance


def get_cost_center_sysid(instance, cost_center_name):
    """Get the sys_id of a cost center by its name"""
    sys_id = table_api_call(
        instance=instance,
        table="cmn_cost_center",
        params={"sysparm_query": f"name={cost_center_name}", "sysparm_fields": "sys_id"},
    )["result"][0]

    return sys_id
