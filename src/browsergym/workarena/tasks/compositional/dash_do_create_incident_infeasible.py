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
from browsergym.workarena.tasks.form import CreateIncidentTask


class DashboardRetrieveIncidentAndCreateIncidentInfeasibleTask(
    DashboardRetrieveIncidentAndDoInfeasibleTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        question: str = None,
        dashboard_class: AbstractServiceNowTask = None,
        provide_reason: bool = True,
    ) -> None:
        """
        Retrieve the worst performing employee and create an incident to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create an incident for the worst performing employee from the list"
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
        self.task_description = ""
        self.short_description = (
            "Create an incident for the worst performing employee from the list."
        )
        self.filter_than = "lesser"
        self.attribute_name = "assigned_to"
        self.prefix = "ICI"

    def set_compositional_task(self) -> None:
        # The unique name for the user is created once the task is instantiated
        base_user = table_api_call(
            instance=self.instance,
            table="sys_user",
            params={
                "sysparm_query": f"sys_id={self._base_user_sysid}",
            },
        )["result"][0]
        self.user_name = base_user["first_name"] + " " + base_user["last_name"]

        agent_full_names, agent_value_sysids = self.get_agent_values(
            self.attribute_name, self.filter_than
        )
        self.agent_value_sysids = agent_value_sysids
        incident_numbers = []
        for _ in range(len(agent_full_names)):
            incident_number = "INC" + str(random.randint(1000000, 9999999))
            while (
                incident_number in self.all_incident_numbers or incident_number in incident_numbers
            ):
                incident_number = "INC" + str(random.randint(1000000, 9999999))
            incident_numbers.append(incident_number)

        self.incident_numbers = incident_numbers

        create_incident_subtasks = []

        for agent_full_name, incident_number in zip(agent_full_names, incident_numbers):
            incident_config = {
                "fields": {
                    "caller_id": "Caller",
                    "category": "Category",
                    "description": "Description",
                    "short_description": "Short description",
                    "impact": "Impact",
                    "number": "Number",
                    "urgency": "Urgency",
                    "assigned_to": "Assigned to",
                },
                "task_fields": [
                    "caller_id",
                    "category",
                    "description",
                    "short_description",
                    "impact",
                    "number",
                    "urgency",
                    "assigned_to",
                ],
                "template_record": {
                    "caller_id": self.user_name,
                    "category": "Inquiry / Help",
                    "description": "Compulsory training for employee in probation",
                    "short_description": "Compulsory training for employee in probation",
                    "impact": "1 - High",
                    "number": incident_number,
                    "urgency": "1 - High",
                    "assigned_to": agent_full_name,
                },
                "infeasible_task_fields": [
                    "category",
                    "description",
                    "short_description",
                    "impact",
                    "number",
                ],
            }

            incident_config, self.infeasible_reasons = self.function(
                config=incident_config, random=self.random
            )

            create_incident_subtask = [
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
                    has_description=False,
                ),
                # Create an incident
                CreateIncidentTask(
                    instance=self.instance,
                    fixed_config=incident_config,
                    is_validated=False,
                    used_in_level_2=True,
                    check_record_created=False,
                    has_description=True,
                ),
            ]
            create_incident_subtasks += create_incident_subtask

        self.compositional_task = create_incident_subtasks

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()
        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()
        incident_numbers_string = ", ".join(self.incident_numbers)

        if self.level == 3:
            self.task_description = (
                self.task_description
                + f"Value to retrieve: {self.description_mapping[self.question]} of all the incidents. Comparator: Less than or equal to the value.\n"
                + f"Task: Create incidents with the following information: \n"
                + f"Category: 'Inquiry / Help', Impact: '1 - High', Urgency: '1 - High', Short description: 'Compulsory training for employee in probation', Caller: '{self.user_name}'.\n"
                + f"Assign the incidents you create to the agents mentioned above. You can use the incident numbers: {incident_numbers_string}, one for each."
            )

        goal, info = super().setup_goal(
            page=page, config=config, build_pretty_print_description=False
        )

        if self.level == 2:
            goal = (
                self.task_description
                + f"\n1. Navigate to the CMDB reports and look for the report with the mentioned hashtag. \n"
                + f"\n2. Find the agents with number of incidents less than or equal to the  {self.description_mapping[self.question]} of the incidents assigned to every one. \n"
                + f"\n3. Navigate to Service Desk > Incidents. \n"
                + f"\n4. Create new incidents with the following field values:- Category: 'Inquiry / Help', Impact: '1 - High', Urgency: '1 - High', Short description: 'Compulsory training for employee in probation' and assign them to each of the agents. You will create as many incidents as there are agents.\n"
                + f"\nYou should use the following incident numbers for each incident (one for each): {incident_numbers_string}."
            )

        return goal, info

    def teardown(self) -> None:
        for incident_number in self.incident_numbers:
            created_incident_response = table_api_call(
                instance=self.instance,
                table="incident",
                params={
                    "sysparm_query": f"number={incident_number}",
                },
                method="GET",
            )["result"]
            if len(created_incident_response) > 1:
                raise Exception("Multiple incidents created")
            if len(created_incident_response) == 1:
                created_incident_sysid = created_incident_response[0]["sys_id"]
                db_delete_from_table(
                    instance=self.instance,
                    table="incident",
                    sys_id=created_incident_sysid,
                )

        return super().teardown()


class DashboardRetrieveIncidentAndMinCreateIncidentInfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndCreateIncidentInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 3,
    ) -> None:
        """
        Retrieve the worst performing employee and create an incident to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create an incident for the worst performing employee from the list"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="min",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMinCreateIncidentInfeasibleTask(
    DashboardRetrieveIncidentAndCreateIncidentInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the worst performing employee and create an incident to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create an incident for the worst performing employee from the list"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="min",
            dashboard_class=SingleChartMinMaxRetrievalTask,
            provide_reason=False,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]
