import random

from browsergym.workarena import get_all_tasks_humans


tasks_l2 = get_all_tasks_humans(filter="l2", meta_seed=42)
tasks_l3 = get_all_tasks_humans(filter="l3", meta_seed=42)

tasks = tasks_l2 + tasks_l3
random.shuffle(tasks)

annotators = [
    "darwiche",
    "parikh",
    "marchand",
    "paquet",
    "nayal",
    "huang",
    "subbaraj",
    "williams",
    "li",
    "marcotte",
    "rancourt",
    "prince_tremblay",
    "ashok",
    "bajaj",
]
random.shuffle(annotators)

print("Number of tasks: ", len(tasks))
print("Number of annotators: ", len(annotators))

tasks_by_annotator = {}
n_base_assignment = len(tasks) // len(annotators)
n_extra_assignment = len(tasks) % len(annotators)
for i, annotator in enumerate(annotators):
    n_assignments = n_base_assignment + (1 if i < n_extra_assignment else 0)
    tasks_by_annotator[annotator] = tasks[:n_assignments]
    tasks = tasks[n_assignments:]
    print(f"{annotator}: {n_assignments}")

    with open(f"{annotator}.tasks", "w") as f:
        for task in tasks_by_annotator[annotator]:
            f.write(f"{task[0].__name__},{task[1]}\n")
