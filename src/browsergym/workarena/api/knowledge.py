from ..instance import SNowInstance
from .utils import table_api_call


def give_kb_read_permissions(admin_instance, user_sys_id, user_name, kb_sys_id, kb_name):
    # Need admin permissions to give KB permissions to the user

    # Create user criteria
    user_criteria_data = {
        "user": user_sys_id,
        "name": f"{user_name} read KB",
        "short_description": f"Let {user_name} read {kb_name}",
    }
    criteria_response = table_api_call(
        instance=admin_instance, table="user_criteria", json=user_criteria_data, method="POST"
    )["result"]
    criteria_sys_id = criteria_response["sys_id"]

    # Add user criteria entry to allow users to access the ADHOC KB
    kb_uc_can_read_mtom_data = {
        "user_criteria": criteria_sys_id,
        "kb_knowledge_base": kb_sys_id,
    }
    _ = table_api_call(
        instance=admin_instance,
        table="kb_uc_can_read_mtom",
        json=kb_uc_can_read_mtom_data,
        method="POST",
    )["result"]
