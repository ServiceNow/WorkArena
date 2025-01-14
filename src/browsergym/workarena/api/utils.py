import requests

from ..instance import SNowInstance

from requests.exceptions import HTTPError
from time import sleep

# ServiceNow API configuration
SNOW_API_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


def table_api_call(
    instance: SNowInstance,
    table: str,
    data: dict = {},
    params: dict = {},
    json: dict = {},
    method: str = "GET",
    wait_for_record: bool = False,
    max_retries: int = 5,
    raise_on_wait_expired: bool = True,
) -> dict:
    """
    Make a call to the ServiceNow Table API

    Parameters:
    -----------
    instance: SNowInstance
        The ServiceNow instance to interact with
    table: str
        The name of the table to interact with
    data: dict
        The data to send with the request
    params: dict
        The parameters to pass to the API
    json: dict
        The JSON data to send with the request
    method: str
        The HTTP method to use (GET, POST, PUT, DELETE).
    wait_for_record: bool
        If True, will wait up to 2 seconds for the record to be present before returning
    max_retries: int
        The number of retries to attempt before failing
    raise_on_wait_expired: bool
        If True, will raise an exception if the record is not found after max_retries.
        Otherwise, will return an empty result.

    Returns:
    --------
    dict
        The JSON response from the API

    """

    # Query API
    response = requests.request(
        method=method,
        url=instance.snow_url + f"/api/now/table/{table}",
        auth=instance.snow_credentials,
        headers=SNOW_API_HEADERS,
        data=data,
        params=params,
        json=json,
    )
    if method == "POST":
        sys_id = response.json()["result"]["sys_id"]
        data = {}
        params = {"sysparm_query": f"sys_id={sys_id}"}

    # Check for HTTP success code (fail otherwise)
    response.raise_for_status()

    record_exists = False
    num_retries = 0
    if method == "POST" or wait_for_record:
        while not record_exists:
            sleep(0.5)
            get_response = table_api_call(
                instance=instance,
                table=table,
                params=params,
                json=json,
                data=data,
                method="GET",
            )
            record_exists = len(get_response["result"]) > 0
            num_retries += 1
            if num_retries > max_retries:
                if raise_on_wait_expired:
                    raise HTTPError(f"Record not found after {max_retries} retries")
                else:
                    return {"result": []}
            if method == "GET":
                response = get_response

    if method != "DELETE":
        # Decode the JSON response into a dictionary if necessary
        # When using wait_for_record=True, the response is already a dict as it is a recursive call
        if type(response) == dict:
            return response
        else:
            return response.json()
    else:
        return response


def table_column_info(instance: SNowInstance, table: str) -> dict:
    """
    Get the column information for a ServiceNow table

    Parameters:
    -----------
    table: str
        The name of the table to interact with

    Returns:
    --------
    dict
        The JSON response from the API

    """
    # Query the Meta API to get most of the column info (e.g., valid choices)
    response = requests.get(
        url=instance.snow_url + f"/api/now/ui/meta/{table}",
        auth=instance.snow_credentials,
        headers=SNOW_API_HEADERS,
    )
    response.raise_for_status()
    meta_info = response.json()["result"]["columns"]

    # Clean column value choices
    for info in meta_info.values():
        if info.get("choices", None):
            info["choices"] = {c["value"]: c["label"] for c in info["choices"]}

    # Query the sys_dictionnary table to find more info (e.g., is this column dependent on another)
    sys_dict_info = table_api_call(
        instance=instance,
        table="sys_dictionary",
        params={
            "sysparm_query": f"name={table}",
            "sysparm_fields": "element,dependent_on_field",
        },
    )
    sys_dict_info = {d["element"]: d for d in sys_dict_info["result"]}

    # Merge information
    for k, v in meta_info.items():
        v.update(sys_dict_info.get(k, {}))

    return meta_info


def db_delete_from_table(instance: SNowInstance, sys_id: str, table: str) -> None:
    """
    Delete an entry from a ServiceNow table using its sys_id

    Parameters:
    -----------
    sys_id: str
        The sys_id of the entry to delete
    table: str
        The name of the table to delete from

    """
    # Query API
    response = requests.delete(
        url=instance.snow_url + f"/api/now/table/{table}/{sys_id}",
        auth=instance.snow_credentials,
        headers=SNOW_API_HEADERS,
    )

    # Check for HTTP code 200 (fail otherwise)
    response.raise_for_status()
