import json
import random

from browsergym.workarena.api.utils import SNowInstance
from browsergym.workarena.config import KB_FILEPATH, KB_CONFIG_PATH
from browsergym.workarena.tasks.knowledge import KnowledgeBaseSearchTask
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt
from tqdm import tqdm


def generate_all_kb_configs(instance=None, num_configs=1000) -> list[dict]:
    """Generate all possible KB configs"""
    instance = instance if instance is not None else SNowInstance()
    with open(KB_FILEPATH, "r") as f:
        kb_entries = json.load(f)
    all_configs = []
    for kb_entry in kb_entries:
        for question in kb_entry["questions"]:
            config = {
                "item": kb_entry["item"],
                "value": kb_entry["value"],
                "alternative_answers": kb_entry["alternative_answers"],
                "question": question,
            }
            all_configs.append(config)
    # sample the configs
    if len(all_configs) > num_configs:
        all_configs = random.sample(all_configs, num_configs)
    return all_configs


@retry(stop=stop_after_attempt(10), reraise=True)
def validate_task(task_config):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        task = KnowledgeBaseSearchTask.from_config(task_config)
        task.setup(page=page)
        chat_messages = []
        task.cheat(page=page, chat_messages=chat_messages)
        task_successful = task.validate(page, chat_messages)[1]
        task.teardown()
        browser.close()

        return task_successful, task_config


def validate_kb_configs() -> list[dict]:
    with open(KB_CONFIG_PATH, "r") as f:
        all_configs = json.load(f)

    failed_tasks = []
    with tqdm(total=len(all_configs), desc="Validating KB configs", ncols=150) as pbar:
        for task_config in all_configs:
            try:
                success, task_config = validate_task(task_config)
                if not success:
                    failed_tasks.append(task_config)
            except Exception as e:
                failed_tasks.append(task_config)
            pbar.update(1)
    # Save failed tasks to a JSON file
    with open("failed_tasks.json", "w") as f:
        json.dump(failed_tasks, f)

    # Now failed_tasks contains all the tasks that failed after 10 attempts
    print(f"Failed tasks: {failed_tasks}")


if __name__ == "__main__":

    validate_kb_configs()
