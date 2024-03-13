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

from browsergym.workarena import ALL_WORKARENA_TASKS


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint", ALL_WORKARENA_TASKS)
@pytest.mark.parametrize("random_seed", range(1))
@pytest.mark.slow
def test_cheat(task_entrypoint, random_seed: int, page: Page):
    task = task_entrypoint()
    goal, info = task.setup(seed=random_seed, page=page)
    chat_messages = []
    reward, done, message, info = task.validate(page, chat_messages)
    assert done is False and reward == 0.0
    task.cheat(page=page, chat_messages=chat_messages)
    reward, done, message, info = task.validate(page, chat_messages)
    assert done is True and reward == 1.0
    task.teardown()
