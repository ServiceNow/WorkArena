# from .edit_knowledge_base import __TASKS__ as EDIT_KNOWLEDGE_BASE_TASKS, __L2_TASKS__ as EDIT_KNOWLEDGE_BASE_L2_TASKS, __L3_TASKS__ as EDIT_KNOWLEDGE_BASE_L3TASKS
from ..dash_do_catalog import (
    DASH_AND_ORDER,
    DASH_COMPUTE_MEAN_AND_ORDER,
    DASH_COMPUTE_MEDIAN_AND_ORDER,
    DASH_COMPUTE_MODE_AND_ORDER,
)
from ..dash_do_create_incident import DASH_AND_CREATE_INCIDENT, DASH_COMPUTE_AND_CREATE_INCIDENT
from ..dash_do_create_problem import DASH_AND_CREATE_PROBLEM, DASH_COMPUTE_AND_CREATE_PROBLEM
from ..dash_do_filter import (
    DASH_COMPUTE_MIN_FILTER_LIST,
    DASH_COMPUTE_MAX_FILTER_LIST,
    DASH_COMPUTE_MEAN_FILTER_LIST,
    DASH_COMPUTE_MEDIAN_FILTER_LIST,
    DASH_COMPUTE_MODE_FILTER_LIST,
)
from ..dash_do_request_item import (
    DASH_AND_REQUEST,
    DASH_COMPUTE_MEAN_AND_REQUEST,
    DASH_COMPUTE_MEDIAN_AND_REQUEST,
    DASH_COMPUTE_MODE_AND_REQUEST,
)
from ..expense_management import __TASKS__ as EXPENSE_MANAGEMENT_TASKS
from ..find_and_order_item import __TASKS__ as FIND_AND_ORDER_ITEM_TASKS
from ..manage_change_request_schedule import (
    SMALL_BASE_SCHEDULING_TASKS,
    LARGE_BASE_SCHEDULING_TASKS,
    SMALL_TIGHT_SCHEDULING_TASKS,
    LARGE_TIGHT_SCHEDULING_TASKS,
)
from ..mark_duplicate_problems import __TASKS__ as MARK_DUPLICATE_PROBLEMS_TASKS
from ..maximize_investment_return import __TASKS__ as MAXIMIZE_INVESTMENT_RETURN_TASKS
from ..navigate_and_do import (
    NAVIGATE_AND_CREATE_TASKS,
    NAVIGATE_AND_FILTER_TASKS,
    NAVIGATE_AND_ORDER_TASKS,
    NAVIGATE_AND_SORT_TASKS,
)
from ..navigate_and_do_infeasible import (
    INFEASIBLE_NAVIGATE_AND_CREATE_WITH_REASON,
    INFEASIBLE_NAVIGATE_AND_CREATE,
    INFEASIBLE_NAVIGATE_AND_ORDER_WITH_REASON,
    INFEASIBLE_NAVIGATE_AND_ORDER,
    INFEASIBLE_NAVIGATE_AND_FILTER_WITH_REASON,
    INFEASIBLE_NAVIGATE_AND_FILTER,
    INFEASIBLE_NAVIGATE_AND_SORT_WITH_REASON,
    INFEASIBLE_NAVIGATE_AND_SORT,
)
from ..offboard_user import __TASKS__ as OFFBOARD_USER_TASKS
from ..onboard_user import __TASKS__ as ONBOARD_USER_TASKS
from ..warranty_check import __TASKS__ as WARRANTY_CHECK_TASKS
from ..work_assignment import __TASKS__ as WORK_ASSIGNMENT_TASKS
from ..workload_balancing import __TASKS__ as WORKLOAD_BALANCING_TASKS

AGENT_CURRICULUM = {
    "planning_and_problem_solving": {
        "buckets": [
            MARK_DUPLICATE_PROBLEMS_TASKS,
            WORKLOAD_BALANCING_TASKS,
            WORK_ASSIGNMENT_TASKS,
            SMALL_BASE_SCHEDULING_TASKS,
            LARGE_BASE_SCHEDULING_TASKS,
            SMALL_TIGHT_SCHEDULING_TASKS,
            LARGE_TIGHT_SCHEDULING_TASKS,
        ],
        "num_seeds": 2,
        "weights": [9, 3, 6, 1, 1, 1, 1],
    },
    "information_retrieval": {
        "buckets": [
            DASH_AND_ORDER,
            DASH_AND_CREATE_INCIDENT,
            DASH_AND_CREATE_PROBLEM,
            DASH_COMPUTE_MIN_FILTER_LIST,
            DASH_COMPUTE_MAX_FILTER_LIST,
            DASH_AND_REQUEST,
            WARRANTY_CHECK_TASKS,
            FIND_AND_ORDER_ITEM_TASKS,
        ],
        "num_seeds": 7,
        "weights": [1, 1, 1, 1, 1, 1, 1, 1],
    },
    "data_driven_decision_making_and_reasoning": {
        "buckets": [
            EXPENSE_MANAGEMENT_TASKS,
            MAXIMIZE_INVESTMENT_RETURN_TASKS,
            DASH_COMPUTE_MEAN_AND_ORDER,
            DASH_COMPUTE_MEDIAN_AND_ORDER,
            DASH_COMPUTE_MODE_AND_ORDER,
            DASH_COMPUTE_AND_CREATE_INCIDENT,
            DASH_COMPUTE_AND_CREATE_PROBLEM,
            DASH_COMPUTE_MEAN_FILTER_LIST,
            DASH_COMPUTE_MEDIAN_FILTER_LIST,
            DASH_COMPUTE_MODE_FILTER_LIST,
            DASH_COMPUTE_MEAN_AND_REQUEST,
            DASH_COMPUTE_MEDIAN_AND_REQUEST,
            DASH_COMPUTE_MODE_AND_REQUEST,
        ],
        "num_seeds": 1,
        "weights": [12, 28, 1, 1, 1, 3, 3, 1, 1, 1, 1, 1, 1],
    },
    "sophisticated_memory": {
        "buckets": [
            NAVIGATE_AND_CREATE_TASKS,
            NAVIGATE_AND_ORDER_TASKS,
            NAVIGATE_AND_FILTER_TASKS,
            NAVIGATE_AND_SORT_TASKS,
            OFFBOARD_USER_TASKS,
            ONBOARD_USER_TASKS,
        ],
        "num_seeds": 8,
        "weights": [1, 1, 1, 1, 1, 1],
    },
    "contextual_understanding_infeasible_tasks": {
        "buckets": [
            INFEASIBLE_NAVIGATE_AND_CREATE_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_CREATE,
            INFEASIBLE_NAVIGATE_AND_ORDER_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_ORDER,
            INFEASIBLE_NAVIGATE_AND_FILTER_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_FILTER,
            INFEASIBLE_NAVIGATE_AND_SORT_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_SORT,
        ],
        "num_seeds": 4,
        "weights": [1, 1, 1, 1, 1, 1, 1, 1],
    },
}

HUMAN_CURRICULUM = {
    "planning_and_problem_solving": {
        "buckets": [
            MARK_DUPLICATE_PROBLEMS_TASKS,
            WORKLOAD_BALANCING_TASKS,
            WORK_ASSIGNMENT_TASKS,
            SMALL_BASE_SCHEDULING_TASKS,
            SMALL_TIGHT_SCHEDULING_TASKS,
        ],
        "num_seeds": 1,
        "weights": [
            3,
            1,
            2,
            1,
            1,
        ],
    },
    "information_retrieval": {
        "buckets": [
            DASH_AND_ORDER,
            DASH_AND_CREATE_INCIDENT,
            DASH_AND_CREATE_PROBLEM,
            DASH_COMPUTE_MIN_FILTER_LIST,
            DASH_COMPUTE_MAX_FILTER_LIST,
            DASH_AND_REQUEST,
            WARRANTY_CHECK_TASKS,
            FIND_AND_ORDER_ITEM_TASKS,
        ],
        "num_seeds": 1,
        "weights": [1, 1, 1, 1, 1, 1, 1, 1],
    },
    "data_driven_decision_making_and_reasoning": {
        "buckets": [
            EXPENSE_MANAGEMENT_TASKS,
            MAXIMIZE_INVESTMENT_RETURN_TASKS,  # Not splitting as small multiplier
            [
                *DASH_COMPUTE_MEAN_AND_ORDER,
                *DASH_COMPUTE_MEDIAN_AND_ORDER,
                *DASH_COMPUTE_MODE_AND_ORDER,
            ],
            [
                *DASH_COMPUTE_AND_CREATE_INCIDENT,
                *DASH_COMPUTE_AND_CREATE_PROBLEM,
                *DASH_COMPUTE_MEAN_AND_REQUEST,
            ],
            DASH_COMPUTE_MEAN_FILTER_LIST,
            [
                *DASH_COMPUTE_MEDIAN_FILTER_LIST,
                *DASH_COMPUTE_MODE_FILTER_LIST,
            ],
            [
                *DASH_COMPUTE_MEDIAN_AND_REQUEST,
                *DASH_COMPUTE_MODE_AND_REQUEST,
            ],
        ],
        "num_seeds": 1,
        "weights": [2, 6, 1, 1, 1, 1, 1],
    },
    "sophisticated_memory": {
        "buckets": [
            NAVIGATE_AND_CREATE_TASKS,
            NAVIGATE_AND_ORDER_TASKS,
            NAVIGATE_AND_FILTER_TASKS,
            NAVIGATE_AND_SORT_TASKS,
            OFFBOARD_USER_TASKS,
            ONBOARD_USER_TASKS,
        ],
        "num_seeds": 2,
        "weights": [1, 1, 1, 1, 1, 1],
    },
    "contextual_understanding_infeasible_tasks": {
        "buckets": [
            INFEASIBLE_NAVIGATE_AND_CREATE_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_CREATE,
            INFEASIBLE_NAVIGATE_AND_ORDER_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_ORDER,
            INFEASIBLE_NAVIGATE_AND_FILTER_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_FILTER,
            INFEASIBLE_NAVIGATE_AND_SORT_WITH_REASON,
            INFEASIBLE_NAVIGATE_AND_SORT,
        ],
        "num_seeds": 1,
        "weights": [1, 1, 1, 1, 1, 1, 1, 1],
    },
}
