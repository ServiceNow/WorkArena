from faker import Faker
import numpy as np
import time

fake = Faker()

from ..instance import SNowInstance
from .ui_themes import get_workarena_theme_variants
from .utils import table_api_call


def create_user(
    instance: SNowInstance,
    first_name: str = None,
    last_name: str = None,
    user_name: str = None,
    return_full_response: bool = False,
    user_roles: list[str] = ["admin"],
    random: np.random = np.random,
) -> list[str]:
    """
    Create a user with a random username and password with an admin role

    Parameters:
    -----------
    first_name: str
        The first name of the user, defaults to a random first name
    last_name: str
        The last name of the user, defaults to a random last name
    user_name: str
        The user name of the user, defaults to first_name.last_name
    user_roles: list[str]
        The roles to assign to the user, defaults to ['admin']

    Returns:
    --------
    username, password, sys_id

    """
    user_idx = str(random.randint(1000, 9999))
    user_password = "aStrongPassword!"
    first_name = fake.first_name() if not first_name else first_name
    last_name = fake.last_name() if not last_name else last_name

    # Create user
    user_data = {
        "user_name": f"{first_name}.{last_name}.{user_idx}" if not user_name else user_name,
        "first_name": first_name,
        "last_name": last_name,
        "email": f"{first_name}.{last_name}.{user_idx}@workarena.com".lower(),
        "user_password": user_password,
        "active": True,
    }
    user_params = {"sysparm_input_display_value": True}
    user_response = table_api_call(
        instance=instance, table="sys_user", json=user_data, params=user_params, method="POST"
    )["result"]
    user_name = user_response["user_name"]
    user_sys_id = user_response["sys_id"]

    # Get role sys_id's
    for role in user_roles:
        role_sys_id = table_api_call(
            instance=instance,
            table="sys_user_role",
            params={"sysparm_query": f"name={role}", "sysparm_fields": "sys_id"},
            method="GET",
        )["result"][0]["sys_id"]

        # Give admin permissions
        association_data = {"user": user_sys_id, "role": role_sys_id}
        table_api_call(
            instance=instance, table="sys_user_has_role", json=association_data, method="POST"
        )

    # Randomly pick a UI theme and set it for the user
    themes = get_workarena_theme_variants(instance)
    theme = random.choice(themes)
    set_user_preference(
        instance, "glide.ui.polaris.theme.variant", theme["style.sys_id"], user=user_sys_id
    )
    if return_full_response:
        return user_response
    return user_name, user_password, user_sys_id


def set_user_preference(instance: SNowInstance, key: str, value: str, user=None) -> dict:
    """
    Set a user preference in the ServiceNow instance

    Parameters:
    -----------
    key: str
        The name of the preference
    value: str
        The value of the preference
    user: str
        The sys_id of the user. If None, the preference will be set globally.

    Returns:
    --------
    dict
        The preference that was set

    """
    if user is None:
        # make it global
        user = ""
        system = True
    else:
        system = False

    # Try to get the preference's sys_id
    preference = table_api_call(
        instance=instance,
        table="sys_user_preference",
        params={"sysparm_query": f"name={key},user={user}", "sysparm_fields": "sys_id"},
    )["result"]

    if not preference:
        # ... The preference key doesn't exist, create it
        pref_sysid = ""
        method = "POST"
    else:
        # ... The preference key exists, update it
        pref_sysid = "/" + preference[0]["sys_id"]
        method = "PUT"

    property = table_api_call(
        instance=instance,
        table=f"sys_user_preference{pref_sysid}",
        method=method,
        json={
            "name": key,
            "value": value,
            "user": user,
            "system": system,
            "description": "Updated by WorkArena",
        },
    )["result"]

    # Verify that the property was updated
    property["user"] = (
        property["user"].get("value") if isinstance(property["user"], dict) else property["user"]
    )
    assert (
        property["value"] == value
    ), f"Error setting system property {key}, incorrect value {property['value']}, while expecting {value}."
    assert (
        property["user"] == user
    ), f"Error setting system property {key}, incorrect user {property['user']}, while expecting {user}."
    assert (
        property["system"] == str(system).lower()
    ), f"Error setting {key}, incorrect system {property['system']}, while expecting {system}."

    return property
