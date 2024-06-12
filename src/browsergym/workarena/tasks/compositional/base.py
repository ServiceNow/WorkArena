import json
import time
import warnings

from typing import List, Tuple
from playwright.sync_api._generated import Page

from browsergym.workarena.config import PROTOCOL_KB_FILEPATH

from .update_task import UpdatePrivateTask

from ..base import AbstractServiceNowTask
from ..navigation import AllMenuTask

from ...instance import SNowInstance


class CompositionalTask(AbstractServiceNowTask):
    # Final private task instructions
    final_private_task_instructions = 'Don\'t forget to mark this task as "Closed - complete" once successfully completed. If the task appears infeasible, mark the task as "Closed - skipped" .'

    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        start_rel_url: str = "/now/nav/ui/home",
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        protocol_name: str = "",
        user_roles: List[str] = ["admin"],
    ) -> None:
        """
        Create a compositional task with specific subtasks

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        start_rel_url: str
            The relative URL to start the task from.
        fixed_config: list[AbstractServiceNowTask]
            A list of subtasks.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        protocol_name: str
            The name of the protocol to follow to complete the task; only used for level 3 tasks.
        user_roles: list[str]
            The roles to assign to the user (default: ["admin"])
        """
        super().__init__(
            seed=seed, instance=instance, start_rel_url=start_rel_url, user_roles=user_roles
        )
        # Set the task as completed in L3
        self.set_private_task_as_completed = True
        self.seed = seed

        self.fixed_config = fixed_config
        self.protocol_name = protocol_name
        self.task_description = ""
        self.short_description = ""

        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        if self.level == 2:
            start_rel_url = "/now/nav/ui/home"
        else:
            self.private_task_id = "PTSK" + str(id(self) % (10**8)).zfill(8)
            self.sys_id = None
            start_rel_url = ""  # For level 3 tasks, the start URL depends on the sys ID of the private task created for it

    def __len__(self) -> int:
        return len(self.subtasks)

    def setup_goal(
        self,
        page: Page,
        config: list[AbstractServiceNowTask],
        build_pretty_print_description: bool = True,
    ) -> tuple[str, str, dict]:
        super().setup_goal(page=page)
        # Index to keep track of the task we are currently validating
        self.valid_index = 0

        # Setup all the subtasks
        self.subtasks = []
        self.subgoals = []
        for task in config:
            if (
                self.level == 2 and not task.used_in_level_2
            ):  # Skip tasks that are not used in level 2; e.g. navigate to the company protocol
                continue
            self.subtasks.append(task)
            self.subgoals.append(self.subtasks[-1].setup(page=page, do_start=False)[0])

        if self.level == 3:
            if build_pretty_print_description:
                self._build_pretty_printed_description(config)
            level_3_final_tasks = [
                # Navigate to the My Work task list
                AllMenuTask(
                    instance=self.instance,
                    fixed_config={
                        "application": "Service Desk",
                        "module": "My Work",
                        "url": "/now/nav/ui/classic/params/target/task_list.do%3Fsysparm_userpref_module%3D1523b8d4c611227b00be8216ec331b9a%26sysparm_query%3Dactive%253Dtrue%255Eassigned_to%253Djavascript%253AgetMyAssignments%2528%2529%255Estate%2521%253D-5%255EEQ",
                    },
                    is_validated=False,
                    used_in_level_2=False,
                ),
                # Close the private task
                UpdatePrivateTask(
                    instance=self.instance,
                    fixed_config={
                        "task_description": self.task_description,
                        "short_description": self.short_description,
                    },
                    set_as_completed=self.set_private_task_as_completed,
                    is_validated=True,
                    used_in_level_2=False,
                ),
            ]
            self.subtasks.extend(level_3_final_tasks)
            # Set identical user credentials for all subtasks
            for task in self.subtasks:
                task._base_initial_instance = self.instance
                task._base_user_name, task._base_user_password, task._base_user_sysid = (
                    self._base_user_name,
                    self._base_user_password,
                    self._base_user_sysid,
                )
                task.instance = self.instance
                task.instance.snow_credentials = (self._base_user_name, self._base_user_password)

            # Finish the setup with the L3-specific tasks
            for task in self.subtasks[-2:]:
                task.setup(page=page, do_start=False)
            # The sys ID of the private task is the sys ID of the last task in the list
            self.sys_id = level_3_final_tasks[-1].sys_id

            self.start_url = (
                self.instance.snow_url
                + f"/now/nav/ui/classic/params/target/vtb_task.do%3Fsys_id%3D{self.sys_id}"
            )

        # For level 2, include all substeps in the goal
        # For level 3, the goal is already set in the private task
        if self.level == 2:
            task_intro = self.short_description + "\n"
            # Get the protocol to follow for the task and pre-pend it to the goal
            goal = task_intro
            goal += " \n Concretely, you need to complete the following steps:"

            # In some cases, more than one subtasks with identical subgoals are present and the duplicated tasks have empty goals
            # These multiple tasks are used to provide a complete cheat for the tasks like ManageChangeRequestScheduleTask subclasses
            # To avoid having empty steps in the enumeration, we check if the goal is empty and skip if it is
            i = 1
            for subgoal in self.subgoals:
                if not subgoal:
                    continue
                goal += f"\n{i}. {subgoal}"
                i += 1

        elif self.level == 3:
            goal = f"Please complete the following task."

        return goal, {}

    def _get_config(self) -> list[AbstractServiceNowTask]:
        """
        Get a configuration for a given compositional task, in the form of a list subtasks.
        """
        raise NotImplementedError("This method should be implemented in a subclass")

    def cheat(self, page: Page, chat_messages: list[str], subtask_idx: int) -> None:
        """
        Solve the a subtask of the task

        Parameters:
        ----------
        page: Page
            The page to solve the task on
        chat_messages: list[str]
            The list of messages in the chat
        subtask_idx: int
            The index of the subtask to solve.

        Note:
        -----
        * We proceed separately for each subtask since this enables validation of each subtask separately.
          This is useful for certifying the feasibility of tasks in the benchmark. Otherwise, cheat would
          bring us to the final state of the task, which would make it impossible to validate subtasks.
        * Use len(self) to get the number of subtasks in the task.

        """
        super().cheat(page, chat_messages)
        self.subtasks[subtask_idx].cheat(page, chat_messages)

    def _build_pretty_printed_description(self, config: list[AbstractServiceNowTask]) -> str:
        """
        Get the task information for the private task description; used for level 3 tasks.
        Args:
        config: list[AbstractServiceNowTask]
            The list of subtasks in the task
        """
        for subtask in config:
            if subtask.is_validated or subtask.has_description:
                self.task_description += subtask.get_pretty_printed_description()
                self.task_description += "\n"
        self.task_description += self.final_private_task_instructions

        return self.task_description

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        super().validate(page, chat_messages)

        # Initialize the index of the first subtask that requires validation
        while (
            self.valid_index < len(self.subtasks)
            and not self.subtasks[self.valid_index].is_validated
        ):
            self.valid_index += 1

        if self.valid_index == len(self.subtasks):
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "Task completed successfully."},
            )
        # Validate the current subtask
        subtask = self.subtasks[self.valid_index]
        reward, stop, info, message = subtask.validate(page, chat_messages)

        # If the subtask is valid
        if reward >= 1.0:
            # ... override the info and message to avoid success messages from the subtask
            info = message["message"] = (
                f"Step {self.valid_index + 1} has been completed successfully."
            )
            # ... this is a subtask, so we don't want to stop
            stop = False
            # ... increment index to flag this one as solved
            self.valid_index += 1

        # If the subtask is not valid
        else:
            # ... contextualize the info and message per subtask
            info = f"Step {self.valid_index + 1}: " + info
            message["message"] = f"Step {self.valid_index + 1}: " + message.get("message", "")

        # Check if all subtasks are solved
        if self.valid_index == len(self.subtasks):
            return (
                1,
                True,
                "Nice work, thank you!",
                {"message": "Task completed successfully."},
            )

        return 0, stop, info, message

    def teardown(self) -> None:
        # XXX: In base.py we define the teardown method as being independent of the
        #      current state of the page. This means that we can just call all the
        #      subtasks' teardown methods.
        for task in self.subtasks:
            task.teardown()
        super().teardown()


class InfeasibleCompositionalTask(CompositionalTask):
    """
    Base class for infeasible tasks.

    Args:
    --------
    infeasible_reason (List[str]):
        The reason why the task is infeasible. If a task is infeasible, the validation will look for one of the reasons in the chat messages.
        set by children classes.
    """

    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        start_rel_url: str = "/now/nav/ui/home",
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        protocol_name: str = "",
        user_roles: List[str] = ["admin"],
        infeasible_reasons: List[str] = [""],
        provide_reason: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            start_rel_url=start_rel_url,
            fixed_config=fixed_config,
            level=level,
            protocol_name=protocol_name,
            user_roles=user_roles,
        )
        # Set the private task as closed-skipped in L3 tasks
        self.set_private_task_as_completed = False
        self.provide_reason = provide_reason
        self.infeasible_reasons = infeasible_reasons
        self.infeasible_reason_found = (
            False  # flag to check if the infeasible reason was found in the chat messages
        )
        self.__dict__.update(kwargs)

    def cheat(self, page: Page, chat_messages: list[str], subtask_idx: int) -> None:
        """Add the infeasible reasons to the chat messages"""
        # Index of the infeasible task that requires sending a message in the chat for the cheat
        # for L2 tasks, the last task is the infeasible one, whereas for L3 tasks, third from last is infeasible
        cheat_index = len(self.subtasks) - 1 if self.level == 2 else len(self.subtasks) - 3
        # We expect the last task of the trajectory to be infeasible. Therefore, we do all but the last cheat step
        if subtask_idx != cheat_index:
            super().cheat(page, chat_messages, subtask_idx)
        else:
            message = ", ".join(self.infeasible_reasons)
            chat_messages.append({"role": "infeasible", "message": message})

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        """Check if the infeasible reasons are in the chat messages"""
        if chat_messages and chat_messages[-1]["role"] == "infeasible":
            answer = chat_messages[-1]["message"].lower()
        else:
            return (
                0,
                False,
                "",
                {"message": "The assistant did not provide an answer."},
            )
        if self.provide_reason and answer == "":
            return (
                0,
                False,
                "",
                {"message": "The assistant did not provide a reason for the infeasibility."},
            )
        if not self.infeasible_reason_found:
            for reason in self.infeasible_reasons:
                if reason.lower() in answer:
                    self.infeasible_reason_found = True
                    break
            if not self.infeasible_reason_found:
                return (
                    0,
                    False,
                    "",
                    {"message": "The assistant did not provide the correct answer."},
                )

        return super().validate(page, chat_messages)


class HumanEvalTask:
    """Base class to label tasks suitable for human evaluation."""

    pass
