import json
import multiprocessing
import random
import re

from browsergym.workarena.tasks.list import __TASKS__
from playwright.sync_api import sync_playwright
from tqdm import tqdm

# Split between filter and sort tasks
FILTER_TASKS = [
    task for task in __TASKS__ if re.compile(r"^Filter\w+ListTask$").match(task.__name__)
]
SORT_TASKS = [task for task in __TASKS__ if re.compile(r"^Sort\w+ListTask$").match(task.__name__)]


def generate_sort_task_configs(task_class, num_configs_per_field_count=50):
    name = task_class.__name__
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    task_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()
    all_configs = []
    for n_fields_to_sort in range(1, 4):
        with sync_playwright() as p:
            task = task_class()
            browser = p.chromium.launch()
            context = browser.new_context()  # Set the timeout here
            context.set_default_timeout(5000)
            page = context.new_page()
            all_new_configs = task._generate_all_configs(
                seed=None, page=page, n_fields_to_sort=n_fields_to_sort
            )
            new_configs = random.sample(all_new_configs, num_configs_per_field_count)
            all_configs.extend(new_configs)

        print(f"{task_name} {n_fields_to_sort} fields - {len(new_configs)} configs")

    with open(
        f"{task_name}.json",
        "w",
    ) as f:
        all_configs = sorted(all_configs, key=lambda x: sorted(list(x["sort_fields"])))
        json.dump(all_configs, f, indent=4, sort_keys=True)


def generate_task_configs(task_class, num_configs=1000, task_type="sort"):
    def try_setup_and_cheat(task_class, seed, current_task_configs):
        """Try to setup and cheat a task, and return its configuration if it's new"""
        try:
            with sync_playwright() as p:
                task = task_class(seed=seed)
                browser = p.chromium.launch()
                context = browser.new_context()  # Set the timeout here
                context.set_default_timeout(5000)
                page = context.new_page()
                goal, _ = task._generate_random_config(page=page)
                chat_messages = []
                try:
                    task.cheat(page=page, chat_messages=chat_messages)
                    reward, done, message, info = task.validate(page, chat_messages)
                    task_successful = done is True and reward == 1.0
                except Exception as e:  # Catch the exception
                    print(f"Error cheating on task {task_name} with seed {seed}: {str(e)}")
                    task_successful = False
                if task_type == "sort":
                    config = {
                        "sort_fields": task.sort_fields,
                        "sort_dirs": task.sort_dirs,
                        "goal": goal,
                    }
                elif task_type == "filter":
                    list_info = {k: v for k, v in task.list_info.items() if k in ["columns"]}
                    config = {
                        "list_info": list_info,
                        "filter_columns": task.filter_columns,
                        "filter_values": task.filter_values,
                        "filter_kind": task.filter_kind,
                    }
                task.teardown()
                browser.close()
                if task_successful and config not in current_task_configs:
                    return config
        except Exception as e:
            print(f"Error setting up task {task_name} with seed {seed}: {str(e)}")
            return None

    name = task_class.__name__
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    task_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    current_task_configs = []
    seed = 1000
    with tqdm(total=num_configs, desc=f"Generating {task_name} configs", ncols=150) as pbar:
        while len(current_task_configs) < num_configs:
            seed += 1
            config = try_setup_and_cheat(task_class, seed, current_task_configs)
            if config:
                current_task_configs.append(config)
                pbar.update(1)
                print(f"Success for {task_name} config")
    with open(
        f"{task_name}.json",
        "w",
    ) as f:
        if task_type == "sort":
            current_task_configs = sorted(
                current_task_configs, key=lambda x: sorted(list(x["sort_fields"]))
            )
        else:
            current_task_configs = sorted(
                current_task_configs, key=lambda x: sorted(list(x["filter_columns"]))
            )
        json.dump(current_task_configs, f, indent=4, sort_keys=True)


if __name__ == "__main__":
    for task in SORT_TASKS:
        generate_sort_task_configs(task)
