from copy import deepcopy
import json
import numpy as np
import pytest

from browsergym.workarena.tasks.compositional.utils.knapsack import KnapsackInstanceGenarator
from browsergym.workarena.tasks.compositional.utils.infeasible_configs import (
    get_infeasible_form_config,
    get_infeasible_service_catalog_config,
    get_infeasible_filter_config,
    get_infeasible_sort_config,
)
from browsergym.workarena.config import (
    CREATE_USER_CONFIG_PATH,
    ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    FILTER_USER_LIST_CONFIG_PATH,
    SORT_USER_LIST_CONFIG_PATH,
)


@pytest.mark.parametrize(
    "mode", ["random", "trivial", "single_item", "single_item_uniform", "n_items"]
)
def test_knapsack(mode: str, num_items_in_solution: int = 2):
    num_items_in_solution = 2 if mode == "n_items" else 1
    knapsack = KnapsackInstanceGenarator(
        random=np.random,
        num_items=3,
        max_capacity=150000,
        mode=mode,
        num_items_in_solution=num_items_in_solution,
    )
    investments, max_return, selected_indices = knapsack.get_instance()

    # In these modes, all items are identical, so the optimal solution can be any
    if mode in ["n_items", "single_item_uniform"]:
        selected_indices = [i for i in range(num_items_in_solution)]

    assert len(investments) == 3
    assert sum(investments[i][0] for i in selected_indices) <= 150000
    assert max_return == sum(investments[i][1] for i in selected_indices)

    if mode != "trivial":
        unselected_index = [i for i in range(3) if i not in selected_indices][0]
        assert (
            sum(investments[i][0] for i in selected_indices) + investments[unselected_index][0]
            > 150000
        )
    else:
        assert len(selected_indices) == len(investments)


config_generator_and_config_path = [
    [get_infeasible_form_config, CREATE_USER_CONFIG_PATH],
    [get_infeasible_service_catalog_config, ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH],
    [get_infeasible_filter_config, FILTER_USER_LIST_CONFIG_PATH],
    [get_infeasible_sort_config, SORT_USER_LIST_CONFIG_PATH],
]


@pytest.mark.parametrize("function_to_path", config_generator_and_config_path)
def test_invalid_config_generator(function_to_path):
    def parse_nested_dict(nested_dict, keywords):
        """Look for keywords in a nested dictionary.
        Return True if any keyword is found, False otherwise.
        """
        for key, value in nested_dict.items():
            if key in keywords or value in keywords:
                return True
            if isinstance(value, dict):
                if parse_nested_dict(value, keywords):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if parse_nested_dict(item, keywords):
                            return True
            elif isinstance(value, str):
                for keyword in keywords:
                    if keyword in value:
                        return True
        return False

    config_generator, config_path = function_to_path
    with open(config_path, "r") as f:
        config = json.load(f)[0]
    base_config = deepcopy(config)

    invalid_config, infeasible_reasons = config_generator(random=np.random, config=config)
    assert invalid_config != base_config
    assert parse_nested_dict(invalid_config, infeasible_reasons)
    assert parse_nested_dict(base_config, infeasible_reasons) == False
