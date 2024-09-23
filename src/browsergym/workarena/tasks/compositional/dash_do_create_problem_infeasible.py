from playwright.sync_api._generated import Page
from typing import Tuple

from .dash_do_base import DashboardRetrieveIncidentAndDoInfeasibleTask, DashDoFinalTask
from .utils.infeasible_configs import get_infeasible_form_config

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask

from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.form import CreateProblemTask


class DashboardRetrieveIncidentAndCreateProblemInfeasibleTask(
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
        provide_reason: bool = None,
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
            function=get_infeasible_form_config,
            provide_reason=provide_reason,
        )
        self.task_description = ""
        self.short_description = "Create a problem for the worst performing employee from the list."
        self.attribute_name = "assigned_to"
        self.filter_than = "lesser"
        self.prefix = "ICP"

    def set_compositional_task(self) -> None:
        agent_full_names, agent_value_sysids = self.get_agent_values(
            self.attribute_name, self.filter_than
        )
        self.agent_value_sysids = agent_value_sysids
        create_problem_subtasks = []
        for agent_full_name in agent_full_names:
            problem_config = {
                "fields": {
                    "short_description": "Problem statement",
                    "description": "Description",
                    "urgency": "Urgency",
                    "assigned_to": "Assigned to",
                    "impact": "Impact",
                },
                "task_fields": [
                    "short_description",
                    "description",
                    "urgency",
                    "assigned_to",
                    "impact",
                ],
                "template_record": {
                    "description": "Compulsory training for employee in probation",
                    "short_description": "Compulsory training for employee in probation",
                    "impact": "1 - High",
                    "urgency": "1 - High",
                    "assigned_to": agent_full_name,
                },
                "infeasible_task_fields": ["short_description", "description", "urgency", "impact"],
            }
            problem_config, self.infeasible_reasons = self.function(
                config=problem_config, random=self.random
            )

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
                + f"Value to retrieve: {self.description_mapping[self.question]} of all the incidents. Comparator: Less than or equal to the value.\n"
                + f"Task: Create problems with the following information: \n"
                + f"Category: 'Inquiry / Help', Impact: '1 - High', Urgency: '1 - High', Short description: 'Compulsory training for employee in probation'.\n"
                + f"Assign the problems you create to the agents mentioned above."
            )

        goal, info = super().setup_goal(page=page, config=config)

        if self.level == 2:
            goal = (
                self.task_description
                + f"\n1. Navigate to the CMDB reports and look for the report with the mentioned hashtag. \n"
                + f"\n2. Find the agents with number of incidents less than or equal to the  {self.description_mapping[self.question]} of the incidents assigned to every one. \n"
                + f"\n3. Navigate to All > Problems. \n"
                + f"\n4. Create new problems with the following field values:- Category: 'Inquiry / Help', Impact: '1 - High', Urgency: '1 - High', Short description: 'Compulsory training for employee in probation' and assign them to each of the agents."
                + "\nYou will create as many problems as there are agents.\n"
            )

        return goal, info

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


class DashboardRetrieveIncidentAndMinCreateProblemInfeasibleWithReasonTask(
    DashboardRetrieveIncidentAndCreateProblemInfeasibleTask, DashDoFinalTask
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
            provide_reason=True,
        )


class DashboardRetrieveIncidentAndMinCreateProblemInfeasibleTask(
    DashboardRetrieveIncidentAndCreateProblemInfeasibleTask, DashDoFinalTask
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
            provide_reason=False,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]
