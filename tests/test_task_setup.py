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
    task = OrderAppleWatchTask(fixed_config=task_config)
    # setup the task and try clicking on the "Add to cart button"
    task.setup(page=page)
    order_apple_watch_page = (
        task.instance.snow_url
        + "/now/nav/ui/classic/params/target/com.glideapp.servicecatalog_cat_item_view.do%3Fv%3D1%26sysparm_id%3D774906834fbb4200086eeed18110c737%26sysparm_link_parent%3Dd258b953c611227a0146101fb1be7c31%26sysparm_catalog%3De0d08b13c3330100c8b837659bba8fb4%26sysparm_catalog_view%3Dcatalog_default%26sysparm_view%3Dcatalog_default"
    )
    task.page.goto(order_apple_watch_page)
    page.wait_for_timeout(1000)
    iframe_element = task.page.wait_for_selector("#gsft_main")
    iframe = iframe_element.content_frame()

    # verify that Add to cart is disabled and order now is enabled
    assert iframe.locator('button[aria-label="Add to Cart"]').is_disabled()
    assert iframe.locator('button[aria-label="Order Now"]').is_enabled()


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

    task_config = json.load(open(ORDER_APPLE_WATCH_TASK_CONFIG_PATH, "r"))[0]
    task = OrderAppleWatchTask(fixed_config=task_config)

    # Setup the task and check if the Top Items panel exists
    task.setup(page=page)
    panel_exists = check_top_items_panel(page=page)
    page.wait_for_timeout(2000)
    assert panel_exists is False
    # Reload the page and check if the Top Items panel exists
    page.goto(task.start_url)
    page.wait_for_timeout(2000)
    panel_exists = check_top_items_panel(page=page)
    assert panel_exists is True
