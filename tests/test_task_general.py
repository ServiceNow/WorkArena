"""
Tests that are not specific to any particular kind of task.

"""

import json
import logging
import pickle
import pytest

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

from playwright.sync_api import Page, TimeoutError
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from browsergym.workarena import ATOMIC_TASKS
from browsergym.workarena.instance import SNowInstance, fetch_instances

INSTANCE_POOL = fetch_instances()

if not INSTANCE_POOL:
    pytest.skip(
        "No ServiceNow instances available from fetch_instances().", allow_module_level=True
    )


@pytest.fixture(
    scope="session", params=INSTANCE_POOL, ids=[entry["url"] for entry in INSTANCE_POOL]
)
def snow_instance_entry(request):
    return request.param


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to an exception..."),
)
@pytest.mark.parametrize("task_entrypoint", ATOMIC_TASKS)
@pytest.mark.parametrize("random_seed", range(3))
@pytest.mark.slow
def test_cheat(task_entrypoint, random_seed: int, page: Page, snow_instance_entry):
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )
    task = task_entrypoint(seed=random_seed, instance=instance)
    goal, info = task.setup(page=page)
    chat_messages = []
    reward, done, message, info = task.validate(page, chat_messages)
    assert done is False and reward == 0.0
    assert type(message) == str and type(info) == dict
    task.cheat(page=page, chat_messages=chat_messages)
    reward, done, message, info = task.validate(page, chat_messages)
    task.teardown()
    assert done is True and reward == 1.0
