import faker

faker = faker.Faker()
import json

from playwright.sync_api import Page
from typing import List, Tuple

from .base import AbstractServiceNowTask

from ..utils.utils import check_url_suffix_match

from ...api.utils import db_delete_from_table, table_api_call


class DeleteRecordTask(AbstractServiceNowTask):
    """
    Delete a record from a list.

    Parameters:
    -----------
    instance: SNowInstance
        The instance to use.
    start_rel_url: str
        The relative URL of the list containing the record to delete.
    list_name: str
        The displayed name of the list containing the record to delete.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/filter_change_request_list_task.json
        for an example of a configuration file.
    all_configs: list[dict]
        A list of all possible configurations to use for the task.
    record_sys_id: str
        The sys_id of the record to delete. If not provided, a record will be created during the setup.
    record_number: str
        The number of the record to delete; used in the cheat. If not provided, the cheat will select the last one.
    """

    def __init__(
        self,
        seed: int = None,
        instance=None,
        start_rel_url: str = "",
        list_name: str = "",
        fixed_config: dict = None,
        all_configs: list[dict] = None,
        record_sys_id: str = None,
        record_number: str = None,
        **kwargs,
    ) -> None:
        super().__init__(seed=seed, instance=instance, start_rel_url=start_rel_url)
        self.list_name = list_name
        self.table_name = start_rel_url.split("/")[-1].split("_list.do")[0]
        self.fixed_config = fixed_config
        self.config = None
        self.pretty_printed_field_name = None
        self.field_name = None
        self.field_value = None
        self.other_fields = None
        self.all_configs = all_configs
        # If the record_sys_id is not provided, it will be created during the setup
        self.record_sys_id = record_sys_id
        self.record_number = record_number
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.config = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        )
        self.field_name = self.config.get("field_name")
        self.pretty_printed_field_name = self.config.get("pretty_printed_field_name")
        self.field_value = self.config.get("field_value")
        self.other_fields = self.config.get("other_fields")
        if self.record_sys_id is None:
            # First, check if the record already exists
            record = table_api_call(
                instance=self.instance,
                table=self.table_name,
                params={
                    "sysparm_query": f"{self.field_name}={self.field_value}",
                    "sysparm_fields": "sys_id",
                },
            )["result"]
            if len(record) > 0:
                raise ValueError(
                    f"Record already with {self.field_name} = {self.field_value} exists. Please delete it before proceeding."
                )

            self.record_sys_id = table_api_call(
                instance=self.instance,
                table=self.table_name,
                data=json.dumps(
                    {
                        self.field_name: self.field_value,
                        **self.other_fields,
                    }
                ),
                method="POST",
            )["result"]["sys_id"]

        goal = self.get_pretty_printed_description()

        return goal, {}

    def get_init_scripts(self) -> List[str]:
        return super().get_init_scripts() + ["registerGsftMainLoaded();"]

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        task_info = f"- Delete the record with {self.pretty_printed_field_name}={self.field_value} from the {self.list_name} list."

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()

        # If the record number is provided, click on the record with that number...
        if self.record_number is not None:
            frame.locator(f"[aria-label='Preview record: {self.record_number}']").click()
            page.wait_for_timeout(500)
            frame.get_by_text("Open Record").click()
        # ....Otherwise, otherwise filter the list and click on the record
        else:
            # Search for the record
            frame.get_by_label(
                f"Search a specific field of the {self.list_name} list"
            ).select_option(f"{self.field_name}")
            search_input = frame.locator('input[aria-label="Search"]')
            search_input.click()
            search_input.fill(self.field_value)
            search_input.press("Enter")
            page.wait_for_function(
                "typeof window.gsft_main !== 'undefined' && window.gsft_main.WORKARENA_LOAD_COMPLETE"
            )
            # Click on the record to open it
            # The first 2 displays of the record are in the search bar; the 3rd and last will be the link to open it
            frame.get_by_label(self.field_value).last.click()

        page.wait_for_function(
            "typeof window.gsft_main !== 'undefined' && window.gsft_main.WORKARENA_LOAD_COMPLETE"
        )
        frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
        # Click on delete, then confirm delete in the popup
        frame.get_by_text("delete").first.click()
        frame.wait_for_selector('header[aria-label="Confirmation"]')
        page.keyboard.press("Enter")
        # Wait for record to be updated in the DB
        record_deleted = False
        while not record_deleted:
            record = table_api_call(
                instance=self.instance,
                table=self.table_name,
                params={
                    "sysparm_query": f"{self.field_name}={self.field_value}",
                    "sysparm_fields": "sys_id",
                },
            )["result"]
            record_deleted = len(record) == 0
        page.wait_for_timeout(3000)

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        """
        Validate the solution
        """
        record = table_api_call(
            instance=self.instance,
            table=self.table_name,
            params={"sysparm_query": f"{self.field_name}={self.field_value}"},
        )["result"]
        if len(record) > 0:
            return 0, False, "", {"message": "Record was not deleted."}

        return 1, True, "Nice work, thank you!", {"message": "Record was deleted successfully."}

    def teardown(self) -> None:
        super().teardown()
        result = table_api_call(
            instance=self.instance,
            table=self.table_name,
            params={
                "sysparm_query": f"{self.field_name}={self.field_value}",
                "sysparm_fields": "sys_id",
            },
        )
        if len(result["result"]) > 0:
            db_delete_from_table(
                instance=self.instance,
                table=self.table_name,
                sys_id=self.record_sys_id,
            )


class DeleteUserTask(DeleteRecordTask):
    def __init__(self, instance=None, fixed_config=None, record_sys_id=None, **kwargs) -> None:
        super().__init__(
            instance=instance,
            start_rel_url="/now/nav/ui/classic/params/target/sys_user_list.do",
            list_name="Users",
            fixed_config=fixed_config,
            record_sys_id=record_sys_id,
            **kwargs,
        )
        if fixed_config is None:
            first_name = faker.first_name()
            last_name = faker.last_name()
            email = first_name.lower() + "." + last_name.lower() + "@workarena.com"
            self.fixed_config = {
                "field_name": "user_name",
                "pretty_printed_field_name": "User ID",
                "field_value": first_name + " " + last_name,
                "other_fields": {"email": email},
            }


class DeleteExpenseLineExpenseManagementTask(DeleteRecordTask):
    """
    Delete one row from the expense lines list

    Args:
    --------
    goal_type (str):
        The type of goal to generate. Choice of "base", "date", "amount", "any"
    level (int):
        The level of the task
    skip_description (bool):
        Whether to skip the description of the task

    """

    def __init__(
        self,
        instance=None,
        fixed_config=None,
        record_sys_id=None,
        goal_type="base",
        level=2,
        skip_description=False,
        **kwargs,
    ) -> None:
        super().__init__(
            instance=instance,
            start_rel_url="/now/nav/ui/classic/params/target/fm_expense_line_list.do",
            list_name="Expense Lines",
            fixed_config=fixed_config,
            record_sys_id=record_sys_id,
            **kwargs,
        )
        self.goal_type = goal_type
        self.level = level
        self.skip_description = skip_description

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in compositional tasks.
        called by subclasses
        """
        task_info = f"Delete expense lines with duplicated short descriptions"
        if self.skip_description:
            task_info = ""
        elif self.level == 3:
            task_info += f" according to the protocol."
        elif self.goal_type == "base":
            task_info += f" where the duplicated expense lines are not associated with tasks."
        elif self.goal_type == "date":
            task_info += f", keeping only the one that has the oldest date."
        elif self.goal_type == "amount":
            task_info += f", keeping only the most expensive duplicate."
        elif self.goal_type == "any":
            task_info += f", keeping only one."

        return task_info


class DeleteExpenseLineKnapsack(DeleteRecordTask):
    """
    Delete one row from the expense lines list

    Args:
    --------
    goal_type (str):
        The type of goal to generate. Choice of "base", "date", "amount", "any"
    answer_format (str):
        The type of answer to generate. Choice of total_return_only, total_return_and_investments, investments_only, cleanup, cleanup_and_return
    level (int):
        The level of the task
    skip_description (bool):
        Whether to skip the description of the task

    """

    def __init__(
        self,
        instance=None,
        fixed_config=None,
        record_sys_id=None,
        goal_type="base",
        level=2,
        answer_format=None,
        skip_description=False,
        **kwargs,
    ) -> None:
        super().__init__(
            instance=instance,
            start_rel_url="/now/nav/ui/classic/params/target/fm_expense_line_list.do",
            list_name="Expense Lines",
            fixed_config=fixed_config,
            record_sys_id=record_sys_id,
            **kwargs,
        )
        self.goal_type = goal_type
        self.level = level
        self.answer_format = answer_format
        self.skip_description = skip_description

    def get_pretty_printed_description(self) -> str:
        if self.skip_description:
            return ""
        if self.level == 3:
            task_info = "Allocate the budget to maximize revenue."
        elif self.level == 2:
            task_info = f"Allocate the budget to maximize revenue. This involves going over expense lines and identifying the ones maximizing revenue while fitting in the allowed budget of {self.budget}. The returns are written in their short description."
            if self.answer_format == "total_return_only":
                task_info += " Provide only the total return of the investments in the chat."
            if self.answer_format == "total_return_and_investments":
                task_info += " Provide the total return of the investments as well as the number of the investments in the chat."
            if self.answer_format == "investments_only":
                task_info += " Provide only the numbers of the investments in the chat."
            if self.answer_format == "cleanup":
                task_info += " Delete the investments that will not be kept so that only the selected investments remain."
            if self.answer_format == "cleanup_and_return":
                task_info += " Delete the investments that will not be kept so that only the selected investments remain as well as returning their total value in the chat."

        return task_info


__TASKS__ = [DeleteUserTask]
