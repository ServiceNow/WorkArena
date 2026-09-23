"""
Network-free tests for how compositional tasks bind their subtasks to the parent's instance.

"""

from types import SimpleNamespace

import pytest

import browsergym.workarena.tasks.compositional.base as compositional_base
from browsergym.workarena.tasks.compositional.base import CompositionalTask

PARENT_URL = "https://parent.service-now.com"


class StubSubtask:
    """A subtask that starts out bound to its own instance, like one built with instance=None."""

    def __init__(self, url="https://own-pick.service-now.com", **kwargs):
        self.instance = SimpleNamespace(snow_url=url, snow_credentials=("admin", "pool-pw"))
        self.used_in_level_2 = True
        self.sys_id = "stub-sys-id"

    def setup(self, page, do_start=True):
        return "stub goal", {}


@pytest.mark.parametrize("level", [2, 3])
def test_subtasks_are_bound_to_parent_instance(level, monkeypatch):
    # The L3 final tasks would otherwise create records on a live instance during setup
    monkeypatch.setattr(compositional_base, "AllMenuTask", StubSubtask)
    monkeypatch.setattr(compositional_base, "UpdatePrivateTask", StubSubtask)

    parent_instance = SimpleNamespace(snow_url=PARENT_URL, snow_credentials=("admin", "pool-pw"))
    task = CompositionalTask(seed=0, instance=parent_instance, level=level)
    task._base_user_name = "task.user"
    task._base_user_password = "task-pw"
    task._base_user_sysid = "task-sysid"

    config = [
        StubSubtask("https://other-a.service-now.com"),
        StubSubtask("https://other-b.service-now.com"),
    ]
    task.setup_goal(page=None, config=config, build_pretty_print_description=False)

    assert len(task.subtasks) == (2 if level == 2 else 4)
    for subtask in task.subtasks:
        assert subtask.instance is task.instance
        assert subtask.instance.snow_url == PARENT_URL
        assert subtask.instance.snow_credentials == ("task.user", "task-pw")
        assert subtask._base_user_sysid == "task-sysid"
