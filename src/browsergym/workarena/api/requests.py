"""
API to interact with requests in ServiceNow

"""

import json

from collections import defaultdict

from .utils import SNowInstance, table_api_call, db_delete_from_table


def delete_request(instance: SNowInstance, sys_id: str) -> None:
    """
    Deletes a request from an instance along with all its items and their options

    Parameters:
    -----------
    sys_id: str
        The sys_id of the request to delete

    """
    # Delete all items
    for item in get_request_items(instance, sys_id):
        # Delete all options for each item
        for option in item["options"].values():
            db_delete_from_table(
                instance,
                option["sys_ids"]["sc_item_option_mtom"],
                "sc_item_option_mtom",
            )
            db_delete_from_table(instance, option["sys_ids"]["sc_item_option"], "sc_item_option")
        db_delete_from_table(instance, item["sys_id"], "sc_req_item")

    # Delete the request
    db_delete_from_table(instance, sys_id, "sc_request")


def get_all_requests(instance: SNowInstance, since_minutes: int = 99999999999) -> list:
    """
    Retrives a list of all requests from an instance

    Parameters:
    -----------
    since_minutes: int
        The number of minutes to look back for requests (used to avoid getting too many requests)

    Returns:
    --------
    list
        A list of all requests from an instance (as dicts)

    """
    # Filter for requests that were created in the time frame
    query = f"sys_created_on>=javascript:gs.minutesAgoStart({since_minutes})"

    # Get all requests
    requests_ = table_api_call(
        instance, table="sc_request", method="GET", params={"sysparm_query": query}
    )["result"]

    # For each request, get the items that were ordered
    for request in requests_:
        request["items"] = get_request_items(instance, request["sys_id"])

    return requests_


def get_request_by_id(instance: SNowInstance, sysid: str) -> dict:
    """
    Get a request by its sys_id

    Parameters:
    -----------
    instance: SNowInstance
        The instance to get the request from
    sysid: str
        The sys_id of the request to get

    Returns:
    --------
    dict
        A dictionary containing the details of the request

    """
    # Get the request
    request = table_api_call(
        instance,
        table=f"sc_request",
        method="GET",
        params={"sysparm_query": f"sys_id={sysid}"},
    )["result"]

    if len(request) == 0:
        return None
    request = request[0]

    # Get the items that were ordered
    request["items"] = get_request_items(instance, request["sys_id"])

    return request


def get_request_items(instance: SNowInstance, sys_id: str) -> list[dict]:
    """
    Get all items that were ordered as part of a request

    Parameters:
    -----------
    sys_id: str
        The sys_id of the request to get items for

    Returns:
    --------
    list
        A list of dicts containing the items

    """
    # Get all items in the request
    items = table_api_call(
        instance=instance,
        table="sc_req_item",
        params={
            "sysparm_query": f"request={sys_id}",
            "sysparm_fields": ",".join(
                [
                    "sys_id",
                    "short_description",
                    "quantity",
                ]
            ),
        },
    )["result"]

    # For each item, get the options that were selected (if there are any)
    for item in items:
        options = table_api_call(
            instance=instance,
            table="sc_item_option_mtom",
            params={
                "sysparm_query": f"request_item={item['sys_id']}",
                "sysparm_fields": ",".join(
                    [
                        "sc_item_option.value",
                        "sc_item_option.item_option_new.question_text",
                    ]
                ),
            },
        )["result"]
        item["options"] = {
            opt["sc_item_option.item_option_new.question_text"]: opt["sc_item_option.value"]
            for opt in options
        }

    return items
