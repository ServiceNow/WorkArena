"""
Tests that are not specific to any particular kind of task.

"""

import pytest
import json
import logging
import random

# bugfix: use same playwright instance in browsergym and pytest
from utils import setup_playwright
from playwright.sync_api import Page, TimeoutError
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from browsergym.workarena.config import ORDER_APPLE_WATCH_TASK_CONFIG_PATH

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.service_catalog import OrderAppleWatchTask


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.slow
def test_add_to_cart_disabled(page: Page):
    task_config = json.load(open(ORDER_APPLE_WATCH_TASK_CONFIG_PATH, "r"))[0]
    task = OrderAppleWatchTask(seed=1, fixed_config=task_config)
    # setup the task and try clicking on the "Add to cart button"
    task.setup(page=page)
    order_apple_watch_page = (
        task.instance.snow_url
        + "/now/nav/ui/classic/params/target/com.glideapp.servicecatalog_cat_item_view.do%3Fv%3D1%26sysparm_id%3D774906834fbb4200086eeed18110c737%26sysparm_link_parent%3Dd258b953c611227a0146101fb1be7c31%26sysparm_catalog%3De0d08b13c3330100c8b837659bba8fb4%26sysparm_catalog_view%3Dcatalog_default%26sysparm_view%3Dcatalog_default"
    )
    task.page.goto(order_apple_watch_page)
    task.page.wait_for_timeout(1000)
    iframe_element = task.page.wait_for_selector("#gsft_main")
    iframe = iframe_element.content_frame()
    task.teardown()
    # verify that Add to cart is disabled and order now is enabled
    assert iframe.locator('button[aria-label="Add to Cart"]').is_disabled()
    assert iframe.locator('button[aria-label="Order Now"]').is_enabled()


@retry(
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
@pytest.mark.slow
def test_top_items_panel_removed(page: Page):
    def check_top_items_panel(page: Page) -> bool:
        """Checks if the 'top items' panel exists on the landing page"""
        frame = page.wait_for_selector("iframe#gsft_main").content_frame()

        # Use evaluate to find divs containing an element with role="heading" and the text "Top Requests"
        panel_exists = frame.evaluate(
            """() => {
                const headings = Array.from(document.querySelectorAll('[role="heading"]'));
                let panelExists = false;
                headings.forEach((heading) => {
                    if (heading.textContent.includes("Top Requests")) {
                        panelExists = true;
                    }
                });
                return panelExists;
            }"""
        )

        return panel_exists

    # # Create a new task outside the service catalog and check if the Top Items panel exists
    # TODO: Uncomment this code and fix the test; it is currently failing, but the functionality is optional
    menu_task = AllMenuTask(seed=1)
    menu_task.setup(page=page)
    menu_task.page.goto(
        menu_task.instance.snow_url
        + r"/now/nav/ui/classic/params/target/catalog_home.do%3Fsysparm_view%3Dcatalog_default"
    )
    menu_task.page.wait_for_timeout(2000)
    panel_exists = check_top_items_panel(page=menu_task.page)
    menu_task.teardown()
    assert panel_exists is True

    service_catalog_task = OrderAppleWatchTask(seed=1)
    # Setup the task and check if the Top Items panel exists
    service_catalog_task.setup(page=page)
    service_catalog_task.page.wait_for_timeout(2000)
    panel_exists = check_top_items_panel(page=service_catalog_task.page)
    service_catalog_task.teardown()
    assert panel_exists is False
