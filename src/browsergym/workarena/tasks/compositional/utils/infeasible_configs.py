import numpy as np

from faker import Faker

fake = Faker()


def get_infeasible_form_config(config, random: np.random, provide_reason: bool = True):
    """
    Get an infeasible form config from a feasible config by replacing the name of one of the task_fields with a random word

    Args:
    --------
    config (dict):
        The feasible form config to be transformed into an infeasible one
    random (np.random):
        The random number generator to use
    provide_reason (bool):
        Whether to provide a reason for the infeasibility. If False, the list of reasons will be [""] so that
        any infeasibility can be detected by the absence of a reason

    Returns:
    --------
    infeasible_config (dict):
        The infeasible form config
    infeasible_keywords (list[str]):
        The name of the new field printed and its system name
    """
    replaced_field = (
        random.choice(config["infeasible_task_fields"])
        if "infeasible_task_fields" in config
        else random.choice(config["task_fields"])
    )
    new_field_printed = fake.word().capitalize() + " " + fake.word()
    new_field_system_name = new_field_printed.lower().replace(" ", "_")

    config["task_fields"].remove(replaced_field)
    config["task_fields"].append(new_field_system_name)
    config["fields"][new_field_system_name] = new_field_printed
    config["template_record"][new_field_system_name] = fake.word()

    infeasible_reasons = [new_field_printed, new_field_system_name] if provide_reason else [""]

    return config, infeasible_reasons


def get_infeasible_service_catalog_config(config, random: np.random, provide_reason: bool = True):
    """
    Get an infeasible service catalog config from a feasible config by replacing the name of one of the additional configuration items with a random word

    Args:
    --------
    config (dict):
        The feasible service catalog config to be transformed into an infeasible one
    random (np.random):
        The random number generator to use
    provide_reason (bool):
        Whether to provide a reason for the infeasibility. If False, the list of reasons will be [""] so that
        any infeasibility can be detected by the absence of a reason

    Returns:
    --------
    infeasible_config (dict):
        The infeasible service catalog config
    infeasible_keywords (list[str]):
        The name of the new field printed and its system name
    """
    item_configuration = list(config["configuration"].keys())
    # if there is a configuration item, replace it with a new one; otherwise, simply add a new one
    if item_configuration:
        replaced_field = random.choice(item_configuration)
        config["configuration"].pop(replaced_field)
    new_field_printed = fake.word().capitalize() + " " + fake.word()
    field_type = random.choice(["radio", "textarea", "checkbox", "select"])
    field_options = [fake.word() for _ in range(random.randint(2, 5))]

    config["configuration"][new_field_printed] = [field_type, ", ".join(field_options)]

    infeasible_reasons = [new_field_printed, *field_options] if provide_reason else [""]

    return config, infeasible_reasons


def get_infeasible_sort_config(config, random: np.random, provide_reason: bool = True):
    """
    Get an infeasible sort config from a feasible config by replacing the name of one sort_fields with a random word

    Args:
    --------
    config (dict):
        The feasible sort config to be transformed into an infeasible one
    random (np.random):
        The random number generator to use
    provide_reason (bool):
        Whether to provide a reason for the infeasibility. If False, the list of reasons will be [""] so that
        any infeasibility can be detected by the absence of a reason

    Returns:
    --------
    infeasible_config (dict):
        The infeasible sort config
    infeasible_keywords (list[str]):
        The name of the new sort option printed and its system name
    """
    goal = config["goal"]
    config_fields = [line[3:].split(" (")[0] for line in goal.split("\n")[1:]]
    replaced_field_index = random.randint(0, len(config["sort_fields"]))

    new_field_printed = fake.word().capitalize() + " " + fake.word()
    new_field_system_name = new_field_printed.lower().replace(" ", "_")

    config["goal"] = goal.replace(config_fields[replaced_field_index], new_field_printed)
    config["sort_fields"][replaced_field_index] = new_field_system_name

    infeasible_reasons = [new_field_printed, new_field_system_name] if provide_reason else [""]

    return config, infeasible_reasons


def get_infeasible_filter_config(config, random: np.random, provide_reason: bool = True):
    """
    Get an infeasible filter config from a feasible config by replacing the name of one of the filter_columns with a random word

    Args:
    --------
    config (dict):
        The feasible filter config to be transformed into an infeasible one
    random (np.random):
        The random number generator to use
    provide_reason (bool):
        Whether to provide a reason for the infeasibility. If False, the list of reasons will be [""] so that
        any infeasibility can be detected by the absence of a reason

    Returns:
    --------
    infeasible_config (dict):
        The infeasible filter config
    infeasible_keywords (list[str]):
        The name of the new filter option printed and its system name
    """
    replaced_field_index = random.randint(0, len(config["filter_columns"]))

    new_field_printed = fake.word().capitalize() + " " + fake.word()
    new_field_system_name = new_field_printed.lower().replace(" ", "_")
    config["filter_columns"][replaced_field_index] = new_field_system_name
    config["filter_values"][replaced_field_index] = fake.word().capitalize()
    config["list_info"]["columns"][new_field_system_name] = {"label": new_field_printed}

    infeasible_reasons = [new_field_printed, new_field_system_name] if provide_reason else [""]

    return config, infeasible_reasons
