import json
import numpy as np
import time

from faker import Faker

fake = Faker()

from ..instance import SNowInstance
from .utils import table_api_call


def create_computer_asset(
    instance: SNowInstance,
    asset_tag: str,
    warranty_expiration_date: str = None,
    user_sys_id: str = None,
    computer_model_info: dict = None,
    random: np.random = None,
):
    """Create a hardware asset -computer model- and assign it to a user
    Args:
    --------
    instance (SNowInstance):
        The instance to create the hardware asset in
    asset_tag (str):
        The asset tag of the hardware asset
    warranty_expiration_date (str):
        The warranty expiration date of the hardware asset. If None, a random date is chosen
    user_sys_id (str):
        The sys_id of the user to assign the hardware asset to. If None, the hardware asset is not assigned to any user
    computer_model_info (dict):
        Contains the sys_id and short_description of the computer model to create the hardware asset with.
        If None, a random computer model is chosen
    random (np.random):
        The random number generator
    Returns:
    --------
    sys_id (str):
        The sys_id of the created hardware asset
    computer_model (dict):
        The computer model information
    warranty_expiration_date (str):
        The warranty expiration date of the hardware asset
    """

    if computer_model_info is None:
        # Get the sys_id of the 'Computer' category
        computer_model_sys_id = table_api_call(
            instance=instance,
            table="cmdb_model_category",
            # The cmdb_model_category is the sys_id for the hardware category; computer in this case
            params={
                "sysparm_query": f"name=Computer",
                "sysparm_fields": "sys_id",
            },
        )["result"][0]["sys_id"]
        # Randomly choose a computer model if needed
        computer_models = table_api_call(
            instance=instance,
            table="cmdb_model",
            # The cmdb_model_category is the sys_id for the hardware category;
            params={
                "sysparm_query": f"cmdb_model_category={computer_model_sys_id}",
                "sysparm_fields": "sys_id,short_description",
            },
        )["result"]
        computer_model = random.choice(computer_models)
    if warranty_expiration_date is None:
        # Warranty expiration date is randomly selected between 1 year ago and 1 year from now
        warranty_expiration_date = str(fake.date_between(start_date="-1y", end_date="+1y"))

    # Create hardware asset
    hardware_result = table_api_call(
        instance=instance,
        table="alm_hardware",
        data=json.dumps(
            {
                "assigned_to": user_sys_id,
                "asset_tag": asset_tag,
                "display_name": asset_tag + " - " + computer_model["short_description"],
                "model": computer_model["sys_id"],
                "model_category": computer_model_sys_id,
                "warranty_expiration": warranty_expiration_date,
            }
        ),
        method="POST",
    )["result"]

    return hardware_result["sys_id"], computer_model, warranty_expiration_date
