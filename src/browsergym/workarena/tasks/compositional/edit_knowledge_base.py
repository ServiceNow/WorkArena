import html
import json
import random

from faker import Faker
from playwright.sync_api._generated import Page
from typing import Tuple

fake = Faker()

from ...api.knowledge import give_kb_read_permissions
from ...api.utils import table_api_call
from ..base import AbstractServiceNowTask
from .base import CompositionalTask
from ...config import KB_FILEPATH, PROTOCOL_KB_NAME
from ...instance import SNowInstance
from ..knowledge import KnowledgeBaseSearchTask, AddCommentToKnowledgeArticleTask
from ..navigation import AllMenuTask


class EditKnowledgeBaseTask(CompositionalTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 3,
    ) -> None:
        """
        Create a compositional task with specific subtasks

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of tuples, each containing a subtask, its configuration and whether or not it should be validated.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. e.g. "Referring to company protocol 'Edit a knowledge article', edit the knowledge base to handle the incorrect information: \n'
        short_description: str
            A short description of the task to be completed. e.g. "Edit knowledge base entries for address of parking lot."
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        self.protocol_name = "Edit a knowledge article to manage incorrect information"

        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            level=level,
            protocol_name=self.protocol_name,
            user_roles=["itil"],  # Required permission to access service desk for l3
        )
        with open(KB_FILEPATH, "r") as f:
            self.kb_entries = json.load(f)
        if not hasattr(self, "_base_initial_instance"):
            self._base_initial_instance = self.instance
        self.adhoc_kb_name = None
        self.task_description = None
        self.short_description = None

    def create_adhoc_kb(self):
        user_full_name = " ".join(self._base_user_name.split(".")[:-1])
        adhoc_kb_name = f"{user_full_name}'s Knowledge Base"
        self.adhoc_kb_name = adhoc_kb_name

        kb = table_api_call(
            instance=self._base_initial_instance,
            table="kb_knowledge_base",
            method="POST",
            data=json.dumps(
                {
                    "title": self.adhoc_kb_name,
                }
            ),
        )["result"]

        return kb["sys_id"]

    def get_random_article_name(self):
        kb = table_api_call(
            instance=self.instance,
            table="kb_knowledge",
            params={
                "sysparm_query": f"kb_knowledge_base={self.adhoc_kb_sys_id}",
                "sysparm_fields": "short_description",
            },
        )["result"]
        self.article_titles = [kb_article["short_description"] for kb_article in kb]

        article_date = fake.date_this_year().strftime("%Y-%m-%d")
        base_article_name = self.base_config["item"].capitalize()
        article_title = f"{base_article_name}-{article_date}"
        while article_title in self.article_titles:
            article_date = fake.date_this_year().strftime("%Y-%m-%d")
            article_title = f"{base_article_name}-{article_date}"

        return article_title

    def create_article(self, article_name, article_text):
        if article_name in self.article_titles:
            raise Exception("Article with the name already exists...")

        adhoc_kb_response = table_api_call(
            instance=self._base_initial_instance,  # admin permissions to contribute to the KB
            table="kb_knowledge",
            method="POST",
            data=json.dumps(
                {
                    "short_description": article_name,
                    "sys_class_name": "kb_knowledge",
                    "text": article_text,
                    "article_type": "text",
                    "kb_knowledge_base": self.adhoc_kb_sys_id,
                }
            ),
        )["result"]

        return adhoc_kb_response

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        # Create the KB
        self.adhoc_kb_sys_id = self.create_adhoc_kb()
        # Sample a configuration
        self.base_config = self.random.choice(self.kb_entries)
        self.incorrect_kb_article_name = self.get_random_article_name()
        self.correct_kb_article_name = self.get_random_article_name()
        self.item = self.base_config["item"]
        self.correct_answer = self.base_config["value"]

        self.incorrect_answer = " ".join(
            [fake.word() for _ in range(len(self.correct_answer.split()))]
        )  # Random incorrect answer with the same number of words as the correct answer

        incorrect_kb_article = self.create_article(
            self.incorrect_kb_article_name,
            self.base_config["article"].replace(self.correct_answer, self.incorrect_answer),
        )
        self.incorrect_kb_article_sys_id = incorrect_kb_article["sys_id"]
        self.incorrect_kb_article_number = incorrect_kb_article["number"]

        correct_kb_article = self.create_article(
            self.correct_kb_article_name, self.base_config["article"]
        )
        self.correct_kb_article_sys_id = correct_kb_article["sys_id"]
        self.correct_kb_article_number = correct_kb_article["number"]

        config = self.fixed_config if self.fixed_config else self._get_config()

        give_kb_read_permissions(
            self._base_initial_instance,
            self._base_user_sysid,
            self._base_user_name,
            self.adhoc_kb_sys_id,
            self.adhoc_kb_name,
        )

        if self.level == 3:
            protocol_kb_sys_id = table_api_call(
                instance=self._base_initial_instance,
                table="kb_knowledge_base",
                params={"sysparm_query": f"title={PROTOCOL_KB_NAME}"},
            )["result"][0]["sys_id"]
            give_kb_read_permissions(
                self._base_initial_instance,
                self._base_user_sysid,
                self._base_user_name,
                protocol_kb_sys_id,
                PROTOCOL_KB_NAME,
            )

        # Get the task description
        self.short_description = f"Edit knowledge base article for {self.item}"
        self.task_description = (
            f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) edit the knowledge base to handle incorrect information. \n'
            + f'Searching for "{self.item}" in the knowledge base gives different articles as the output: "{self.incorrect_kb_article_name}" with number "{self.incorrect_kb_article_number}" and "{self.correct_kb_article_name}" with number "{self.correct_kb_article_number}". \n'
            # + f'One of the articles has incorrect information "{self.incorrect_answer}" and the other one has the correct answer "{self.correct_answer}". \n'
            + f'The correct information for "{self.item}" should be {self.correct_answer}. '
        )

        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[tuple[AbstractServiceNowTask, dict, bool]]:
        """Add more extensive definition here."""

        self.incorrect_config = {
            "item": self.item,
            "kb_article_title": self.incorrect_kb_article_name,
            "value": self.incorrect_answer,
            "question": self.base_config["questions"][0],
            # "replaced_text": self.incorrect_answer,
            "comment": f"This article has incorrect information and is obsolete. Please refer to the article numbered {self.correct_kb_article_number} for reference.",
            "alternative_answers": [
                self.incorrect_answer,
            ],
        }

        self.correct_config = {
            "item": self.item,
            "kb_article_title": self.correct_kb_article_name,
            "value": self.correct_answer,
            "question": self.base_config["questions"][0],
            "comment": f"This article has correct information. Please DO NOT refer to the article numbered {self.incorrect_kb_article_number} for reference.",
            "alternative_answers": [
                self.correct_answer,
            ],
        }

        navigate_to_protocol_subtask = [
            # Navigate to the KB
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Knowledge",
                    "url": "/now/nav/ui/classic/params/target/%24knowledge.do",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
            # Find the protocol for on-boarding a new user
            KnowledgeBaseSearchTask(
                instance=self.instance,
                fixed_config={
                    "alternative_answers": [],
                    "item": f"{self.protocol_name}",
                    "question": 'Can you find the "Edit Knowledge Article Protocol" in the Knowledge Base?',
                    "value": "",
                },
                is_validated=False,
                used_in_level_2=False,
            ),
        ]

        search_and_comment_knowledge_base_incorrect_subtask = [
            # Navigate to the knowledge base home page
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Knowledge",
                    "url": "/now/nav/ui/classic/params/target/%24knowledge.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            KnowledgeBaseSearchTask(
                instance=self.instance,
                fixed_config=self.incorrect_config,
                is_validated=False,
                used_in_level_2=True,
                is_correct=False,
                is_only_navigating=True,
                search_by_title=True,
            ),
            # Search the knowledge base for the incorrect article
            AddCommentToKnowledgeArticleTask(
                instance=self.instance,
                fixed_config=self.incorrect_config,
                is_validated=False,
                used_in_level_2=True,
            ),
        ]

        search_and_comment_knowledge_base_correct_subtask = [
            # Navigate to the knowledge base home page
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "application": "Self-Service",
                    "module": "Knowledge",
                    "url": "/now/nav/ui/classic/params/target/%24knowledge.do",
                },
                is_validated=False,
                used_in_level_2=True,
            ),
            KnowledgeBaseSearchTask(
                instance=self.instance,
                fixed_config=self.correct_config,
                is_validated=False,
                used_in_level_2=True,
                is_only_navigating=True,
                search_by_title=True,
            ),
            # Search the knowledge base for the incorrect article
            AddCommentToKnowledgeArticleTask(
                instance=self.instance,
                fixed_config=self.correct_config,
                is_validated=False,
                used_in_level_2=True,
            ),
        ]

        config = (
            navigate_to_protocol_subtask
            + search_and_comment_knowledge_base_incorrect_subtask
            + search_and_comment_knowledge_base_correct_subtask
        )

        return config

    def validate(self, page: Page, chat_messages: list[str]) -> Tuple[float, bool, str, dict]:
        incorrect_article_kb_sys_id = table_api_call(
            instance=self.instance,
            table="kb_knowledge",
            params={
                "sysparm_query": f"short_description={self.incorrect_kb_article_name}",
            },
        )["result"][0]["sys_id"]

        incorrect_synonyms = [
            "incorrect",
            "wrong",
            "false",
            "inaccurate",
            "mistaken",
            "erroneous",
            "improper",
            "invalid",
            "untrue",
            "misleading",
            "off",
            "obsolete",
        ]
        incorrect_validated = 0
        all_comments = table_api_call(
            instance=self.instance,
            table="kb_feedback",
            params={
                "sysparm_query": f"article={incorrect_article_kb_sys_id}",
            },
        )["result"]

        for comment in all_comments:
            if (
                any(
                    incorrect_synonym.lower() in html.unescape(comment["comments"]).lower()
                    for incorrect_synonym in incorrect_synonyms
                )
                and comment["sys_created_by"] == self._base_user_name
                and self.correct_kb_article_number.lower()
                in html.unescape(comment["comments"]).lower()
            ):
                incorrect_validated = 1
                break

        correct_article_kb_sys_id = table_api_call(
            instance=self.instance,
            table="kb_knowledge",
            params={
                "sysparm_query": f"short_description={self.correct_kb_article_name}",
            },
        )["result"][0]["sys_id"]

        correct_synonyms = [
            "correct",
            "right",
            "accurate",
            "true",
            "exact",
            "precise",
            "proper",
            "valid",
            "factual",
            "appropriate",
            "verifiable",
            "up-to-date",
            "up to date",
        ]
        correct_validated = 0
        all_comments = table_api_call(
            instance=self.instance,
            table="kb_feedback",
            params={
                "sysparm_query": f"article={correct_article_kb_sys_id}",
            },
        )["result"]

        for comment in all_comments:
            if (
                any(
                    correct_synonym.lower() in html.unescape(comment["comments"]).lower()
                    for correct_synonym in correct_synonyms
                )
                and comment["sys_created_by"] == self._base_user_name
                and self.incorrect_kb_article_number.lower()
                in html.unescape(comment["comments"]).lower()
            ):
                correct_validated = 1
                break

        if incorrect_validated and correct_validated:
            # Validate final_l3 tasks
            reward, done, message, info = super().validate(page, chat_messages)
            return reward, done, message, info
        elif incorrect_validated and not correct_validated:
            return (
                0,
                False,
                "",
                {
                    "message": "Comment successfully added to the incorrect article but not the correct article."
                },
            )
        elif not incorrect_validated and correct_validated:
            return (
                0,
                False,
                "",
                {
                    "message": "Comment successfully added to the correct article but not the incorrect article."
                },
            )
        else:
            return (
                0,
                False,
                "",
                {
                    "message": "Comment not added to either the correct article or the incorrect article."
                },
            )

    def teardown(self) -> None:
        # Delete created articles
        table_api_call(
            instance=self._base_initial_instance,
            table=f"kb_knowledge/{self.incorrect_kb_article_sys_id}",
            method="DELETE",
        )
        table_api_call(
            instance=self._base_initial_instance,
            table=f"kb_knowledge/{self.correct_kb_article_sys_id}",
            method="DELETE",
        )

        # Archive knowledge base
        table_api_call(
            instance=self._base_initial_instance,
            table=f"kb_knowledge_base/{self.adhoc_kb_sys_id}",
            method="PATCH",
            json={"title": f"archived_{self.adhoc_kb_sys_id}", "active": "false"},
        )
        return super().teardown()


__TASKS__ = [EditKnowledgeBaseTask]
