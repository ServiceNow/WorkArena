__version__ = "0.0.1a10"

from browsergym.core.registration import register_task

from .tasks.form import __TASKS__ as FORM_TASKS
from .tasks.knowledge import __TASKS__ as KB_TASKS
from .tasks.list import __TASKS__ as LIST_TASKS
from .tasks.navigation import __TASKS__ as NAVIGATION_TASKS
from .tasks.service_catalog import __TASKS__ as SERVICE_CATALOG_TASKS

ALL_WORKARENA_TASKS = [
    *FORM_TASKS,
    *KB_TASKS,
    *LIST_TASKS,
    *NAVIGATION_TASKS,
    *SERVICE_CATALOG_TASKS,
]

# register the WorkArena benchmark
for task in ALL_WORKARENA_TASKS:
    register_task(task.get_task_id(), task)
