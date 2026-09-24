"""
Checks that every pool instance still satisfies the catalog preconditions the task code relies on.

These detect instance drift (e.g. a benchmark agent editing a catalog item) rather than code bugs.

"""

from collections import Counter
from functools import lru_cache
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

from utils import RedactedInstanceEntry

INSTANCE_POOL = [RedactedInstanceEntry(entry) for entry in fetch_instances()]

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


# Content fields expected to be identical on every instance; sys_updated_on and the like churn legitimately
COMPARED_FIELDS = (
    "name",
    "sys_name",
    "active",
    "category",
    "price",
    "short_description",
    "sc_catalogs",
    "order",
)


def _host(entry):
    return entry["url"].split("//")[1].split(".")[0]


@lru_cache(maxsize=None)
def _fetch_catalog(url, password):
    instance = SNowInstance(snow_url=url, snow_credentials=("admin", password))
    fields = ("sys_id", "category.title", "sys_updated_by") + COMPARED_FIELDS
    return table_api_call(
        instance=instance,
        table="sc_cat_item",
        params={
            "sysparm_fields": ",".join(fields),
            "sysparm_limit": "10000",
            "sysparm_exclude_reference_link": "true",
        },
    )["result"]


@pytest.fixture(scope="module", params=INSTANCE_POOL, ids=[_host(e) for e in INSTANCE_POOL])
def instance_entry(request):
    return request.param


@pytest.fixture(scope="module")
def catalog(instance_entry):
    return _fetch_catalog(instance_entry["url"], instance_entry["password"])


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


@pytest.mark.pool_health
def test_catalog_matches_other_instances(instance_entry, catalog):
    # Compares against the majority of the pool, so drift shared by most instances goes unnoticed
    pool = {
        _host(e): {row["sys_id"]: row for row in _fetch_catalog(e["url"], e["password"])}
        for e in INSTANCE_POOL
    }
    if len(pool) < 2:
        pytest.skip("Only one instance in the pool, nothing to compare against")
    size = len(pool)
    mine = {row["sys_id"]: row for row in catalog}

    problems = []
    for sys_id in sorted(set().union(*pool.values())):
        holders = [host for host in pool if sys_id in pool[host]]
        if len(holders) == size:
            continue
        if sys_id in mine and len(holders) * 2 <= size:
            row = mine[sys_id]
            problems.append(
                f"extra item {row['name']!r} ({sys_id}) found on {len(holders)}/{size} instances, "
                f"last updated by {row['sys_updated_by']}"
            )
        elif sys_id not in mine and len(holders) * 2 > size:
            name = pool[holders[0]][sys_id]["name"]
            problems.append(
                f"missing item {name!r} ({sys_id}) found on {len(holders)}/{size} instances"
            )

    for sys_id, row in sorted(mine.items()):
        if any(sys_id not in pool[host] for host in pool):
            continue  # presence differences are reported above
        for field in COMPARED_FIELDS:
            counts = Counter(pool[host][sys_id][field] for host in pool)
            if len(counts) == 1:
                continue
            value, count = counts.most_common(1)[0]
            if row[field] != value or count * 2 <= size:
                problems.append(
                    f"{row['name']!r}: {field}={row[field]!r} while {count}/{size} instances have "
                    f"{value!r}, last updated by {row['sys_updated_by']}"
                )

    assert not problems, "catalog differs from the rest of the pool:\n" + "\n".join(problems)
