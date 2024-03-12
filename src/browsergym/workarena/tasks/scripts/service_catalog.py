import json
import multiprocessing
import random
import re

from itertools import product, combinations
from browsergym.workarena.tasks.service_catalog import META_CONFIGS
from browsergym.workarena.config import (
    ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH,
    ORDER_IPAD_MINI_TASK_CONFIG_PATH,
    ORDER_IPAD_PRO_TASK_CONFIG_PATH,
    ORDER_SALES_LAPTOP_TASK_CONFIG_PATH,
    ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH,
    ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
    ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH,
    ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH,
)
from browsergym.workarena.tasks.service_catalog import __TASKS__

# The number of configurations to generate per item, as described in the WorkArena paper
NUM_CONFIGS_PER_ITEM = {
    "Developer Laptop (Mac)": 1000,
    "iPad mini": 80,
    "iPad pro": 90,
    "Sales Laptop": 1000,
    "Standard Laptop": 1000,
    "Apple Watch": 10,
    "Apple MacBook Pro 15": 10,
    "Development Laptop (PC)": 40,
    "Loaner Laptop": 350,
}

placeholder_tasks = [task() for task in __TASKS__]
ITEM_TO_TASK = {task.fixed_request_item: task.__class__.__name__ for task in placeholder_tasks}

CONFIG_PATHS = [
    ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH,
    ORDER_IPAD_MINI_TASK_CONFIG_PATH,
    ORDER_IPAD_PRO_TASK_CONFIG_PATH,
    ORDER_SALES_LAPTOP_TASK_CONFIG_PATH,
    ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH,
    ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
    ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH,
    ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH,
]
TASK_TO_CONFIG_PATH = dict(zip(__TASKS__, CONFIG_PATHS))


def generate_configs_for_all_items():
    """Create task configs for all items; one file per task"""
    for item_choice, configs in META_CONFIGS.items():
        all_configs_for_a_single_item = generate_all_item_configs(item_choice, configs)
        num_configs_for_item = NUM_CONFIGS_PER_ITEM[item_choice]
        if len(all_configs_for_a_single_item) > num_configs_for_item:
            all_configs_for_a_single_item = random.sample(
                all_configs_for_a_single_item, num_configs_for_item
            )
        name = ITEM_TO_TASK[item_choice]
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        task_name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()
        with open(
            f"browsergym/workarena/src/browsergym/workarena/data_files/task_configs/{task_name}.json",
            "w",
        ) as f:
            json.dump(all_configs_for_a_single_item, f)


def generate_all_item_configs(item_choice, configs):
    """
    generates all possible configurations for a given item choice and its configuration options.
    """
    all_configs = []

    # Prepare the configuration options by maintaining their type and possible values
    config_options = {}
    for config_key, config_values in configs["options"].items():
        if config_values[0] in ["checkbox", "radio"]:
            # Store each option with its type and each possible value
            config_options[config_key] = [(config_values[0], value) for value in config_values[1]]
        elif config_values[0] == "textarea":
            text_options = config_values[1]
            if config_key == "Additional software requirements":
                config_options[config_key] = [
                    ("textarea", ", ".join(option))
                    for n in range(
                        1, len(text_options) + 1
                    )  # Changed to 1 to len to avoid empty selection
                    for option in combinations(text_options, n)
                ]
            else:
                config_options[config_key] = [("textarea", option) for option in text_options]

    # Iterate over all possible configurations
    for values in product(*config_options.values()):
        # Pair each configuration key with its corresponding (type, value) tuple
        config_dict = dict(zip(config_options.keys(), values))
        for quantity in range(1, 11):
            # Construct the full configuration dictionary for each combination
            task_config = {
                "item": item_choice,
                "description": configs["desc"],
                "quantity": quantity,  # Static quantity; can be adjusted if needed
                "configuration": config_dict,
            }
            all_configs.append(task_config)

    return all_configs


def count_all_item_occurrences(configs):
    counts = {}
    for config in configs:
        item_name = config["item"]
        if item_name in counts:
            counts[item_name] += 1
        else:
            counts[item_name] = 1
    return counts
