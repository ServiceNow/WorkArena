"""Tests for sysverb_insert_and_stay normalization patches on create-record tasks.

Three patches work together to prevent sysverb_insert_and_stay from reaching the server
when an agent submits a new-record form, which would cause ServiceNow to auto-generate
fields like Number instead of preserving the user-supplied value:

  Patch 1 (JS, gsftSubmit): classic button path inside gsft_main iframe.
  Patch 2 (JS, Object.defineProperty): sys_action value setter — catches any code path
      including the outer React UI calling form.submit() after setting the action.
  Patch 3 (Playwright page.route): network-level catch-all for remaining paths.

Unit tests here require no ServiceNow instance.
Integration tests are marked @pytest.mark.slow and require a live instance.
"""

import json
import logging
from unittest.mock import MagicMock

import pytest
from tenacity import retry, retry_if_exception_type, stop_after_attempt

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright  # noqa: F401

from playwright.sync_api import Page, TimeoutError

from browsergym.workarena.config import (
    CREATE_CHANGE_REQUEST_CONFIG_PATH,
    CREATE_HARDWARE_CONFIG_PATH,
)
from browsergym.workarena.instance import SNowInstance, fetch_instances
from browsergym.workarena.tasks.form import CreateChangeRequestTask, CreateHardwareAssetTask

INSTANCE_POOL = fetch_instances()


# ---------------------------------------------------------------------------
# Unit tests — no browser, no ServiceNow instance
# ---------------------------------------------------------------------------


class _FakeRequest:
    def __init__(self, method: str, post_data: str | None):
        self.method = method
        self.post_data = post_data


def _make_task() -> CreateChangeRequestTask:
    """Return an uninitialised task instance suitable for calling the method under test."""
    return CreateChangeRequestTask.__new__(CreateChangeRequestTask)


def test_patch3_normalizes_sysverb_in_post_body():
    """_normalize_sysverb_in_post replaces sysverb_insert_and_stay with sysverb_insert."""
    task = _make_task()
    route = MagicMock()
    body = "sysparm_action=sysverb_insert_and_stay&number=CHG0000013"
    task._normalize_sysverb_in_post(route, _FakeRequest("POST", body))

    route.continue_.assert_called_once()
    call_kwargs = route.continue_.call_args.kwargs
    assert "sysverb_insert_and_stay" not in call_kwargs["post_data"]
    assert "sysverb_insert" in call_kwargs["post_data"]


def test_patch3_leaves_correct_sysverb_unchanged():
    """_normalize_sysverb_in_post does not modify bodies that already use sysverb_insert."""
    task = _make_task()
    route = MagicMock()
    body = "sysparm_action=sysverb_insert&number=CHG0000013"
    task._normalize_sysverb_in_post(route, _FakeRequest("POST", body))

    route.continue_.assert_called_once_with()  # called with no kwargs — body unchanged


def test_patch3_ignores_non_post_requests():
    """_normalize_sysverb_in_post passes GET requests through without modification."""
    task = _make_task()
    route = MagicMock()
    task._normalize_sysverb_in_post(route, _FakeRequest("GET", None))

    route.continue_.assert_called_once_with()


def test_patch3_handles_none_post_data():
    """_normalize_sysverb_in_post handles POST requests with no body gracefully."""
    task = _make_task()
    route = MagicMock()
    task._normalize_sysverb_in_post(route, _FakeRequest("POST", None))

    route.continue_.assert_called_once_with()


# ---------------------------------------------------------------------------
# Integration tests — require a live ServiceNow instance
# ---------------------------------------------------------------------------

if not INSTANCE_POOL:
    pytest.skip(
        "No ServiceNow instances available from fetch_instances().", allow_module_level=True
    )


@pytest.fixture(scope="session", params=INSTANCE_POOL, ids=[e["url"] for e in INSTANCE_POOL])
def snow_instance_entry(request):
    return request.param


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying after TimeoutError..."),
)
@pytest.mark.slow
def test_patch2_sys_action_setter_normalizes_value(page: Page, snow_instance_entry):
    """Patch 2: writing sysverb_insert_and_stay to sys_action reads back as sysverb_insert.

    Simulates what the outer React UI does when it sets the form action before calling
    form.submit() — verifies the Object.defineProperty setter intercepts correctly.
    """
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )
    task_config = json.load(open(CREATE_CHANGE_REQUEST_CONFIG_PATH))[0]
    task = CreateChangeRequestTask(seed=1, fixed_config=task_config, instance=instance)
    task.setup(page=page)

    # Access gsft_main via Playwright's content_frame() — gsft_main is nested inside
    # gsft_root and is not reachable from the outer page's document.getElementById.
    gsft_main = page.wait_for_selector("iframe#gsft_main").content_frame()
    result = gsft_main.evaluate(
        """() => {
        const form = document.querySelector('form');
        if (!form) return 'no_form';
        const sysAction = form.elements['sys_action'];
        if (!sysAction) return 'no_sys_action';
        sysAction.value = 'sysverb_insert_and_stay';
        return sysAction.value;
    }"""
    )

    task.teardown()
    assert (
        result == "sysverb_insert"
    ), f"Expected sys_action.value to be normalized to 'sysverb_insert', got {result!r}"


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying after TimeoutError..."),
)
@pytest.mark.slow
def test_patch3_route_intercepts_before_network(page: Page, snow_instance_entry):
    """Patch 3: sysverb_insert_and_stay never reaches the server.

    Registers a verification route *before* task setup (so it sits outermost in
    Playwright's LIFO stack and sees the already-normalized body), then simulates
    a programmatic form.submit() with sysverb_insert_and_stay and asserts no
    insert_and_stay verb appears in the POST that would have reached the server.
    """
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )
    task_config = json.load(open(CREATE_CHANGE_REQUEST_CONFIG_PATH))[0]
    task = CreateChangeRequestTask(seed=1, fixed_config=task_config, instance=instance)

    # Registered FIRST → fires LAST in LIFO → sees body after Patch 3 has normalized it.
    seen_insert_and_stay: list[str] = []

    def _verify_route(route, request):
        if request.method == "POST" and "sysverb_insert_and_stay" in (request.post_data or ""):
            seen_insert_and_stay.append(request.post_data)
        route.continue_()

    page.route("**", _verify_route)
    task.setup(page=page)  # Patch 3 registered SECOND → fires FIRST in LIFO

    # Simulate the React Submit path: set sys_action to insert_and_stay, then submit().
    page.evaluate(
        """() => {
        const iframe = document.getElementById('gsft_main');
        if (!iframe) return;
        const form = iframe.contentDocument.querySelector('form');
        if (!form) return;
        const sysAction = form.elements['sys_action'];
        if (sysAction) sysAction.value = 'sysverb_insert_and_stay';
        form.submit();
    }"""
    )
    page.wait_for_timeout(3000)

    task.teardown()
    page.unroute("**", _verify_route)

    assert seen_insert_and_stay == [], (
        f"sysverb_insert_and_stay reached the server in {len(seen_insert_and_stay)} request(s): "
        f"{seen_insert_and_stay[0][:200] if seen_insert_and_stay else ''}"
    )


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying after TimeoutError..."),
)
@pytest.mark.slow
@pytest.mark.parametrize(
    "task_cls,config_path",
    [
        (CreateChangeRequestTask, CREATE_CHANGE_REQUEST_CONFIG_PATH),
        (CreateHardwareAssetTask, CREATE_HARDWARE_CONFIG_PATH),
    ],
    ids=["create-change-request", "create-hardware-asset"],
)
def test_cheat_still_passes_after_patches(page: Page, snow_instance_entry, task_cls, config_path):
    """Sanity check: the existing cheat path (Patch 1) still produces reward=1.0.

    Verifies that the new patches do not break the classic sysverb_insert path used
    by cheat() and by agents that click the hidden #sysverb_insert button directly.
    Each task runs on a fresh page (pytest-playwright function-scoped fixture) to
    avoid state contamination between task types.
    """
    instance = SNowInstance(
        snow_url=snow_instance_entry["url"],
        snow_credentials=("admin", snow_instance_entry["password"]),
    )
    task_config = json.load(open(config_path))[0]
    task = task_cls(seed=1, fixed_config=task_config, instance=instance)
    task.setup(page=page)
    task.cheat(page=page, chat_messages=[])
    reward, done, _, _ = task.validate(page, [])
    task.teardown()
    assert reward == 1.0 and done is True, (
        f"{task_cls.__name__}: expected reward=1.0 done=True after cheat, "
        f"got reward={reward} done={done}"
    )
