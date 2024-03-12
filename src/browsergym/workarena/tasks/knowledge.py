"""
Tasks related to knowledge bases.

"""

import json
import logging

from playwright.sync_api import Page

from .base import AbstractServiceNowTask
from ..config import KB_FILEPATH, KB_CONFIG_PATH, SNOW_BROWSER_TIMEOUT
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

    def __init__(self, instance=None, fixed_config: dict = None) -> None:
        super().__init__(
            instance=instance,
            start_rel_url="/now/nav/ui/classic/params/target/knowledge_home_launcher.do",
        )

        # Load the knowledge base and check its integrity
        with open(KB_FILEPATH, "r") as f:
            self.kb_entries = json.load(f)
        _, requires_install, requires_delete = check_knowledge_base(
            self.instance, kb_data=self.kb_entries
        )
        with open(KB_CONFIG_PATH, "r") as f:
            self.all_configs = json.load(f)
        if any([requires_install, requires_delete]):
            raise RuntimeError(
                f"The knowledge base in instance {self.instance.snow_url} is missing or corrupted. "
                "See README for setup instructions."
            )
        self.fixed_config = fixed_config

    def _wait_for_ready(self, page: Page) -> None:
        """
        Waits for the main iframe to be fully loaded

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

    def setup(self, page: Page, seed: int = None) -> tuple[str, dict]:
        self.pre_setup(seed, page)
        config = self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        self.item = config["item"]
        self.answer = config["value"]
        self.alternative_answers = config["alternative_answers"]
        self.question = config["question"]

        # generate goal
        goal = f'Answer the following question using the knowledge base: "{self.question}"'
        info = {}

        return goal, info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        self._wait_for_ready(page)

        iframe = page.frame(name="gsft_main")
        search = iframe.locator("input.form-control-search")
        search.fill(f'"{self.item}"')
        self.page.keyboard.press("Enter")

        # Click on the article
        with self.page.expect_navigation():
            iframe.locator(".kb_link").first.click()

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
                inner_html = inner_html.replace(
                    str(self.answer),
                    f'<span style="background-color: yellow;">{self.answer}</span>',
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
            return 1, True, "That is correct, thank you!", {"message": "Correct answer."}
        else:
            return 0, False, "", {"message": "Incorrect answer provided by the assistant."}


__TASKS__ = [KnowledgeBaseSearchTask]
