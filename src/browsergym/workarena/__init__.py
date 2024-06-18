__version__ = "0.3.1"

import inspect
import numpy as np

from browsergym.core.registration import register_task

from .tasks.comp_building_block import CompositionalBuildingBlockTask
from .tasks.dashboard import __TASKS__ as DASHBOARD_TASKS
from .tasks.form import __TASKS__ as FORM_TASKS
from .tasks.knowledge import __TASKS__ as KB_TASKS
from .tasks.list import __TASKS__ as LIST_TASKS
from .tasks.navigation import __TASKS__ as NAVIGATION_TASKS
from .tasks.service_catalog import __TASKS__ as SERVICE_CATALOG_TASKS
from .tasks.compositional.base import CompositionalTask

ALL_WORKARENA_TASKS = [
    *DASHBOARD_TASKS,
    *FORM_TASKS,
    *KB_TASKS,
    *LIST_TASKS,
    *NAVIGATION_TASKS,
    *SERVICE_CATALOG_TASKS,
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
