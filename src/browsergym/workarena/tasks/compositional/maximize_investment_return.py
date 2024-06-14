import re

from faker import Faker
from typing import List, Tuple

fake = Faker()

from playwright.sync_api._generated import Page

from browsergym.workarena.tasks.send_chat_message import SendChatMessageForBudgetAllocationTask

from .base import HumanEvalTask
from .delete_record import DeleteExpenseLineKnapsack
from .filter_and_do import FilterAndDoTask
from .utils.knapsack import KnapsackInstanceGenarator

from ..base import AbstractServiceNowTask

from ...api.expense_line import create_expense_line
from ...api.utils import table_api_call, db_delete_from_table
from ...config import (
    # Expected columns for the different lists
    EXPECTED_EXPENSE_LINE_COLUMNS_PATH,
)
from ...instance import SNowInstance


class FilterExpensesAndAllocateInvestmentsTask(FilterAndDoTask):
    """Task to filter expenses and allocate investments.
    Args:
    num_expenses: list[int]
        The range to choose the number of expenses from
    budget: int
        The budget to allocate to the expenses
    mode: str
        Mode of generation. Choice of "random", "trivial", "single_item", "single_item_uniform", "n_items"
        - random: Randomly generate the instance and return it; guaranteed to have a unique optimal solution
        - trivial: Generate a trivial instance with all items fitting in the knapsack; return the instance
        - single_item: Generate an instance where the optimal solution has only one item
        - n_items: Generate an instance with all items having uniform weight and value; n items fitting in the knapsack
        - single_item_uniform: Generate an instance with all items having uniform weight and value; optimal solution has only one item and it can be any
    answer_format: str
        The type of answer to generate. Choice of total_return_only, total_return_and_investments, investments_only, cleanup, cleanup_and_return
    num_items_uniform: int
        The number of items to generate in the "n_items" mode
    """

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        num_expenses: list[int] = [3, 4],
        budget: int = 150000,
        mode: str = "random",
        num_items_uniform: int = None,
        answer_format: str = None,
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
            protocol_name="Maximizing total investment return",
        )
        self.num_expenses = self.random.randint(num_expenses[0], num_expenses[1] + 1)
        # In these settings, we need to vary the budget
        if mode in ["single_item_uniform", "n_items"]:
            min_budget = budget / 5
            max_budget = budget * 5
            self.budget = self.random.randint(min_budget, max_budget)
        else:
            self.budget = budget
        self.mode = mode
        self.answer_format = answer_format
        self.num_items_uniform = 1 if mode == "single_item_uniform" else num_items_uniform

        self.expense_hashtag = "#" + self.unique_id[:10]
        self.short_description = f"Allocate investments to maximize returns"
        self.expense_line_sys_ids = []
        self.expense_line_numbers = []
        self.correct_investments = (
            []
        )  # List of correct investments to check for in the chat messages
        self.incorrect_investments = (
            []
        )  # List of incorrect investments to check for in the chat messages
        self.potential_investments = None  # List of tuples (cost, return) of potential investments
        self.max_return = None  # Maximum return possible with optimal solution
        self.alternative_max_return_formats = (
            []
        )  # List of alternative formats for the maximum return to check for in the chat messages
        self.selected_investment_indices = (
            None  # Indices of the selected investments in the optimal solution
        )
        # flag to check if the investments are correctly selected and total return is correct
        self.investments_correctly_selected = False
        self.total_return_correct = False

    def _setup_list(self) -> None:
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
        knapsack = KnapsackInstanceGenarator(
            random=self.random,
            num_items=self.num_expenses,
            max_capacity=self.budget,
            mode=self.mode,
            num_items_in_solution=self.num_items_uniform,
        )
        # investments is a list of tuples, where each tuple is (cost, return)
        self.potential_investments, self.max_return, self.selected_investment_indices = (
            knapsack.get_instance()
        )
        # Accepted answer formats for the maximum return
        self.alternative_max_return_formats = [
            str(self.max_return),  # No comma
            "{:,}".format(self.max_return),  # Comma as thousand separator
            "{:,}".format(self.max_return).replace(
                ",", ", "
            ),  # Comma as thousand separator with space after
            "{:,}".format(self.max_return).replace(",", " "),  # Space as thousand separator
        ]

        for i, investment in enumerate(self.potential_investments):
            expense_number = f"EXP-{i}{self.unique_id[:10]}"
            # Include the return inside the short description
            short_description = f"Build {fake.sentence(2)} - Return: {investment[1]}$ "
            expense_sys_id, expense_number = create_expense_line(
                instance=self.instance,
                amount=investment[0],
                number=expense_number,
                date=str(fake.date_this_year(before_today=True, after_today=False)),
                short_description=short_description,
                expense_hashtag=self.expense_hashtag,
                user_sys_id=self._base_user_sysid,
            )
            self.expense_line_sys_ids.append(expense_sys_id)
            self.expense_line_numbers.append(expense_number)

        # In this setting there is only one valid answer
        if self.mode in ["random", "trivial", "single_item"]:
            for i, investment in enumerate(self.potential_investments):
                if i in self.selected_investment_indices:
                    self.correct_investments.append(self.expense_line_numbers[i])
                else:
                    self.incorrect_investments.append(self.expense_line_numbers[i])
        # In this setting, many answers are possible, it's only a matter of respecting the number of items in the solution
        # We store values here just so the cheat function can work uniformly
        elif self.mode in ["n_items", "single_item_uniform"]:
            for i, investment in enumerate(self.potential_investments):
                if i < self.num_items_uniform:
                    self.correct_investments.append(self.expense_line_numbers[i])
                else:
                    self.incorrect_investments.append(self.expense_line_numbers[i])

    def validate(self, page: Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        super().validate(page, chat_messages)

    def check_total_return(
        self, page: Page, chat_messages: List[str]
    ) -> Tuple[float, bool, str, dict]:
        """Simple check that validates that the total return is correct."""
        if self.total_return_correct:
            return (
                1,
                True,
                "That is correct, thank you!",
                {"message": "Correct total return."},
            )

        if chat_messages and chat_messages[-1]["role"] == "assistant":
            answer = chat_messages[-1]["message"]
        else:
            return (
                0,
                False,
                "",
                {"message": "The assistant did not provide an answer."},
            )
        for format in self.alternative_max_return_formats:
            if format in answer:
                self.total_return_correct = True
                return (
                    1,
                    True,
                    "That is correct, thank you!",
                    {"message": "Correct answer."},
                )

        return (
            0,
            False,
            "",
            {"message": "Incorrect answer."},
        )

    def check_correct_investments_sent_in_chat(
        self, page: Page, chat_messages: List[str]
    ) -> Tuple[float, bool, str, dict]:
        """Check that the correct investments have been selected and their numbers have been sent in the chat"""
        if not self.investments_correctly_selected:
            if chat_messages and chat_messages[-1]["role"] == "assistant":
                answer = chat_messages[-1]["message"]
            else:
                return (
                    0,
                    False,
                    "",
                    {"message": "The assistant did not provide an answer."},
                )

            # In these settings, there is only one valid answer
            if self.mode in ["random", "trivial", "single_item"]:
                # Check that the correct investments have been selected
                for investment in self.correct_investments:
                    if investment not in answer:
                        return (
                            0,
                            False,
                            "",
                            {"message": "Investment missing from selected list."},
                        )
                # Check that the incorrect investments have not been selected
                for investment in self.incorrect_investments:
                    if investment in answer:
                        return (
                            0,
                            False,
                            "",
                            {"message": "Incorrect investment selected."},
                        )
            # In those settings, many answers are possible, it's only a matter of respecting the number of items in the solution
            elif self.mode in ["n_items", "single_item_uniform"]:
                # Extract the expense line numbers from the answer
                pattern = r"EXP-\w+-\w+"
                matches = re.findall(pattern, answer)
                if len(matches) != self.num_items_uniform:
                    return (
                        0,
                        False,
                        "",
                        {"message": "Incorrect number of investments selected."},
                    )
            self.correct_investments_selected = True

        return (
            1,
            True,
            "That is correct, thank you!",
            {"message": "Correct investments selected."},
        )

    def check_only_right_investment_kept(
        self, page: Page, chat_messages: List[str]
    ) -> Tuple[float, bool, str, dict]:
        """Checks that only the expected investments were kept; i.e. the others were deleted"""
        for i, investment_sys_id in enumerate(self.expense_line_sys_ids):
            record_expected = i in self.selected_investment_indices
            record_exists = table_api_call(
                instance=self.instance,
                table="fm_expense_line",
                params={"sysparm_query": f"sys_id={investment_sys_id}"},
            )["result"]
            # Missing investment that should be kept
            if record_expected and not record_exists:
                return (
                    0,
                    True,
                    "",
                    {"message": "Expected investment has been deleted."},
                )
            # Unexpected investment that should be deleted
            if not record_expected and record_exists:
                return (
                    0,
                    False,
                    "",
                    {"message": "Unexpected investment is present."},
                )

        return (
            1,
            True,
            "That is correct, thank you!",
            {"message": "Correct investments kept."},
        )

    def teardown(self) -> None:
        for expense_sys_id in self.expense_line_sys_ids:
            record_exists = table_api_call(
                instance=self.instance,
                table="fm_expense_line",
                params={"sysparm_query": f"sys_id={expense_sys_id}"},
            )["result"]
            if record_exists:
                db_delete_from_table(
                    instance=self.instance,
                    table="fm_expense_line",
                    sys_id=expense_sys_id,
                )
        super().teardown()


class FilterExpensesAndFindTotalReturnTask(FilterExpensesAndAllocateInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        num_expenses: list[int] = [3, 4],
        budget: int = 150000,
        mode: str = "random",
        answer_format: str = "total_return_only",
        num_items_uniform: int = 1,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=num_expenses,
            budget=budget,
            mode=mode,
            num_items_uniform=num_items_uniform,
            answer_format=answer_format,
            level=level,
        )
        self.task_description = f'Follow protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) to allocate investments to the expenses with short description containing {self.expense_hashtag} to maximize returns while fitting inside the budget of {self.budget}$. Give total return of selected investments only. '

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SendChatMessageForBudgetAllocationTask(
                instance=self.instance,
                message=f"The total value of the investments is {self.max_return}$",
                used_in_level_2=True,
                is_validated=False,
                budget=self.budget,
                answer_format=self.answer_format,
                level=self.level,
            )
        ]

    def validate(self, page: Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        reward, done, message, info = self.check_total_return(page, chat_messages)
        if reward == 1 and done:
            return FilterAndDoTask.validate(self, page, chat_messages)
        else:
            return reward, done, message, info


class FilterRandomExpensesAndFindTotalReturnSmallTask(
    FilterExpensesAndFindTotalReturnTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesAndFindTotalReturnMediumTask(FilterExpensesAndFindTotalReturnTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesAndFindTotalReturnLargeTask(FilterExpensesAndFindTotalReturnTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterTrivialExpensesAndFindTotalReturnSmallTask(
    FilterExpensesAndFindTotalReturnTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterTrivialExpensesAndFindTotalReturnMediumTask(FilterExpensesAndFindTotalReturnTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterTrivialExpensesAndFindTotalReturnLargeTask(FilterExpensesAndFindTotalReturnTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterSingleItemExpensesAndFindTotalReturnSmallTask(
    FilterExpensesAndFindTotalReturnTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesAndFindTotalReturnMediumTask(FilterExpensesAndFindTotalReturnTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesAndFindTotalReturnLargeTask(FilterExpensesAndFindTotalReturnTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemUniformExpensesAndFindTotalReturnSmallTask(
    FilterExpensesAndFindTotalReturnTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesAndFindTotalReturnMediumTask(
    FilterExpensesAndFindTotalReturnTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesAndFindTotalReturnLargeTask(
    FilterExpensesAndFindTotalReturnTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterTwoItemsUniformExpensesAndFindTotalReturnSmallTask(
    FilterExpensesAndFindTotalReturnTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=2,
        )


class FilterThreeItemsUniformExpensesAndFindTotalReturnMediumTask(
    FilterExpensesAndFindTotalReturnTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


class FilterThreeItemsUniformExpensesAndFindTotalReturnLargeTask(
    FilterExpensesAndFindTotalReturnTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


class FilterExpensesAndSelectInvestmentsTask(FilterExpensesAndAllocateInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        num_expenses: list[int] = [3, 4],
        budget: int = 150000,
        mode: str = "random",
        num_items_uniform: int = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=num_expenses,
            budget=budget,
            mode=mode,
            level=level,
            answer_format="investments_only",
            num_items_uniform=num_items_uniform,
        )
        self.task_description = f'Follow protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) to allocate investments to the expenses with short description containing {self.expense_hashtag} to maximize returns while fitting inside the budget of {self.budget}$. Give selected investments only. '

    def _setup_list(self) -> None:
        super()._setup_list()
        message = f"The correct investments to select are: {', '.join(self.correct_investments)}"
        self.tasks.append(
            SendChatMessageForBudgetAllocationTask(
                instance=self.instance,
                message=message,
                used_in_level_2=True,
                is_validated=False,
                budget=self.budget,
                answer_format=self.answer_format,
                level=self.level,
            )
        )

    def validate(self, page: Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        reward, done, message, info = self.check_correct_investments_sent_in_chat(
            page, chat_messages
        )
        if reward == 1 and done:
            return FilterAndDoTask.validate(self, page, chat_messages)
        else:
            return reward, done, message, info


class FilterRandomExpensesAndSelectInvestmentsSmallTask(
    FilterExpensesAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesAndSelectInvestmentsMediumTask(FilterExpensesAndSelectInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesAndSelectInvestmentsLargeTask(FilterExpensesAndSelectInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterTrivialExpensesAndSelectInvestmentsSmallTask(
    FilterExpensesAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterTrivialExpensesAndSelectInvestmentsMediumTask(FilterExpensesAndSelectInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterTrivialExpensesAndSelectInvestmentsLargeTask(FilterExpensesAndSelectInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterSingleItemExpensesAndSelectInvestmentsSmallTask(
    FilterExpensesAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesAndSelectInvestmentsMediumTask(
    FilterExpensesAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesAndSelectInvestmentsLargeTask(FilterExpensesAndSelectInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemUniformExpensesAndSelectInvestmentsSmallTask(
    FilterExpensesAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesAndSelectInvestmentsMediumTask(
    FilterExpensesAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesAndSelectInvestmentsLargeTask(
    FilterExpensesAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterTwoItemsUniformExpensesAndSelectInvestmentsSmallTask(
    FilterExpensesAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=2,
        )


class FilterThreeItemsUniformExpensesAndSelectInvestmentsMediumTask(
    FilterExpensesAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


class FilterThreeItemsUniformExpensesAndSelectInvestmentsLargeTask(
    FilterExpensesAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


class FilterExpensesFindTotalReturnAndSelectInvestmentsTask(FilterExpensesAndFindTotalReturnTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_expenses: list[int] = [3, 4],
        budget: int = 150000,
        mode="random",
        num_items_uniform: int = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=num_expenses,
            budget=budget,
            mode=mode,
            num_items_uniform=num_items_uniform,
            answer_format="total_return_and_investments",
            level=level,
        )
        self.task_description = f'Follow protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) to allocate investments to the expenses with short description containing {self.expense_hashtag} to maximize returns while fitting inside the budget of {self.budget}$. Give selected investments and total return. '

    def _setup_list(self) -> None:
        super()._setup_list()
        message = f"The correct investments to select are: {', '.join(self.correct_investments)} and their total return is {self.max_return}$"
        self.tasks = [
            SendChatMessageForBudgetAllocationTask(
                instance=self.instance,
                message=message,
                used_in_level_2=True,
                is_validated=False,
                budget=self.budget,
                answer_format=self.answer_format,
                level=self.level,
            )
        ]

    def validate(self, page: Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        reward, done, message, info = self.check_correct_investments_sent_in_chat(
            page, chat_messages
        )
        if not (reward == 1 and done):
            return reward, done, message, info

        reward, done, message, info = self.check_total_return(page, chat_messages)
        if not (reward == 1 and done):
            return reward, done, message, info

        return FilterAndDoTask.validate(self, page, chat_messages)


class FilterRandomExpensesFindTotalReturnAndSelectInvestmentsSmallTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesFindTotalReturnAndSelectInvestmentsMediumTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesFindTotalReturnAndSelectInvestmentsLargeTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterTrivialExpensesFindTotalReturnAndSelectInvestmentsSmallTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterTrivialExpensesFindTotalReturnAndSelectInvestmentsMediumTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterTrivialExpensesFindTotalReturnAndSelectInvestmentsLargeTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="trivial",
            level=level,
        )


class FilterSingleItemExpensesFindTotalReturnAndSelectInvestmentsSmallTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesFindTotalReturnAndSelectInvestmentsMediumTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesFindTotalReturnAndSelectInvestmentsLargeTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemUniformExpensesFindTotalReturnAndSelectInvestmentsSmallTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesFindTotalReturnAndSelectInvestmentsMediumTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesFindTotalReturnAndSelectInvestmentsLargeTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterTwoItemsUniformExpensesFindTotalReturnAndSelectInvestmentsSmallTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=2,
        )


class FilterThreeItemsUniformExpensesFindTotalReturnAndSelectInvestmentsMediumTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


class FilterThreeItemsUniformExpensesFindTotalReturnAndSelectInvestmentsLargeTask(
    FilterExpensesFindTotalReturnAndSelectInvestmentsTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


class FilterExpenseLinesAndDeleteWrongInvestments(FilterExpensesAndAllocateInvestmentsTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        num_expenses: List[int] = [3, 4],
        budget: int = 150000,
        mode: str = "random",
        num_items_uniform: int = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            num_expenses=num_expenses,
            budget=budget,
            mode=mode,
            answer_format="cleanup",
            num_items_uniform=num_items_uniform,
            level=level,
        )
        self.task_description = f'Follow protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) to allocate investments to the expenses with short description containing {self.expense_hashtag} to maximize returns while fitting inside the budget of {self.budget}$. Delete the investments that were not selected. '

    def _setup_list(self) -> None:
        super()._setup_list()
        # in modes "n_items", "single_item_uniform", this yields one of many valid solutions
        for i, expense_line_number in enumerate(self.incorrect_investments):
            skip_description = i > 0
            expense_line_sys_id = self.expense_line_sys_ids[i]
            self.tasks.append(
                DeleteExpenseLineKnapsack(
                    instance=self.instance,
                    record_number=expense_line_number,
                    record_sys_id=expense_line_sys_id,
                    fixed_config={
                        "field_name": "number",
                        "field_value": f"{expense_line_number}",
                    },
                    used_in_level_2=True,
                    is_validated=False,
                    budget=self.budget,
                    answer_format=self.answer_format,
                    level=self.level,
                    skip_description=skip_description,
                )
            )

    def validate(self, page: Page, chat_messages: List[str]) -> Tuple[float, bool, str, dict]:
        expenses = table_api_call(
            instance=self.instance,
            table="fm_expense_line",
            params={
                "sysparm_query": f"short_descriptionLIKE{self.expense_hashtag}",
                "sysparm_fields": "number,amount,sys_id",
            },
        )["result"]

        if self.mode in ["random", "trivial", "single_item"]:
            # Check that the correct investments have been selected
            for investment in self.correct_investments:
                if investment not in [expense["number"] for expense in expenses]:
                    return (
                        0,
                        False,
                        "",
                        {"message": "Investment missing from selected list."},
                    )
            # Check that the incorrect investments have not been selected
            for investment in self.incorrect_investments:
                if investment in [expense["number"] for expense in expenses]:
                    return (
                        0,
                        False,
                        "",
                        {"message": "Incorrect investment selected."},
                    )
        # In those settings, many answers are possible, it's only a matter of respecting the number of items in the solution
        elif self.mode in ["n_items", "single_item_uniform"]:
            if len(expenses) != self.num_items_uniform:
                return (
                    0,
                    False,
                    "",
                    {"message": "Incorrect number of investments selected."},
                )
        reward, done, message, info = FilterAndDoTask.validate(self, page, chat_messages)

        return reward, done, message, info


class FilterRandomExpensesAndDeleteWrongInvestmentsSmallTask(
    FilterExpenseLinesAndDeleteWrongInvestments, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesAndDeleteWrongInvestmentsMediumTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterRandomExpensesAndDeleteWrongInvestmentsLargeTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="random",
            level=level,
        )


class FilterSingleItemExpensesAndDeleteWrongInvestmentsSmallTask(
    FilterExpenseLinesAndDeleteWrongInvestments, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesAndDeleteWrongInvestmentsMediumTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemExpensesAndDeleteWrongInvestmentsLargeTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item",
            level=level,
        )


class FilterSingleItemUniformExpensesAndDeleteWrongInvestmentsSmallTask(
    FilterExpenseLinesAndDeleteWrongInvestments, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesAndDeleteWrongInvestmentsMediumTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterSingleItemUniformExpensesAndDeleteWrongInvestmentsLargeTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="single_item_uniform",
            level=level,
        )


class FilterTwoItemsUniformExpensesAndDeleteWrongInvestmentsSmallTask(
    FilterExpenseLinesAndDeleteWrongInvestments, HumanEvalTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[3, 5],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=2,
        )


class FilterThreeItemsUniformExpensesAndDeleteWrongInvestmentsMediumTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[6, 8],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


class FilterThreeItemsUniformExpensesAndDeleteWrongInvestmentsLargeTask(
    FilterExpenseLinesAndDeleteWrongInvestments
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: List[AbstractServiceNowTask] = None,
        level: int = 2,
    ):
        super().__init__(
            seed,
            instance,
            fixed_config,
            num_expenses=[9, 12],
            budget=150000,
            mode="n_items",
            level=level,
            num_items_uniform=3,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type)
    and issubclass(var, FilterAndDoTask)
    and var is not FilterAndDoTask
    and var is not FilterExpensesAndAllocateInvestmentsTask
    and var is not FilterExpensesAndFindTotalReturnTask
    and var is not FilterExpenseLinesAndDeleteWrongInvestments
    and var is not FilterExpensesFindTotalReturnAndSelectInvestmentsTask
    and var is not FilterExpensesAndSelectInvestmentsTask
]
