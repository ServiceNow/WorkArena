import faker

fake = faker.Faker()

from playwright.sync_api._generated import Page

from .base import CompositionalTask, HumanEvalTask

from ..base import AbstractServiceNowTask
from ..dashboard import WorkLoadBalancingMinMaxRetrievalTask
from ..form import EditProblemTask
from ..knowledge import KnowledgeBaseSearchTask
from ..list import FilterProblemListForWorkLoadBalancingTask
from ..navigation import AllMenuTask
from ..send_chat_message import SendChatMessageGenericTask

from ...api.problem import create_problem
from ...api.report import create_report
from ...api.user import create_user
from ...api.utils import db_delete_from_table, table_api_call
from ...instance import SNowInstance


class WorkloadBalancingTask(CompositionalTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        min_users: int = 2,
        max_users: int = 4,
        # Ranges to randomly choose from
        max_problem_range: int = [3, 4],
        mid_problem_range: int = [2, 3],
        min_problem_range: int = [1, 2],
    ) -> None:
        """
        Workload balancing task:
        - Navigate to the KB
        - Find the protocol for re-distributing work
        - Find the user who has the greatest number of problems assigned to them
        - Re-assign the problems to the user having the least number of problems assigned to them

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of subtasks.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        min_users: int
            The minimum number of users to create and to distribute the problems to
        max_users: int
            The maximum number of users to create and to distribute the problems to
        max_problem_range: list[int, int]
            The range of the number of problems to assign to the user with the most problems
        mid_problem_range: list[int, int]
            The range of the number of problems to assign to all users but the ones with the least/most problems
        min_problem_range: list[int, int]
            The range of the number of problems to assign to the user with the least problems
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. e.g. "Referring to company protocol 'Agent Workload Balancing', re-distribute the problems with description containing {self.problem_hashtag}"
        short_description: str
            A short description of the task to be completed. e.g. "Balance the workload for problems with description containing {self.problem_hashtag}"
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        self.protocol_name = "Agent Workload Balancing"
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            level=level,
            protocol_name=self.protocol_name,
        )

        self.problem_hashtag = (
            f"#PRB{str(id(self) % (10**8)).zfill(9)}"  # identifier to select problems
        )
        self.task_description = None
        self.short_description = None
        self.min_users = min_users
        self.max_users = max_users
        self.max_problem_range = max_problem_range
        self.mid_problem_range = mid_problem_range
        self.min_problem_range = min_problem_range

        # In this case, there will only be 2 users as the values are bound and the top value is excluded in the randint function
        if self.min_users == 2 and self.max_users == 3:
            assert (
                self.min_problem_range[1] <= self.max_problem_range[0]
            ), "The problem ranges should not overlap"
        # In this case, there will be 3 users
        else:
            assert (
                self.min_problem_range[1] <= self.mid_problem_range[0]
                and self.mid_problem_range[1] <= self.max_problem_range[0]
            ), "The problem ranges should not overlap"
        assert self.max_problem_range[1] <= 6, "The maximum number of problems should not exceed 6"

        self.plot_title = None  # The title of the plot created for the report
        self.lowest_priority = 0  # The lowest priority of the problems; a high number indicates a low priority. Set in the setup_goal method

        self.category_name = (
            fake.word() + "-" + fake.word()
        )  # The category of the problems to re-distribute
        self.category_sys_id = (
            None  # The sys_id of the category created for the task; create in the setup_goal method
        )
        self.user_sys_ids = []  # The sys_ids of the users created for the task
        self.problem_sys_ids = []  # The sys_ids of the problems created for the task
        self.report_sys_id = None  # The sys_id of the report created for the task
        self.user_with_most_problems = None  # The name of the user that has the most problems assigned; defined in the setup_goal method
        self.user_with_least_problems = None  # The name of the user that has the least problems assigned; defined in the setup_goal method
        self.problem_to_edit_sys_id = (
            None  # The sys_id of the problem to re-assign; defined in the setup_goal method
        )
        self.problem_to_edit_number = (
            None  # The number of the problem to re-assign; defined in the setup_goal method
        )

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        num_users = self.random.randint(self.min_users, self.max_users)
        max_problems = self.random.randint(*self.max_problem_range)
        min_problems = self.random.randint(*self.min_problem_range)

        # Create users, create problems and assign problems to users
        for i in range(num_users):
            if i == 0:
                num_problems = max_problems
            elif i == num_users - 1:
                num_problems = min_problems
            else:
                num_problems = self.random.randint(*self.mid_problem_range)
            first_name = fake.first_name() + "-" + fake.first_name()
            last_name = fake.last_name() + "-" + fake.last_name()
            user_full_name = first_name + " " + last_name
            _, _, user_sys_id = create_user(
                instance=self.instance,
                first_name=first_name,
                last_name=last_name,
                user_roles=[
                    "admin",
                    "problem_admin",
                    "problem_manager",
                    "problem_coordinator",
                    "problem_task_analyst",
                ],
                random=self.random,
            )
            self.user_sys_ids.append(user_sys_id)

            if i == 0:
                self.user_with_most_problems = user_full_name
            elif i == num_users - 1:
                self.user_with_least_problems = user_full_name

            # Create problems assigned to current user
            for j in range(num_problems):
                # Assign a priority to the problem; 1 being highest priority and 5 being lowest
                # the use of j % 5 is to ensure that the priority is between 1 and 5 and that there is
                # only one problem with the lowest priority
                priority = (j % 5) + 1
                self.lowest_priority = max(self.lowest_priority, priority)
                problem_sys_id, problem_number = create_problem(
                    instance=self.instance,
                    user_sys_id=user_sys_id,
                    priority=priority,
                    problem_hashtag=self.problem_hashtag,
                    return_number=True,
                )
                # The last problem created is the one to re-assign as it will be the one with the lowest priority (highest priority value)
                # and the first user will be the one with the most problems assigned
                if i == 0 and j == num_problems - 1:
                    self.problem_to_edit_sys_id = problem_sys_id
                    self.problem_to_edit_number = problem_number
                self.problem_sys_ids.append(problem_sys_id)

        # Create a report for problems of the current category
        self.report_sys_id, plot_title = create_report(
            instance=self.instance,
            table="problem",
            filter_hashtag=self.problem_hashtag,
            field="assigned_to",
            plot_title=f"Problems for with hashtag {self.problem_hashtag}",
            random=self.random,
        )
        self.plot_title = plot_title

        # Sample a configuration
        config = self._get_config()
        # Get the task description
        self.short_description = (
            f"Balance the workload for problems with hashtag {self.problem_hashtag}"
        )
        self.task_description = f"Referring to company protocol '{self.protocol_name}' (located in the \"Company Protocols\" knowledge base) re-distribute the problems with hashtag={self.problem_hashtag}."

        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[AbstractServiceNowTask]:
        """ """
        navigate_to_protocol_subtask = [
            # Navigate to the KB
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Knowledge",
                    "url": "/now/nav/ui/classic/params/target/%24knowledge.do",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
            # Find the protocol for on-boarding a new user
            KnowledgeBaseSearchTask(
                instance=self.instance,
                fixed_config={
                    "alternative_answers": [],
                    "item": f"{self.protocol_name}",
                    "question": f"Can you find the '{self.protocol_name}' Protocol in the Knowledge Base?",
                    "value": "",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
        ]

        find_most_and_least_busy_users_subtask = [
            # Navigate to the reports list
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Reports",
                    "module": "Administration > All",
                    "url": "/now/nav/ui/classic/params/target/sys_report_list.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            WorkLoadBalancingMinMaxRetrievalTask(
                instance=self.instance,
                fixed_config={
                    "url": "/now/nav/ui/classic/params/target/sys_report",
                    "chart_title": self.plot_title,
                    "chart_series": "",
                    "question": "min",
                },
                is_validated=False,
                used_in_level_2=True,
                problem_hashtag=self.problem_hashtag,
            ),
        ]

        reassign_problem_subtask = [
            # Navigate to the hardware asset list
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
            # Filter the problems by assignee, and priority = lowest priority
            # The existence of a lower priority problem is guaranteed
            FilterProblemListForWorkLoadBalancingTask(
                instance=self.instance,
                fixed_config={
                    "filter_columns": ["assigned_to", "priority"],
                    "filter_kind": "AND",
                    "filter_values": [
                        f"{self.user_with_most_problems}",
                        f"{self.lowest_priority}",
                    ],
                },
                is_validated=False,
                used_in_level_2=True,
                goal=f'Create a filter to find problems where \n - "Assigned to" is the user with the most problems assigned and \n - "Priority" is "{self.lowest_priority}".',
            ),
            # Assign a problem to the user with the least problems assigned to them
            EditProblemTask(
                instance=self.instance,
                new_values={"assigned_to": f"{self.user_with_least_problems}"},
                record_sys_id=self.problem_to_edit_sys_id,
                record_number=self.problem_to_edit_number,
                is_validated=True,
                used_in_level_2=True,
                level=self.level,
            ),
        ]

        config = (
            navigate_to_protocol_subtask
            + find_most_and_least_busy_users_subtask
            + reassign_problem_subtask
        )

        return config

    def teardown(self) -> None:
        # Delete the users
        for user_sys_id in self.user_sys_ids:
            record_exists = table_api_call(
                instance=self.instance,
                table="sys_user",
                params={"sysparm_query": f"sys_id={user_sys_id}"},
            )
            if record_exists:
                db_delete_from_table(
                    instance=self.instance,
                    table="sys_user",
                    sys_id=user_sys_id,
                )
        # Delete the problems
        for problem_sys_id in self.problem_sys_ids:
            record_exists = table_api_call(
                instance=self.instance,
                table="problem",
                params={"sysparm_query": f"sys_id={problem_sys_id}"},
            )
            if record_exists:
                db_delete_from_table(
                    instance=self.instance,
                    table="problem",
                    sys_id=problem_sys_id,
                )
        # Delete the report
        db_delete_from_table(
            instance=self.instance,
            table="sys_report",
            sys_id=self.report_sys_id,
        )
        super().teardown()


class WorkloadBalancingSmallTask(WorkloadBalancingTask, HumanEvalTask):
    def __init__(self, seed: int = None, instance: SNowInstance = None, level: int = 2) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            level=level,
            min_users=2,
            max_users=4,
            max_problem_range=[4, 6],
            mid_problem_range=[3, 4],
            min_problem_range=[1, 3],
        )


class WorkloadBalancingMediumTask(WorkloadBalancingTask):
    def __init__(self, seed: int = None, instance: SNowInstance = None, level: int = 2) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            level=level,
            min_users=5,
            max_users=7,
            max_problem_range=[5, 6],
            mid_problem_range=[3, 5],
            min_problem_range=[1, 3],
        )


class WorkloadBalancingLargeTask(WorkloadBalancingTask):
    def __init__(self, seed: int = None, instance: SNowInstance = None, level: int = 2) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            level=level,
            min_users=8,
            max_users=10,
            max_problem_range=[5, 6],
            mid_problem_range=[3, 5],
            min_problem_range=[1, 3],
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type)
    and issubclass(var, WorkloadBalancingTask)
    and var is not WorkloadBalancingTask
]
