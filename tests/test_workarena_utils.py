"""
Tests for workarena utility functions.
"""
import pytest
from browsergym.workarena import get_all_tasks_agents
from browsergym.workarena.tasks.compositional import (
    AGENT_CURRICULUM_L2,
    AGENT_CURRICULUM_L3,
    HUMAN_CURRICULUM_L2,
    HUMAN_CURRICULUM_L3,
    specialize_task_class_to_level,
)
from browsergym.workarena.tasks.compositional.base import CompositionalTask
from browsergym.workarena.tasks.compositional.mark_duplicate_problems import (
    BasicFilterProblemsAndMarkDuplicatesSmallTask,
    PriorityFilterProblemsAndMarkDuplicatesSmallTask,
)
from browsergym.workarena.tasks.compositional.navigate_and_do_infeasible import (
    InfeasibleNavigateAndCreateUserWithReasonTask,
)


def get_tasks_from_curriculum(curriculum):
    """Helper function to extract all unique tasks from a curriculum."""
    all_tasks = set()
    for category, items in curriculum.items():
        for bucket in items["buckets"]:
            for task in bucket:
                all_tasks.add(task)
    return all_tasks


def test_get_all_tasks_agents():
    """Test that get_all_tasks_agents returns the correct tasks from the curricula."""
    # Test L1 filter (atomic tasks)
    tasks_with_seeds_l1 = get_all_tasks_agents(filter="l1")
    assert len(tasks_with_seeds_l1) > 0
    for task, seed in tasks_with_seeds_l1:
        assert not issubclass(task, CompositionalTask)
        assert isinstance(seed, int)

    # Test L2 Human Curriculum
    tasks_with_seeds_l2_human = get_all_tasks_agents(filter="l2", is_agent_curriculum=False)
    expected_l2_human_tasks = get_tasks_from_curriculum(HUMAN_CURRICULUM_L2)
    assert len(tasks_with_seeds_l2_human) > 0
    for task, seed in tasks_with_seeds_l2_human:
        assert task in expected_l2_human_tasks

    # Test L3 Human Curriculum
    tasks_with_seeds_l3_human = get_all_tasks_agents(filter="l3", is_agent_curriculum=False)
    expected_l3_human_tasks = get_tasks_from_curriculum(HUMAN_CURRICULUM_L3)
    assert len(tasks_with_seeds_l3_human) > 0
    for task, seed in tasks_with_seeds_l3_human:
        assert task in expected_l3_human_tasks

    # Test category filtering
    category = "planning_and_problem_solving"
    tasks_with_seeds_cat = get_all_tasks_agents(
        filter=f"l3.{category}", is_agent_curriculum=True
    )
    assert len(tasks_with_seeds_cat) > 0
    # Expected tasks from the specified category's buckets
    expected_cat_tasks = set()
    for bucket in AGENT_CURRICULUM_L3[category]["buckets"]:
        expected_cat_tasks.update(bucket)

    returned_tasks = {task for task, seed in tasks_with_seeds_cat}
    assert returned_tasks.issubset(expected_cat_tasks)

    # Check that tasks from other categories are not present
    for other_category, items in AGENT_CURRICULUM_L3.items():
        if other_category != category:
            for bucket in items["buckets"]:
                for task in bucket:
                    assert task not in returned_tasks

    # Test task_bucket filtering
    category = "planning_and_problem_solving"
    # This bucket contains BasicFilterProblemsAndMarkDuplicatesSmallTask
    bucket_to_test = AGENT_CURRICULUM_L3[category]["buckets"][0]

    tasks_with_seeds_bucket = get_all_tasks_agents(
        filter=f"l3.{category}", is_agent_curriculum=True, task_bucket=bucket_to_test
    )
    assert len(tasks_with_seeds_bucket) > 0

    returned_tasks_from_bucket = {task for task, seed in tasks_with_seeds_bucket}

    # 1. All returned tasks are from the specified bucket
    assert returned_tasks_from_bucket.issubset(set(bucket_to_test))

    # 2. A specific task from the bucket is present
    expected_task_base = BasicFilterProblemsAndMarkDuplicatesSmallTask
    # Find the specialized task in the bucket that corresponds to the base task
    expected_task_specialized = next(
        task
        for task in bucket_to_test
        if expected_task_base in task.__mro__
    )
    assert expected_task_specialized in returned_tasks_from_bucket

    # A task from a different category is not present
    unexpected_task = specialize_task_class_to_level(
        InfeasibleNavigateAndCreateUserWithReasonTask, level=3
    )
    assert unexpected_task not in returned_tasks_from_bucket

    # Test invalid filter
    with pytest.raises(Exception):
        get_all_tasks_agents(filter="invalid")

    # Test invalid category filter
    with pytest.raises(Exception):
        get_all_tasks_agents(filter="l3.invalid_category") 