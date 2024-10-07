__version__ = "0.4.1"

import inspect
from logging import warning

import numpy as np
from browsergym.core.registration import register_task

from .tasks.comp_building_block import CompositionalBuildingBlockTask
from .tasks.compositional import (
    AGENT_CURRICULUM_L2,
    AGENT_CURRICULUM_L3,
    ALL_COMPOSITIONAL_TASKS,
    ALL_COMPOSITIONAL_TASKS_L2,
    ALL_COMPOSITIONAL_TASKS_L3,
    HUMAN_CURRICULUM_L2,
    HUMAN_CURRICULUM_L3,
)
from .tasks.compositional.base import CompositionalTask, HumanEvalTask
from .tasks.compositional.update_task import __TASKS__ as UPDATE_TASKS
from .tasks.dashboard import __TASKS__ as DASHBOARD_TASKS
from .tasks.form import __TASKS__ as FORM_TASKS
from .tasks.knowledge import __TASKS__ as KB_TASKS
from .tasks.list import __TASKS__ as LIST_TASKS
from .tasks.navigation import __TASKS__ as NAVIGATION_TASKS
from .tasks.service_catalog import __TASKS__ as SERVICE_CATALOG_TASKS
from .tasks.compositional.base import CompositionalTask

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

workarena_tasks_all = [task_class.get_task_id() for task_class in ALL_WORKARENA_TASKS]
workarena_tasks_atomic = [task_class.get_task_id() for task_class in ATOMIC_TASKS]

TASK_CATEGORY_MAP = {
    "workarena.servicenow.all-menu": "menu",
    "workarena.servicenow.create-change-request": "form",
    "workarena.servicenow.create-hardware-asset": "form",
    "workarena.servicenow.create-incident": "form",
    "workarena.servicenow.create-problem": "form",
    "workarena.servicenow.create-user": "form",
    "workarena.servicenow.filter-asset-list": "list-filter",
    "workarena.servicenow.filter-change-request-list": "list-filter",
    "workarena.servicenow.filter-hardware-list": "list-filter",
    "workarena.servicenow.filter-incident-list": "list-filter",
    "workarena.servicenow.filter-service-catalog-item-list": "list-filter",
    "workarena.servicenow.filter-user-list": "list-filter",
    "workarena.servicenow.impersonation": "menu",
    "workarena.servicenow.knowledge-base-search": "knowledge",
    "workarena.servicenow.order-apple-mac-book-pro15": "service catalog",
    "workarena.servicenow.order-apple-watch": "service catalog",
    "workarena.servicenow.order-developer-laptop": "service catalog",
    "workarena.servicenow.order-development-laptop-p-c": "service catalog",
    "workarena.servicenow.order-ipad-mini": "service catalog",
    "workarena.servicenow.order-ipad-pro": "service catalog",
    "workarena.servicenow.order-loaner-laptop": "service catalog",
    "workarena.servicenow.order-sales-laptop": "service catalog",
    "workarena.servicenow.order-standard-laptop": "service catalog",
    "workarena.servicenow.sort-asset-list": "list-sort",
    "workarena.servicenow.sort-change-request-list": "list-sort",
    "workarena.servicenow.sort-hardware-list": "list-sort",
    "workarena.servicenow.sort-incident-list": "list-sort",
    "workarena.servicenow.sort-service-catalog-item-list": "list-sort",
    "workarena.servicenow.sort-user-list": "list-sort",
    "workarena.servicenow.multi-chart-min-max-retrieval": "dashboard",
    "workarena.servicenow.multi-chart-value-retrieval": "dashboard",
    "workarena.servicenow.single-chart-value-retrieval": "dashboard",
    "workarena.servicenow.single-chart-min-max-retrieval": "dashboard",
}


workarena_tasks_l1 = list(TASK_CATEGORY_MAP.keys())
workarena_task_categories = {}
for task in workarena_tasks_atomic:
    if task not in TASK_CATEGORY_MAP:
        warning(f"Atomic task {task} not found in TASK_CATEGORY_MAP")
        continue
    cat = TASK_CATEGORY_MAP[task]
    if cat in workarena_task_categories:
        workarena_task_categories[cat].append(task)
    else:
        workarena_task_categories[cat] = [task]


def get_task_category(task_name):
    benchmark = task_name.split(".")[0]
    return benchmark, TASK_CATEGORY_MAP.get(task_name, None)


def get_all_tasks_agents(filter="l2", meta_seed=42, n_seed_l1=10, is_agent_curriculum=True):
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

    if is_agent_curriculum:
        if level == "l2":
            ALL_COMPOSITIONAL_TASKS_CATEGORIES = AGENT_CURRICULUM_L2
        else:
            ALL_COMPOSITIONAL_TASKS_CATEGORIES = AGENT_CURRICULUM_L3
    else:
        if level == "l2":
            ALL_COMPOSITIONAL_TASKS_CATEGORIES = HUMAN_CURRICULUM_L2
        else:
            ALL_COMPOSITIONAL_TASKS_CATEGORIES = HUMAN_CURRICULUM_L3

    for category, items in ALL_COMPOSITIONAL_TASKS_CATEGORIES.items():
        category_seeds = rng.randint(0, 1000, items["num_seeds"])
        if filter_category and category != filter_category:
            continue
        for curr_seed in category_seeds:
            random_gen = np.random.RandomState(curr_seed)
            for task_set, count in zip(items["buckets"], items["weights"]):
                tasks = random_gen.choice(task_set, count, replace=False)
                for task in tasks:
                    all_task_tuples.append((task, int(curr_seed)))

    return all_task_tuples
