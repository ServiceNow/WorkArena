"""
Checks that every pool instance still satisfies the catalog preconditions the task code relies on.

These detect instance drift (e.g. a benchmark agent editing a catalog item) rather than code bugs.

"""

from types import SimpleNamespace

import pytest

from browsergym.workarena.api.utils import table_api_call
from browsergym.workarena.instance import SNowInstance, fetch_instances
from browsergym.workarena.tasks import service_catalog
from browsergym.workarena.tasks.compositional import (
    dash_do_request_item,
    dash_do_request_item_infeasible,
    find_and_order_item,
)
from browsergym.workarena.tasks.compositional.dash_do_base import CATALOG_ITEM_SYS_NAMES

INSTANCE_POOL = fetch_instances()

# Tasks only read snow_url at construction, so a stand-in lets us read their item names offline
_OFFLINE = SimpleNamespace(snow_url="https://offline.service-now.com")

# Names that OrderHardwareTask.cheat clicks in the Hardware category via h2:has-text(...)
STOREFRONT_ITEMS = sorted(
    {config["item"] for task in service_catalog.__TASKS__ for config in task.all_configs()}
)

# Names that task setup resolves with a sys_name= Table API query (case-insensitive)
QUERIED_SYS_NAMES = sorted(
    set(CATALOG_ITEM_SYS_NAMES.values())
    | {task(seed=0, instance=_OFFLINE).fixed_request_item for task in find_and_order_item.__TASKS__}
)

# Names that request-item validation compares to the ordered item's sys_name with != (case-sensitive)
VALIDATED_SYS_NAMES = sorted(
    {
        task(seed=0, instance=_OFFLINE).item
        for module in (dash_do_request_item, dash_do_request_item_infeasible)
        for task in module.__TASKS__
    }
)


@pytest.fixture(
    scope="module",
    params=INSTANCE_POOL,
    ids=[entry["url"].split("//")[1].split(".")[0] for entry in INSTANCE_POOL],
)
def catalog(request):
    instance = SNowInstance(
        snow_url=request.param["url"], snow_credentials=("admin", request.param["password"])
    )
    return table_api_call(
        instance=instance,
        table="sc_cat_item",
        params={"sysparm_fields": "name,sys_name,active,category.title", "sysparm_limit": "10000"},
    )["result"]


@pytest.mark.pool_health
@pytest.mark.parametrize("item", STOREFRONT_ITEMS)
def test_storefront_item_is_unique(catalog, item):
    # has-text is a case-insensitive substring match, so a second active item containing the
    # name (e.g. "Apple Watch Series 2" for "Apple Watch") breaks the order tasks
    matches = sorted(
        row["name"]
        for row in catalog
        if row["active"] == "true"
        and row["category.title"] == "Hardware"
        and item.lower() in row["name"].lower()
    )
    assert len(matches) == 1, f"'{item}' matches {len(matches)} active Hardware items: {matches}"


def _sys_name_matches(catalog, sys_name):
    return sorted(row["sys_name"] for row in catalog if row["sys_name"].lower() == sys_name.lower())


@pytest.mark.pool_health
@pytest.mark.parametrize("sys_name", QUERIED_SYS_NAMES)
def test_queried_sys_name_resolves(catalog, sys_name):
    # sys_name is resynced from the name when a record is edited, which breaks these lookups
    matches = _sys_name_matches(catalog, sys_name)
    assert len(matches) == 1, f"sys_name '{sys_name}' matches {len(matches)} items: {matches}"


@pytest.mark.pool_health
@pytest.mark.parametrize("sys_name", VALIDATED_SYS_NAMES)
def test_validated_sys_name_is_exact(catalog, sys_name):
    matches = _sys_name_matches(catalog, sys_name)
    assert matches == [sys_name], f"expected exactly sys_name '{sys_name}', found {matches}"
