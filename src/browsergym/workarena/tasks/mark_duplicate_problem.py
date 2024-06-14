import json

from playwright.sync_api import Page
from typing import Tuple

from .base import AbstractServiceNowTask
from .comp_building_block import CompositionalBuildingBlockTask

from ..api.utils import table_api_call


class SetProblemAsDuplicateTask(AbstractServiceNowTask, CompositionalBuildingBlockTask):
    """
    Set a problem as duplicate, assuming we start on the problems list view.

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
    respect_problem_ordering: bool
        Whether to respect the ordering of the problems in the list. If True, the task will pick the first problem in the
        list as the target problem. If False, the task validation will check if any problem is a duplicate of the other.
    add_comment: bool
        Whether or not to add comment to the duplicated task. If set to True, will add "Duplicate" as the problem description
    goal_version: str
        choice of "base", "priority", "high_priority". Adjusts the goal to the task setting for L2
    """

    def __init__(
        self,
        seed: int = None,
        instance=None,
        start_rel_url="/now/nav/ui/classic/params/target/problem_list.do",
        fixed_config: dict = None,
        respect_problem_ordering: bool = False,
        add_comment: bool = False,
        goal_version: str = "base",
        level: int = None,
        **kwargs,
    ) -> None:
        super().__init__(seed=seed, instance=instance, start_rel_url=start_rel_url)
        self.fixed_config = fixed_config
        self.config = fixed_config

        self.problem_sys_id = None
        self.respect_problem_ordering = respect_problem_ordering
        self.add_comment = add_comment
        self.goal_version = goal_version
        self.level = level
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        self.target_problem = self.fixed_config["target_problem"]
        self.source_problem = self.fixed_config["source_problem"]

        goal = self.get_pretty_printed_description()

        return goal, {}

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L2 compositional tasks.
        called by subclasses
        """

        if self.level == 3:
            task_info = " "
        elif self.goal_version == "base":
            task_info = "Mark problems with duplicated problem statements as such. You can mark any as duplicate of the other."
        elif self.goal_version == "priority":
            task_info = "Among the problems with duplicated problem statements, mark the lower priority one as duplicate of the higher priority one"
        elif self.goal_version == "high priority":
            task_info = "Among the problems with duplicated problem statements, mark any as duplicate of the other. Change the description of the problem marked as duplicate to 'duplicate'."

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        target_problem_number = self.target_problem["number"]

        frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
        # Search for the private task by search for the number
        frame.wait_for_selector(f"[aria-label='Preview record: {target_problem_number}']").click()
        page.wait_for_timeout(1500)
        # Click on the private task to open it
        frame.get_by_text("Open Record").click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state("networkidle")
        frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
        page.wait_for_timeout(1500)
        # Open the duplicate mode
        frame.get_by_text("Mark Duplicate").first.click()
        page.wait_for_timeout(1000)
        # Close the pop-up to edit the duplicate problem in the same window
        frame.get_by_text("Close").last.click()
        frame.locator('[aria-labelledby="label.problem.duplicate_of"]').fill(
            self.source_problem["number"]
        )
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)
        if self.add_comment:
            frame.locator('[id="problem.description"]').fill("Duplicate")

        frame.get_by_text("update").first.click()

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        """
        Validate the solution
        """
        target_problem_record = table_api_call(
            instance=self.instance,
            table="problem",
            params={"sysparm_query": f"number={self.target_problem['number']}"},
        )["result"]
        source_problem_record = table_api_call(
            instance=self.instance,
            table="problem",
            params={"sysparm_query": f"number={self.source_problem['number']}"},
        )["result"]
        # If the ordering can be anything, we check both problems
        problem_found = source_problem_record and target_problem_record

        if not problem_found:
            return 0, False, "", {"message": "Problem not found in DB."}

        # if the duplicate value is not set, the field will be an empty string; otherwise it will be a dict
        target_duplicate_value = target_problem_record[0]["duplicate_of"]
        if target_duplicate_value:
            target_duplicate_value = target_duplicate_value["value"]

        target_is_duplicate = target_duplicate_value == source_problem_record[0]["sys_id"]
        if self.respect_problem_ordering:
            problem_marked_as_duplicate = target_is_duplicate
        else:
            source_duplicate_value = source_problem_record[0]["duplicate_of"]
            if source_duplicate_value:
                source_duplicate_value = source_duplicate_value["value"]
            source_is_duplicate = source_duplicate_value == target_problem_record[0]["sys_id"]
            problem_marked_as_duplicate = target_is_duplicate or source_is_duplicate

        if self.add_comment:
            comment_added = (
                target_problem_record[0]["description"].lower() == "duplicate"
                and target_is_duplicate
            )
            if not self.respect_problem_ordering:
                comment_added = comment_added or (
                    source_problem_record[0]["description"].lower() == "duplicate"
                    and source_is_duplicate
                )
            if not comment_added:
                return 0, False, "", {"message": "Comment not added."}

        if not problem_marked_as_duplicate:
            return 0, False, "", {"message": "Problem not marked as duplicate."}

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "Problem task was closed as duplicate."},
        )


__TASKS__ = [SetProblemAsDuplicateTask]
