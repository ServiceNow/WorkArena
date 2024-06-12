"""
Tasks related to knowledge bases.

"""

import json
import logging
import re

from playwright.sync_api import Page
from typing import Tuple
from urllib import parse

from .base import AbstractServiceNowTask
from .comp_building_block import CompositionalBuildingBlockTask
from .utils.utils import check_url_suffix_match

from ..api.utils import table_api_call
from ..config import KB_FILEPATH, KB_CONFIG_PATH, KB_NAME, SNOW_BROWSER_TIMEOUT
from ..install import check_knowledge_base
from ..instance import SNowInstance


class KnowledgeBaseSearchTask(AbstractServiceNowTask):
    """
    Generic task to create a search for information in the knowledge base.

    Parameters:
    -----------

    instance: SNowInstance
        The instance on which to create the record.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/knowledge_base_configs.json
        for an example of a configuration file.

    """

    def __init__(
        self,
        instance=None,
        fixed_config: dict = None,
        is_correct: bool = True,
        is_only_navigating: bool = False,
        search_by_title: bool = False,
        seed: int = None,
        **kwargs,
    ) -> None:
        """
        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config:
            A fixed configuration for the task, if required.
        is_correct: bool
            Used for the compositional task.
            If false, the answer is highlighted in 'red' instead of 'yellow' when using cheat.
        is_only_navigating: bool
            Used for the compositional task.
            If we only are navigating and not searching, change the goal for the agent.
        search_by_title: bool
            Used for the compositional task.
            If true, clicks on the article title using the article name, else opens the first article.
        """
        super().__init__(
            seed=seed,
            instance=instance,
            start_rel_url="/now/nav/ui/classic/params/target/kb?id=kb_home",
        )

        # Load the knowledge base and check its integrity
        with open(KB_FILEPATH, "r") as f:
            self.kb_entries = json.load(f)
        if hasattr(self, "_base_initial_instance"):
            _, requires_install, requires_delete = check_knowledge_base(
                self._base_initial_instance,  # if user does not have permission to view the kb then this breaks
                kb_name=KB_NAME,
                kb_data=self.kb_entries,  # Need admin permissions to check
            )
        else:
            _, requires_install, requires_delete = check_knowledge_base(
                SNowInstance(),  # instance would be the non-admin instance here and this might break in case user does not have required permissions
                kb_name=KB_NAME,
                kb_data=self.kb_entries,  # Need admin permissions to check
            )
        with open(KB_CONFIG_PATH, "r") as f:
            self.all_configs = json.load(f)
        if any([requires_install, requires_delete]):
            raise RuntimeError(
                f"The knowledge base in instance {self.instance.snow_url} is missing or corrupted. "
                "See README for setup instructions."
            )
        self.fixed_config = fixed_config
        self.config = None

        # Attributes for compositional task
        self.is_correct = is_correct
        self.is_only_navigating = is_only_navigating
        self.search_by_title = search_by_title

        self.__dict__.update(kwargs)

    def _wait_for_ready(self, page: Page) -> None:
        """
        Checks that the main iframe is fully loaded

        """
        # TODO: We don't use the flag-based method used in other tasks
        #       because gsft_main doesn't have the event we register
        #       on this page. Not sure why.
        logging.debug(f"Waiting for page to be fully loaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector('iframe[name="gsft_main"]')
        logging.debug(f"Detected page ready")

        # Get main iframe
        # XXX: We use a loop because sometimes the iframe evaluates to None
        #      even though we wait for it to be ready. This seems like a
        #      playwright bug.
        timeout = SNOW_BROWSER_TIMEOUT
        while timeout > 0:
            iframe = page.frame(name="gsft_main")
            if iframe:
                break
            page.wait_for_timeout(100)
            timeout -= 100
        else:
            raise TimeoutError(
                f"Timed out waiting for iframe to be ready in {self.instance.snow_url}"
            )

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get task configuration
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        self.item = config["item"]
        self.answer = config["value"]
        self.alternative_answers = config["alternative_answers"]
        self.question = config["question"]
        if self.search_by_title:
            self.kb_article_title = config["kb_article_title"]

        # Generate goal
        if self.is_only_navigating:
            goal = f'Navigate to a relevant article in the knowledge base by searching for: "{self.item}" and open the article: "{self.kb_article_title}"'
        else:
            goal = f'Answer the following question using the knowledge base: "{self.question}"'
        info = {}

        return goal, info

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        class_name = self.__class__.__name__
        class_name = class_name.replace("Task", "")
        # Split the words
        words = re.findall(r"[A-Z][^A-Z]*", class_name)
        class_name_formatted = " ".join(words)

        task_info = f"- {class_name_formatted}: {self.item} \n"

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        self._wait_for_ready(page)

        iframe = page.frame(name="gsft_main")
        search = iframe.locator('input[aria-label="Search"][role="textbox"]')
        search.fill(f'"{self.item}"')

        with page.expect_navigation():
            self.page.keyboard.press("Enter")

        # Click on the article
        with page.expect_navigation():
            if self.search_by_title:
                iframe.locator(f'a.kb-title:has-text("{self.kb_article_title}")').click()
            else:
                iframe.locator("a.kb-title").first.click()

        # Color the query and answer (this is just for visualization, it changes nothing to the validation)
        paragraphs = iframe.locator("p")
        for i in range(paragraphs.count()):
            paragraph = paragraphs.nth(i)
            inner_html = paragraph.inner_html()
            if self.item in inner_html:
                # Edit the inner html to change the background color of the answer
                inner_html = inner_html.replace(
                    self.item,
                    f'<span style="background-color: cyan;">{self.item}</span>',
                )
                if self.is_correct:
                    inner_html = inner_html.replace(
                        str(self.answer),
                        f'<span style="background-color: yellow;">{self.answer}</span>',
                    )
                else:
                    inner_html = inner_html.replace(
                        str(self.answer),
                        f'<span style="background-color: pink;">{self.answer}</span>',
                    )
                paragraph.evaluate(f"element => element.innerHTML = `{inner_html}`")
                break

        # Add the "extracted" answer to the chat messages
        # TODO: this is a hack, the message will not be displayed in the html
        chat_messages.append({"role": "assistant", "message": str(self.answer)})

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[float, bool, str, dict]:
        if chat_messages and chat_messages[-1]["role"] == "assistant":
            answer = chat_messages[-1]["message"]
        else:
            return (
                0,
                False,
                "",
                {"message": "The assistant did not provide an answer."},
            )

        accepted_answers = [a.lower() for a in [self.answer] + self.alternative_answers]
        answer = answer.lower()
        if any(a in answer for a in accepted_answers):
            return (
                1,
                True,
                "That is correct, thank you!",
                {"message": "Correct answer."},
            )
        else:
            return (
                0,
                False,
                "",
                {"message": "Incorrect answer provided by the assistant."},
            )


class AddCommentToKnowledgeArticleTask(AbstractServiceNowTask, CompositionalBuildingBlockTask):
    """
    Task to add a comment to a knowledge base article. Only used as a part of the compositional task for edit knowledge base
    Parameters:
    -----------
    instance: SNowInstance
        The instance on which to create the record.
    fixed_config: dict
        Configuration to use for the task.
    """

    def __init__(
        self, seed: int = None, instance=None, fixed_config: dict = None, **kwargs
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            start_rel_url="/now/nav/ui/classic/params/target/kb?id=kb_home",
            user_roles=[],
        )
        self.fixed_config = fixed_config
        if self.fixed_config is None:
            raise Exception("Please provide a config for the add comment task.")
        self.__dict__.update(kwargs)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)
        config = self.fixed_config

        if "kb_article_title" not in config.keys():
            raise Exception("Need title in config file...")
        self.article_name = config["kb_article_title"]
        adhoc_kb_response = table_api_call(
            instance=self.instance,  # admin permissions to contribute to the KB
            table="kb_knowledge",
            method="GET",
            params={
                "sysparm_query": f"short_description={self.article_name}",
            },
        )["result"]
        if len(adhoc_kb_response) != 1:
            raise Exception("Required article not found, please fix config...")

        self.kb_article_sys_id = adhoc_kb_response[0]["sys_id"]
        self.comment = config["comment"]

        goal = f'Add the following comment to the knowledge base: "{self.comment}"'
        info = {}

        return goal, info

    def _wait_for_ready(self, page: Page) -> None:
        """
        Checks that the main iframe is fully loaded

        """
        # TODO: We don't use the flag-based method used in other tasks
        #       because gsft_main doesn't have the event we register
        #       on this page. Not sure why.
        logging.debug(f"Waiting for page to be fully loaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector('iframe[name="gsft_main"]')
        logging.debug(f"Detected page ready")

        # Get main iframe
        # XXX: We use a loop because sometimes the iframe evaluates to None
        #      even though we wait for it to be ready. This seems like a
        #      playwright bug.
        timeout = SNOW_BROWSER_TIMEOUT
        while timeout > 0:
            iframe = page.frame(name="gsft_main")
            if iframe:
                break
            page.wait_for_timeout(100)
            timeout -= 100
        else:
            raise TimeoutError(
                f"Timed out waiting for iframe to be ready in {self.instance.snow_url}"
            )

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        class_name = self.__class__.__name__
        class_name = class_name.replace("Task", "")
        # Split the words
        words = re.findall(r"[A-Z][^A-Z]*", class_name)
        class_name_formatted = " ".join(words)

        task_info = f"- {class_name_formatted}: Add the comment '{self.comment}' for the article with title {self.article_name} \n"

        return task_info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)

        # Check if we need to do something else, gsft_main is not loading, it seems to load when navigating from the search, so might need for compositional tasks
        self._wait_for_ready(page)
        frame = page.frame("gsft_main")
        frame.locator("button.comment-text").click()
        frame.frame_locator('iframe[title="Rich Text Area"]').locator("html").click()
        frame.frame_locator('iframe[title="Rich Text Area"]').get_by_label("Comments").fill(
            self.comment
        )
        frame.get_by_role("button", name="Submit").click()

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        return super().validate(page, chat_messages)


__TASKS__ = [
    KnowledgeBaseSearchTask,
]
