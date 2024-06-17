from faker import Faker

fake = Faker()

from playwright.sync_api._generated import Page

from .base import HumanEvalTask
from .filter_and_do import FilterAndDoTask

from ..mark_duplicate_problem import SetProblemAsDuplicateTask
from ..base import AbstractServiceNowTask

from ...api.problem import create_problem
from ...api.utils import db_delete_from_table, table_api_call
from ...config import (
    # Expected columns for the different lists
    EXPECTED_PROBLEM_COLUMNS_PATH,
)
from ...instance import SNowInstance


class FilterProblemsAndMarkDuplicatesTask(FilterAndDoTask):
    """Basic task to filter problems with a specific hashtag and mark them as duplicates."""

    def __init__(
        self,
        seed: int,
        extra_problems: int,
        navigation_config: dict,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config=navigation_config,
            level=level,
            protocol_name="Problem List Cleanup",
        )
        self.extra_problems = extra_problems  # Number of non-duplicates to create; total problems will be extra_problems + 2
        self.problem_priorities = [2, 2] + [
            1
        ] * extra_problems  # The first two problems will be duplicates with the same priority; the other ones will get top priority by default
        self.problem_sys_ids = []
        self.duplicate_problems = []

        self.problem_hashtag = "#SERIES-" + self.unique_id[:10]
        self.short_description = f"Clean-up your duplicate problems"
        self.task_description = f'Referring to company protocol "{self.protocol_name}" (located in the "Company Protocols" knowledge base) clean-up your problem list (problems assigned to you) by marking duplicate problems among those with hashtag {self.problem_hashtag}.'

    def _setup_list(self) -> None:
        duplicated_short_descripton = f"{fake.sentence(4)}"

        for i, priority in enumerate(self.problem_priorities):
            # The first two problems will have the same short description; the other ones will get random ones
            if i < 2:
                short_description = duplicated_short_descripton
            else:
                short_description = None

            problem_sys_id, problem_number = create_problem(
                instance=self.instance,
                problem_hashtag=self.problem_hashtag,
                priority=priority,
                user_sys_id=self._base_user_sysid,
                short_description=short_description,
                return_number=True,
            )
            self.problem_sys_ids.append(problem_sys_id)

            if i < 2:
                self.duplicate_problems.append({"number": problem_number, "sys_id": problem_sys_id})

        self.filter_config = {
            "list_url": "/now/nav/ui/classic/params/target/problem_list.do",
            "expected_fields_path": EXPECTED_PROBLEM_COLUMNS_PATH,
            "filter_columns": [
                "short_description",
            ],
            "filter_kind": "AND",
            "filter_operators": ["contains"],
            "filter_values": [
                f"{self.problem_hashtag}",
            ],
        }
        # the 'tasks' attribute needs to be defined by children classes

    def teardown(self) -> None:
        for problem_sys_id in self.problem_sys_ids:
            record_exists = table_api_call(
                instance=self.instance,
                table="problem",
                params={"sysparm_query": f"sys_id={problem_sys_id}"},
            )["result"]
            if record_exists:
                db_delete_from_table(
                    instance=self.instance,
                    table="problem",
                    sys_id=problem_sys_id,
                )
        super().teardown()


class BasicFilterProblemsAndMarkDuplicatesSmallTask(
    FilterProblemsAndMarkDuplicatesTask, HumanEvalTask
):
    """Basic task to filter problems with a specific hashtag and mark them as duplicates. This"""

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "Assigned to me",
                "application": "Problem",
            },
            level=level,
        )

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                is_validated=True,
                used_in_level_2=True,
                goal_version="base",
                level=self.level,
            ),
        ]


class BasicFilterProblemsAndMarkDuplicatesMediumTask(FilterProblemsAndMarkDuplicatesTask):
    """Basic task to filter problems with a specific hashtag and mark them as duplicates. This"""

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 4,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "Assigned to me",
                "application": "Problem",
            },
            level=level,
        )

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                is_validated=True,
                used_in_level_2=True,
                goal_version="base",
                level=self.level,
            ),
        ]


class BasicFilterProblemsAndMarkDuplicatesLargeTask(FilterProblemsAndMarkDuplicatesTask):
    """Basic task to filter problems with a specific hashtag and mark them as duplicates. This"""

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 6,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "Assigned to me",
                "application": "Problem",
            },
            level=level,
        )

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                is_validated=True,
                used_in_level_2=True,
                goal_version="base",
                level=self.level,
            ),
        ]


class PriorityFilterProblemsAndMarkDuplicatesSmallTask(
    FilterProblemsAndMarkDuplicatesTask, HumanEvalTask
):
    """Task to filter problems with a specific hashtag and mark the least priority one as duplicate of the first."""

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "All",
                "application": "Problem",
            },
            level=level,
        )
        self.problem_priorities = [1, 2] + [1] * extra_problems

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                respect_problem_ordering=True,
                is_validated=True,
                used_in_level_2=True,
                goal_version="priority",
                level=self.level,
            ),
        ]


class PriorityFilterProblemsAndMarkDuplicatesMediumTask(FilterProblemsAndMarkDuplicatesTask):
    """Task to filter problems with a specific hashtag and mark the least priority one as duplicate of the first."""

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 4,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "All",
                "application": "Problem",
            },
            level=level,
        )
        self.problem_priorities = [1, 2] + [1] * extra_problems

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                respect_problem_ordering=True,
                is_validated=True,
                used_in_level_2=True,
                goal_version="priority",
                level=self.level,
            ),
        ]


class PriorityFilterProblemsAndMarkDuplicatesLargeTask(FilterProblemsAndMarkDuplicatesTask):
    """Task to filter problems with a specific hashtag and mark the least priority one as duplicate of the first."""

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 6,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "All",
                "application": "Problem",
            },
            level=level,
        )
        self.problem_priorities = [1, 2] + [1] * extra_problems

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                respect_problem_ordering=True,
                is_validated=True,
                used_in_level_2=True,
                goal_version="priority",
                level=self.level,
            ),
        ]


class HighPriorityFilterProblemsAndMarkDuplicatesSmallTask(
    FilterProblemsAndMarkDuplicatesTask, HumanEvalTask
):
    """Task to filter problems with a specific hashtag and mark high priority items as duplicates. As
    a top priority item is marked as duplicate, we have to add a comment to it.
    """

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 2,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "All",
                "application": "Problem",
            },
            level=level,
        )
        self.problem_priorities = [1, 1] + [1] * extra_problems

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                respect_problem_ordering=False,
                is_validated=True,
                used_in_level_2=True,
                goal_version="high priority",
                level=self.level,
            ),
        ]


class HighPriorityFilterProblemsAndMarkDuplicatesMediumTask(FilterProblemsAndMarkDuplicatesTask):
    """Task to filter problems with a specific hashtag and mark high priority items as duplicates. As
    a top priority item is marked as duplicate, we have to add a comment to it.
    """

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 4,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "All",
                "application": "Problem",
            },
            level=level,
        )
        self.problem_priorities = [1, 1] + [1] * extra_problems

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                respect_problem_ordering=False,
                is_validated=True,
                used_in_level_2=True,
                goal_version="high priority",
                level=self.level,
            ),
        ]


class HighPriorityFilterProblemsAndMarkDuplicatesLargeTask(FilterProblemsAndMarkDuplicatesTask):
    """Task to filter problems with a specific hashtag and mark high priority items as duplicates. As
    a top priority item is marked as duplicate, we have to add a comment to it.
    """

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        extra_problems: int = 6,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            extra_problems=extra_problems,
            fixed_config=fixed_config,
            navigation_config={
                "module": "All",
                "application": "Problem",
            },
            level=level,
        )
        self.problem_priorities = [1, 1] + [1] * extra_problems

    def _setup_list(self) -> None:
        super()._setup_list()
        self.tasks = [
            SetProblemAsDuplicateTask(
                instance=self.instance,
                fixed_config={
                    "target_problem": self.duplicate_problems[1],
                    "source_problem": self.duplicate_problems[0],
                },
                respect_problem_ordering=False,
                is_validated=True,
                used_in_level_2=True,
                goal_version="high priority",
                level=self.level,
            ),
        ]


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type)
    and issubclass(var, FilterAndDoTask)
    and var is not FilterAndDoTask
    and var is not FilterProblemsAndMarkDuplicatesTask
]
