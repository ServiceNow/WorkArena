import json
import multiprocessing
import re

from browsergym.workarena.tasks.list import __TASKS__
from playwright.sync_api import sync_playwright
from tqdm import tqdm

# Split between filter and sort tasks
FILTER_TASKS = [
    task for task in __TASKS__ if re.compile(r"^Filter\w+ListTask$").match(task.__name__)
]
SORT_TASKS = [task for task in __TASKS__ if re.compile(r"^Sort\w+ListTask$").match(task.__name__)]


def generate_task_configs(task_class, num_configs=1000, task_type="sort"):
    def try_setup_and_cheat(task_class, seed, current_task_configs):
        """Try to setup and cheat a task, and return its configuration if it's new"""
        try:
            with sync_playwright() as p:
                task = task_class()
                browser = p.chromium.launch()
                context = browser.new_context()  # Set the timeout here
                context.set_default_timeout(5000)
                page = context.new_page()
                task._generate_random_config(seed=seed, page=page)
                chat_messages = []
                try:
                    task.cheat(page=page, chat_messages=chat_messages)
                    task_successful = task.validate(page, chat_messages)[1]
                except Exception as e:  # Catch the exception
                    print(f"Error cheating on task {task_name} with seed {seed}: {str(e)}")
                    task_successful = False
                if task_type == "sort":
                    config = {
                        "sort_fields": task.sort_fields,
                        "sort_dirs": task.sort_dirs,
                        "goal": task.goal,
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
        f"browsergym/workarena/src/browsergym/workarena/data_files/task_configs/{task_name}.json",
        "w",
    ) as f:
        json.dump(current_task_configs, f)


if __name__ == "__main__":
    print(FILTER_TASKS)
    with multiprocessing.Pool() as pool:
        pool.starmap(
            generate_task_configs,
            [(task, 1000, "sort") for task in SORT_TASKS]
            + [(task, 1000, "filter") for task in FILTER_TASKS],
        )
