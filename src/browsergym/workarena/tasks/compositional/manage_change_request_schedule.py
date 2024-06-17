import re

from datetime import datetime, timedelta
from faker import Faker
from typing import List, Tuple

fake = Faker()

from playwright.sync_api._generated import Page

from browsergym.workarena.tasks.form import (
    EditChangeRequestScheduleTask,
)

from .base import HumanEvalTask
from .filter_and_do import FilterAndDoTask

from ..base import AbstractServiceNowTask

from ...api.change_request import create_change_request
from ...api.utils import table_api_call, db_delete_from_table
from ...config import (
    # Expected columns for the different lists
    EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
)
from ...instance import SNowInstance


class ManageChangeRequestScheduleTask(FilterAndDoTask):
    """Task to schedule change requests.
    Args:

    goal_type: str
        The type of goal to set. Choices are "base", "priority", "tight", "tight priority". Used for validation
    wide_schedule: bool
        Whether or not the change requests should be scheduled in a 'wide' schedule. If set to True, the change requests
        will have a period of 2 longer than the optimal schedule to be fitted in. Otherwise, they will have
        a period of 2 days longer than the optimal schedule.
    uniform_risk: bool
        whether to use uniform risk for the change requests. The risk is between 2 (high) and 4 (low) and sets the
        duration of the change request (high) risk=2 -> 3 days, (medium) risk=3 -> 2 days, (low) risk=4 -> 1 day
    num_change_requests: int
        The number of change requests to create a schedule for
    pre_existing_schedule: bool
        Whether to create a pre-existing schedule for the change requests. If set to True, the change requests created
        will all overlap and have durations of one day.
    """

    # mapping between risk and duration
    risk_to_duration = {2: 3, 3: 2, 4: 1}

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        goal_type: str = "base",
        wide_schedule: bool = False,
        uniform_risk: bool = True,
        num_change_requests: int = 2,
        pre_existing_schedule: bool = False,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "module": "All",
                "application": "Change",
            },
            level=level,
            protocol_name="Scheduling Your Change Requests",
        )
        self.goal_type = goal_type
        self.wide_schedule = wide_schedule
        self.uniform_risk = uniform_risk
        self.num_change_requests = num_change_requests
        self.pre_existing_schedule = pre_existing_schedule
        self.change_request_sys_ids = []
        self.change_request_numbers = []
        self.change_request_impacts = [2] * num_change_requests  # Medium priorities by default

        # start and end dates of the schedule
        self.schedule_start_date = fake.date_time_this_decade(
            after_now=True, before_now=False, tzinfo=None
        ).replace(microsecond=0)
        self.schedule_end_date = None
        self.schedule_bounds_goal = None  # Part of the goal to append at the end of the goal to indicate the start and end of the schedule. Used in L2 tasks

        if self.uniform_risk:
            self.risks = [4] * num_change_requests
        else:
            self.risks = list(self.random.randint(2, 4, num_change_requests))

        self.change_request_hashtag = "#SERIES-" + self.unique_id[:10]
        if not self.pre_existing_schedule:
            schedule_type = "tight schedule" if "tight" in self.goal_type else "schedule"
            self.short_description = f"Scheduling Your Change Requests"
            self.task_description = f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) create a {schedule_type} for your change requests for those with hashtag {self.change_request_hashtag}.'
        else:
            self.short_description = f"Re-scheduling Your Change Requests"
            self.task_description = f'The schedule for your change requests with hashtag {self.change_request_hashtag} is currently broken. Please refer to company protocol "{self.protocol_name}" (located in the company protocols knowledge base) to fix it.'
            if "tight" in self.goal_type:
                self.task_description += " The change requests should be scheduled according to the tight schedule setting."
        self.tasks = []

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        goal, info = super().setup_goal(page=page)

        if self.level == 2:
            goal += self.schedule_bounds_goal

        return goal, info

    def _setup_list(self) -> None:
        self.filter_config = {
            "list_url": "/now/nav/ui/classic/params/target/change_request_list.do",
            "expected_fields_path": EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
            "filter_columns": [
                "short_description",
            ],
            "filter_kind": "AND",
            "filter_operators": ["contains"],
            "filter_values": [
                f"{self.change_request_hashtag}",
            ],
        }
        self.change_request_impacts.sort()  # Sort the impacts to make sure the the top impact requests are scheduled first

        start_date = self.schedule_start_date

        for risk, impact in zip(self.risks, self.change_request_impacts):
            if self.pre_existing_schedule:
                change_request_start_date = start_date + timedelta(hours=self.random.randint(1, 4))
                change_request_end_date = change_request_start_date + timedelta(days=1)
            else:
                change_request_start_date = ""
                change_request_end_date = ""
            change_request_sys_id, change_request_number = create_change_request(
                instance=self.instance,
                user_sys_id=self._base_user_sysid,
                risk=risk,
                start_date=str(change_request_start_date),
                end_date=str(change_request_end_date),
                impact=impact,
                hashtag=self.change_request_hashtag,
                random=self.random,
            )
            self.change_request_sys_ids.append(change_request_sys_id)
            self.change_request_numbers.append(change_request_number)

        for i, risk in enumerate(self.risks):
            skip_description = i > 0
            duration = self.risk_to_duration[risk]
            end_date = start_date + timedelta(days=duration)
            self.tasks.append(
                EditChangeRequestScheduleTask(
                    instance=self.instance,
                    is_validated=False,
                    used_in_level_2=True,
                    record_sys_id=self.change_request_sys_ids[i],
                    record_number=self.change_request_numbers[i],
                    # Here the values will only be used by the cheat; the goal will be over-ridden to explain the task
                    # at a high level only; see the get_pretty_printed_description method
                    new_values={"start_date": str(start_date), "end_date": str(end_date)},
                    level=self.level,
                    goal_type=self.goal_type,
                    skip_description=skip_description,
                )
            )
            start_date = end_date + timedelta(minutes=1)

        if self.wide_schedule:
            self.schedule_end_date = end_date + timedelta(weeks=2)
        else:
            self.schedule_end_date = end_date + timedelta(days=2)

        self.schedule_bounds_goal = f" All the change requests should be scheduled between {self.schedule_start_date} and {self.schedule_end_date}, inclusively. "
        # Add the schedule bounds to the task description
        self.task_description += self.schedule_bounds_goal

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        change_requests = table_api_call(
            instance=self.instance,
            table="change_request",
            params={
                "sysparm_query": f"short_descriptionLIKE{self.change_request_hashtag}",
                "sysparm_fields": "impact,start_date,end_date,risk",
            },
        )["result"]
        change_requests = sorted(change_requests, key=lambda x: x["start_date"])

        # max difference is 1 day if not tight, 1 hour if tight
        max_difference = 1 if self.goal_type == "tight" else 24

        for i, change_request in enumerate(change_requests):
            # Check that the change request has start/end dates
            if (
                not change_request["start_date"]
                or not change_request["end_date"]
                or (i > 0 and not change_requests[i - 1]["end_date"])
            ):
                return (
                    0,
                    False,
                    "",
                    {"message": "Change request start date or end date is missing."},
                )
            # Confirm that the change request has appropriate duration (within 20% of expected duration)
            current_start_date = datetime.strptime(
                change_request["start_date"], "%Y-%m-%d %H:%M:%S"
            )
            current_end_date = datetime.strptime(change_request["end_date"], "%Y-%m-%d %H:%M:%S")

            # Check that the bounds of the schedule are respected
            if (
                current_start_date < self.schedule_start_date
                or current_end_date > self.schedule_end_date
            ):
                return (
                    0,
                    False,
                    "",
                    {
                        "message": "Change request start date or end date is outside of the target schedule."
                    },
                )

            difference = current_end_date - current_start_date
            # Expected duration is 3 days for high risk, 2 days for medium risk, 1 day for low risk
            duration = self.risk_to_duration[int(change_request["risk"])]
            expected_duration = timedelta(days=duration)

            if difference < expected_duration * 0.95 or difference > expected_duration * 1.05:
                return (
                    0,
                    False,
                    "",
                    {
                        "message": "Change request duration is not within 5% of the expected duration."
                    },
                )

            if i == 0:
                continue
            # Confirm change requests are not overlapping and respect maximum spacing (1 day if not tight, 1h if tight)
            previous_end_date = datetime.strptime(
                change_requests[i - 1]["end_date"], "%Y-%m-%d %H:%M:%S"
            )
            difference = current_start_date - previous_end_date
            if difference > timedelta(hours=max_difference) or difference < timedelta(0):
                return (
                    0,
                    False,
                    "",
                    {
                        "message": "Change requests are overlapping or not respecting the maximum spacing."
                    },
                )
            # Confirm change requests are ordered by impact - lower number being more impactful
            if change_request["impact"] > change_requests[i - 1]["impact"]:
                return (
                    0,
                    False,
                    "",
                    {"message": "Change requests are not ordered by priority."},
                )

        # Validate final_l3 tasks
        reward, done, message, info = super().validate(page, chat_messages)
        return reward, done, message, info

    def teardown(self) -> None:
        for change_request_sys_id in self.change_request_sys_ids:
            record_exists = table_api_call(
                instance=self.instance,
                table="change_request",
                params={"sysparm_query": f"sys_id={change_request_sys_id}"},
            )["result"]
            if record_exists:
                db_delete_from_table(
                    instance=self.instance,
                    table="change_request",
                    sys_id=change_request_sys_id,
                )
        super().teardown()


class TwoChangesBasicUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesWideBasicUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesFixBasicUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesFixWideBasicUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesBasicVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesWideBasicVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesFixBasicVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesFixWideBasicVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesPriorityUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesWidePriorityUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesFixPriorityUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesFixWidePriorityUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesWidePriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesFixPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesFixWidePriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesTightUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesWideScheduleTightUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesFixTightUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesFixWideScheduleTightUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesWideTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class TwoChangesFixTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class TwoChangesFixWideTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            uniform_risk=False,
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesBasicUniformRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesWideBasicUniformRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesFixBasicUniformRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesFixWideBasicUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesBasicVariedRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesWideBasicVariedRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesFixBasicVariedRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesFixWideBasicVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="base",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesPriorityUniformRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesWidePriorityUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesFixPriorityUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesFixWidePriorityUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesPriorityVariedRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesWidePriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesFixPriorityVariedRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesFixWidePriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="priority",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesTightUniformRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesWideScheduleTightUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesFixTightUniformRiskChangeRequestSchedulingTask(ManageChangeRequestScheduleTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesFixWideScheduleTightUniformRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight",
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesWideTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            wide_schedule=True,
            uniform_risk=False,
            num_change_requests=num_change_requests,
            level=level,
        )


class ThreeChangesFixTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            uniform_risk=False,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


class ThreeChangesFixWideTightPriorityVariedRiskChangeRequestSchedulingTask(
    ManageChangeRequestScheduleTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_change_requests: int = 3,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            goal_type="tight priority",
            uniform_risk=False,
            wide_schedule=True,
            num_change_requests=num_change_requests,
            pre_existing_schedule=True,
            level=level,
        )


local_vars = locals().copy()


SMALL_BASE_SCHEDULING_TASKS = [
    TwoChangesBasicUniformRiskChangeRequestSchedulingTask,
    TwoChangesWideBasicUniformRiskChangeRequestSchedulingTask,
    TwoChangesFixBasicUniformRiskChangeRequestSchedulingTask,
    TwoChangesFixWideBasicUniformRiskChangeRequestSchedulingTask,
    TwoChangesBasicVariedRiskChangeRequestSchedulingTask,
    TwoChangesWideBasicVariedRiskChangeRequestSchedulingTask,
    TwoChangesFixBasicVariedRiskChangeRequestSchedulingTask,
    TwoChangesFixWideBasicVariedRiskChangeRequestSchedulingTask,
]
SMALL_TIGHT_SCHEDULING_TASKS = [
    TwoChangesPriorityUniformRiskChangeRequestSchedulingTask,
    TwoChangesWidePriorityUniformRiskChangeRequestSchedulingTask,
    TwoChangesFixPriorityUniformRiskChangeRequestSchedulingTask,
    TwoChangesFixWidePriorityUniformRiskChangeRequestSchedulingTask,
    TwoChangesPriorityVariedRiskChangeRequestSchedulingTask,
    TwoChangesWidePriorityVariedRiskChangeRequestSchedulingTask,
    TwoChangesFixPriorityVariedRiskChangeRequestSchedulingTask,
    TwoChangesFixWidePriorityVariedRiskChangeRequestSchedulingTask,
    TwoChangesTightUniformRiskChangeRequestSchedulingTask,
    TwoChangesWideScheduleTightUniformRiskChangeRequestSchedulingTask,
    TwoChangesFixTightUniformRiskChangeRequestSchedulingTask,
    TwoChangesFixWideScheduleTightUniformRiskChangeRequestSchedulingTask,
    TwoChangesTightPriorityVariedRiskChangeRequestSchedulingTask,
    TwoChangesWideTightPriorityVariedRiskChangeRequestSchedulingTask,
    TwoChangesFixTightPriorityVariedRiskChangeRequestSchedulingTask,
    TwoChangesFixWideTightPriorityVariedRiskChangeRequestSchedulingTask,
]

LARGE_BASE_SCHEDULING_TASKS = [
    ThreeChangesBasicUniformRiskChangeRequestSchedulingTask,
    ThreeChangesWideBasicUniformRiskChangeRequestSchedulingTask,
    ThreeChangesFixBasicUniformRiskChangeRequestSchedulingTask,
    ThreeChangesFixWideBasicUniformRiskChangeRequestSchedulingTask,
    ThreeChangesBasicVariedRiskChangeRequestSchedulingTask,
    ThreeChangesWideBasicVariedRiskChangeRequestSchedulingTask,
    ThreeChangesFixBasicVariedRiskChangeRequestSchedulingTask,
    ThreeChangesFixWideBasicVariedRiskChangeRequestSchedulingTask,
]

LARGE_TIGHT_SCHEDULING_TASKS = [
    ThreeChangesPriorityUniformRiskChangeRequestSchedulingTask,
    ThreeChangesWidePriorityUniformRiskChangeRequestSchedulingTask,
    ThreeChangesFixPriorityUniformRiskChangeRequestSchedulingTask,
    ThreeChangesFixWidePriorityUniformRiskChangeRequestSchedulingTask,
    ThreeChangesPriorityVariedRiskChangeRequestSchedulingTask,
    ThreeChangesWidePriorityVariedRiskChangeRequestSchedulingTask,
    ThreeChangesFixPriorityVariedRiskChangeRequestSchedulingTask,
    ThreeChangesFixWidePriorityVariedRiskChangeRequestSchedulingTask,
    ThreeChangesTightUniformRiskChangeRequestSchedulingTask,
    ThreeChangesWideScheduleTightUniformRiskChangeRequestSchedulingTask,
    ThreeChangesFixTightUniformRiskChangeRequestSchedulingTask,
    ThreeChangesFixWideScheduleTightUniformRiskChangeRequestSchedulingTask,
    ThreeChangesTightPriorityVariedRiskChangeRequestSchedulingTask,
    ThreeChangesWideTightPriorityVariedRiskChangeRequestSchedulingTask,
    ThreeChangesFixTightPriorityVariedRiskChangeRequestSchedulingTask,
    ThreeChangesFixWideTightPriorityVariedRiskChangeRequestSchedulingTask,
]

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type)
    and issubclass(var, FilterAndDoTask)
    and var is not FilterAndDoTask
    and var is not ManageChangeRequestScheduleTask
]
