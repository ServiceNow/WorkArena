import json
import os

from playwright.sync_api import sync_playwright


# Load environment variables
SNOW_INSTANCE_URL = os.getenv("SNOW_INSTANCE_URL")
SNOW_INSTANCE_UNAME = os.getenv("SNOW_INSTANCE_UNAME")
SNOW_INSTANCE_PWD = os.getenv("SNOW_INSTANCE_PWD")

# ==================================================================================================================
# This file is a script that extracts all the menu tasks from the ServiceNow instance. It uses                     #
# Playwright to navigate to the ServiceNow instance, log in, and extract all the menu items.  It then saves        #
# menu items to a JSON file. The extracted menu items can be used to create tasks for the WorkArena benchmark.     #
# ==================================================================================================================


if __name__ == "__main__":

    base_paths = []
    seen = dict()

    def close_all_paths(page, parent_selector="body", current_path=[]):
        """Recursively expand all menu items"""
        # Select all collapsible lists, regardless of whether they are expanded or not
        collapsible_lists = page.query_selector_all(
            f"{parent_selector} .snf-collapsible-list > .snf-collapsible-list-header"
        )
        for list_header in collapsible_lists:
            aria_label = list_header.get_attribute("aria-label")
            aria_expanded = list_header.get_attribute("aria-expanded")

            new_path = current_path + [aria_label] if aria_label else current_path

            if aria_expanded == "true":
                # If the list is not expanded, click to expand it
                list_header.click()
                page.wait_for_timeout(500)
                # Depending on the page, you might need to wait here for the list to actually expand

            # Get the unique identifier for the list to target nested lists within it
            data_id = list_header.get_attribute("data-id")
            nested_parent_selector = f".snf-collapsible-list-items[data-id='{data_id}-rows']"

            # Recursively handle nested lists, now that the current list has been expanded
            close_all_paths(page, nested_parent_selector, new_path)

    def expand_and_gather_paths(page, parent_selector="body", current_path=[]):
        """Recursively expand all menu items"""
        # Select all collapsible lists, regardless of whether they are expanded or not
        collapsible_lists = page.query_selector_all(
            f"{parent_selector} .snf-collapsible-list > .snf-collapsible-list-header"
        )
        for list_header in collapsible_lists:
            aria_label = list_header.get_attribute("aria-label")
            aria_expanded = list_header.get_attribute("aria-expanded")

            new_path = current_path + [aria_label] if aria_label else current_path

            if aria_expanded == "false":
                # If the list is not expanded, click to expand it
                list_header.click()
                page.wait_for_timeout(3000)
                # Depending on the page, you might need to wait here for the list to actually expand

            # Get the unique identifier for the list to target nested lists within it
            data_id = list_header.get_attribute("data-id")
            nested_parent_selector = f".snf-collapsible-list-items[data-id='{data_id}-rows']"

            # Recursively handle nested lists, now that the current list has been expanded
            expand_and_gather_paths(page, nested_parent_selector, new_path)

        if not collapsible_lists:
            current_path_item = {"path": current_path.copy(), "selector": parent_selector}
            base_paths.append(current_path_item)

    def expand_menu():
        menu_button = page.locator('div[aria-label="All"]')
        if menu_button.get_attribute("aria-expanded").lower() != "true":
            menu_button.click()

    def pin_menu():
        pin_menu_button_locator = page.locator('button[aria-label="Pin All menu"]')
        if pin_menu_button_locator.count():
            pin_menu_button_locator.click()

    def unpin_menu():
        unpin_menu_button_locator = page.locator('button[aria-label="Unpin All menu"]')
        if unpin_menu_button_locator.count():
            unpin_menu_button_locator.click()

    def scroll_to_menu_bottom():
        locator = None
        # Wait for the menu to load and locate an item
        while locator is None:
            locator = page.query_selector(
                f" .snf-collapsible-list > .snf-collapsible-list-header[aria-expanded='false']"
            )
            if not locator:
                locator = page.query_selector(
                    f".snf-collapsible-list > .snf-collapsible-list-header[aria-expanded='true']"
                )

        # hover on a menu item and slowly scroll to the bottom to load all the elements
        # scrolling fast will not load all the elements
        locator.hover()
        for i in range(60):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(700)

    def get_application_names():
        applicaton_locators = page.query_selector_all(
            ".snf-collapsible-list > .snf-collapsible-list-header"
        )
        application_names = [app.get_attribute("aria-label") for app in applicaton_locators]

        return application_names

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Navigate to the login page
        page.goto(SNOW_INSTANCE_URL)

        # Fill in the login form
        page.fill("#user_name", SNOW_INSTANCE_UNAME)
        page.fill("#user_password", SNOW_INSTANCE_PWD)
        page.click("#sysverb_login")

        try:
            expand_menu()
            pin_menu()
            scroll_to_menu_bottom()
            # close all paths to get the base paths; this allows us to get the name of applications, as they are at the top level
            # Otherwise, because the selectors are nested, some modules get confused with applications
            close_all_paths(page)
            page.wait_for_timeout(1000)
            application_names = get_application_names()
            expand_and_gather_paths(page)

            all_menu_items = []
            urls = dict()
            no_href_count = 0
            new_tabs = []

            for path_item in base_paths:
                selector = path_item["selector"]
                # Select all menu items under the current parent selector

                # The selectors in base_paths point to the parents of the menu items
                # Now, we need to select the menu items themselves. Doing all this in one
                # step -in the recursive function when reaching leaf nodes- would be more
                # efficient, but it led to heap memory issues. This is a workaround.
                menu_items = page.query_selector_all(f"{selector} .menu-item-row")
                for item in menu_items:
                    a_tag = item.query_selector("a")
                    if a_tag:
                        aria_label = a_tag.get_attribute("aria-label")
                        application = path_item["path"][0]
                        module_path = path_item["path"][1:] + [aria_label]

                        module = " > ".join(module_path)  # .replace(" (opens in a new tab)", "")
                        # Exclude some modules that modify the state of the application
                        if (
                            module in ["My Notification Preferences"]
                            or "\u279a"
                            in module  # arrow character that appears in 4 modules to indicate redirection and breaks the JSON
                            or "(opens in a new tab)" in module
                            or "Session Debug" in module_path
                            or "Session Debug" in application
                            or "Debugging" in application
                            or "Debugging" in module
                            # These 3 have a '>' in their name, which breaks the cheat function
                            or "Index Suggestions > In Progress" in module
                            or "Index Suggestions > Done" in module
                            or "Index Suggestions > To Review" in module
                            or application not in application_names
                        ):
                            continue
                        try:
                            item.click()
                        except:
                            print(module, "could not be clicked")
                            continue
                        context.pages[-1].wait_for_timeout(1500)
                        url = context.pages[-1].evaluate("() => window.location.href")[
                            45:
                        ]  # get only the end of the url
                        if url not in urls:
                            menu_task = {"application": application, "module": module, "url": url}
                            all_menu_items.append(menu_task)
                            urls[url] = True

                    num_pages = len(context.pages)
                    tab_opened = num_pages > 1
                    if tab_opened:
                        while len(context.pages) > 1:
                            context.pages[-1].close()
            with open("Menu-Tasks.json", "w") as f:
                json.dump(all_menu_items, f)

        except Exception as e:
            print("An error occurred while extracting the menu items")
        finally:
            unpin_menu()
            browser.close()
