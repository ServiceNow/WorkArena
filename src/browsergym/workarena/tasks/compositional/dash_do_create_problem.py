from playwright.sync_api._generated import Page
from typing import Tuple

from .dash_do_base import DashboardRetrieveIncidentAndDoTask, DashDoFinalTask

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask, SingleChartMeanMedianModeRetrievalTask

from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.form import CreateProblemTask


class DashboardRetrieveIncidentAndCreateProblemTask(DashboardRetrieveIncidentAndDoTask):
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
        Retrieve the worst performing employee and create a problem to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a problem for the worst performing employee from the list"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question=question,
            dashboard_class=dashboard_class,
        )
        self.attribute_name = "assigned_to"
        self.filter_than = "lesser"
        self.prefix = "DCP"

    def set_compositional_task(self) -> None:
        agent_full_names, agent_value_sysids = self.get_agent_values(
            self.attribute_name, self.filter_than
        )
        self.agent_value_sysids = agent_value_sysids
        create_problem_subtasks = []
        self.short_description = "Compulsory training for employee in probation"
        for agent_full_name in agent_full_names:
            problem_config = {
                "fields": {
                    "short_description": "Problem statement",
                    "urgency": "Urgency",
                    "assigned_to": "Assigned to",
                    "impact": "Impact",
                },
                "task_fields": [
                    "short_description",
                    "urgency",
                    "assigned_to",
                    "impact",
                ],
                "template_record": {
                    "short_description": self.short_description,
                    "impact": "1 - High",
                    "urgency": "1 - High",
                    "assigned_to": agent_full_name,
                },
            }

            create_problem_subtask = [
                # Navigate to the incident list
                AllMenuTask(
                    instance=self.instance,
                    fixed_config={
                        "application": "Problem",
                        "module": "All",
                        "url": "/now/nav/ui/classic/params/target/problem_list.do",
                    },
                    is_validated=False,
                    used_in_level_2=True,
                ),
                # Create a problem
                CreateProblemTask(
                    instance=self.instance,
                    fixed_config=problem_config,
                    is_validated=False,
                    used_in_level_2=True,
                    check_record_created=False,
                ),
            ]
            create_problem_subtasks += create_problem_subtask

        self.compositional_task = create_problem_subtasks

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report(
            user_roles=[
                "itil",
                "problem_admin",
                "problem_manager",
                "problem_coordinator",
                "problem_task_analyst",
            ]
        )
        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()

        if self.level == 3:
            self.task_description = (
                self.task_description
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of the number of incidents assigned across agents. Retrieve agents that have less than or equal number of incidents assigned to them compared to this value.\n"
                + f"\t   For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have less than or equal to 2 assigned incidents.\n\n"
                + f"\t - Task: For each agent that fits the above criteria, create a 'problem' with the following information (only fill these fields) and assign it to them using the 'Assigned to' field: \n"
                + f"\t\t Impact: '1 - High', Urgency: '1 - High', Problem statement: 'Compulsory training for employee in probation'.\n"
                + f"Note that you will create as many problems as there are agents matching the above criteria.\n"
                + f"\t For example, consider the above case and say you have 3 agents with less than or equal to 2 incidents assigned to them in the chart. You will be creating '3' problems here, one assigned to each agent. \n\n"
            )

        goal, info = super().setup_goal(page=page, config=config)

        if self.level == 2:
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page. \n"
                + f"\n2. Given the title of the report, search for it on this page. The report shows the number of 'incidents' assigned to an 'agent'.\n"
                + f"\n3. Find the agents with a number of incidents assigned less than or equal to the {self.description_mapping[self.question]} of the number of assigned incidents across agents. For example, if you were asked to find the 'mean' or 'average' for a case where there are 4 agents assigned 1,2,3,2 incidents respectively, the mean would be 2. The list of agents required for solving the following task would be all the agents that have less than or equal to 2 assigned incidents.\n"
                + f"\n4. Navigate to All > Problems. \n"
                + f"\n5. You have to create new 'problems' from this page for all the agents based on the above criteria. Only fill the following fields when creating a new problem:- Impact: '1 - High', Urgency: '1 - High', Problem statement: 'Compulsory training for employee in probation' and 'assign' them to each agent.\n\n"
                + f"Note that you will create as many problems as there are agents matching the above criteria."
                + "\nFor example, consider the above case and say you have 3 agents with less than or equal to 2 incidents assigned to them in the chart. You will be creating '3' problems here, one assigned to each agent. \n"
            )

        return goal, info

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        fixed_template_record = {
            "short_description": "Compulsory training for employee in probation",
            "impact": "1",
            "urgency": "1",
        }
        for agent_sysid in self.agent_value_sysids:
            created_problem_response = table_api_call(
                instance=self.instance,
                table="problem",
                params={
                    "sysparm_query": f"assigned_to={agent_sysid}^short_description={self.short_description}",
                },
                method="GET",
            )["result"]
            if len(created_problem_response) == 0:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"No problem created for agent {self.agents[agent_sysid]['user_name']}."
                    },
                )
            elif len(created_problem_response) > 1:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"Multiple problems created for agent {self.agents[agent_sysid]['user_name']}."
                    },
                )
            created_problem_response = created_problem_response[0]
            for key, value in fixed_template_record.items():
                if str(created_problem_response[key]).lower() != str(value).lower():
                    return (
                        0,
                        False,
                        "",
                        {
                            "message": f"Problem for agent {self.agents[agent_sysid]['user_name']} assigned incorrect value to field {key}."
                        },
                    )
        reward, done, message, info = super().validate(page, chat_messages)
        return reward, done, message, info

    def teardown(self) -> None:
        for agent_sysid in self.agent_sysids:
            created_problem_response = table_api_call(
                instance=self.instance,
                table="problem",
                params={
                    "sysparm_query": f"assigned_to={agent_sysid}",
                },
                method="GET",
            )["result"]
            for problem in created_problem_response:
                db_delete_from_table(
                    instance=self.instance,
                    table="problem",
                    sys_id=problem["sys_id"],
                )
        return super().teardown()


class DashboardRetrieveIncidentAndMinCreateProblemTask(
    DashboardRetrieveIncidentAndCreateProblemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the worst performing employee and create a problem to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a problem for the worst performing employee from the list"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="min",
            dashboard_class=SingleChartMinMaxRetrievalTask,
        )


class DashboardRetrieveIncidentAndMeanCreateProblemTask(
    DashboardRetrieveIncidentAndCreateProblemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the worst performing employee and create a problem to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a problem for the worst performing employee from the list"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="mean",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndMedianCreateProblemTask(
    DashboardRetrieveIncidentAndCreateProblemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the worst performing employee and create a problem to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a problem for the worst performing employee from the list"
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            question="median",
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
        )


class DashboardRetrieveIncidentAndModeCreateProblemTask(
    DashboardRetrieveIncidentAndCreateProblemTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve the worst performing employee and create a problem to assign them a probation course.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a problem for the worst performing employee from the list"
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

DASH_AND_CREATE_PROBLEM = [DashboardRetrieveIncidentAndMinCreateProblemTask]
DASH_COMPUTE_AND_CREATE_PROBLEM = [
    DashboardRetrieveIncidentAndMeanCreateProblemTask,
    DashboardRetrieveIncidentAndMedianCreateProblemTask,
    DashboardRetrieveIncidentAndModeCreateProblemTask,
]
