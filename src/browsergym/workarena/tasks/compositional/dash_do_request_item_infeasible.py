import random
from playwright.sync_api._generated import Page
from typing import Tuple

from .dash_do_base import DashboardRetrieveIncidentAndDoInfeasibleTask, DashDoFinalTask
from .utils.infeasible_configs import get_infeasible_form_config

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask

from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.form import CreateItemRequestTask


class DashboardRetrieveIncidentAndRequestItemInfeasibleTask(
    DashboardRetrieveIncidentAndDoInfeasibleTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        item: str = None,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
        provide_reason: bool = None,
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
            function=get_infeasible_form_config,
            provide_reason=provide_reason,
        )
        if not item:
            raise Exception("No item passed to assign")
        self.item = item
        self.task_description = ""
        self.short_description = (
            f"Order an {self.item} for the best performing employee from the list."
        )
        self.attribute_name = "assigned_to"  # Return full name
        self.filter_than = "greater"
        self.prefix = "IRI"

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
                "infeasible_task_fields": ["number", "cat_item", "quantity"],
            }
            request_item_config, self.infeasible_reasons = self.function(
                config=request_item_config, random=self.random
            )
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
        if self.level == 3:
            self.task_description = (
                self.task_description
                + f"Value to retrieve: {self.description_mapping[self.question]} of all the incidents. Comparator: Greather than or equal to the value.\n"
                + f"Task: Request items with the following information: \n"
                + f"Item: {self.item}, Quantity: 1.\n"
                + f"Request the item for each of the agents mentioned above. You can use the item numbers: {self.requested_item_numbers}, one for each request."
            )

        goal, info = super().setup_goal(page=page, config=config)

        if self.level == 2:
            goal = (
                self.task_description
                + f"1. Navigate to the CMDB reports and look for the report with the mentioned hashtag. \n"
                + f"2. Find the agents with number of incidents greater than or equal to the  {self.description_mapping[self.question]} of the incidents assigned to every one. \n"
                + f"3. Navigate to Open Records > Items. \n"
                + f"4. Create new item requests with the following field values:- 'Item: {self.item}, Quantity: 1' and assign them to each of the agents. You will create as many item requests as there are agents.\n"
                + f"You should use the following request numbers for each item request (one for each): {self.requested_item_numbers}."
            )

        return goal, info

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


class DashboardRetrieveIncidentAndMaxRequestAppleWatchInfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleWatchInfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleWatch2InfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple Watch Series 2",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleWatch2InfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple Watch Series 2",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIpad3InfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple iPad 3",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIpad3InfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple iPad 3",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIphone13proInfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple iPhone 13 pro",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIphone13proInfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple iPhone 13 pro",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIphone13InfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple iPhone 13",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestAppleIphone13InfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Apple iPhone 13",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestGalaxyNote20InfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Galaxy Note 20",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestGalaxyNote20InfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Galaxy Note 20",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestGoogleNexus7InfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Google Nexus 7",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestGoogleNexus7InfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Google Nexus 7",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestMicrosoftSurfacePro3InfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Microsoft Surface Pro 3",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestMicrosoftSurfacePro3InfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Microsoft Surface Pro 3",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestPixel4aInfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Pixel 4a",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestPixel4aInfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Pixel 4a",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


class DashboardRetrieveIncidentAndMaxRequestWindowsSurfacePro4InfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Windows Surface Pro 4",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMaxRequestWindowsSurfacePro4InfeasibleTask(
    DashboardRetrieveIncidentAndRequestItemInfeasibleTask, DashDoFinalTask
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
            item="Windows Surface Pro 4",
            question="max",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]
