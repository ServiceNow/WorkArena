import warnings
from faker import Faker

fake = Faker()

from .utils import table_api_call

from ..instance import SNowInstance


def create_category(
    instance: SNowInstance,
    list_name: str,
    category_name: str = None,
) -> list[str]:
    """
    NOTE: This function creates a new category in the given list. Because categories are in a drop-down list, adding more
    categories will make the list longer and this will affect the difficulty of the task. Use only if you are certain you know
    what you are doing.

    Create a category for a given list

    Parameters:
    -----------
    instance: SNowInstance
        The instance to create the category in
    list_name: str
        The name of the list to create the category for (e.g. problem, incident, etc.)
    category_name: str
        The name of the category to create, defaults to a random category name

    Returns:
    --------
    category_name, sys_id

    """
    warnings.warn(
        "This function creates a new category in the given list. Because categories are in a drop-down list, adding more "
        "categories will make the list longer and this will affect the difficulty of the task. Use only if you are certain you know "
        "what you are doing.",
        UserWarning,
    )

    if category_name is None:
        category_name = fake.word() + "-" + fake.word()

    # Create category
    category_data = {
        "name": list_name,
        "element": "category",
        "value": category_name,
    }
    result = table_api_call(
        instance=instance,
        table="sys_choice",
        json=category_data,
        method="POST",
        wait_for_record=True,
    )["result"]

    sys_id = result["sys_id"]

    return category_name, sys_id


def get_categories(instance, list_name):
    """Get the name of the categories for a given list name"""
    categories = table_api_call(
        instance=instance,
        table="sys_choice",
        params={"sysparm_query": f"name={list_name}^element=category", "sysparm_fields": "value"},
    )["result"]

    return categories
