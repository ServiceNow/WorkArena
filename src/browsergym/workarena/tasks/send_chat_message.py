from typing import Tuple
from playwright.sync_api import Page

from .base import AbstractServiceNowTask
from .comp_building_block import CompositionalBuildingBlockTask

from ..instance import SNowInstance


class SendChatMessageTask(AbstractServiceNowTask, CompositionalBuildingBlockTask):
    """Task to send a chat message in the chat. Only used as a compositional building block for the cheat function.
    Args:
    --------
    message (str):
        The message to send in the chat
    answer_format (str):
        The type of answer to generate. Choice of total_return_only, total_return_and_investments, investments_only, cleanup, cleanup_and_return
    """

    def __init__(
        self,
        instance: SNowInstance,
        message: str,
        answer_format: str,
        use_description_in_l3: bool = False,
        **kwargs,
    ):
        super().__init__(seed=0, instance=instance, start_rel_url="")
        self.message = message
        self.answer_format = answer_format
        self.use_description_in_l3 = use_description_in_l3
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page):
        return self.get_pretty_printed_description(), {}

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float | bool | str | dict]:
        return super().validate(page, chat_messages)

    def cheat(self, page: Page, chat_messages: list[str]):
        super().cheat(page=page, chat_messages=chat_messages)
        chat_messages.append({"role": "assistant", "message": str(self.message)})

    def teardown(self) -> None:
        pass

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in compositional tasks.
        """
        raise NotImplementedError


class SendChatMessageForBudgetAllocationTask(SendChatMessageTask):
    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in compositional tasks.
        """
        if self.level == 3:
            task_info = "Allocate the budget to maximize revenue."
        elif self.level == 2:
            task_info = f"Allocate the budget to maximize revenue. This involves going over expense lines and identifying the ones maximizing revenue while fitting in the allowed budget of {self.budget} $. The returns are written in their short description."
            if self.answer_format == "total_return_only":
                task_info += " Provide only the total return of the investments in the chat."
            if self.answer_format == "total_return_and_investments":
                task_info += " Provide the total return of the investments as well as the value of their 'Number' field in the chat."
            if self.answer_format == "investments_only":
                task_info += " Provide only the value of the 'Number' field of the selected investments in the chat."
            if self.answer_format == "cleanup":
                task_info += " Delete the investments that will not be kept so that only the selected investments remain."
            if self.answer_format == "cleanup_and_return":
                task_info += " Delete the investments that will not be kept so that only the selected investments remain as well as returning their total value in the chat."

        return task_info


class SendChatMessageGenericTask(SendChatMessageTask):

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in compositional tasks.
        """
        if self.use_description_in_l3:
            task_info = self.description
        elif self.level == 3:
            task_info = ""
        elif self.level == 2:
            task_info = self.description

        return task_info
