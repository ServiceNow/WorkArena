import inspect
from browsergym.core.task import OpenEndedTask
from playwright.sync_api._generated import Page
from typing import Tuple


class SearchSamsungTask(OpenEndedTask):
    def setup(self, page: Page) -> tuple[str, dict]:
        page.goto(self.start_url, timeout=10000)
        return self.goal, {}

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

    def teardown(self) -> None:
        pass

    def validate(
        self, page: Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        reward, done, msg, info = 0, False, "", {}

        answer_str = "YES".lower()

        if chat_messages and chat_messages[-1]["role"] == "assistant":
            answer = chat_messages[-1]["message"].lower()

            if answer_str in answer:
                return 1.0, True, "Thank you for giving me the answer", {"message": f"Thank you for giving me the answer: {answer}"}
        else:
            return (
                0,
                False,
                "",
                {"message": "The assistant did not provide an answer."},
            )

        return 0.0, False, "", {"message": "The assistant did not provide an answer."}


class SearchSamsungGalaxyPhone(SearchSamsungTask):
    @classmethod
    def get_task_id(cls):
        return "other.search-samsung-galaxy-phone"

    def __init__(self, seed: int, start_url: str = "http://www.samsung.com/", goal: str = "Tell me how I replace the hard drive in my thinkpad t440") -> None:
        product = "galaxy s23 phones"
        goal = f"Please tell me whether {product} have AI features. Accept all cookies, if needed. Once you have the answer, send me a message with only YES or NO, and the URL where you found the answer."
        super().__init__(seed, start_url, goal)


class SearchSamsungGalaxyTabActive5(SearchSamsungTask):
    @classmethod
    def get_task_id(cls):
        return "other.search-samsung-galaxy-tab-active5"

    def __init__(self, seed: int, start_url: str = "http://www.samsung.com/", goal: str = "Tell me how I replace the hard drive in my thinkpad t440") -> None:
        product = "galaxy tab active5"
        goal = f"Please tell me whether {product} have AI features. Accept all cookies, if needed. Once you have the answer, send me a message with only YES or NO, and the URL where you found the answer."
        super().__init__(seed, start_url, goal)

    def validate(
        self, page: Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        reward, done, msg, info = 0, False, "", {}

        answer_str = "NO".lower()

        if chat_messages and chat_messages[-1]["role"] == "assistant":
            answer = chat_messages[-1]["message"].lower()

            if answer_str in answer:
                return 1.0, True, "Thank you for giving me the answer", {"message": f"Thank you for giving me the answer: {answer}"}
        else:
            return (
                0,
                False,
                "",
                {"message": "The assistant did not provide an answer."},
            )

        return 0.0, False, "", {"message": "The assistant did not provide an answer."}


class SearchSamsungOledTvs(SearchSamsungTask):

    @classmethod
    def get_task_id(cls):
        return "other.search-samsung-oled-tvs"

    def __init__(self, seed: int, start_url: str = "http://www.samsung.com/", goal: str = "Tell me how I replace the hard drive in my thinkpad t440") -> None:
        product = "oled tvs"
        goal = f"Please tell me whether {product} have AI features. Accept all cookies, if needed. Once you have the answer, send me a message with only YES or NO, and the URL where you found the answer."
        super().__init__(seed, start_url, goal)


local_vars = locals().copy()


__TASKS__ = [
    var
    for var in local_vars.values()
    if inspect.isclass(var)
    and (issubclass(var, SearchSamsungGalaxyPhone) or issubclass(var, SearchSamsungGalaxyTabActive5) or issubclass(var, SearchSamsungOledTvs))
]