import faker

fake = faker.Faker()

from ..instance import SNowInstance
from .utils import table_api_call


def create_requested_item(
    instance: SNowInstance,
    user_sys_id: str,
    system_name: str,
    quantity: int = 1,
    short_description: str = None,
) -> list[str]:
    """
    Create a requested item for a given user

    Parameters:
    -----------
    instance: SNowInstance
        The instance to create the requested item in
    user_sys_id: str
        The sys_id of the user to request the item for
    system_name: str
        The name of the system to request (e.g. "Developer Laptop (Mac)" )
    quantity: int
        The quantity of the item to request
    short_description: str
        The short description of the item (optional). if not provided, a random one will be generated

    Returns:
    --------
    sys_id, number of the requested item

    """
    if short_description is None:
        short_description = fake.sentence(4)

    item_sys_id = table_api_call(
        instance=instance,
        table="sc_cat_item",
        params={"sysparm_query": f"sys_name={system_name}", "sysparm_fields": "sys_id"},
    )["result"][0]["sys_id"]

    item_config = {
        "requested_for": user_sys_id,
        "state": "3",
        "impact": "3",
        "active": "true",
        "priority": "4",
        "short_description": short_description,
        "urgency": "3",
        "quantity": str(quantity),
        "billable": "false",
        "cat_item": item_sys_id,
    }

    result = table_api_call(
        instance=instance, table="sc_req_item", json=item_config, method="POST"
    )["result"]

    return result["sys_id"], result["number"]
