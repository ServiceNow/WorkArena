__version__ = "0.3.0"

import inspect
import numpy as np

from browsergym.core.registration import register_task

from .tasks.comp_building_block import CompositionalBuildingBlockTask
from .tasks.dashboard import __TASKS__ as DASHBOARD_TASKS
from .tasks.form import __TASKS__ as FORM_TASKS
from .tasks.knowledge import __TASKS__ as KB_TASKS
from .tasks.list import __TASKS__ as LIST_TASKS
from .tasks.navigation import __TASKS__ as NAVIGATION_TASKS
from .tasks.compositional.base import CompositionalTask
from .tasks.compositional.update_task import __TASKS__ as UPDATE_TASKS
from .tasks.compositional import (
    ALL_COMPOSITIONAL_TASKS,
    ALL_COMPOSITIONAL_TASKS_L2,
    ALL_COMPOSITIONAL_TASKS_L3,
    AGENT_CURRICULUM_L2,
    AGENT_CURRICULUM_L3,
    HUMAN_CURRICULUM_L2,
    HUMAN_CURRICULUM_L3,
)
from .tasks.compositional.base import HumanEvalTask
from .tasks.service_catalog import __TASKS__ as SERVICE_CATALOG_TASKS

ALL_WORKARENA_TASKS = [
    *ALL_COMPOSITIONAL_TASKS_L2,
    *ALL_COMPOSITIONAL_TASKS_L3,
    *DASHBOARD_TASKS,
    *FORM_TASKS,
    *KB_TASKS,
    *LIST_TASKS,
    *NAVIGATION_TASKS,
    *SERVICE_CATALOG_TASKS,
    *UPDATE_TASKS,
]
ATOMIC_TASKS = [
    task
    for task in ALL_WORKARENA_TASKS
    if inspect.isclass(task)
    and not issubclass(task, CompositionalTask)
    and not issubclass(task, CompositionalBuildingBlockTask)
]


# register the WorkArena benchmark
for task in ALL_WORKARENA_TASKS:
    register_task(
        task.get_task_id(),
        task,
    )


def get_all_tasks_agents(filter="l2", meta_seed=42, n_seed_l1=10):
    all_task_tuples = []
    filter = filter.split(".")
    if len(filter) > 2:
        raise Exception("Unsupported filter used.")
    if len(filter) == 1:
        level = filter[0]
        if level not in ["l1", "l2", "l3"]:
            raise Exception("Unsupported category of tasks.")
        else:
            rng = np.random.RandomState(meta_seed)
        if level == "l1":
            for task in ATOMIC_TASKS:
                for seed in rng.randint(0, 1000, n_seed_l1):
                    all_task_tuples.append((task, int(seed)))

            return all_task_tuples

    if len(filter) == 2:
        level, filter_category = filter[0], filter[1]
        if filter_category not in list(AGENT_CURRICULUM_L2.keys()):
            raise Exception("Unsupported category of tasks.")
    else:
        filter_category = None

    if level == "l2":
        ALL_COMPOSITIONAL_TASKS_CATEGORIES = AGENT_CURRICULUM_L2
    else:
        ALL_COMPOSITIONAL_TASKS_CATEGORIES = AGENT_CURRICULUM_L3

    for category, items in ALL_COMPOSITIONAL_TASKS_CATEGORIES.items():
        if filter_category and category != filter_category:
            continue
        for curr_seed in rng.randint(0, 1000, items["num_seeds"]):
            random_gen = np.random.RandomState(curr_seed)
            for task_set, count in zip(items["buckets"], items["weights"]):
                tasks = random_gen.choice(task_set, count, replace=False)
                for task in tasks:
                    all_task_tuples.append((task, curr_seed))

    return all_task_tuples


def get_all_tasks_humans(filter="l2", meta_seed=42):
    OFFSET = 42
    all_task_tuples = []
    filter = filter.split(".")
    if len(filter) > 2:
        raise Exception("Unsupported filter used.")
    if len(filter) == 1:
        level = filter[0]
        if level not in ["l1", "l2", "l3"]:
            raise Exception("Unsupported category of tasks.")
        else:
            rng = np.random.RandomState(meta_seed)
        if level == "l1":
            return [(task, rng.randint(0, 1000)) for task in ATOMIC_TASKS]

    if len(filter) == 2:
        level, filter_category = filter[0], filter[1]
        if filter_category not in list(HUMAN_CURRICULUM_L2.keys()):
            raise Exception("Unsupported category of tasks.")
    else:
        filter_category = None

    if level == "l2":
        ALL_COMPOSITIONAL_TASKS_CATEGORIES = HUMAN_CURRICULUM_L2
    else:
        ALL_COMPOSITIONAL_TASKS_CATEGORIES = HUMAN_CURRICULUM_L3

    for category, items in ALL_COMPOSITIONAL_TASKS_CATEGORIES.items():
        if filter_category and category != filter_category:
            continue
        # We will come back to this after the submission
        for curr_seed in rng.randint(0, 1000, items["num_seeds"]):
            random_gen = np.random.RandomState(curr_seed)
            for task_set, count in zip(items["buckets"], items["weights"]):
                tasks = random_gen.choice(task_set, count, replace=False)
                for task in tasks:
                    all_task_tuples.append((task, curr_seed))

    return all_task_tuples
