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
    all_configs = sorted(all_configs, key=lambda x: x["item"] + x["question"])

    return all_configs


if __name__ == "__main__":

    validate_kb_configs()
