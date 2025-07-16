"""
Tests that are not specific to any particular kind of task.

"""
import logging
import os

import pytest

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright

from playwright.sync_api import Page, TimeoutError
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from browsergym.workarena import get_all_tasks_agents
from browsergym.workarena.tasks.compositional.base import CompositionalTask

# Combine all tasks into a single list for parameterization
AGENT_L2_SAMPLED_SET = get_all_tasks_agents(filter="l2", is_agent_curriculum=True)
AGENT_L3_SAMPLED_SET = get_all_tasks_agents(filter="l3", is_agent_curriculum=True)
HUMAN_L2_SAMPLED_SET = get_all_tasks_agents(filter="l2", is_agent_curriculum=False)
HUMAN_L3_SAMPLED_SET = get_all_tasks_agents(filter="l3", is_agent_curriculum=False)

all_tasks_to_test = (
    AGENT_L2_SAMPLED_SET + AGENT_L3_SAMPLED_SET + HUMAN_L2_SAMPLED_SET + HUMAN_L3_SAMPLED_SET
)

test_category = os.environ.get("TEST_CATEGORY")
if test_category:
    # If a category is specified, filter the tasks to test
    tasks_to_test = get_all_tasks_agents(filter=f"l3.{test_category}", is_agent_curriculum=True)
else:
    tasks_to_test = all_tasks_to_test


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.parametrize("task_class, seed", tasks_to_test)
@pytest.mark.pricy
def test_cheat_compositional(task_class, seed, page: Page):
    """
    Test that the cheat method works for all compositional tasks.
    This test is parameterized to run for all tasks in the agent and human curricula.
    """
    task = task_class(seed=seed)
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
