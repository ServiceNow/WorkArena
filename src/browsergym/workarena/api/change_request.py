import faker
import numpy as np

fake = faker.Faker()

from datetime import datetime, timedelta

from .category import get_categories
from .utils import table_api_call

from ..instance import SNowInstance


def create_change_request(
    instance: SNowInstance,
    user_sys_id: str,
    impact: int,
    risk: int,
    start_date: datetime = "",
    end_date: datetime = "",
    hashtag: str = "",
    short_description: str = None,
    random: np.random = None,
) -> list[str]:
    """
    Create a change request

    Parameters:
    -----------
    instance: SNowInstance
        The instance to create the change request in
    user_sys_id: str
        The sys_id of the user to assign the problem to
    impact: str
        The impact of the change request; ranges from 1 (high) to 3 (low)
    risk: str
        The risk of the change request; ranges from 2 (high) to 4 (low)
    start_date: datetime.datetime
        The start date of the change request; empty if not set
    end_date: datetime.datetime
        The end date of the change request; empty if not set
    hashtag: str
        The name of the hashtag for the change request. If "", no hashtag will be added
    short_description: str
        The short description of the change request. If None, a random sentence will be generated
    random: np.random
        The random number generator

    Returns:
    --------
    sys_id of the change request
    number of the change request

    """
    if short_description is None:
        short_description = fake.sentence(4)
    categories = get_categories(instance=instance, list_name="change_request")
    category = random.choice(categories)

    cfg = {
        "reason": "broken",
        "upon_reject": "cancel",
        "type": "emergency",
        "state": "-5",
        "phase": "requested",
        "impact": str(impact),
        "active": "true",
        "short_description": short_description + " " + hashtag,
        "assigned_to": user_sys_id,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "upon_approval": "proceed",
        "justification": fake.sentence(),
        "implementation_plan": fake.sentence(),
        "phase_state": "open",
        "risk": str(risk),
        "cab_required": "false",
        "category": category,
    }
    result = table_api_call(
        instance=instance,
        table="change_request",
        method="POST",
        json=cfg,
    )["result"]

    return result["sys_id"], result["number"]
