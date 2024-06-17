import random
from playwright.sync_api._generated import Page

from .dash_do_base import DashboardRetrieveIncidentAndDoTask, DashDoFinalTask

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask, SingleChartMeanMedianModeRetrievalTask

from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.list import (
    FilterAssetListTask,
    FilterHardwareListTask,
    FilterIncidentListTask,
    FilterUserListTask,
)


class DashboardRetrieveIncidentAndFilterListTask(DashboardRetrieveIncidentAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a list based on their assignments"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )
        self.prefix = "DIF"

    def get_filter_config(self, attribute_name, filter_than) -> dict:
        filter_values, agent_value_sysids = self.get_agent_values(
            attribute_name=attribute_name, filter_than=filter_than
        )
        self.agent_value_sysids = agent_value_sysids
        if len(filter_values) == 1:
            filter_kind = "AND"
        else:
            filter_kind = "OR"

        filter_config = {
            "filter_columns": [self.attribute_name] * len(filter_values),
            "filter_kind": filter_kind,
            "filter_values": filter_values,
        }
        return filter_config


class DashboardRetrieveIncidentAndFilterAssetListTask(DashboardRetrieveIncidentAndFilterListTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_assets_per_agent: int = 2,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )
        self.max_assets_per_agent = max_assets_per_agent
        self.attribute_name = "assigned_to"

    def set_compositional_task(self) -> None:
        filter_config = self.get_filter_config(
            attribute_name=self.attribute_name, filter_than=self.filter_than
        )

        filter_asset_list_subtask = [
            # Navigate to the asset list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Asset",
                    "module": "Portfolios > All Assets",
                    "url": "/now/nav/ui/classic/params/target/alm_asset_list.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            # Filter asset list
            FilterAssetListTask(
                is_validated=True,
                list_name="alm_asset",
                used_in_level_2=True,
                fixed_config=filter_config,
            ),
        ]

        self.compositional_task = filter_asset_list_subtask

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()

        # We create dummy assets for the consumable and license categories here
        ### NOTE: We can create assets without any of the following information, save time, and still assign them to the user. The task should be fine.
        consumable_category_sysid = table_api_call(
            instance=self.instance,
            table="cmdb_model_category",
            method="GET",
            params={"sysparm_query": "asset_class=alm_consumable", "sysparm_fields": "sys_id"},
        )["result"][0]["sys_id"]

        consumables = table_api_call(
            instance=self.instance,
            table="cmdb_model",
            method="GET",
            params={
                "sysparm_query": f"cmdb_model_category={consumable_category_sysid}",
                "sysparm_fields": "sys_id",
            },
        )["result"]
        consumables_sysids = [consumable["sys_id"] for consumable in consumables]

        license_category_sysid = table_api_call(
            instance=self.instance,
            table="cmdb_model_category",
            method="GET",
            params={"sysparm_query": "asset_class=alm_license", "sysparm_fields": "sys_id"},
        )["result"][0]["sys_id"]

        licenses = table_api_call(
            instance=self.instance,
            table="cmdb_model",
            method="GET",
            params={
                "sysparm_query": f"cmdb_model_category={license_category_sysid}",
                "sysparm_fields": "sys_id",
            },
        )["result"][:10]
        license_sysids = [license["sys_id"] for license in licenses]

        self.new_asset_sys_ids = []
        for agent_sysid in self.agent_sysids:
            num_assets = self.random.choice(range(1, self.max_assets_per_agent))
            for _ in range(num_assets):
                consumable_asset_data = {
                    "asset_tag": "CONSUMABLE" + str(random.randint(100, 999)),
                    "model": self.random.choice(consumables_sysids),
                    "model_category": consumable_category_sysid,
                    "assigned_to": agent_sysid,
                    "cost": 1000.00,
                    "purchase_date": "2024-05-08",
                    "substatus": "in_use",
                }
                response = table_api_call(
                    instance=self.instance,
                    table="alm_asset",
                    json=consumable_asset_data,
                    method="POST",
                )
                self.new_asset_sys_ids.append(response["result"]["sys_id"])
                license_asset_data = {
                    "asset_tag": "LICENSE" + str(random.randint(100, 999)),
                    "model": self.random.choice(license_sysids),
                    "model_category": license_category_sysid,
                    "assigned_to": agent_sysid,
                    "cost": 1000.00,
                    "purchase_date": "2024-05-08",
                    "substatus": "in_use",
                }
                response = table_api_call(
                    instance=self.instance,
                    table="alm_asset",
                    json=license_asset_data,
                    method="POST",
                )
                self.new_asset_sys_ids.append(response["result"]["sys_id"])

        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()

        if self.level == 3:
            filter_than = f"{self.filter_than} than or " if self.filter_than else ""
            self.task_description = (
                self.task_description
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of the number of incidents assigned across agents. Retrieve agents that have {filter_than}equal number of incidents assigned to them compared to this value.\n"
                + f"\t   For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have {filter_than}equal to 2 assigned incidents.\n\n"
                + f"\t - Task: Filter the Asset List using the {self.attribute_name} field corresponding to the agents that fit the criteria above. \n"
                + f"The list is present at Portfolios > All Assets. \n\n"
                + self.final_private_task_instructions
            )

        goal, info = super().setup_goal(
            page=page, config=config, build_pretty_print_description=False
        )

        if self.level == 2:
            if self.filter_than:
                step_3 = f"\n3. Find the agents with number of incidents {self.filter_than} than or equal to the {self.description_mapping[self.question]} value of the number of incidents assigned across agents. \n"
            else:
                step_3 = f"\n3. Find the agent with the {self.description_mapping[self.question]} assigned incidents. \n"
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page. \n"
                + f"\n2. Given the title of the report, search for it on this page. The report shows the number of 'incidents' assigned to an 'agent'.\n"
                + step_3
                + f"\n4. Navigate to Portfolios > All Assets. \n"
                + f"\nUsing the field {self.attribute_name} for the agent/ agents that fit the critera above, filter the list.\n"
            )

        return goal, info

    def teardown(self) -> None:
        # Delete all assets
        for new_asset_sysid in self.new_asset_sys_ids:
            db_delete_from_table(
                instance=self.instance,
                table="alm_asset",
                sys_id=new_asset_sysid,
            )
        return super().teardown()


class DashboardRetrieveIncidentAndFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterListTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_assets_per_agent: int = 2,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.max_assets_per_agent = max_assets_per_agent
        self.attribute_name = "assigned_to"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )

    def set_compositional_task(self) -> None:

        filter_config = self.get_filter_config(
            attribute_name=self.attribute_name, filter_than=self.filter_than
        )

        filter_hardware_asset_list_subtask = [
            # Navigate to the hardware asset list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Asset",
                    "module": "Portfolios > Hardware Assets",
                    "url": "/now/nav/ui/classic/params/target/alm_hardware_list.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            # Filter hardware list
            FilterHardwareListTask(
                is_validated=True,
                list_name="alm_hardware",
                used_in_level_2=True,
                fixed_config=filter_config,
            ),
        ]

        self.compositional_task = filter_hardware_asset_list_subtask

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()

        hardware_category_sysid = table_api_call(
            instance=self.instance,
            table="cmdb_model_category",
            method="GET",
            params={"sysparm_query": "asset_class=alm_hardware", "sysparm_fields": "sys_id"},
        )["result"][0]["sys_id"]

        hardwares = table_api_call(
            instance=self.instance,
            table="cmdb_model",
            method="GET",
            params={
                "sysparm_query": f"cmdb_model_category={hardware_category_sysid}",
                "sysparm_fields": "sys_id",
            },
        )["result"]
        hardware_sysids = [hardware["sys_id"] for hardware in hardwares]
        self.new_asset_sysids = []
        for agent_sysid in self.agent_sysids:
            num_assets = self.random.choice(range(1, self.max_assets_per_agent))
            for _ in range(num_assets):
                hardware_asset_data = {
                    "asset_tag": "CONSUMABLE" + str(random.randint(100, 999)),
                    "model": self.random.choice(hardware_sysids),
                    "model_category": hardware_category_sysid,
                    "assigned_to": agent_sysid,
                    "cost": 1000.00,
                    "purchase_date": "2024-05-08",
                    "substatus": "in_use",
                }
                response = table_api_call(
                    instance=self.instance,
                    table="alm_hardware",
                    json=hardware_asset_data,
                    method="POST",
                )
                self.new_asset_sysids.append(response["result"]["sys_id"])

        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()

        if self.level == 3:
            filter_than = f"{self.filter_than} than or " if self.filter_than else ""
            self.task_description = (
                self.task_description
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of the number of incidents assigned across agents. Retrieve agents that have {filter_than}equal number of incidents assigned to them compared to this value.\n"
                + f"\t   For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have {filter_than}equal to 2 assigned incidents.\n\n"
                + f"\t - Task: Filter the Hardware List using the {self.attribute_name} field corresponding to the agents that fit the criteria above. \n"
                + f"The list is present at Portfolios > Hardware Assets. \n\n"
                + self.final_private_task_instructions
            )

        goal, info = super().setup_goal(
            page=page, config=config, build_pretty_print_description=False
        )

        if self.level == 2:
            if self.filter_than:
                step_3 = f"\n3. Find the agents with number of incidents {self.filter_than} than or equal to the {self.description_mapping[self.question]} value of the number of incidents assigned across agents. \n"
            else:
                step_3 = f"\n3. Find the agent with the {self.description_mapping[self.question]} assigned incidents. \n"
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page. \n"
                + f"\n2. Given the title of the report, search for it on this page. The report shows the number of 'incidents' assigned to an 'agent'.\n"
                + step_3
                + f"\n4. Navigate to Portfolios > Hardware Assets. \n"
                + f"\nUsing the field {self.attribute_name} for the agent/ agents that fit the critera above, filter the list.\n"
            )

        return goal, info

    def teardown(self) -> None:
        # Delete all assets
        for new_asset_sysid in self.new_asset_sysids:
            db_delete_from_table(
                instance=self.instance,
                table="alm_hardware",
                sys_id=new_asset_sysid,
            )
        return super().teardown()


class DashboardRetrieveIncidentAndFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterListTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.attribute_name = "assigned_to"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )

    def set_compositional_task(self) -> None:

        filter_config = self.get_filter_config(
            attribute_name=self.attribute_name, filter_than=self.filter_than
        )

        filter_incident_list_subtask = [
            # Navigate to the incident list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Service Desk",
                    "module": "Incidents",
                    "url": "/now/nav/ui/classic/params/target/incident_list.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            # Filter incident list
            FilterIncidentListTask(
                is_validated=True,
                list_name="incident",
                used_in_level_2=True,
                fixed_config=filter_config,
            ),
        ]

        self.compositional_task = filter_incident_list_subtask

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()
        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()

        if self.level == 3:
            filter_than = f"{self.filter_than} than or " if self.filter_than else ""
            self.task_description = (
                self.task_description
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of the number of incidents assigned across agents. Retrieve agents that have {filter_than}equal number of incidents assigned to them compared to this value.\n"
                + f"\t   For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have {filter_than}equal to 2 assigned incidents.\n\n"
                + f"\t - Task: Filter the Incident List using the {self.attribute_name} field corresponding to the agents that fit the criteria above. \n"
                + f"The list is present at Service Desk > Incidents. \n\n"
                + self.final_private_task_instructions
            )

        goal, info = super().setup_goal(
            page=page, config=config, build_pretty_print_description=False
        )

        if self.level == 2:
            if self.filter_than:
                step_3 = f"\n3. Find the agents with number of incidents {self.filter_than} than or equal to the {self.description_mapping[self.question]} value of the number of incidents assigned across agents. \n"
            else:
                step_3 = f"\n3. Find the agent with the {self.description_mapping[self.question]} assigned incidents. \n"
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page. \n"
                + f"\n2. Given the title of the report, search for it on this page. The report shows the number of 'incidents' assigned to an 'agent'.\n"
                + step_3
                + f"\n4. Navigate to Service Desk > Incidents. \n"
                + f"\nUsing the field {self.attribute_name} for the agent/ agents that fit the critera above, filter the list.\n"
            )

        return goal, info


class DashboardRetrieveIncidentAndFilterUserListTask(DashboardRetrieveIncidentAndFilterListTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.attribute_name = "first_name"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )

    def set_compositional_task(self) -> None:
        filter_config = self.get_filter_config(
            attribute_name=self.attribute_name, filter_than=self.filter_than
        )

        filter_user_list_subtask = [
            # Navigate to the user list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Organization",
                    "module": "Users",
                    "url": "/now/nav/ui/classic/params/target/sys_user_list.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            # Filter user list
            FilterUserListTask(
                is_validated=True,
                list_name="user",
                used_in_level_2=True,
                fixed_config=filter_config,
            ),
        ]

        self.compositional_task = filter_user_list_subtask

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()
        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()

        if self.level == 3:
            filter_than = f"{self.filter_than} than or " if self.filter_than else ""
            self.task_description = (
                self.task_description
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of the number of incidents assigned across agents. Retrieve agents that have {filter_than}equal number of incidents assigned to them compared to this value.\n"
                + f"\t   For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have {filter_than}equal to 2 assigned incidents.\n\n"
                + f"\t - Task: Filter the User List using the {self.attribute_name} field corresponding to the agents that fit the criteria above. \n"
                + f"The list is present at Organization > Users. \n\n"
                + self.final_private_task_instructions
            )

        goal, info = super().setup_goal(
            page=page, config=config, build_pretty_print_description=False
        )

        if self.level == 2:
            if self.filter_than:
                step_3 = f"3. Find the agents with number of incidents {self.filter_than} than or equal to the {self.description_mapping[self.question]} value of the number of incidents assigned across agents. \n"
            else:
                step_3 = f"3. Find the agent with the {self.description_mapping[self.question]} assigned incidents. \n"
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page. \n"
                + f"\n2. Given the title of the report, search for it on this page. The report shows the number of 'incidents' assigned to an 'agent'.\n"
                + step_3
                + f"\n4. Navigate to Organization > Users. \n"
                + f"\nUsing the field {self.attribute_name} for the agent/ agents that fit the critera above, filter the list.\n"
            )

        return goal, info


class DashboardRetrieveIncidentAndMaxFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMinFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="min",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanGreaterFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianGreaterFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeGreaterFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanLesserFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianLesserFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeLesserFilterAssetListTask(
    DashboardRetrieveIncidentAndFilterAssetListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an asset list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list based on incidents assigned to an employee"
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMinFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="min",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanGreaterFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianGreaterFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeGreaterFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanLesserFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianLesserFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeLesserFilterHardwareListTask(
    DashboardRetrieveIncidentAndFilterHardwareListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a hardware list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a hardware list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMinFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="min",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanGreaterFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianGreaterFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeGreaterFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanLesserFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianLesserFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeLesserFilterIncidentListTask(
    DashboardRetrieveIncidentAndFilterIncidentListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter an incident list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter an incident list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMinFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = None
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="min",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanGreaterFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianGreaterFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeGreaterFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = "greater"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanLesserFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianLesserFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeLesserFilterUserListTask(
    DashboardRetrieveIncidentAndFilterUserListTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best or worst performing agent and filter a user list based on their assignments.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Retrieve the best or worst performing agent and filter a user list based on their assignments."
        """
        self.filter_than = "lesser"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]

DASH_COMPUTE_MAX_FILTER_LIST = [
    DashboardRetrieveIncidentAndMaxFilterAssetListTask,
    DashboardRetrieveIncidentAndMaxFilterHardwareListTask,
    DashboardRetrieveIncidentAndMaxFilterIncidentListTask,
    DashboardRetrieveIncidentAndMaxFilterUserListTask,
]
DASH_COMPUTE_MIN_FILTER_LIST = [
    DashboardRetrieveIncidentAndMinFilterAssetListTask,
    DashboardRetrieveIncidentAndMinFilterHardwareListTask,
    DashboardRetrieveIncidentAndMinFilterIncidentListTask,
    DashboardRetrieveIncidentAndMinFilterUserListTask,
]
DASH_COMPUTE_MEAN_FILTER_LIST = [
    DashboardRetrieveIncidentAndMeanGreaterFilterAssetListTask,
    DashboardRetrieveIncidentAndMeanGreaterFilterHardwareListTask,
    DashboardRetrieveIncidentAndMeanGreaterFilterIncidentListTask,
    DashboardRetrieveIncidentAndMeanGreaterFilterUserListTask,
    DashboardRetrieveIncidentAndMeanLesserFilterAssetListTask,
    DashboardRetrieveIncidentAndMeanLesserFilterHardwareListTask,
    DashboardRetrieveIncidentAndMeanLesserFilterIncidentListTask,
    DashboardRetrieveIncidentAndMeanLesserFilterUserListTask,
]

DASH_COMPUTE_MEDIAN_FILTER_LIST = [
    DashboardRetrieveIncidentAndMedianGreaterFilterAssetListTask,
    DashboardRetrieveIncidentAndMedianLesserFilterAssetListTask,
    DashboardRetrieveIncidentAndMedianGreaterFilterHardwareListTask,
    DashboardRetrieveIncidentAndMedianLesserFilterHardwareListTask,
    DashboardRetrieveIncidentAndMedianGreaterFilterIncidentListTask,
    DashboardRetrieveIncidentAndMedianLesserFilterIncidentListTask,
    DashboardRetrieveIncidentAndMedianGreaterFilterUserListTask,
    DashboardRetrieveIncidentAndMedianLesserFilterUserListTask,
]

DASH_COMPUTE_MODE_FILTER_LIST = [
    DashboardRetrieveIncidentAndModeGreaterFilterAssetListTask,
    DashboardRetrieveIncidentAndModeLesserFilterAssetListTask,
    DashboardRetrieveIncidentAndModeGreaterFilterHardwareListTask,
    DashboardRetrieveIncidentAndModeLesserFilterHardwareListTask,
    DashboardRetrieveIncidentAndModeGreaterFilterIncidentListTask,
    DashboardRetrieveIncidentAndModeLesserFilterIncidentListTask,
    DashboardRetrieveIncidentAndModeGreaterFilterUserListTask,
    DashboardRetrieveIncidentAndModeLesserFilterUserListTask,
]
