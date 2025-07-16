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

from browsergym.workarena import ATOMIC_TASKS, get_all_tasks_agents


L1_SET = get_all_tasks_agents(filter="l1")
L1_TASKS, L1_SEEDS = [item[0] for item in L1_SET], [item[1] for item in L1_SET]


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint", ATOMIC_TASKS)
@pytest.mark.parametrize("random_seed", range(1))
@pytest.mark.slow
def test_cheat(task_entrypoint, random_seed: int, page: Page):
    task = task_entrypoint(seed=random_seed)
    goal, info = task.setup(page=page)
    chat_messages = []
    reward, done, message, info = task.validate(page, chat_messages)
    assert done is False and reward == 0.0
    assert type(message) == str and type(info) == dict
    task.cheat(page=page, chat_messages=chat_messages)
    reward, done, message, info = task.validate(page, chat_messages)
    task.teardown()
    assert done is True and reward == 1.0


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint, seed", zip(L1_TASKS, L1_SEEDS))
@pytest.mark.slow
def test_l1_cheat(task_entrypoint, seed, page: Page):
    task = task_entrypoint(seed=seed)
    goal, info = task.setup(page=page)
    chat_messages = []
    for i in range(len(task)):
        page.wait_for_timeout(1000)
        task.cheat(page=page, chat_messages=chat_messages, subtask_idx=i)
        page.wait_for_timeout(1000)
        reward, done, message, info = task.validate(page=page, chat_messages=chat_messages)
        if i < len(task) - 1:
            assert done is False and reward == 0.0

    task.teardown()

    assert done is True and reward == 1.0
