"""
Tests that are not specific to any particular kind of task.

"""

import logging

import pytest

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

from playwright.sync_api import Page, TimeoutError
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from browsergym.workarena import ALL_COMPOSITIONAL_TASKS, get_all_tasks_agents

AGENT_L2_SAMPLED_SET = get_all_tasks_agents(filter="l2")

AGENT_L2_SAMPLED_TASKS, AGENT_L2_SEEDS = [sampled_set[0] for sampled_set in AGENT_L2_SAMPLED_SET], [
    sampled_set[1] for sampled_set in AGENT_L2_SAMPLED_SET
]

AGENT_L3_SAMPLED_SET = get_all_tasks_agents(filter="l3")

AGENT_L3_SAMPLED_TASKS, AGENT_L3_SEEDS = [sampled_set[0] for sampled_set in AGENT_L3_SAMPLED_SET], [
    sampled_set[1] for sampled_set in AGENT_L3_SAMPLED_SET
]

HUMAN_L2_SAMPLED_SET = get_all_tasks_agents(filter="l2", is_agent_curriculum=False)

HUMAN_L2_SAMPLED_TASKS, HUMAN_L2_SEEDS = [sampled_set[0] for sampled_set in HUMAN_L2_SAMPLED_SET], [
    sampled_set[1] for sampled_set in HUMAN_L2_SAMPLED_SET
]

HUMAN_L3_SAMPLED_SET = get_all_tasks_agents(filter="l3", is_agent_curriculum=False)

HUMAN_L3_SAMPLED_TASKS, HUMAN_L3_SEEDS = [sampled_set[0] for sampled_set in HUMAN_L3_SAMPLED_SET], [
    sampled_set[1] for sampled_set in HUMAN_L3_SAMPLED_SET
]


@retry(
    stop=stop_after_attempt(5),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint", ALL_COMPOSITIONAL_TASKS)
@pytest.mark.parametrize("random_seed", range(1))
@pytest.mark.parametrize("level", range(2, 4))
@pytest.mark.pricy
def test_cheat_compositional(task_entrypoint, random_seed, level, page: Page):
    task = task_entrypoint(seed=random_seed, level=level)
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


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint, seed", zip(AGENT_L2_SAMPLED_TASKS, AGENT_L2_SEEDS))
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_cheat_compositional_sampled_agent_set_l2(task_entrypoint, seed, page: Page):
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


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint, seed", zip(AGENT_L3_SAMPLED_TASKS, AGENT_L3_SEEDS))
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_cheat_compositional_sampled_agent_set_l3(task_entrypoint, seed, page: Page):
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


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint, seed", zip(HUMAN_L2_SAMPLED_TASKS, HUMAN_L2_SEEDS))
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_cheat_compositional_sampled_human_set_l2(task_entrypoint, seed, page: Page):
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


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_entrypoint, seed", zip(HUMAN_L3_SAMPLED_TASKS, HUMAN_L3_SEEDS))
@pytest.mark.slow
@pytest.mark.skip(reason="Tests are too slow")
def test_cheat_compositional_sampled_human_set_l3(task_entrypoint, seed, page: Page):
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
