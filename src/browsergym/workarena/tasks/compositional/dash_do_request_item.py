import random
from playwright.sync_api._generated import Page
from typing import Tuple

from .dash_do_base import DashboardRetrieveIncidentAndDoTask, DashDoFinalTask

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask, SingleChartMeanMedianModeRetrievalTask

from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.form import CreateItemRequestTask


class DashboardRetrieveIncidentAndRequestItemTask(DashboardRetrieveIncidentAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        item: str = None,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Retrieve the best performing agent and request an item for them.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. ""Order an item for the best performing employee from the list"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )
        if not item:
            raise Exception("No item passed to assign")
        self.item = item
        self.attribute_name = "assigned_to"  # Return full name
        self.filter_than = "greater"
        self.prefix = "DRI"

    def set_compositional_task(self) -> None:
        # The unique name for the user is created once the task is instantiated
        requested_items = table_api_call(
            instance=self.instance,
            table="sc_req_item",
            method="GET",
        )["result"]
        current_requested_items_numbers = [
            requested_item["number"] for requested_item in requested_items
        ]

        agent_full_names, agent_value_sysids = self.get_agent_values(
            self.attribute_name, self.filter_than
        )
        self.agent_value_sysids = agent_value_sysids

        requested_item_numbers = []

        for _ in range(len(agent_full_names)):
            requested_item_number = "RITM" + str(random.randint(1000000, 9999999))
            while (
                requested_item_number in current_requested_items_numbers
                or requested_item_number in requested_item_numbers
            ):
                requested_item_number = "RITM" + str(random.randint(1000000, 9999999))
            requested_item_numbers.append(requested_item_number)

        self.requested_item_numbers = requested_item_numbers

        create_item_request_subtasks = []

        for agent_full_name, requested_item_number in zip(agent_full_names, requested_item_numbers):
            request_item_config = {
                "fields": {
                    "number": "Number",
                    "cat_item": "Item",
                    "requested_for": "Requested for",
                    "quantity": "Quantity",
                },
                "task_fields": ["number", "cat_item", "requested_for", "quantity"],
                "template_record": {
                    "number": requested_item_number,
                    "cat_item": self.item,
                    "requested_for": agent_full_name,
                    "quantity": "1",
                },
            }

            create_item_request_subtask = [
                # Navigate to the item request list
                AllMenuTask(
                    instance=self.instance,
                    fixed_config={
                        "application": "Open Records",
                        "module": "Open Records > Items",
                        "url": "/now/nav/ui/classic/params/target/sc_req_item_list.do",
                    },
                    is_validated=False,
                    used_in_level_2=True,
                ),
                # Create an item request
                CreateItemRequestTask(
                    instance=self.instance,
                    fixed_config=request_item_config,
                    is_validated=False,
                    used_in_level_2=True,
                    check_record_created=False,
                ),
            ]
            create_item_request_subtasks += create_item_request_subtask

        self.compositional_task = create_item_request_subtasks

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()
        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()
        requested_item_numbers_string = ", ".join(self.requested_item_numbers)

        if self.level == 3:
            self.task_description = (
                self.task_description
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of the number of incidents assigned across agents. Retrieve agents that have greater than or equal number of incidents assigned to them compared to this value.\n"
                + f"\t   For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have greater than or equal to 2 assigned incidents.\n\n"
                + f"\t - Task: For each agent that fits the above criteria, create an 'item request' with the following information (only fill these fields and the 'request item number' from below) and 'request it' for them using the 'Requested for' field: \n"
                + f"\t\t Item: {self.item}, Quantity: 1, Requested for: <agent name>.\n"
                + f"\t   Importantly, you should override the default request item numbers in the form and instead use one request item number from the following list for each item request you create: {requested_item_numbers_string}.\n\n"
                + f"Note that you will create as many item requests as there are agents matching the above criteria.\n"
                + f"\t   For example, consider the above case and say you have 3 agents with greater than or equal to 2 incidents assigned to them in the chart. You will be creating '3' item requests here, one for each agent. \n\n"
            )

        goal, info = super().setup_goal(page=page, config=config)

        if self.level == 2:
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page. \n"
                + f"\n2. Given the title of the report, search for it on this page. The report shows the number of 'incidents' assigned to an 'agent'.\n"
                + f"\n3. Find the agents with a number of incidents assigned greater than or equal to the {self.description_mapping[self.question]} of the number of assigned incidents across agents. For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have greater than or equal to 2 assigned incidents.\n"
                + f"\n4. Navigate to Open Records > Items. \n"
                + f"\n5. You have to create new 'item requests' from this page for all the agents based on the above criteria. Only fill the following fields when creating a new item request:- Item: {self.item}, Quantity: 1 and 'request' them for each agent using the 'Requested For' field.\n\n"
                + f"Importantly, you should override the default request item numbers in the form and instead use one request item number from the following list for each item request you create: {requested_item_numbers_string}.\n"
                + f"Note that you will create as many item requests as there are agents matching the above criteria.\n"
                + "For example, consider the above case and say you have 3 agents with greater than or equal to 2 incidents assigned to them in the chart. You will be creating '3' item requests here, one for each agent. \n"
            )

        return goal, info

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        for requested_item_number in self.requested_item_numbers:
            created_request_item_response = table_api_call(
                instance=self.instance,
                table="sc_req_item",
                params={
                    "sysparm_query": f"number={requested_item_number}",
                    "sysparm_fields": "requested_for,cat_item,quantity",
                },
                method="GET",
            )["result"]
            if len(created_request_item_response) == 0:
                return (
                    0,
                    False,
                    "",
                    {"message": f"No request item created with number {requested_item_number}."},
                )
            elif len(created_request_item_response) > 1:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"Multiple request items created with number {requested_item_number}."
                    },
                )
            created_request_item_response = created_request_item_response[0]
            if (
                created_request_item_response["requested_for"]["value"]
                not in self.agent_value_sysids
            ):
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"Request item {requested_item_number} created for a random agent."
                    },
                )
            if str(created_request_item_response["quantity"]) != "1":
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"Request item {requested_item_number} requested incorrect number of items."
                    },
                )
            cat_item = created_request_item_response["cat_item"]
            if not cat_item:
                return (
                    0,
                    False,
                    "",
                    {"message": f"Request item {requested_item_number} did not request an item."},
                )
            cat_item_response = table_api_call(
                instance=self.instance,
                table="sc_cat_item",
                params={
                    "sysparm_query": f"sys_id={cat_item['value']}",
                    "sysparm_fields": "sys_name",
                },
                method="GET",
            )["result"]
            if len(cat_item_response) == 0:
                return (
                    0,
                    False,
                    "",
                    {"message": f"Request item {requested_item_number} did not request an item."},
                )

            if cat_item_response[0]["sys_name"] != self.item:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"Request item {requested_item_number} requested an incorrect item."
                    },
                )

        for agent_sysid in self.agent_value_sysids:
            created_request_item_response = table_api_call(
                instance=self.instance,
                table="sc_req_item",
                params={
                    "sysparm_query": f"requested_for={agent_sysid}",
                    "sysparm_fields": "requested_for",
                },
                method="GET",
            )["result"]
            if len(created_request_item_response) == 0:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"No request created for agent {self.agents[agent_sysid]['user_name']}."
                    },
                )
            elif len(created_request_item_response) > 1:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"Multiple requests created for agent {self.agents[agent_sysid]['user_name']}."
                    },
                )
        reward, done, message, info = super().validate(page, chat_messages)
        return reward, done, message, info

    def teardown(self) -> None:
        for requested_item_number in self.requested_item_numbers:
            created_item_request_response = table_api_call(
                instance=self.instance,
                table="sc_req_item",
                params={
                    "sysparm_query": f"number={requested_item_number}",
                },
                method="GET",
            )["result"]
            if len(created_item_request_response) > 1:
                raise Exception("Multiple request items created")
            if len(created_item_request_response) == 1:
                created_item_request_sysid = created_item_request_response[0]["sys_id"]
                db_delete_from_table(
                    instance=self.instance,
                    table="sc_req_item",
                    sys_id=created_item_request_sysid,
                )
        return super().teardown()


class DashboardRetrieveIncidentAndMaxRequestAppleWatchTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an apple watch for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestAppleWatchTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an apple watch for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestAppleWatchTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an apple watch for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestAppleWatchTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an apple watch for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleWatch2Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple Watch Series 2 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch Series 2",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestAppleWatch2Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple Watch Series 2 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch Series 2",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestAppleWatch2Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple Watch Series 2 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch Series 2",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestAppleWatch2Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple Watch Series 2 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple Watch Series 2",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIpad3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPad 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPad 3",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestAppleIpad3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPad 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPad 3",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestAppleIpad3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPad 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPad 3",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestAppleIpad3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPad 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPad 3",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIphone13proTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 pro for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13 pro",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestAppleIphone13proTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 pro for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13 pro",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestAppleIphone13proTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 pro for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13 pro",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestAppleIphone13proTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 pro for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13 pro",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIphone13Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestAppleIphone13Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestAppleIphone13Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestAppleIphone13Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Apple iPhone 13 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Apple iPhone 13",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestGalaxyNote20Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Galaxy Note 20 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Galaxy Note 20",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestGalaxyNote20Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Galaxy Note 20 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Galaxy Note 20",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestGalaxyNote20Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Galaxy Note 20 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Galaxy Note 20",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestGalaxyNote20Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Galaxy Note 20 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Galaxy Note 20",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestGoogleNexus7Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Google Nexus 7 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Google Nexus 7",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestGoogleNexus7Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Google Nexus 7 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Google Nexus 7",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestGoogleNexus7Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Google Nexus 7 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Google Nexus 7",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestGoogleNexus7Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Google Nexus 7 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Google Nexus 7",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestMicrosoftSurfacePro3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Microsoft Surface Pro 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Microsoft Surface Pro 3",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestMicrosoftSurfacePro3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Microsoft Surface Pro 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Microsoft Surface Pro 3",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestMicrosoftSurfacePro3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Microsoft Surface Pro 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Microsoft Surface Pro 3",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestMicrosoftSurfacePro3Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Microsoft Surface Pro 3 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Microsoft Surface Pro 3",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestPixel4aTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Pixel 4a for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Pixel 4a",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestPixel4aTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Pixel 4a for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Pixel 4a",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestPixel4aTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Pixel 4a for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Pixel 4a",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestPixel4aTask(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request an Pixel 4a for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Pixel 4a",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMaxRequestWindowsSurfacePro4Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Windows Surface Pro 4 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Windows Surface Pro 4",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanRequestWindowsSurfacePro4Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Windows Surface Pro 4 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Windows Surface Pro 4",
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianRequestWindowsSurfacePro4Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Windows Surface Pro 4 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Windows Surface Pro 4",
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeRequestWindowsSurfacePro4Task(
    DashboardRetrieveIncidentAndRequestItemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the best performing agent and request a Windows Surface Pro 4 for them.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            item="Windows Surface Pro 4",
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]


DASH_AND_REQUEST = [
    DashboardRetrieveIncidentAndMaxRequestAppleWatchTask,
    DashboardRetrieveIncidentAndMaxRequestAppleWatch2Task,
    DashboardRetrieveIncidentAndMaxRequestAppleIpad3Task,
    DashboardRetrieveIncidentAndMaxRequestAppleIphone13proTask,
    DashboardRetrieveIncidentAndMaxRequestAppleIphone13Task,
    DashboardRetrieveIncidentAndMaxRequestGalaxyNote20Task,
    DashboardRetrieveIncidentAndMaxRequestGoogleNexus7Task,
    DashboardRetrieveIncidentAndMaxRequestMicrosoftSurfacePro3Task,
    DashboardRetrieveIncidentAndMaxRequestPixel4aTask,
    DashboardRetrieveIncidentAndMaxRequestWindowsSurfacePro4Task,
]
DASH_COMPUTE_MEAN_AND_REQUEST = [
    DashboardRetrieveIncidentAndMeanRequestAppleWatchTask,
    DashboardRetrieveIncidentAndMeanRequestAppleWatch2Task,
    DashboardRetrieveIncidentAndMeanRequestAppleIpad3Task,
    DashboardRetrieveIncidentAndMeanRequestAppleIphone13proTask,
    DashboardRetrieveIncidentAndMeanRequestAppleIphone13Task,
    DashboardRetrieveIncidentAndMeanRequestGalaxyNote20Task,
    DashboardRetrieveIncidentAndMeanRequestGoogleNexus7Task,
    DashboardRetrieveIncidentAndMeanRequestMicrosoftSurfacePro3Task,
    DashboardRetrieveIncidentAndMeanRequestPixel4aTask,
    DashboardRetrieveIncidentAndMeanRequestWindowsSurfacePro4Task,
]

DASH_COMPUTE_MEDIAN_AND_REQUEST = [
    DashboardRetrieveIncidentAndMedianRequestAppleWatchTask,
    DashboardRetrieveIncidentAndMedianRequestAppleWatch2Task,
    DashboardRetrieveIncidentAndMedianRequestAppleIpad3Task,
    DashboardRetrieveIncidentAndMedianRequestAppleIphone13proTask,
    DashboardRetrieveIncidentAndMedianRequestAppleIphone13Task,
    DashboardRetrieveIncidentAndMedianRequestGalaxyNote20Task,
    DashboardRetrieveIncidentAndMedianRequestGoogleNexus7Task,
    DashboardRetrieveIncidentAndMedianRequestMicrosoftSurfacePro3Task,
    DashboardRetrieveIncidentAndMedianRequestPixel4aTask,
    DashboardRetrieveIncidentAndMedianRequestWindowsSurfacePro4Task,
]

DASH_COMPUTE_MODE_AND_REQUEST = [
    DashboardRetrieveIncidentAndModeRequestAppleWatchTask,
    DashboardRetrieveIncidentAndModeRequestAppleWatch2Task,
    DashboardRetrieveIncidentAndModeRequestAppleIpad3Task,
    DashboardRetrieveIncidentAndModeRequestAppleIphone13proTask,
    DashboardRetrieveIncidentAndModeRequestAppleIphone13Task,
    DashboardRetrieveIncidentAndModeRequestGalaxyNote20Task,
    DashboardRetrieveIncidentAndModeRequestGoogleNexus7Task,
    DashboardRetrieveIncidentAndModeRequestMicrosoftSurfacePro3Task,
    DashboardRetrieveIncidentAndModeRequestPixel4aTask,
    DashboardRetrieveIncidentAndModeRequestWindowsSurfacePro4Task,
]
