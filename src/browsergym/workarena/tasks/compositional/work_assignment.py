from typing import Tuple
from faker import Faker
import random

fake = Faker()

from playwright.sync_api._generated import Page

from .base import CompositionalTask, HumanEvalTask

from ...api.incident import create_incident
from ...api.user import create_user
from ...api.utils import table_api_call, db_delete_from_table
from ..base import AbstractServiceNowTask
from ..list import FilterIncidentListTask
from ..form import EditIncidentTask
from ..knowledge import KnowledgeBaseSearchTask
from ..navigation import AllMenuTask

from ...instance import SNowInstance


class WorkAssignmentTask(CompositionalTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_experts_per_category: int = 2,
        max_assignments: int = None,
        min_assignments: int = None,
        num_categories: int = None,
        seed: int = None,
        prefix: str = None,
    ) -> None:
        """
        Create a compositional task with specific subtasks

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[tuple[AbstractServiceNowTask, dict, bool]]
            A list of tuples, each containing a subtask, its configuration and whether or not it should be validated.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        max_experts_per_category: int
            How many maximum new agents to create for each category.
        max_assignments: int
            Maximum number of incidents created to be assigned.
            For a task, the number is randomly sampled between max_assignments and min_assignments.
        max_assignments: int
            Minimum number of incidents created to be assigned.
            For a task, the number is randomly sampled between max_assignments and min_assignments.
        prefix: str
            Prefix to name the incidents created with a unique prefix
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. e.g. "Referring to company protocol 'Work Assignment', assign incidents to different agents with the following information: \n"
        short_description: str
            A short description of the task to be completed. e.g. "Assign task to relevant expert agents"
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        self.protocol_name = "Work Assignment: Assign Incidents to Relevant Agents"
        super().__init__(
            instance=instance,
            fixed_config=fixed_config,
            level=level,
            protocol_name=self.protocol_name,
            seed=seed,
        )

        self.task_description = None
        self.short_description = f"Assign work to relevant agents"
        self.max_experts_per_category = max_experts_per_category
        self.max_assignments = max_assignments
        self.min_assignments = min_assignments
        self.num_categories = num_categories
        if self.num_categories > 4 or self.num_categories < 1:
            raise Exception("Should have at least 1 and at most 4 categories.")
        self.prefix = prefix

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.incident_configs = []
        number_assignments = self.random.randint(self.min_assignments, self.max_assignments)

        all_existing_incidents = table_api_call(
            instance=self.instance, table="incident", method="GET"
        )["result"]
        all_incident_numbers = [incident["number"] for incident in all_existing_incidents]
        new_incident_numbers = []
        for _ in range(number_assignments):
            incident_number = (
                self.prefix + str(id(self) % (10**8)).zfill(8)[:4] + str(random.randint(100, 999))
            )
            while (
                incident_number in all_incident_numbers or incident_number in new_incident_numbers
            ):
                incident_number = (
                    self.prefix
                    + str(id(self) % (10**8)).zfill(8)[:4]
                    + str(random.randint(100, 999))
                )
            new_incident_numbers.append(incident_number)

        self.active_categories = self.random.choice(
            ["hardware", "software", "network", "database"], self.num_categories, replace=False
        )
        for incident_number in new_incident_numbers:
            ### We can reduce the categories here if the setup takes too long
            category = self.random.choice(self.active_categories)
            incident_response = create_incident(
                instance=self.instance,
                incident_number=incident_number,
                caller_sys_id=self._base_user_sysid,
                category=category,
                priority=4,
                impact=2,  # priority is calculated as some combination of impact and urgency
                urgency=3,
            )
            self.incident_configs.append(incident_response)

        self.experts = dict({category: [] for category in self.active_categories})
        for _ in range(self.max_experts_per_category):
            for category in self.active_categories:
                self.experts[category].append(
                    create_user(
                        instance=self.instance,
                        first_name=f"{fake.first_name()}-{fake.first_name()}",
                        last_name=f"{fake.last_name()}-{fake.last_name()}",
                        return_full_response=True,
                        user_roles=["itil"],
                        random=self.random,
                    )
                )
        expert_string = ""
        for category in self.active_categories:
            category_experts = ", ".join(
                expert["first_name"] + " " + expert["last_name"]
                for expert in self.experts[category]
            )
            expert_string += f"{category.capitalize()} agents: {category_experts} \n"
        incident_numbers = ", ".join(new_incident_numbers)

        # Get the task description
        self.task_description = (
            f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) assign work to the agents with the following information: \n'
            + f"Incidents to assign: {incident_numbers} \n\n"
            + f"{expert_string}"
        )

        # Sample a configuration
        config = self.fixed_config if self.fixed_config else self._get_config()

        goal, info = super().setup_goal(page=page, config=config)

        if self.level == 2:
            goal = (
                self.short_description
                + f"\n1. Navigate to the Service Desk > Incidents. \n"
                + f"\n2. You have to assign the following incidents to relevant agents: {incident_numbers}. You can filter the list using each incident number and use the 'Assigned to' field to assign an incident.\n"
                + f"\n3. You have to ensure that each incident is assigned to a relevant agent based on the category of the incident.\n"
                + f"\nThe category wise agents are as follows. You can assign an incident to ANY agent from the category:\n"
                + f"{expert_string}"
            )

        return goal, info

    def _get_config(self) -> list[tuple[AbstractServiceNowTask, dict, bool]]:

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
                    "question": "Can you find the Work Assignment Protocol in the Knowledge Base?",
                    "value": "",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
        ]

        all_incident_assignments = []

        for incident_config in self.incident_configs:
            assigned_to = self.random.choice(self.experts[incident_config["category"]])
            assigned_to = assigned_to["first_name"] + " " + assigned_to["last_name"]
            assign_incidents_subtask = [
                # Navigate to the incidents list
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
                # Filter incident
                FilterIncidentListTask(
                    instance=self.instance,
                    fixed_config={
                        "filter_columns": [
                            "number",
                        ],
                        "filter_kind": "AND",
                        "filter_values": [
                            incident_config["number"],
                        ],
                    },
                    is_validated=False,
                    used_in_level_2=True,
                ),
                # Edit incident
                EditIncidentTask(
                    instance=self.instance,
                    # fixed_config=incident_config,
                    new_values={"assigned_to": assigned_to},
                    is_validated=False,
                    used_in_level_2=True,
                    record_sys_id=incident_config["sys_id"],
                    level=self.level,
                ),
            ]
            all_incident_assignments.extend(assign_incidents_subtask)

        config = navigate_to_protocol_subtask + all_incident_assignments

        return config

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        experts_sys_ids = {
            category: [expert["sys_id"] for expert in self.experts[category]]
            for category in self.experts
        }
        for incident_config in self.incident_configs:
            incident_response = table_api_call(
                instance=self.instance,
                table="incident",
                params={
                    "sysparm_query": f"sys_id={incident_config['sys_id']}",
                    "sysparm_fields": "category,assigned_to",
                },
                method="GET",
            )["result"][0]
            if incident_response["category"] != incident_config["category"]:
                raise Exception("Corrupted incident data")
            if not incident_response["assigned_to"]:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"The incident {incident_config['number']} has not been assigned to anyone."
                    },
                )
            if (
                incident_response["assigned_to"]["value"]
                not in experts_sys_ids[incident_response["category"]]
            ):
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"The incident {incident_config['number']} was assigned to an incorrect expert."
                    },
                )
        # Validate final_l3 tasks
        reward, done, message, info = super().validate(page, chat_messages)
        return reward, done, message, info

    def teardown(self) -> None:
        for incident in self.incident_configs:
            db_delete_from_table(
                instance=self.instance, table="incident", sys_id=incident["sys_id"]
            )

        for experts in self.experts.values():
            for expert in experts:
                db_delete_from_table(
                    instance=self.instance, table="sys_user", sys_id=expert["sys_id"]
                )

        return super().teardown()


class WorkAssignmentSmallTask(WorkAssignmentTask, HumanEvalTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Small version of workassignment task.
        """
        super().__init__(
            instance=instance,
            level=level,
            max_experts_per_category=2,
            max_assignments=4,
            min_assignments=3,
            num_categories=2,
            fixed_config=fixed_config,
            seed=seed,
            prefix="WAS",
        )


class WorkAssignmentMediumTask(WorkAssignmentTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Medium version of workassignment task.
        """
        super().__init__(
            instance=instance,
            level=level,
            max_experts_per_category=2,
            max_assignments=6,
            min_assignments=5,
            num_categories=3,
            fixed_config=fixed_config,
            seed=seed,
            prefix="WAM",
        )


class WorkAssignmentLargeTask(WorkAssignmentTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Large version of workassignment task.
        """
        super().__init__(
            instance=instance,
            level=level,
            max_experts_per_category=2,
            max_assignments=8,
            min_assignments=7,
            num_categories=4,
            fixed_config=fixed_config,
            seed=seed,
            prefix="WAL",
        )


class PriorityAssignmentTask(CompositionalTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_tasks_per_priority: int = 2,
        min_tasks_per_priority: int = 1,
        num_categories: int = None,
        seed: int = None,
        prefix: str = None,
    ) -> None:
        """
        Create a compositional task with specific subtasks

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[tuple[AbstractServiceNowTask, dict, bool]]
            A list of tuples, each containing a subtask, its configuration and whether or not it should be validated.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        experts_per_category: int
            How many new agents to create for each category.
        max_assignments: int
            Maximum number of incidents created to be assigned.
            For a task, the number is randomly sampled between max_assignments and min_assignments.
        max_assignments: int
            Minimum number of incidents created to be assigned.
            For a task, the number is randomly sampled between max_assignments and min_assignments.
        prefix: str
            Prefix to name the incidents created with a unique prefix
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. e.g. "Referring to company protocol 'Priority Assignment', assign incidents to different agents in terms of priority with the following information: \n"
        short_description: str
            A short description of the task to be completed. e.g. "Assign task to relevant expert agents based on the incident priorities"
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        self.protocol_name = "Work Assignment: Assign Incidents to Relevant Agents"
        super().__init__(
            instance=instance,
            fixed_config=fixed_config,
            level=level,
            protocol_name=self.protocol_name,
            seed=seed,
        )

        self.task_description = None
        self.short_description = None
        self.experts_per_category = 3  # We divide agents into 'expert', 'supporter', and 'planner'
        self.max_tasks_per_priority = max_tasks_per_priority
        self.min_tasks_per_priority = min_tasks_per_priority
        # Priority 1 is urgent, 3 is moderate, 5 is planning.
        # Also priority depends on impact and urgency rather than being an independent attribute
        self.priorities = {
            1: {
                "impact": 1,
                "urgency": 1,
                "num_incidents": self.random.randint(
                    self.min_tasks_per_priority, self.max_tasks_per_priority
                ),
                "agent_type": "expert",
            },
            3: {
                "impact": 2,
                "urgency": 2,
                "num_incidents": self.random.randint(
                    self.min_tasks_per_priority, self.max_tasks_per_priority
                ),
                "agent_type": "supporter",
            },
            5: {
                "impact": 3,
                "urgency": 3,
                "num_incidents": self.random.randint(
                    self.min_tasks_per_priority, self.max_tasks_per_priority
                ),
                "agent_type": "planner",
            },
        }
        self.num_categories = num_categories
        if self.num_categories > 4 or self.num_categories < 1:
            raise Exception("Should have at least 1 and at most 4 categories.")
        self.prefix = prefix

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.incident_configs = []
        number_assignments = sum(
            [attribute["num_incidents"] for attribute in self.priorities.values()]
        )

        all_existing_incidents = table_api_call(
            instance=self.instance, table="incident", method="GET"
        )["result"]
        all_incident_numbers = [incident["number"] for incident in all_existing_incidents]

        new_incident_numbers = []
        for _ in range(number_assignments):
            incident_number = (
                self.prefix + str(id(self) % (10**8)).zfill(8)[:4] + str(random.randint(100, 999))
            )
            while (
                incident_number in all_incident_numbers or incident_number in new_incident_numbers
            ):
                incident_number = (
                    self.prefix
                    + str(id(self) % (10**8)).zfill(8)[:4]
                    + str(random.randint(100, 999))
                )
            new_incident_numbers.append(incident_number)
        incident_category = []
        self.active_categories = self.random.choice(
            ["hardware", "software", "network", "database"], self.num_categories, replace=False
        )
        incident_number_idx = 0
        for priority, attributes in self.priorities.items():
            for _ in range(attributes["num_incidents"]):
                category = self.random.choice(self.active_categories)
                incident_response = create_incident(
                    instance=self.instance,
                    incident_number=new_incident_numbers[incident_number_idx],
                    caller_sys_id=self._base_user_sysid,
                    category=category,
                    priority=priority,
                    impact=attributes[
                        "impact"
                    ],  # priority is calculated as some combination of impact and urgency
                    urgency=attributes["urgency"],
                )
                self.incident_configs.append(incident_response)
                incident_category.append(
                    [new_incident_numbers[incident_number_idx], category, priority]
                )
                incident_number_idx += 1

        self.agents_per_category = dict({category: {} for category in self.active_categories})
        for category in self.agents_per_category:
            self.agents_per_category[category]["expert"] = create_user(
                instance=self.instance,
                first_name=f"{fake.first_name()}-{fake.first_name()}",
                last_name=f"{fake.last_name()}-{fake.last_name()}",
                return_full_response=True,
                user_roles=["itil"],
                random=self.random,
            )
            self.agents_per_category[category]["expert"]["full_name"] = (
                self.agents_per_category[category]["expert"]["first_name"]
                + " "
                + self.agents_per_category[category]["expert"]["last_name"]
            )

            self.agents_per_category[category]["supporter"] = create_user(
                instance=self.instance,
                first_name=f"{fake.first_name()}-{fake.first_name()}",
                last_name=f"{fake.last_name()}-{fake.last_name()}",
                return_full_response=True,
                user_roles=["itil"],
                random=self.random,
            )
            self.agents_per_category[category]["supporter"]["full_name"] = (
                self.agents_per_category[category]["supporter"]["first_name"]
                + " "
                + self.agents_per_category[category]["supporter"]["last_name"]
            )

            self.agents_per_category[category]["planner"] = create_user(
                instance=self.instance,
                first_name=f"{fake.first_name()}-{fake.first_name()}",
                last_name=f"{fake.last_name()}-{fake.last_name()}",
                return_full_response=True,
                user_roles=["itil"],
                random=self.random,
            )
            self.agents_per_category[category]["planner"]["full_name"] = (
                self.agents_per_category[category]["planner"]["first_name"]
                + " "
                + self.agents_per_category[category]["planner"]["last_name"]
            )

        incident_numbers = ", ".join(new_incident_numbers)

        expert_string = ""
        for category in self.active_categories:
            category_experts = f"Expert: {self.agents_per_category[category]['expert']['full_name']}, Supporter: {self.agents_per_category[category]['supporter']['full_name']}, Planner: {self.agents_per_category[category]['planner']['full_name']}"
            expert_string += f"{category.capitalize()} agents - {category_experts} \n"
        # Get the task description
        self.short_description = f"Assign work using priority to relevant agents"
        self.task_description = (
            f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) assign work to the agents with the following information: \n'
            + f"Incidents to assign: {incident_numbers} \n\n"
            + f"{expert_string}"
        )
        # Sample a configuration
        config = self.fixed_config if self.fixed_config else self._get_config()

        goal, info = super().setup_goal(page=page, config=config)

        if self.level == 2:
            goal = (
                self.short_description
                + f"\n1. Navigate to the Service Desk > Incidents. \n"
                + f"\n2. You have to assign the following incidents to relevant agents: {incident_numbers}. You can filter the list using each incident number and use the 'Assigned to' field to assign an incident.\n"
                + f"\n3. You have to ensure that each incident is assigned to a relevant agent based on the priority of the incident and its category. For an incident with priority 1 - Critical, assign it to an 'expert' agent of the category, for priority 3 - Moderate, assign it to a 'supporter' of the category, and for priority 5 - Planning assign it to a 'planner' of the category.\n"
                + f"\nThe category wise relevant agent are as follows:\n"
                + f"{expert_string}"
            )

        return goal, info

    def _get_config(self) -> list[tuple[AbstractServiceNowTask, dict, bool]]:

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
                    "question": "Can you find the Work Assignment Protocol in the Knowledge Base?",
                    "value": "",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
        ]

        all_incident_assignments = []

        for incident_config in self.incident_configs:
            assigned_to = self.agents_per_category[incident_config["category"]][
                self.priorities[int(incident_config["priority"])]["agent_type"]
            ]["full_name"]
            assign_incidents_subtask = [
                # Navigate to the incidents list
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
                # Filter incident
                FilterIncidentListTask(
                    instance=self.instance,
                    fixed_config={
                        "filter_columns": [
                            "number",
                        ],
                        "filter_kind": "AND",
                        "filter_values": [
                            incident_config["number"],
                        ],
                    },
                    is_validated=False,
                    used_in_level_2=True,
                ),
                # Edit incident
                EditIncidentTask(
                    instance=self.instance,
                    # fixed_config=incident_config,
                    new_values={"assigned_to": assigned_to},
                    is_validated=False,
                    used_in_level_2=True,
                    record_sys_id=incident_config["sys_id"],
                    level=self.level,
                ),
            ]
            all_incident_assignments.extend(assign_incidents_subtask)

        config = navigate_to_protocol_subtask + all_incident_assignments

        return config

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        agents_per_category_sys_ids = {
            category: {
                agent_type: agent["sys_id"]
                for agent_type, agent in self.agents_per_category[category].items()
            }
            for category in self.agents_per_category
        }
        for incident_config in self.incident_configs:
            incident_response = table_api_call(
                instance=self.instance,
                table="incident",
                params={
                    "sysparm_query": f"sys_id={incident_config['sys_id']}",
                    "sysparm_fields": "category,assigned_to,priority",
                },
                method="GET",
            )["result"][0]
            if incident_response["category"] != incident_config["category"]:
                raise Exception("Corrupted incident data")
            if not incident_response["assigned_to"]:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"The incident {incident_config['number']} has not been assigned to anyone."
                    },
                )
            if (
                incident_response["assigned_to"]["value"]
                != agents_per_category_sys_ids[incident_response["category"]][
                    self.priorities[int(incident_response["priority"])]["agent_type"]
                ]
            ):
                return (
                    0,
                    False,
                    "",
                    {
                        "message": f"The incident {incident_config['number']} was assigned to an incorrect agent."
                    },
                )
        # Validate final_l3 tasks
        reward, done, message, info = super().validate(page, chat_messages)
        return reward, done, message, info

    def teardown(self) -> None:
        for incident in self.incident_configs:
            db_delete_from_table(
                instance=self.instance, table="incident", sys_id=incident["sys_id"]
            )

        for category in self.agents_per_category.values():
            for agent in category.values():
                db_delete_from_table(
                    instance=self.instance, table="sys_user", sys_id=agent["sys_id"]
                )

        return super().teardown()


class PriorityAssignmentSmallTask(PriorityAssignmentTask, HumanEvalTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 3,
    ) -> None:
        """
        Small version of priority assignment task.
        """
        super().__init__(
            instance=instance,
            level=level,
            num_categories=2,
            fixed_config=fixed_config,
            seed=0,
            prefix="PAS",
        )


class PriorityAssignmentMediumTask(PriorityAssignmentTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 3,
    ) -> None:
        """
        Medium version of priority assignment task.
        """
        super().__init__(
            instance=instance,
            level=level,
            num_categories=3,
            fixed_config=fixed_config,
            seed=seed,
            prefix="PAM",
        )


class PriorityAssignmentLargeTask(PriorityAssignmentTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 3,
    ) -> None:
        """
        Large version of priority assignment task.
        """
        super().__init__(
            instance=instance,
            level=level,
            num_categories=4,
            fixed_config=fixed_config,
            seed=seed,
            prefix="PAL",
        )


__TASKS__ = [
    WorkAssignmentSmallTask,
    WorkAssignmentMediumTask,
    WorkAssignmentLargeTask,
    PriorityAssignmentSmallTask,
    PriorityAssignmentMediumTask,
    PriorityAssignmentLargeTask,
]
