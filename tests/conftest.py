import os

import pytest

SHARD_ENV = "WORKARENA_TEST_SHARD"


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    # Nightly CI sets e.g. WORKARENA_TEST_SHARD=3/7 to run one seventh of the selected tests
    spec = os.environ.get(SHARD_ENV)
    if not spec:
        return
    try:
        index, count = (int(part) for part in spec.split("/"))
    except ValueError:
        raise pytest.UsageError(f"{SHARD_ENV} must look like '3/7', got {spec!r}")
    if not 0 <= index < count:
        raise pytest.UsageError(f"{SHARD_ENV} index must be in [0, {count}), got {spec!r}")

    selected = [item for i, item in enumerate(items) if i % count == index]
    deselected = [item for i, item in enumerate(items) if i % count != index]
    config.hook.pytest_deselected(items=deselected)
    items[:] = selected
