import numpy as np
import pytest
import random

from time import sleep

from browsergym.workarena.instance import SNowInstance
from browsergym.workarena.api.utils import table_api_call
from browsergym.workarena.api.user import create_user, set_user_preference


@pytest.mark.parametrize("system", [True, False])
def test_set_user_preference(system):
    admin_instance = SNowInstance()

    # Create a user to get a sys_id
    if not system:
        uname, pwd, sysid = create_user(SNowInstance())
        user_instance = SNowInstance(snow_credentials=(uname, pwd))
        user = sysid
    else:
        user_instance = admin_instance

    # Do it twice to test updating existing preference
    pref_key = f"workarena.unittest.{random.randint(1, 100000000)}"
    for _ in range(2):
        pref = set_user_preference(
            user_instance, key=pref_key, value="1234", user=None if system else user
        )
        assert pref["name"] == pref_key
        assert pref["value"] == "1234"
        assert pref["user"] == "" if system else user
        assert str(pref["system"]).lower() == str(system).lower()
        assert pref["description"] == "Updated by WorkArena"

    # Delete the preference
    table_api_call(admin_instance, table=f"sys_user_preference/{pref['sys_id']}", method="DELETE")

    # Delete the user
    if not system:
        table_api_call(admin_instance, table=f"sys_user/{user}", method="DELETE")
