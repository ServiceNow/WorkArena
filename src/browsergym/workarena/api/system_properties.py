from .utils import table_api_call


def set_sys_property(instance, property_name: str, value: str):
    """
    Set a sys_property in the instance.

    Parameters:
    -----------
    instance: SNowInstance
        The instance to set the property in
    property_name: str
        The name of the property to set
    value: str
        The value to set for the property

    """

    property = table_api_call(
        instance=instance,
        table="sys_properties",
        params={"sysparm_query": f"name={property_name}", "sysparm_fields": "sys_id"},
    )["result"]

    if not property:
        property_sysid = ""
        method = "POST"
    else:
        property_sysid = "/" + property[0]["sys_id"]
        method = "PUT"

    property = table_api_call(
        instance=instance,
        table=f"sys_properties{property_sysid}",
        method=method,
        json={"name": property_name, "value": value},
    )

    # Verify that the property was updated
    assert property["result"]["value"] == value, f"Error setting {property_name}."


def get_sys_property(instance, property_name: str) -> str:
    """
    Get a sys_property from the instance.

    Parameters:
    -----------
    instance: SNowInstance
        The instance to get the property from
    property_name: str
        The name of the property to get

    Returns:
    --------
    str
        The value of the property

    """
    property_value = table_api_call(
        instance=instance,
        table="sys_properties",
        params={"sysparm_query": f"name={property_name}", "sysparm_fields": "value"},
    )["result"][0]["value"]

    return property_value
