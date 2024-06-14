import faker

fake = faker.Faker()

from ..instance import SNowInstance
from .utils import table_api_call


def create_problem(
    instance: SNowInstance,
    priority: str,
    user_sys_id: str,
    problem_hashtag: str,
    short_description: str = None,
    return_number: bool = False,
) -> list[str]:
    """
    Create a problem with a random cause, description, and short description. The problem is assigned to a user and
    is created with a hashtag.

    Parameters:
    -----------
    instance: SNowInstance
        The instance to create the problem in
    priority: str
        The priority of the problem
    user_sys_id: str
        The sys_id of the user to assign the problem to
    problem_hashtag: str
        The name of the hashtag for the problem
    short_description: str
        The short description of the problem (optional). if not provided, a random one will be generated
    return_number: bool
        whether or not to return the problem number that was created

    Returns:
    --------
    sys_id of the problem
    problem_number (optional)

    """
    cause = fake.sentence()
    description = fake.text()
    if short_description is None:
        short_description = fake.sentence(4)

    # Priority is a read-only field defined by a combo of impact and urgency. The mapping is as follows:
    # https://docs.servicenow.com/bundle/washingtondc-it-service-management/page/product/problem-management/concept/prioritise-problems.html
    priority_to_impact_and_urgency = {
        1: (1, 1),
        2: (1, 2),
        3: (1, 3),
        4: (2, 3),
        5: (3, 3),
    }

    impact, urgency = priority_to_impact_and_urgency[priority]

    problem_cfg = {
        "made_sla": True,
        "upon_reject": "cancel",
        "cause_notes": f" <p>{cause}</p> ",
        "fix_notes": " placeholder ",  # placeholder value - will not work without a fix note
        "knowledge": False,
        "major_problem": False,
        "impact": f"{impact}",
        "active": False,
        "sys_domain_path": "/",
        "short_description": f"{short_description} {problem_hashtag}",
        "known_error": False,
        "description": f"{description}",
        "sla_due": "2021-04-11 17:39:07",
        "closed_at": "",
        "resolution_code": "fix_applied",
        "urgency": f"{urgency}",
        "assigned_to": f"{user_sys_id}",
        "active": True,
    }

    result = table_api_call(
        instance=instance,
        table="problem",
        json=problem_cfg,
        method="POST",
    )["result"]

    if return_number:
        return result["sys_id"], result["number"]

    return result["sys_id"]
