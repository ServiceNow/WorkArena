from .utils.curriculum import AGENT_CURRICULUM, HUMAN_CURRICULUM

ALL_COMPOSITIONAL_TASKS = []

for category, items in AGENT_CURRICULUM.items():
    category_tasks = []
    for task in items["buckets"]:
        category_tasks += task
    ALL_COMPOSITIONAL_TASKS += category_tasks


def specialize_task_class_to_level(task_cls, level):
    """
    Function to hardcode the level for the tasks
    """
    new_name = f"{task_cls.__name__}L{level}"
    patched_cls = f"""
class {new_name}(task_cls):
    def __init__(self, **kwargs):
        super().__init__(level={level}, **kwargs)
"""
    # Dictionary to capture local variables defined by exec
    local_vars = {"task_cls": task_cls}
    exec(patched_cls, globals(), local_vars)
    return local_vars[new_name]


ALL_COMPOSITIONAL_TASKS_L2 = [
    specialize_task_class_to_level(task, level=2) for task in ALL_COMPOSITIONAL_TASKS
]
ALL_COMPOSITIONAL_TASKS_L3 = [
    specialize_task_class_to_level(task, level=3) for task in ALL_COMPOSITIONAL_TASKS
]


AGENT_CURRICULUM_L2 = dict()
AGENT_CURRICULUM_L3 = dict()

for category, items in AGENT_CURRICULUM.items():
    AGENT_CURRICULUM_L2[category] = {
        "buckets": [
            [specialize_task_class_to_level(task, level=2) for task in task_set]
            for task_set in items["buckets"]
        ],
        "num_seeds": items["num_seeds"],
        "weights": items["weights"],
    }
    AGENT_CURRICULUM_L3[category] = {
        "buckets": [
            [specialize_task_class_to_level(task, level=3) for task in task_set]
            for task_set in items["buckets"]
        ],
        "num_seeds": items["num_seeds"],
        "weights": items["weights"],
    }

HUMAN_CURRICULUM_L2 = dict()
HUMAN_CURRICULUM_L3 = dict()

for category, items in HUMAN_CURRICULUM.items():
    HUMAN_CURRICULUM_L2[category] = {
        "buckets": [
            [specialize_task_class_to_level(task, level=2) for task in task_set]
            for task_set in items["buckets"]
        ],
        "num_seeds": items["num_seeds"],
        "weights": items["weights"],
    }
    HUMAN_CURRICULUM_L3[category] = {
        "buckets": [
            [specialize_task_class_to_level(task, level=3) for task in task_set]
            for task_set in items["buckets"]
        ],
        "num_seeds": items["num_seeds"],
        "weights": items["weights"],
    }
