"""
Dashboard retrieval and do action comp tasks
"""

import json
from functools import partial
import random
import numpy as np
from typing import List

from faker import Faker

fake = Faker()

from playwright.sync_api._generated import Page

from .base import CompositionalTask, InfeasibleCompositionalTask, HumanEvalTask
from .utils.infeasible_configs import get_infeasible_service_catalog_config
from ..base import AbstractServiceNowTask
from ..knowledge import KnowledgeBaseSearchTask

from ...api.incident import create_incident
from ...api.report import create_report
from ...api.user import create_user
from ...api.utils import table_api_call, db_delete_from_table
from ...instance import SNowInstance

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.service_catalog import META_CONFIGS


class DashboardRetrieveAndDoTask(CompositionalTask, HumanEvalTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        dashboard_class: AbstractServiceNowTask = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        dashboard_config: dict = None,
        level: int = 2,
    ) -> None:
        """
        Generic task to perform a dashboard retrieval and perform a task.
        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of tuples, each containing a subtask
        dashboard_config: dict
            Configuration to use for the dashboard task.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. Provided by the child class.
        short_description: str
            A short description of the task to be completed. Provided by the child class.
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
        )
        self.used_in_level_2 = self.level == 2
        self.dashboard_config = dashboard_config
        self.task_description = None
        self.short_description = None
        self.dashboard_class = dashboard_class
        self.protocol_name = "Dashboard Retrieve Information and Perform Task"
        self.description_mapping = {
            "max": self.random.choice(["maximum", "highest", "greatest"]),
            "min": self.random.choice(["minimum", "lowest", "least"]),
            "mean": self.random.choice(["mean", "average"]),
            "median": "median",
            "mode": "mode (most frequent)",
        }

    def create_report(self) -> None:
        """
        Create task relevant dashboard report
        """
        raise NotImplementedError

    def set_compositional_task(self) -> None:
        """
        Create and return the compositional task
        """
        raise NotImplementedError

    def get_compositional_task(self) -> list[AbstractServiceNowTask]:
        """
        Return the compositional task
        """
        return self.compositional_task

    def _get_config(self) -> list[AbstractServiceNowTask]:

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

        dashboard_retrieval_subtask = [
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
            # Find the user with the desired config
            self.dashboard_class(
                instance=self.instance,
                seed=None,
                fixed_config=self.dashboard_config,
                is_validated=False,
                used_in_level_2=True,
            ),
        ]

        config = (
            navigate_to_protocol_subtask
            + dashboard_retrieval_subtask
            + self.get_compositional_task()
        )
        return config

    def teardown(self) -> None:
        return super().teardown()


class DashboardRetrieveAndDoInfeasibleTask(InfeasibleCompositionalTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        dashboard_class: AbstractServiceNowTask = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        dashboard_config: dict = None,
        level: int = 2,
    ) -> None:
        """
        Generic task to perform a dashboard retrieval and perform a task.
        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of tuples, each containing a subtask
        dashboard_config: dict
            Configuration to use for the dashboard task.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. Provided by the child class.
        short_description: str
            A short description of the task to be completed. Provided by the child class.
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
        )
        self.used_in_level_2 = self.level == 2
        self.dashboard_config = dashboard_config
        self.task_description = None
        self.short_description = None
        self.dashboard_class = dashboard_class
        self.protocol_name = "Dashboard Retrieve Information and Perform Task"
        self.description_mapping = {
            "max": self.random.choice(["maximum", "highest", "most"]),
            "min": self.random.choice(["minimum", "lowest", "least"]),
            "mean": self.random.choice(["mean", "average"]),
            "median": "median",
            "mode": "mode (most frequent)",
        }

    def create_report(self) -> None:
        """
        Create task relevant dashboard report
        """
        raise NotImplementedError

    def set_compositional_task(self) -> None:
        """
        Create and return the compositional task
        """
        raise NotImplementedError

    def get_compositional_task(self) -> list[AbstractServiceNowTask]:
        """
        Return the compositional task
        """
        return self.compositional_task

    def _get_config(self) -> list[AbstractServiceNowTask]:

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
                has_description=False,
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
                has_description=False,
            ),
        ]

        dashboard_retrieval_subtask = [
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
                has_description=False,
            ),
            # Find the user with the desired config
            self.dashboard_class(
                instance=self.instance,
                seed=None,
                fixed_config=self.dashboard_config,
                is_validated=False,
                used_in_level_2=True,
            ),
        ]

        config = (
            navigate_to_protocol_subtask
            + dashboard_retrieval_subtask
            + self.get_compositional_task()
        )
        return config

    def teardown(self) -> None:
        return super().teardown()


class DashboardRetrieveIncidentAndDoTask(DashboardRetrieveAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_incidents_per_agent: int = 4,
        min_incidents_per_agent: int = 1,
        num_agents: int = 4,
        question: str = "",
        dashboard_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.incident_hashtag = (
            f"#INC{str(id(self) % (10**8)).zfill(9)}"  # identifier to select problems
        )
        self.chart_title = f"Incidents with hashtag {self.incident_hashtag}"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            dashboard_config={
                "url": "/now/nav/ui/classic/params/target/sys_report",
                "chart_title": self.chart_title,
                "question": question,
                "chart_series": "",
            },
            level=level,
            dashboard_class=dashboard_class,
        )
        self.question = question
        self.max_incidents_per_agent = max_incidents_per_agent
        self.min_incidents_per_agent = min_incidents_per_agent
        self.num_agents = num_agents
        if (self.max_incidents_per_agent - self.min_incidents_per_agent) < 2 or self.num_agents < 2:
            raise Exception(
                "The difference between maximum incidents and minimum incidents should be at least two. The number of agents should also be at least 2."
            )
        self.task_description = f"You have to retrieve some information from a dashboard chart based on the description below. The chart presents the number of 'incidents' assigned to different agents. After retrieving the information, you will be asked to use it to complete a task.\n \n"
        self.task_description += f"Title of the report: {self.incident_hashtag}\n\n"
        if self.level == 3:
            self.task_description += f"Referring to the company protocol '{self.protocol_name}' (located in the 'Company Protocols' knowledge base), complete the dashboard retrieval task.\n\n"
        self.short_description = (
            f"Retrieve information from the chart with title {self.incident_hashtag} and perform the mentioned task."
            + "\n For calculations, please round off to the next highest integer if required. If the required calculation has multiple possible answers (for example, 'mode' or 'most frequently' occuring value), please consider the highest value.\n\n"
        )

    def create_report(
        self,
        user_roles=["itil"],
    ) -> None:
        self.agents = {}
        self.agent_sysids = []
        for _ in range(self.num_agents):
            agent_response = create_user(
                instance=self.instance,
                first_name=f"{fake.first_name()}-{fake.first_name()}",
                last_name=f"{fake.last_name()}-{fake.last_name()}",
                return_full_response=True,
                user_roles=user_roles,
            )
            self.agents[agent_response["sys_id"]] = agent_response
            self.agent_sysids.append(agent_response["sys_id"])

        highest_agent = self.agent_sysids[
            -1
        ]  # Choose last agent as the agent with maximum incidents
        self.agents[highest_agent]["num_incidents"] = self.max_incidents_per_agent
        self.agents[highest_agent]["incident_configs"] = []

        lowest_agent = self.agent_sysids[
            0
        ]  # Choose first agent as the agent with minimum incidents
        self.agents[lowest_agent]["num_incidents"] = self.min_incidents_per_agent
        self.agents[lowest_agent]["incident_configs"] = []

        for agent_sysid in self.agent_sysids[1:-1]:
            self.agents[agent_sysid]["num_incidents"] = self.random.randint(
                self.min_incidents_per_agent + 1, self.max_incidents_per_agent - 1
            )
            self.agents[agent_sysid]["incident_configs"] = []

        number_assignments = sum([agent["num_incidents"] for agent in self.agents.values()])

        all_existing_incidents = table_api_call(
            instance=self.instance, table="incident", method="GET"
        )["result"]
        self.all_incident_numbers = [incident["number"] for incident in all_existing_incidents]

        self.new_incident_numbers = []
        for _ in range(number_assignments):
            incident_number = (
                self.prefix
                + str(id(self) % (10**8)).zfill(8)[:4]
                + str(self.random.randint(1000, 9999))
            )
            while (
                incident_number in self.all_incident_numbers
                or incident_number in self.new_incident_numbers
            ):
                incident_number = (
                    self.prefix
                    + str(id(self) % (10**8)).zfill(8)[:4]
                    + str(random.randint(1000, 9999))
                )
            self.new_incident_numbers.append(incident_number)

        incident_number_idx = 0
        for agent, agent_attributes in self.agents.items():
            for _ in range(agent_attributes["num_incidents"]):
                incident_response = create_incident(
                    instance=self.instance,
                    incident_number=self.new_incident_numbers[incident_number_idx],
                    caller_sys_id=self._base_user_sysid,
                    category="software",
                    priority=4,
                    impact=2,  # priority is calculated as some combination of impact and urgency
                    urgency=3,
                    incident_hastag=self.incident_hashtag,
                    assigned_to=agent,
                )
                self.agents[agent]["incident_configs"].append(incident_response)
                incident_number_idx += 1

        self.report_sys_id, _ = create_report(
            instance=self.instance,
            table="incident",
            filter_hashtag=self.incident_hashtag,
            field="assigned_to",
            plot_title=self.chart_title,
            random=self.random,
        )

    def get_agent_values(self, attribute_name, filter_than) -> list[str]:
        agent_values = []
        agent_value_sysids = []
        agent_incidents = [
            agent_attributes["num_incidents"] for agent_attributes in self.agents.values()
        ]

        if self.question == "max":
            agent_value_sysids.append(self.agents[self.agent_sysids[-1]]["sys_id"])
            if attribute_name == "assigned_to":
                agent_full_name = (
                    self.agents[self.agent_sysids[-1]]["first_name"]
                    + " "
                    + self.agents[self.agent_sysids[-1]]["last_name"]
                )
                agent_values.append(agent_full_name)
            elif attribute_name == "first_name":
                agent_first_name = self.agents[self.agent_sysids[-1]]["first_name"]
                agent_values.append(agent_first_name)
            else:
                raise Exception("Filter column not supported.")
        elif self.question == "min":
            agent_value_sysids.append(self.agents[self.agent_sysids[0]]["sys_id"])
            if attribute_name == "assigned_to":
                agent_full_name = (
                    self.agents[self.agent_sysids[0]]["first_name"]
                    + " "
                    + self.agents[self.agent_sysids[0]]["last_name"]
                )
                agent_values.append(agent_full_name)
            elif attribute_name == "first_name":
                agent_first_name = self.agents[self.agent_sysids[0]]["first_name"]
                agent_values.append(agent_first_name)
            else:
                raise Exception("Filter column not supported.")
        elif self.question == "mean" or self.question == "median" or self.question == "mode":
            if self.question == "mean":
                mean_incidents = np.mean(agent_incidents)
                incidents_count = int(np.ceil(mean_incidents))
            elif self.question == "median":
                incidents_count = int(np.ceil(np.median(agent_incidents)))
            elif self.question == "mode":
                # We select the maximum value if there are two or more modes
                frequencies = {}
                for count in agent_incidents:
                    if count not in frequencies:
                        frequencies[count] = 1
                    else:
                        frequencies[count] += 1
                sorted_frequencies = {
                    count: frequency
                    for count, frequency in sorted(
                        frequencies.items(), key=lambda item: item[1], reverse=True
                    )
                }
                max_frequency = list(sorted_frequencies.values())[0]
                max_frequencies = [
                    count
                    for count, frequency in sorted_frequencies.items()
                    if frequency == max_frequency
                ]
                incidents_count = int(max(max_frequencies))

            for agent_sysid, agent_attributes in self.agents.items():
                if (
                    filter_than == "greater"
                    and agent_attributes["num_incidents"] >= incidents_count
                ) or (
                    filter_than == "lesser" and agent_attributes["num_incidents"] <= incidents_count
                ):
                    agent_value_sysids.append(agent_sysid)
                    if attribute_name == "assigned_to":
                        agent_full_name = (
                            agent_attributes["first_name"] + " " + agent_attributes["last_name"]
                        )
                        agent_values.append(agent_full_name)

                    elif attribute_name == "first_name":
                        agent_first_name = agent_attributes["first_name"]
                        agent_values.append(agent_first_name)
                    else:
                        raise Exception("Filter column not supported.")
        else:
            raise Exception("Unsopprted question type.")

        return agent_values, agent_value_sysids

    def set_compositional_task(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        # Delete the report
        db_delete_from_table(
            instance=self.instance,
            table="sys_report",
            sys_id=self.report_sys_id,
        )
        # Delete the incidents and users
        for agent_sys_id in self.agents:
            for incident in self.agents[agent_sys_id]["incident_configs"]:
                db_delete_from_table(
                    instance=self.instance,
                    table="incident",
                    sys_id=incident["sys_id"],
                )
            db_delete_from_table(
                instance=self.instance,
                table="sys_user",
                sys_id=agent_sys_id,
            )
        return super().teardown()


class DashboardRetrieveIncidentAndDoInfeasibleTask(DashboardRetrieveAndDoInfeasibleTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_incidents_per_agent: int = 4,
        min_incidents_per_agent: int = 1,
        num_agents: int = 4,
        question: str = "",
        dashboard_class: AbstractServiceNowTask = None,
        function: callable = None,
        provide_reason: bool = True,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.incident_hashtag = (
            f"#INC{str(id(self) % (10**8)).zfill(9)}"  # identifier to select problems
        )
        self.chart_title = f"Incidents with hashtag {self.incident_hashtag}"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            dashboard_config={
                "url": "/now/nav/ui/classic/params/target/sys_report",
                "chart_title": self.chart_title,
                "question": question,
                "chart_series": "",
            },
            level=level,
            dashboard_class=dashboard_class,
        )
        self.question = question
        self.max_incidents_per_agent = max_incidents_per_agent
        self.min_incidents_per_agent = min_incidents_per_agent
        self.num_agents = num_agents
        if (self.max_incidents_per_agent - self.min_incidents_per_agent) < 2 or self.num_agents < 2:
            raise Exception(
                "The difference between maximum incidents and minimum incidents should be at least two. The number of agents should also be at least 2."
            )
        self.task_description = f"Retrieve the information mentioned in the following description from the report of the incidents with the title {self.incident_hashtag}. Using the information, follow the subsequent task steps mentioned. For all calculations, round of to the next highest integer first. For multiple modes, choose the highest value.\n"
        if self.level == 3:
            self.task_description += f"Follow the '{self.protocol_name}' protocol from the knowledge base for extra instructions.\n"
        self.short_description = "Retrieve incident information and perform the mentioned task"
        self.function = partial(function, provide_reason=provide_reason)

    def create_report(
        self,
        user_roles=["itil"],
    ) -> None:
        self.agents = {}
        self.agent_sysids = []
        for _ in range(self.num_agents):
            agent_response = create_user(
                instance=self.instance,
                first_name=f"{fake.first_name()}-{fake.first_name()}",
                last_name=f"{fake.last_name()}-{fake.last_name()}",
                return_full_response=True,
                user_roles=user_roles,
            )
            self.agents[agent_response["sys_id"]] = agent_response
            self.agent_sysids.append(agent_response["sys_id"])

        highest_agent = self.agent_sysids[
            -1
        ]  # Choose last agent as the agent with maximum incidents
        self.agents[highest_agent]["num_incidents"] = self.max_incidents_per_agent
        self.agents[highest_agent]["incident_configs"] = []

        lowest_agent = self.agent_sysids[
            0
        ]  # Choose first agent as the agent with minimum incidents
        self.agents[lowest_agent]["num_incidents"] = self.min_incidents_per_agent
        self.agents[lowest_agent]["incident_configs"] = []

        for agent_sysid in self.agent_sysids[1:-1]:
            self.agents[agent_sysid]["num_incidents"] = self.random.randint(
                self.min_incidents_per_agent + 1, self.max_incidents_per_agent - 1
            )
            self.agents[agent_sysid]["incident_configs"] = []

        number_assignments = sum([agent["num_incidents"] for agent in self.agents.values()])

        all_existing_incidents = table_api_call(
            instance=self.instance, table="incident", method="GET"
        )["result"]
        self.all_incident_numbers = [incident["number"] for incident in all_existing_incidents]

        self.new_incident_numbers = []
        for _ in range(number_assignments):
            incident_number = (
                self.prefix + str(id(self) % (10**8)).zfill(8)[:4] + str(random.randint(1000, 9999))
            )
            while (
                incident_number in self.all_incident_numbers
                or incident_number in self.new_incident_numbers
            ):
                incident_number = (
                    self.prefix
                    + str(id(self) % (10**8)).zfill(8)[:4]
                    + str(random.randint(1000, 9999))
                )
            self.new_incident_numbers.append(incident_number)

        incident_number_idx = 0
        for agent, agent_attributes in self.agents.items():
            for _ in range(agent_attributes["num_incidents"]):
                incident_response = create_incident(
                    instance=self.instance,
                    incident_number=self.new_incident_numbers[incident_number_idx],
                    caller_sys_id=self._base_user_sysid,
                    category="software",
                    priority=4,
                    impact=2,  # priority is calculated as some combination of impact and urgency
                    urgency=3,
                    incident_hastag=self.incident_hashtag,
                    assigned_to=agent,
                )
                self.agents[agent]["incident_configs"].append(incident_response)
                incident_number_idx += 1

        self.report_sys_id, _ = create_report(
            instance=self.instance,
            table="incident",
            filter_hashtag=self.incident_hashtag,
            field="assigned_to",
            plot_title=self.chart_title,
            random=self.random,
        )

    def get_agent_values(self, attribute_name, filter_than) -> list[str]:
        agent_values = []
        agent_value_sysids = []
        agent_incidents = [
            agent_attributes["num_incidents"] for agent_attributes in self.agents.values()
        ]

        if self.question == "max":
            agent_value_sysids.append(self.agents[self.agent_sysids[-1]]["sys_id"])
            if attribute_name == "assigned_to":
                agent_full_name = (
                    self.agents[self.agent_sysids[-1]]["first_name"]
                    + " "
                    + self.agents[self.agent_sysids[-1]]["last_name"]
                )
                agent_values.append(agent_full_name)
            elif attribute_name == "first_name":
                agent_first_name = self.agents[self.agent_sysids[-1]]["first_name"]
                agent_values.append(agent_first_name)
            else:
                raise Exception("Filter column not supported.")
        elif self.question == "min":
            agent_value_sysids.append(self.agents[self.agent_sysids[0]]["sys_id"])
            if attribute_name == "assigned_to":
                agent_full_name = (
                    self.agents[self.agent_sysids[0]]["first_name"]
                    + " "
                    + self.agents[self.agent_sysids[0]]["last_name"]
                )
                agent_values.append(agent_full_name)
            elif attribute_name == "first_name":
                agent_first_name = self.agents[self.agent_sysids[0]]["first_name"]
                agent_values.append(agent_first_name)
            else:
                raise Exception("Filter column not supported.")
        elif self.question == "mean" or self.question == "median" or self.question == "mode":
            if self.question == "mean":
                mean_incidents = np.mean(agent_incidents)
                incidents_count = int(np.ceil(mean_incidents))
            elif self.question == "median":
                incidents_count = int(np.ceil(np.median(agent_incidents)))
            elif self.question == "mode":
                # We select the maximum value if there are two or more modes
                frequencies = {}
                for count in agent_incidents:
                    if count not in frequencies:
                        frequencies[count] = 1
                    else:
                        frequencies[count] += 1
                sorted_frequencies = {
                    count: frequency
                    for count, frequency in sorted(
                        frequencies.items(), key=lambda item: item[1], reverse=True
                    )
                }
                max_frequency = list(sorted_frequencies.values())[0]
                max_frequencies = [
                    count
                    for count, frequency in sorted_frequencies.items()
                    if frequency == max_frequency
                ]
                incidents_count = int(max(max_frequencies))

            for agent_sysid, agent_attributes in self.agents.items():
                if (
                    filter_than == "greater"
                    and agent_attributes["num_incidents"] >= incidents_count
                ) or (
                    filter_than == "lesser" and agent_attributes["num_incidents"] <= incidents_count
                ):
                    agent_value_sysids.append(agent_sysid)
                    if attribute_name == "assigned_to":
                        agent_full_name = (
                            agent_attributes["first_name"] + " " + agent_attributes["last_name"]
                        )
                        agent_values.append(agent_full_name)

                    elif attribute_name == "first_name":
                        agent_first_name = agent_attributes["first_name"]
                        agent_values.append(agent_first_name)
                    else:
                        raise Exception("Filter column not supported.")
        else:
            raise Exception("Unsopprted question type.")

        return agent_values, agent_value_sysids

    def set_compositional_task(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        # Delete the report
        db_delete_from_table(
            instance=self.instance,
            table="sys_report",
            sys_id=self.report_sys_id,
        )
        # Delete the incidents and users
        for agent_sys_id in self.agents:
            for incident in self.agents[agent_sys_id]["incident_configs"]:
                db_delete_from_table(
                    instance=self.instance,
                    table="incident",
                    sys_id=incident["sys_id"],
                )
            db_delete_from_table(
                instance=self.instance,
                table="sys_user",
                sys_id=agent_sys_id,
            )
        return super().teardown()


class DashboardRetrieveCatalogAndDoTask(DashboardRetrieveAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_items: int = 5,
        min_items: int = 3,
        question: str = "",
        dashboard_class: AbstractServiceNowTask = None,
        min_catalog_item: str = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.catalog_hashtag = (
            f"#CAT{str(id(self) % (10**8)).zfill(9)}"  # identifier to select problems
        )
        self.chart_title = f"Catalog with hashtag {self.catalog_hashtag}"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            dashboard_config={
                "url": "/now/nav/ui/classic/params/target/sys_report",
                "chart_title": self.chart_title,
                "question": question,
                "chart_series": "",
            },
            level=level,
            dashboard_class=dashboard_class,
        )
        self.question = question
        self.max_number_per_item = self.random.choice([5, 6, 7])
        self.min_number_per_item = self.random.choice([1, 2])
        self.max_items = max_items
        self.min_items = min_items
        if self.max_items < 2 or self.min_items < 2:
            raise Exception("The items allowed should at least be 2.")
        self.min_catalog_item = min_catalog_item
        self.task_description = f"You have to retrieve some information from a dashboard chart based on the description below. The chart presents the number of 'hardware items' available in stock. After retrieving the information, you will be asked to use it to complete a task.\n \n"
        self.task_description += f"Title of the report: {self.catalog_hashtag}\n\n"
        if self.level == 3:
            self.task_description += f"Referring to the company protocol '{self.protocol_name}' (located in the 'Company Protocols' knowledge base), complete the dashboard retrieval task.\n\n"
        self.short_description = (
            f"Retrieve information from the chart with the title {self.catalog_hashtag} and perform the mentioned task."
            + "\nFor calculations, please round off to the next highest integer if required. If the required calculation has multiple possible answers (for example, 'mode' or 'most frequently' occuring value), please consider the highest value.\n\n"
        )

    def get_catalog_item_sysid(self, catalog_item: str) -> str:
        catalog_item_response = table_api_call(
            instance=self.instance,
            table="sc_cat_item",
            params={"sysparm_query": f"sys_name={catalog_item}", "sysparm_fields": "sys_id"},
            method="GET",
        )["result"]
        if len(catalog_item_response) == 0:
            raise Exception("Catalog item not found.")
        elif len(catalog_item_response) > 1:
            raise Exception("Multiple catalog items found.")
        return catalog_item_response[0]["sys_id"]

    def create_report(
        self,
        user_roles=["itil"],
    ) -> None:
        catalog_item_list = list(META_CONFIGS.keys())
        catalog_item_list.remove(self.min_catalog_item)
        random_service_catalog_items = self.random.choice(
            catalog_item_list, self.random.randint(self.min_items, self.max_items), replace=False
        ).tolist()
        cat_item_sys_name = {
            "Developer Laptop (Mac)": "Developer Laptop (Mac)",
            "iPad mini": "iPad mini",
            "iPad pro": "iPad pro",
            "Sales Laptop": "Sales Laptop",
            "Standard Laptop": "Standard Laptop",
            "Apple Watch": "Apple Watch",
            "Apple MacBook Pro 15": 'Apple MacBook Pro 15"',
            "Development Laptop (PC)": "Development Laptop (PC)",
            "Loaner Laptop": "Notebook Computer Loaner",
        }

        # shuffle
        self.random.shuffle(random_service_catalog_items)
        self.random_service_catalog_items = random_service_catalog_items
        random_service_catalog_items = [self.min_catalog_item] + random_service_catalog_items

        service_catalog_report_config = {}
        service_catalog_report_config[random_service_catalog_items[0]] = {
            "quantity": self.min_number_per_item,
            "description": META_CONFIGS[random_service_catalog_items[0]]["desc"],
            "configuration": {},
            "item": random_service_catalog_items[0],
            "sys_id": self.get_catalog_item_sysid(
                cat_item_sys_name[random_service_catalog_items[0]]
            ),
        }
        service_catalog_report_config[random_service_catalog_items[-1]] = {
            "quantity": self.max_number_per_item,
            "description": META_CONFIGS[random_service_catalog_items[-1]]["desc"],
            "configuration": {},
            "item": random_service_catalog_items[-1],
            "sys_id": self.get_catalog_item_sysid(
                cat_item_sys_name[random_service_catalog_items[-1]]
            ),
        }

        for service_catalog_item in random_service_catalog_items[1:-1]:
            service_catalog_report_config[service_catalog_item] = {
                "quantity": self.random.randint(
                    self.min_number_per_item + 1, self.max_number_per_item - 1
                ),
                "description": META_CONFIGS[service_catalog_item]["desc"],
                "configuration": {},
                "item": service_catalog_item,
                "sys_id": self.get_catalog_item_sysid(cat_item_sys_name[service_catalog_item]),
            }

        self.service_catalog_report_config = service_catalog_report_config
        created_request_items = []
        for (
            service_catalog_item,
            service_catalog_item_config,
        ) in service_catalog_report_config.items():
            for _ in range(service_catalog_item_config["quantity"]):
                request_item_dict = {
                    "requested_for": self._base_user_sysid,
                    "quantity": 1,
                    "cat_item": service_catalog_item_config["sys_id"],
                }
                criteria_response = table_api_call(
                    instance=self.instance,
                    table="sc_req_item",
                    json=request_item_dict,
                    method="POST",
                )["result"]
                created_request_items.append((service_catalog_item, criteria_response["sys_id"]))

        self.created_request_items = created_request_items

        user_details = table_api_call(
            instance=self.instance,
            table="sys_user",
            params={
                "sysparm_query": f"sys_id={self._base_user_sysid}",
                "sysparm_fields": "first_name,last_name",
            },
            method="GET",
        )["result"][0]
        user_full_name = user_details["first_name"] + " " + user_details["last_name"]

        self.report_sys_id, _ = create_report(
            instance=self.instance,
            table="sc_req_item",
            filter_hashtag=user_full_name,
            filter_field="requested_for",
            field="cat_item",
            plot_title=self.chart_title,
            random=self.random,
        )

    def get_order_quantity_value(self) -> list[str]:
        quantities = [
            service_catalog_report_config_attribute["quantity"]
            for service_catalog_report_config_attribute in self.service_catalog_report_config.values()
        ]
        if self.question == "max":
            if max(quantities) != self.max_number_per_item:
                raise Exception("Maximum of quantities does not match attribute. Please check.")
            target_quantity = self.max_number_per_item
        elif self.question == "mean":
            mean_quantity = np.mean(quantities)
            target_quantity = int(np.ceil(mean_quantity))
        elif self.question == "median":
            target_quantity = int(np.ceil(np.median(quantities)))
        elif self.question == "mode":
            frequencies = {}
            for count in quantities:
                if count not in frequencies:
                    frequencies[count] = 1
                else:
                    frequencies[count] += 1
            sorted_frequencies = {
                count: frequency
                for count, frequency in sorted(
                    frequencies.items(), key=lambda item: item[1], reverse=True
                )
            }
            max_frequency = list(sorted_frequencies.values())[0]
            max_frequencies = [
                count
                for count, frequency in sorted_frequencies.items()
                if frequency == max_frequency
            ]
            target_quantity = int(max(max_frequencies))
        if target_quantity - self.min_number_per_item <= 0:
            raise Exception("Unable to order quantity {target_quantity - self.min_number_per_item}")
        return int(target_quantity - self.min_number_per_item)

    def set_compositional_task(self) -> None:

        order_config = {
            "configuration": {},
            "description": META_CONFIGS[self.min_catalog_item]["desc"],
            "item": self.min_catalog_item,
            "quantity": self.get_order_quantity_value(),
        }

        create_order_item_subtask = [
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Service Catalog",
                    "url": "/now/nav/ui/classic/params/target/catalog_home.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            self.order_item_class(
                instance=self.instance,
                fixed_config=order_config,
                is_validated=True,
                used_in_level_2=True,
            ),
        ]

        self.compositional_task = create_order_item_subtask

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()
        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()

        if self.level == 3:
            self.task_description = (
                self.task_description
                + f"\t - Please retrieve the '{self.description_mapping[self.question]}' value of all the items in stock.\n\n"
                + f"\t - Task: Place an order for the least available item in stock. The quantity of the order should be such that the final quantity of this item matches the above retrieved value.\n"
                + f"\t   For example, consider the above task asks you to retrieve the maximum number of items in stock, say 4, and the least available item is an Apple Watch and its quantity is 1. You have to order 3 more Apple Watches.\n\n"
                + f"\t - Please do not change any other configuration while placing the order for the item. You can find important links to the pages in the protocol article.\n\n"
                + self.final_private_task_instructions
            )

        goal, info = super().setup_goal(
            page=page, config=config, build_pretty_print_description=False
        )

        if self.level == 2:
            goal = (
                self.short_description
                + f"\n1. Navigate to the Reports > View/Run page.\n"
                + f"\n2. Given the title of the report, search for it on this page.\n"
                + f"\n3. Find the value which is the {self.description_mapping[self.question]} of the items present in stock as per the chart. Also remember the least available item in the stock.\n"
                + f"\n4. Navigate to Self-Service > Service Catalog. \n"
                + f"\n5. For the least available item in stock, place an order for extra items such that its quantity matches the value you found."
                + "\nFor example, if you were requested to find the maximum value across the items, you would place an order for the least available item such that its NEW quantity matches this number. Please do not change any 'configuration' when placing the order.\n"
            )

        return goal, info

    def teardown(self) -> None:
        # Delete the report
        db_delete_from_table(
            instance=self.instance,
            table="sys_report",
            sys_id=self.report_sys_id,
        )
        # Delete the request items
        for created_request_item in self.created_request_items:
            db_delete_from_table(
                instance=self.instance,
                table="sc_req_item",
                sys_id=created_request_item[1],
            )
        return super().teardown()


class DashboardRetrieveCatalogAndDoInfeasibleTask(DashboardRetrieveAndDoInfeasibleTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        max_items: int = 5,
        min_items: int = 3,
        question: str = "",
        dashboard_class: AbstractServiceNowTask = None,
        min_catalog_item: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.catalog_hashtag = (
            f"#CAT{str(id(self) % (10**8)).zfill(9)}"  # identifier to select problems
        )
        self.chart_title = f"Catalog with hashtag {self.catalog_hashtag}"
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            dashboard_config={
                "url": "/now/nav/ui/classic/params/target/sys_report",
                "chart_title": self.chart_title,
                "question": question,
                "chart_series": "",
            },
            level=level,
            dashboard_class=dashboard_class,
        )
        self.question = question
        self.max_number_per_item = self.random.choice([5, 6, 7])
        self.min_number_per_item = self.random.choice([1, 2])
        self.max_items = max_items
        self.min_items = min_items
        if self.max_items < 2 or self.min_items < 2:
            raise Exception("The items allowed should at least be 2.")
        self.task_description = f"Retrieve the information mentioned in the following description from the report of the catalogs with the title {self.catalog_hashtag}. Using the information, follow the subsequent task steps mentioned. For all calculations, round of to the next highest integer first. For multiple modes, choose the highest value.\n"
        if self.level == 3:
            self.task_description += f"Follow the '{self.protocol_name}' protocol from the knowledge base for extra instructions.\n"
        self.short_description = "Retrieve catalog information and perform the mentioned task"
        self.min_catalog_item = min_catalog_item
        self.function = partial(
            get_infeasible_service_catalog_config, provide_reason=provide_reason
        )
        self.all_configs = self.all_configs()

    @classmethod
    def all_configs(cls) -> List[dict]:
        with open(cls.config_path, "r") as f:
            return json.load(f)

    def get_catalog_item_sysid(self, catalog_item: str) -> str:
        catalog_item_response = table_api_call(
            instance=self.instance,
            table="sc_cat_item",
            params={"sysparm_query": f"sys_name={catalog_item}", "sysparm_fields": "sys_id"},
            method="GET",
        )["result"]
        if len(catalog_item_response) == 0:
            raise Exception("Catalog item not found.")
        elif len(catalog_item_response) > 1:
            raise Exception("Multiple catalog items found.")
        return catalog_item_response[0]["sys_id"]

    def create_report(
        self,
        user_roles=["itil"],
    ) -> None:
        catalog_item_list = list(META_CONFIGS.keys())
        catalog_item_list.remove(self.min_catalog_item)
        random_service_catalog_items = self.random.choice(
            catalog_item_list, self.random.randint(self.min_items, self.max_items), replace=False
        ).tolist()
        cat_item_sys_name = {
            "Developer Laptop (Mac)": "Developer Laptop (Mac)",
            "iPad mini": "iPad mini",
            "iPad pro": "iPad pro",
            "Sales Laptop": "Sales Laptop",
            "Standard Laptop": "Standard Laptop",
            "Apple Watch": "Apple Watch",
            "Apple MacBook Pro 15": 'Apple MacBook Pro 15"',
            "Development Laptop (PC)": "Development Laptop (PC)",
            "Loaner Laptop": "Notebook Computer Loaner",
        }

        # shuffle
        self.random.shuffle(random_service_catalog_items)
        random_service_catalog_items = [
            self.min_catalog_item
        ] + random_service_catalog_items.tolist()
        self.random_service_catalog_items = random_service_catalog_items

        service_catalog_report_config = {}
        service_catalog_report_config[random_service_catalog_items[0]] = {
            "quantity": self.min_number_per_item,
            "description": META_CONFIGS[random_service_catalog_items[0]]["desc"],
            "configuration": {},
            "item": random_service_catalog_items[0],
            "sys_id": self.get_catalog_item_sysid(
                cat_item_sys_name[random_service_catalog_items[0]]
            ),
        }
        service_catalog_report_config[random_service_catalog_items[-1]] = {
            "quantity": self.max_number_per_item,
            "description": META_CONFIGS[random_service_catalog_items[-1]]["desc"],
            "configuration": {},
            "item": random_service_catalog_items[-1],
            "sys_id": self.get_catalog_item_sysid(
                cat_item_sys_name[random_service_catalog_items[-1]]
            ),
        }

        for service_catalog_item in random_service_catalog_items[1:-1]:
            service_catalog_report_config[service_catalog_item] = {
                "quantity": self.random.randint(
                    self.min_number_per_item + 1, self.max_number_per_item - 1
                ),
                "description": META_CONFIGS[service_catalog_item]["desc"],
                "configuration": {},
                "item": service_catalog_item,
                "sys_id": self.get_catalog_item_sysid(cat_item_sys_name[service_catalog_item]),
            }

        self.service_catalog_report_config = service_catalog_report_config
        created_request_items = []
        for (
            service_catalog_item,
            service_catalog_item_config,
        ) in service_catalog_report_config.items():
            for _ in range(service_catalog_item_config["quantity"]):
                request_item_dict = {
                    "requested_for": self._base_user_sysid,
                    "quantity": 1,
                    "cat_item": service_catalog_item_config["sys_id"],
                }
                criteria_response = table_api_call(
                    instance=self.instance,
                    table="sc_req_item",
                    json=request_item_dict,
                    method="POST",
                )["result"]
                created_request_items.append((service_catalog_item, criteria_response["sys_id"]))

        self.created_request_items = created_request_items

        user_details = table_api_call(
            instance=self.instance,
            table="sys_user",
            params={
                "sysparm_query": f"sys_id={self._base_user_sysid}",
                "sysparm_fields": "first_name,last_name",
            },
            method="GET",
        )["result"][0]
        user_full_name = user_details["first_name"] + " " + user_details["last_name"]

        self.report_sys_id, _ = create_report(
            instance=self.instance,
            table="sc_req_item",
            filter_hashtag=user_full_name,
            filter_field="requested_for",
            field="cat_item",
            plot_title=self.chart_title,
            random=self.random,
        )

    def get_order_quantity_value(self) -> list[str]:
        quantities = [
            service_catalog_report_config_attribute["quantity"]
            for service_catalog_report_config_attribute in self.service_catalog_report_config.values()
        ]
        if self.question == "max":
            if max(quantities) != self.max_number_per_item:
                raise Exception("Maximum of quantities does not match attribute. Please check.")
            target_quantity = self.max_number_per_item
        elif self.question == "mean":
            mean_quantity = np.mean(quantities)
            target_quantity = int(np.ceil(mean_quantity))
        elif self.question == "median":
            target_quantity = int(np.ceil(np.median(quantities)))
        elif self.question == "mode":
            frequencies = {}
            for count in quantities:
                if count not in frequencies:
                    frequencies[count] = 1
                else:
                    frequencies[count] += 1
            sorted_frequencies = {
                count: frequency
                for count, frequency in sorted(
                    frequencies.items(), key=lambda item: item[1], reverse=True
                )
            }
            max_frequency = list(sorted_frequencies.values())[0]
            max_frequencies = [
                count
                for count, frequency in sorted_frequencies.items()
                if frequency == max_frequency
            ]
            target_quantity = int(max(max_frequencies))
        if target_quantity - self.min_number_per_item <= 0:
            raise Exception("Unable to order quantity {target_quantity - self.min_number_per_item}")
        return int(target_quantity - self.min_number_per_item)

    def set_compositional_task(self) -> None:

        config = self.random.choice(self.all_configs)
        self.configuration = config["configuration"]
        order_config = {
            "configuration": self.configuration,
            "description": META_CONFIGS[self.min_catalog_item]["desc"],
            "item": self.min_catalog_item,
            "quantity": self.get_order_quantity_value(),
        }
        order_config, self.infeasible_reasons = self.function(
            config=order_config, random=self.random
        )

        create_order_item_subtask = [
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Service Catalog",
                    "url": "/now/nav/ui/classic/params/target/catalog_home.do",
                },
                is_validated=False,
                used_in_level_2=True,
                has_description=False,
            ),
            self.order_item_class(
                instance=self.instance,
                fixed_config=order_config,
                is_validated=False,
                used_in_level_2=True,
            ),
        ]

        self.compositional_task = create_order_item_subtask

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.create_report()
        self.set_compositional_task()
        config = self.fixed_config if self.fixed_config else self._get_config()
        if self.level == 3:
            self.task_description = (
                self.task_description
                + f"Value to retrieve: {self.description_mapping[self.question]} of all the catalog items.\n"
                + f"Task: Place an order for requesting more of the least available item in the report. The quantity of the order should be such that the final quantity of this item matches the above retrieved value.\n\n"
                + self.final_private_task_instructions
            )

        goal, info = super().setup_goal(
            page=page, config=config, build_pretty_print_description=False
        )

        if self.level == 2:
            goal = (
                self.task_description
                + f"\n1. Navigate to the CMDB reports and look for the catalog report with the mentioned hashtag. \n"
                + f"\n2. Find the value which is the {self.description_mapping[self.question]} of the catalog items present in stock shown in the report. \n"
                + f"\n3. Navigate to Self-Service  > Service Catalog. \n"
                + f"\n4. For the least available item in stock, place an order for extra items such that its quantity matches the value you found.\n"
            )

        return goal, info

    def teardown(self) -> None:
        # Delete the report
        db_delete_from_table(
            instance=self.instance,
            table="sys_report",
            sys_id=self.report_sys_id,
        )
        # Delete the request items
        for created_request_item in self.created_request_items:
            db_delete_from_table(
                instance=self.instance,
                table="sc_req_item",
                sys_id=created_request_item[1],
            )
        return super().teardown()


class DashDoFinalTask:
    """Base class for dash do final tasks block tasks. Used to include these tasks across multiple superclasses."""

    pass
