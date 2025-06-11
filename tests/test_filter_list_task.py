import pytest
from playwright.sync_api import Page
from browsergym.workarena.tasks.list import FilterIncidentListTask


# These are all the same ways to express the same filter query (empty string) in ServiceNow.
@pytest.mark.parametrize(
    "query",
    [
        "assigned_toEMPTYSTRING^short_descriptionISEMPTY^description=This is a beautiful incident",
        "assigned_toISEMPTY^short_descriptionEMPTYSTRING^description=This is a beautiful incident^",
        "assigned_toISEMPTY^short_descriptionISEMPTY^description=This is a beautiful incident",
        "assigned_toEMPTYSTRING^short_descriptionEMPTYSTRING^description=This is a beautiful incident^",
        "assigned_to=^short_description=^description=This is a beautiful incident",
    ],
)
@pytest.mark.slow
def test_validate_filter_list_task(page: Page, query):
    fixed_config = {
        "filter_columns": [
            "short_description",
            "assigned_to",
            "description",
        ],
        "filter_kind": "AND",
        "filter_values": [
            "",
            "",
            "This is a beautiful incident",
        ],
    }
    task = FilterIncidentListTask(seed=1, fixed_config=fixed_config)
    _, _ = task.setup(page=page)
    query = query.replace("^", r"%5E").replace("=", r"%3D")
    task.page.goto(
        task.instance.snow_url
        + rf"/now/nav/ui/classic/params/target/incident_list.do?sysparm_query={query}"
    )
    reward, done, _, info = task.validate(page, [])
    task.teardown()
    assert done is True and reward == 1.0 and "Correct filter" in info["message"]


# Different ways in which the filter is wrong
@pytest.mark.parametrize(
    "query, expected_message",
    [
        ("", "There are no filters yet"),
        ("assignment_groupEMPTYSTRING", "Incorrect number of filter conditions"),
        (
            "assigned_toEMPTYSTRING^short_description!=Description",
            "Unexpected operator in filter condition",
        ),
        ("assigned_toEMPTYSTRING^short_description=Description", "Incorrect filter columns"),
        ("assigned_toISEMPTY^description=My Description", "Incorrect filter values"),
    ],
)
@pytest.mark.slow
def test_invalid_filter_list_task(page: Page, query, expected_message):
    fixed_config = {
        "filter_columns": [
            "assigned_to",
            "description",
        ],
        "filter_kind": "AND",
        "filter_values": [
            "",
            "Description",
        ],
    }
    task = FilterIncidentListTask(seed=1, fixed_config=fixed_config)
    _, _ = task.setup(page=page)
    query = query.replace("^", r"%5E").replace("=", r"%3D")
    task.page.goto(
        task.instance.snow_url
        + f"/now/nav/ui/classic/params/target/incident_list.do?sysparm_query={query}"
    )
    reward, done, _, info = task.validate(page, [])
    task.teardown()
    print(info["message"])
    assert done is False and reward == 0.0 and expected_message in info["message"]
