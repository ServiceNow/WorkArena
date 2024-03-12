import json
import logging
import multiprocessing
import re

from browsergym.workarena.tasks.form import __TASKS__
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from tqdm import tqdm


def camel_to_snake(name):
    """Convert camel case to snake case."""
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def generate_form_task_configs(task_name, task_class, num_configs=1000):
    """Generate forms by using random setup and validating the feasibility of the task; also ensure that the task is new."""

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_exception_type(TimeoutError),
        reraise=False,
        before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
    )
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
                config = {
                    "template_record": task.template_record,
                    "fields": {
                        f: task.fields[f]["label"] for f in task.fields
                    },  # the validate function only needs the field names
                    "task_fields": task.task_fields,
                }
                # If the task was never seen before, store it
                chat_messages = []
                try:
                    task.cheat(page=page, chat_messages=chat_messages)
                    task_successful = task.validate(page, chat_messages)[1]
                except Exception as e:  # Catch the exception
                    print(f"Error cheating on task {task_name} with seed {seed}: {str(e)}")
                    task_successful = False

                task.teardown()
                browser.close()
                if config not in current_task_configs and task_successful:
                    return config
        except Exception as e:
            print(f"Error setting up task {task_name} with seed {seed}: {str(e)}")
            return None

    current_task_configs = []
    seed = 30
    with tqdm(total=num_configs, desc=f"Generating {task_name} configs", ncols=70) as pbar:
        while len(current_task_configs) < num_configs:
            seed += 1
            config = try_setup_and_cheat(task_class, seed, current_task_configs)
            if config:
                current_task_configs.append(config)
                pbar.update(1)

    path = f"/home/toolkit/ui-copilot/browsergym/workarena/src/browsergym/workarena/data_files/task_configs/{camel_to_snake(task_name)}.json"
    with open(path, "w") as f:
        json.dump(current_task_configs, f)


if __name__ == "__main__":
    form_tasks = {task.__name__: task for task in __TASKS__}
    # iterate over all form tasks and generate their configurations
    # all form tasks should be saved in separate json files
    with multiprocessing.Pool() as pool:
        pool.starmap(generate_form_task_configs, form_tasks.items())
    # single process for debugging
    # for task_name, task_class in form_tasks.items():
    #     generate_form_task_configs(task_name, task_class)
