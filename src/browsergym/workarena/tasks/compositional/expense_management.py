import re

from datetime import timedelta
from faker import Faker
from typing import List, Tuple

fake = Faker()

from playwright.sync_api._generated import Page

from .base import HumanEvalTask
from .delete_record import DeleteExpenseLineExpenseManagementTask
from .filter_and_do import FilterAndDoTask

from ..base import AbstractServiceNowTask

from ...api.change_request import create_change_request
from ...api.expense_line import create_expense_line
from ...api.utils import table_api_call, db_delete_from_table
from ...config import (
    # Expected columns for the different lists
    EXPECTED_EXPENSE_LINE_COLUMNS_PATH,
)
from ...instance import SNowInstance


class ExpenseManagementTask(FilterAndDoTask):
    """Task to manage expenses.
    Args:

    num_duplicates: int
        The number of duplicate expenses to create
    extra_expenses: int
        The number of extra expenses to create (total expenses will be num_duplicates + extra_expenses)
    goal_type: str
        The type of goal to generate. Choice of "base", "date", "amount", "any".
        - "base": one expense is linked to a change request, others are not and are expected to be deleted
        - "date": none of the expenses are linked to change requests; the oldest one is expeted to be deleted
        - "amount": none of the expenses are linked to change requests and they are all created on the same date;
                    the most expensive one is expeted to be deleted
        - "any": any of the expenses can be deleted
    """

    min_allowed_amount = 100
    max_allowed_amount = 10000

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        num_duplicates: int = 2,
        extra_expenses: int = 2,
        goal_type: str = "base",
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "module": "Expense Lines",
                "application": "Cost",
            },
            level=level,
            protocol_name="Managing Your Existing Expenses",
        )
        self.num_duplicates = num_duplicates
        self.extra_expenses = extra_expenses
        self.total_expenses = num_duplicates + extra_expenses
        self.goal_type = goal_type
        self.change_request_sysids = []

        # mappings between number -> (is_duplicate, sys_id)
        self.expense_lines = {}
        self.expense_to_keep_number = None  # The number of the expense that will be kept; i.e. not deleted by the cheat/agent if successful

        self.expense_hashtag = "#SERIES-" + self.unique_id[:10]
        self.short_description = f"Managing Your Existing Expenses"
        self.task_description = f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) manage your expenses with short description containing hashtag {self.expense_hashtag}. '
        self.tasks = []

    def _setup_list(self) -> None:
        """The setup might be a bit complex on a first read. To understand it better, refer to the protocol for this task."""
        self.filter_config = {
            "list_url": "/now/nav/ui/classic/params/target/fm_expense_line_list.do",
            "expected_fields_path": EXPECTED_EXPENSE_LINE_COLUMNS_PATH,
            "filter_columns": [
                "short_description",
            ],
            "filter_kind": "AND",
            "filter_operators": ["contains"],
            "filter_values": [
                f"{self.expense_hashtag}",
            ],
        }

        # Short description to use for duplicate expenses
        duplicate_short_description = f"{fake.sentence(4)}"

        # Set the default amount and date in case uniform_amount and uniform_date are True
        amount = round(self.random.uniform(self.min_allowed_amount, self.max_allowed_amount), 2)
        start_date = fake.date_this_decade(before_today=True, after_today=False)
        date = start_date

        most_expensive_amount = float("-inf")

        most_expensive_duplicate_expense_number = None
        oldest_duplicate_expense_number = None
        only_expense_with_change_request = None
        # id of expenses will be this id + their order in the creation
        unique_id = str(int(self.unique_id.replace("-", ""), 16))[:10]
        for i in range(self.total_expenses):
            expense_number = f"EXP-{i}{unique_id }"
            is_duplicate = i < self.num_duplicates
            # set task sys_id to empty string if no change request is created
            task_sys_id = ""

            # Set a random date between start_date and today
            if self.goal_type in ["base", "date"] and i > 0:
                date = str(
                    fake.date_between(start_date=start_date + timedelta(1), end_date="today")
                )
            else:
                date = start_date
            if i == 0:
                oldest_duplicate_expense_number = expense_number

            # In the 'any' case, there are no change requests, all dates are the same and the prices are the same
            if self.goal_type != "any":
                amount = round(
                    self.random.uniform(self.min_allowed_amount, self.max_allowed_amount), 2
                )
                if is_duplicate and amount > most_expensive_amount:
                    most_expensive_amount = amount
                    most_expensive_duplicate_expense_number = expense_number

            # Create a change request for the base case
            if self.goal_type == "base" and i == 0:
                task_sys_id, _ = create_change_request(
                    instance=self.instance,
                    user_sys_id=self._base_user_sysid,
                    hashtag=self.expense_hashtag,
                    impact=2,
                    risk=2,
                    random=self.random,
                )
                self.change_request_sysids.append(task_sys_id)
                only_expense_with_change_request = expense_number

            # Set the short description for the duplicate expenses; otherwise pass None, which will generate a random one
            short_description = duplicate_short_description if i < self.num_duplicates else None

            expense_sys_id, _ = create_expense_line(
                instance=self.instance,
                amount=amount,
                number=expense_number,
                date=str(date),
                short_description=short_description,
                expense_hashtag=self.expense_hashtag,
                user_sys_id=self._base_user_sysid,
                task_sys_id=task_sys_id,
            )
            self.expense_lines[expense_number] = (is_duplicate, expense_sys_id)

        # keep the number of the expense that will be linked to the change request
        if self.goal_type == "base":
            self.expense_to_keep_number = only_expense_with_change_request
        # keep the oldest expense
        elif self.goal_type == "date":
            self.expense_to_keep_number = oldest_duplicate_expense_number
        elif self.goal_type == "amount":
            self.expense_to_keep_number = most_expensive_duplicate_expense_number
        else:
            self.expense_to_keep_number = oldest_duplicate_expense_number

        # As the task description redundant, we keep only the first one and skip the rest
        skip_description = False
        # Create the tasks to delete the extra expenses
        for expense_number, (is_duplicate, expense_sys_id) in self.expense_lines.items():
            if expense_number == self.expense_to_keep_number or not is_duplicate:
                continue
            self.tasks.append(
                DeleteExpenseLineExpenseManagementTask(
                    instance=self.instance,
                    fixed_config={
                        "field_name": "number",
                        "field_value": f"{expense_number}",
                    },
                    is_validated=False,
                    used_in_level_2=True,
                    record_sys_id=expense_sys_id,
                    record_number=expense_number,
                    level=self.level,
                    skip_description=skip_description,
                    goal_type=self.goal_type,
                )
            )
            skip_description = True

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        expenses = table_api_call(
            instance=self.instance,
            table="fm_expense_line",
            params={
                "sysparm_query": f"short_descriptionLIKE{self.expense_hashtag}",
                "sysparm_fields": "number,amount,sys_id",
            },
        )["result"]
        # There should remain only one duplicate expense after the task is completed and the extra expenses should reamin
        target_num_expenses = self.extra_expenses + 1
        # Check that only one of the duplicated expenses exists and it is the right one
        if len(expenses) != target_num_expenses:
            return (
                0,
                False,
                "",
                {"message": "Wrong number of expenses."},
            )

        existing_expense_numbers = {expense["number"] for expense in expenses}
        for expense_number, (is_duplicate, _) in self.expense_lines.items():
            # Check that only one of the duplicated expenses exists and it is the right one
            if expense_number == self.expense_to_keep_number:
                if expense_number not in existing_expense_numbers:
                    return (
                        0,
                        False,
                        "",
                        {"message": "The expected duplicate to keep is missing."},
                    )

            # Check that other duplicates have been deleted
            elif is_duplicate and expense_number in existing_expense_numbers:
                return (
                    0,
                    False,
                    "",
                    {"message": "An unexpected duplicate is present."},
                )
            # Check that the extra expenses have not been deleted
            elif not is_duplicate and expense_number not in existing_expense_numbers:
                return (
                    0,
                    False,
                    "",
                    {"message": "An extra expense has been deleted."},
                )

        # Validate final_l3 tasks
        reward, done, message, info = super().validate(page, chat_messages)
        return reward, done, message, info

    def teardown(self) -> None:
        for _, expense_sys_id in self.expense_lines.values():
            record_exists = table_api_call(
                instance=self.instance,
                table="fm_expense_line",
                params={"sysparm_query": f"sys_id={expense_sys_id}"},
            )["result"]
            if not record_exists:
                continue
            db_delete_from_table(
                instance=self.instance,
                table="fm_expense_line",
                sys_id=expense_sys_id,
            )
        for change_request_sys_id in self.change_request_sysids:
            record_exists = table_api_call(
                instance=self.instance,
                table="change_request",
                params={"sysparm_query": f"sys_id={change_request_sys_id}"},
            )["result"]
            if not record_exists:
                continue
            db_delete_from_table(
                instance=self.instance,
                table="change_request",
                sys_id=change_request_sys_id,
            )
        super().teardown()


class BasicExpenseManagementSmallTask(ExpenseManagementTask, HumanEvalTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 2,
        extra_expenses: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="base",
            level=level,
        )


class DateBasedExpenseManagementSmallTask(ExpenseManagementTask, HumanEvalTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 2,
        extra_expenses: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="date",
            level=level,
        )


class AmountBasedExpenseManagementSmallTask(ExpenseManagementTask, HumanEvalTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 2,
        extra_expenses: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="amount",
            level=level,
        )


class EasyExpenseManagementTask(ExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 2,
        extra_expenses: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="any",
            level=level,
        )

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        expenses = table_api_call(
            instance=self.instance,
            table="fm_expense_line",
            params={
                "sysparm_query": f"short_descriptionLIKE{self.expense_hashtag}",
                "sysparm_fields": "number,amount,sys_id",
            },
        )["result"]
        # There should remain only one expense after the task is completed and the extra expenses should reamin
        target_num_expenses = self.extra_expenses + 1
        # Check that only one of the duplicated expenses exists and it is the right one
        if len(expenses) != target_num_expenses:
            return (
                0,
                False,
                "",
                {"message": "Wrong number of expenses."},
            )

        existing_expense_numbers = {expense["number"] for expense in expenses}
        for expense_number, (is_duplicate, _) in self.expense_lines.items():
            if not is_duplicate and expense_number not in existing_expense_numbers:
                return (
                    0,
                    False,
                    "",
                    {"message": "An extra expense has been deleted."},
                )

        # Validate final_l3 tasks
        reward, done, message, info = FilterAndDoTask.validate(self, page, chat_messages)
        return reward, done, message, info


class EasyExpenseManagementSmallTask(EasyExpenseManagementTask, HumanEvalTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 2,
        extra_expenses: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            level=level,
        )


class BasicExpenseManagementMediumTask(ExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 4,
        extra_expenses: int = 4,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="base",
            level=level,
        )


class DateBasedExpenseManagementMediumTask(ExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 4,
        extra_expenses: int = 4,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="date",
            level=level,
        )


class AmountBasedExpenseManagementMediumTask(ExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 4,
        extra_expenses: int = 4,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="amount",
            level=level,
        )


class EasyExpenseManagementMediumTask(EasyExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 4,
        extra_expenses: int = 4,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            level=level,
        )


class BasicExpenseManagementLargeTask(ExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 6,
        extra_expenses: int = 6,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="base",
            level=level,
        )


class DateBasedExpenseManagementLargeTask(ExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 6,
        extra_expenses: int = 6,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="date",
            level=level,
        )


class AmountBasedExpenseManagementLargeTask(ExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 6,
        extra_expenses: int = 6,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            goal_type="amount",
            level=level,
        )


class EasyExpenseManagementLargeTask(EasyExpenseManagementTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_duplicates: int = 6,
        extra_expenses: int = 6,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_duplicates=num_duplicates,
            extra_expenses=extra_expenses,
            level=level,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type)
    and issubclass(var, FilterAndDoTask)
    and var is not FilterAndDoTask
    and var is not ExpenseManagementTask
    and var is not EasyExpenseManagementTask
]
