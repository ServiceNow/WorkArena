from faker import Faker
from ..instance import SNowInstance

fake = Faker()

from .utils import table_api_call


def create_incident(
    instance: SNowInstance,
    incident_number: int,
    caller_sys_id: str,
    category: str,
    impact: int,
    urgency: int,
    priority: int,
    incident_hastag: str = None,
    assigned_to: str = None,
):
    incident_config = {
        "task_effective_number": incident_number,
        "number": incident_number,
        "state": 2,
        "knowledge": False,
        "impact": impact,
        "active": True,
        "priority": priority,
        "caller_id": caller_sys_id,
        "short_description": incident_hastag if incident_hastag else " ".join(fake.words(5)),
        "description": " ".join(fake.words(10)),
        "incident_state": 2,
        "urgency": urgency,
        "severity": 3,
        "category": category,
    }
    if assigned_to:
        incident_config["assigned_to"] = assigned_to

    incident_response = table_api_call(
        instance=instance,
        table="incident",
        json=incident_config,
        method="POST",
    )["result"]
    return incident_response
