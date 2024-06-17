import random
from playwright.sync_api._generated import Page
from typing import Tuple

from .dash_do_base import DashboardRetrieveIncidentAndDoTask, DashDoFinalTask

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask, SingleChartMeanMedianModeRetrievalTask

from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.form import CreateIncidentTask


class DashboardRetrieveIncidentAndCreateIncidentTask(DashboardRetrieveIncidentAndDoTask):
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
        Retrieve the worst performing employee and create an incident to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create an incident for the worst performing employee from the list"
        """
        self.filter_than = "lesser"
        self.attribute_name = "assigned_to"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )
        self.prefix = "DCI"

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
            self.incident_short_description = "Compulsory training for employee in probation"
            incident_config = {
                "fields": {
                    "caller_id": "Caller",
                    "category": "Category",
                    "short_description": "Short description",
                    "impact": "Impact",
                    "number": "Number",
                    "urgency": "Urgency",
                    "assigned_to": "Assigned to",
                },
                "task_fields": [
                    "caller_id",
                    "category",
                    "short_description",
                    "impact",
                    "number",
                    "urgency",
                    "assigned_to",
                ],
                "template_record": {
                    "caller_id": self.user_name,
                    "category": "Inquiry / Help",
                    "short_description": self.incident_short_description,
                    "impact": "1 - High",
                    "number": incident_number,
                    "urgency": "1 - High",
                    "assigned_to": agent_full_name,
                },
            }

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
                ),
                # Create an incident
                CreateIncidentTask(
                    instance=self.instance,
                    fixed_config=incident_config,
                    is_validated=False,
                    used_in_level_2=True,
                    check_record_created=False,
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
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of the number of incidents assigned across agents. Using this value, retrieve agents that have less than or equal number of incidents assigned to them compared to this value.\n"
                + f"\t   For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have less than or equal to 2 assigned incidents.\n\n"
                + f"\t - Task: For each agent that fits the above criteria, create an 'incident' with the following information (only fill these fields and the 'incident number' from below) and assign it to them using the 'Assigned to' field: \n"
                + f"\t\t Category: 'Inquiry / Help', Impact: '1 - High', Urgency: '1 - High', Short description: 'Compulsory training for employee in probation', Caller: '{self.user_name}'. Make sure to use an 'incident number' from the list as described below.\n"
                + f"\t   Importantly, you should override the default incident numbers in the form and instead use one incident number from the following list for each incident you create: {incident_numbers_string}.\n\n"
                + f"Note that you will create as many incidents as there are agents matching the above criteria.\n"
                + f"\t   For example, consider the above case and say you have 3 agents with less than or equal to 2 incidents assigned to them in the chart. You will be creating '3' new incidents here, one assigned to each agent. \n\n"
            )

        goal, info = super().setup_goal(page=page, config=config)

        if self.level == 2:
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page. \n"
                + f"\n2. Given the title of the report, search for it on this page. The report shows the number of 'incidents' assigned to an 'agent'.\n"
                + f"\n3. Find the agents with a number of incidents assigned less than or equal to the {self.description_mapping[self.question]} of the number of assigned incidents across agents. For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have less than or equal to 2 assigned incidents.\n"
                + f"\n4. Navigate to Service Desk > Incidents. \n"
                + f"\n5. You have to create new 'incidents' from this page for all the agents based on the above criteria. Only fill the following fields when creating a new incident:- Category: 'Inquiry / Help', Impact: '1 - High', Urgency: '1 - High', Short description: 'Compulsory training for employee in probation', Caller: '{self.user_name}' and 'assign' them to each agent using the 'Assigned to' field.\n\n"
                + f"Importantly, you should override the default incident numbers in the form and instead use one incident number from the following list for each incident you create: {incident_numbers_string}.\n"
                + f"Note that you will create as many incidents as there are agents matching the above criteria."
                + "\nFor example, consider the above case and say you have 3 agents with less than or equal to 2 incidents assigned to them in the chart. You will be creating '3' new incidents here, one assigned to each agent. \n"
            )

        return goal, info

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        fixed_template_record = {
            "short_description": "Compulsory training for employee in probation",
            "impact": "1",
            "urgency": "1",
        }
        for incident_number in self.incident_numbers:
            created_incident_response = table_api_call(
                instance=self.instance,
                table="incident",
                params={
                    "sysparm_query": f"number={incident_number}",
                    "sysparm_fields": "assigned_to,impact,urgency,short_description,description",
                },
                method="GET",
            )["result"]
            if len(created_incident_response) == 0:
                return (
                    0,
                    False,
                    "",
                    {"message": f"No incident created with number {incident_number}."},
                )
            elif len(created_incident_response) > 1:
                return (
                    0,
                    False,
                    "",
                    {"message": f"Multiple incidents created with number {incident_number}."},
                )
            created_incident_response = created_incident_response[0]
            if created_incident_response["assigned_to"]["value"] not in self.agent_value_sysids:
                return (
                    0,
                    False,
                    "",
                    {"message": f"Incident {incident_number} assigned to a random agent."},
                )

            for key, value in fixed_template_record.items():
                if str(created_incident_response[key]).lower() != str(value).lower():
                    return (
                        0,
                        False,
                        "",
                        {
                            "message": f"Incident {incident_number} assigned incorrect value to field {key}."
                        },
                    )

        for agent_sysid in self.agent_value_sysids:
            created_incident_response = table_api_call(
                instance=self.instance,
                table="incident",
                params={
                    "sysparm_query": f"assigned_to={agent_sysid}^short_description={self.incident_short_description}",
                    "sysparm_fields": "assigned_to",
                },
                method="GET",
            )["result"]
            if len(created_incident_response) == 0:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"No incident assigned to agent {self.agents[agent_sysid]['user_name']}."
                    },
                )
            elif len(created_incident_response) > 1:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"Multiple incidents assigned to agent {self.agents[agent_sysid]['user_name']}."
                    },
                )
        reward, done, message, info = super().validate(page, chat_messages)
        return reward, done, message, info

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


class DashboardRetrieveIncidentAndMinCreateIncidentTask(
    DashboardRetrieveIncidentAndCreateIncidentTask, DashDoFinalTask
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
        )


class DashboardRetrieveIncidentAndMeanCreateIncidentTask(
    DashboardRetrieveIncidentAndCreateIncidentTask, DashDoFinalTask
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
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianCreateIncidentTask(
    DashboardRetrieveIncidentAndCreateIncidentTask, DashDoFinalTask
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
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeCreateIncidentTask(
    DashboardRetrieveIncidentAndCreateIncidentTask, DashDoFinalTask
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
            question="mode",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]

DASH_AND_CREATE_INCIDENT = [
    DashboardRetrieveIncidentAndMinCreateIncidentTask,
]
DASH_COMPUTE_AND_CREATE_INCIDENT = [
    DashboardRetrieveIncidentAndMeanCreateIncidentTask,
    DashboardRetrieveIncidentAndMedianCreateIncidentTask,
    DashboardRetrieveIncidentAndModeCreateIncidentTask,
]
