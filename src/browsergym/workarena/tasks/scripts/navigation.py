import json

from browsergym.workarena.api.utils import table_api_call, SNowInstance

NUM_CONFIGS = 650  # number of impersonation tasks in the paper


def get_all_impersonation_users():
    instance = SNowInstance()
    candidate_users = [
        u["first_name"] + " " + u["last_name"]
        for u in table_api_call(
            instance=instance,
            table="sys_user",
            params={"sysparm_query": "user_name!=admin"},
        )["result"]
        if u["first_name"].strip() and u["last_name"].strip()
    ]

    return candidate_users[:NUM_CONFIGS]


if __name__ == "__main__":
    all_users = get_all_impersonation_users()
    with open(
        "browsergym/workarena/src/browsergym/workarena/data_files/task_configs/impersonation_users.json",
        "w",
    ) as f:
        json.dump(all_users, f)
