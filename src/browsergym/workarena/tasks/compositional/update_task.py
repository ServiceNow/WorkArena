from playwright.sync_api import Page
from typing import List, Tuple

from ..base import AbstractServiceNowTask
from ..comp_building_block import CompositionalBuildingBlockTask
from ..utils.utils import check_url_suffix_match
from ..utils.private_tasks import create_private_task_and_get_sys_id

from ...api.utils import db_delete_from_table, table_api_call


class UpdatePrivateTask(AbstractServiceNowTask, CompositionalBuildingBlockTask):
    """
    Set a private task to complete, assuming we start on the task viewed as form.

    Parameters:
    -----------
    instance: SNowInstance
        The instance to use.
    start_rel_url: str
        The relative URL of the task list.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/filter_change_request_list_task.json
        for an example of a configuration file.
    set_as_completed: bool
        Whether the task should be marked as complete or not. If True, the task will be marked as complete; otherwise, marked as.
        used to set infeasible tasks to incomplete.
    """

    def __init__(
        self,
        seed: int = None,
        instance=None,
        start_rel_url="/now/nav/ui/classic/params/target/task_list.do%3Fsysparm_userpref_module%3D1523b8d4c611227b00be8216ec331b9a%26sysparm_query%3Dactive%253Dtrue%255Eassigned_to%253Djavascript%253AgetMyAssignments%2528%2529%255Estate%2521%253D-5%255EEQ",
        fixed_config: dict = None,
        set_as_completed: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(seed=seed, instance=instance, start_rel_url=start_rel_url)
        self.fixed_config = fixed_config
        self.config = fixed_config
        self.set_as_completed = set_as_completed
        # 3 is the state for "Closed-Complete", 4 is "Closed-Incomplete", 7 is "Closed-Skipped"
        self.allowed_options = ["3"] if self.set_as_completed else ["4", "7"]
        self.private_task_id = "PTSK" + str(id(self) % (10**8)).zfill(8)
        if self.fixed_config is None:
            self.config = {
                "task_description": "Close private task",
                "short_description": self.private_task_id,
            }
        self.sys_id = None
        self.task_rel_url = None  # Relative URL of the task in form view
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        task_description = self.config["task_description"]
        short_description = self.config["short_description"]
        self.sys_id = create_private_task_and_get_sys_id(
            self.instance,
            page,
            self.private_task_id,
            task_description,
            short_description,
            user_sys_id=self._base_user_sysid,
        )
        self.task_rel_url = (
            f"/now/nav/ui/classic/params/target/vtb_task.do%3Fsys_id%3D{self.sys_id}"
        )
        goal = f"Close private task {self.private_task_id}"

        return goal, {}

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        task_info = "Don't forget to mark this task as complete once you're done."

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
        # Search for the private task by search for the number
        frame.get_by_label("Search a specific field of the Tasks list").select_option("number")
        search_input = frame.locator('input[aria-label="Search"]')
        search_input.click()
        search_input.fill(self.private_task_id)
        search_input.press("Enter")
        page.wait_for_timeout(1500)
        # Click on the private task to open it
        frame.get_by_label(f"Open record: {self.private_task_id}").click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
        page.wait_for_timeout(1500)
        # Click on the task state, select "Closed-Complete" if complete, else "Closed Skipped" and update the task
        option = "3" if self.set_as_completed else "7"
        frame.get_by_label("state").first.select_option(option)
        frame.get_by_text("update").first.click()
        # Wait for record to be updated in the DB
        record_updated = False
        while not record_updated:
            record = table_api_call(
                instance=self.instance,
                table="vtb_task",
                params={"sysparm_query": f"task_effective_number={self.private_task_id}"},
            )["result"]
            record_updated = record[0]["state"] == option
        page.wait_for_timeout(1000)

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        """
        Validate the solution
        """
        record = table_api_call(
            instance=self.instance,
            table="vtb_task",
            params={"sysparm_query": f"task_effective_number={self.private_task_id}"},
        )["result"]
        if not record:
            return 0, False, "", {"message": "Private task not found."}
        if record[0]["state"] not in self.allowed_options:
            return 0, False, "", {"message": "Private task not closed appropriately."}

        return 1, True, "Nice work, thank you!", {"message": "Private task was closed."}

    def teardown(self) -> None:
        record_exists = table_api_call(
            instance=self.instance,
            table="vtb_task",
            params={"sysparm_query": f"sys_id={self.sys_id}"},
        )["result"]
        if record_exists:
            db_delete_from_table(
                instance=self.instance,
                table="vtb_task",
                sys_id=self.sys_id,
            )
        super().teardown()


__TASKS__ = [UpdatePrivateTask]
