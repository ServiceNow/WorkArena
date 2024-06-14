import html
import json
import logging
import re
import tenacity

from datetime import datetime
from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, retry_if_exception_type
from requests import HTTPError
from time import sleep

from .api.ui_themes import get_workarena_theme_variants
from .api.user import create_user
from .api.utils import table_api_call, table_column_info
from .config import (
    # for knowledge base setup
    KB_FILEPATH,
    KB_NAME,
    PROTOCOL_KB_FILEPATH,
    PROTOCOL_KB_NAME,
    # For list setup
    EXPECTED_ASSET_LIST_COLUMNS_PATH,
    EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
    EXPECTED_EXPENSE_LINE_COLUMNS_PATH,
    EXPECTED_HARDWARE_COLUMNS_PATH,
    EXPECTED_INCIDENT_COLUMNS_PATH,
    EXPECTED_PROBLEM_COLUMNS_PATH,
    EXPECTED_REQUESTED_ITEMS_COLUMNS_PATH,
    EXPECTED_SERVICE_CATALOG_COLUMNS_PATH,
    EXPECTED_USER_COLUMNS_PATH,
    # for form setup
    EXPECTED_CHANGE_REQUEST_FORM_FIELDS_PATH,
    EXPECTED_HARDWARE_FORM_FIELDS_PATH,
    EXPECTED_INCIDENT_FORM_FIELDS_PATH,
    EXPECTED_PROBLEM_FORM_FIELDS_PATH,
    EXPECTED_REQUEST_ITEM_FORM_FIELDS_PATH,
    EXPECTED_USER_FORM_FIELDS_PATH,
    # Patch flag for reports
    REPORT_PATCH_FLAG,
    REPORT_DATE_FILTER,
    # Supported ServiceNow releases
    SNOW_SUPPORTED_RELEASES,
    # For workflows setup
    WORKFLOWS,
    # For UI themes setup
    UI_THEMES_UPDATE_SET,
)
from .api.user import set_user_preference
from .instance import SNowInstance
from .utils import url_login


def _set_sys_property(property_name: str, value: str):
    """
    Set a sys_property in the instance.

    """
    instance = SNowInstance()

    property = table_api_call(
        instance=instance,
        table="sys_properties",
        params={"sysparm_query": f"name={property_name}", "sysparm_fields": "sys_id"},
    )["result"]

    if not property:
        property_sysid = ""
        method = "POST"
    else:
        property_sysid = "/" + property[0]["sys_id"]
        method = "PUT"

    property = table_api_call(
        instance=instance,
        table=f"sys_properties{property_sysid}",
        method=method,
        json={"name": property_name, "value": value},
    )

    # Verify that the property was updated
    assert property["result"]["value"] == value, f"Error setting {property_name}."


def _get_sys_property(property_name: str) -> str:
    """
    Get a sys_property from the instance.

    """
    instance = SNowInstance()

    property_value = table_api_call(
        instance=instance,
        table="sys_properties",
        params={"sysparm_query": f"name={property_name}", "sysparm_fields": "value"},
    )["result"][0]["value"]

    return property_value


def _install_update_set(path: str, name: str):
    """
    Install a ServiceNow update set

    Parameters:
    -----------
    path: str
        The path to the update set file.
    name: str
        The name of the update set as it should appear in the UI.

    Notes: requires interacting with the UI, so we use playwright instead of the API

    """
    with sync_playwright() as playwright:
        instance = SNowInstance()
        browser = playwright.chromium.launch(headless=True, slow_mo=1000)
        page = browser.new_page()
        url_login(instance, page)

        # Navigate to the update set upload page and upload all update sets
        logging.info("Uploading update set...")
        page.goto(
            instance.snow_url
            + "/now/nav/ui/classic/params/target/upload.do%3Fsysparm_referring_url%3Dsys_remote_update_set_list.do%253Fsysparm_fixed_query%253Dsys_class_name%253Dsys_remote_update_set%26sysparm_target%3Dsys_remote_update_set"
        )
        iframe = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
        with page.expect_file_chooser() as fc_info:
            iframe.locator("#attachFile").click()
        file_chooser = fc_info.value
        file_chooser.set_files(path)
        iframe.locator("input:text('Upload')").click()
        sleep(5)

        # Apply all update sets
        logging.info("Applying update set...")
        # ... retrieve all update sets that are ready to be applied
        update_set = table_api_call(
            instance=instance,
            table="sys_remote_update_set",
            params={
                "sysparm_query": f"name={name}^state=loaded",
            },
        )["result"][0]
        # ... apply them
        logging.info(f"... {update_set['name']}")
        page.goto(instance.snow_url + "/sys_remote_update_set.do?sys_id=" + update_set["sys_id"])
        page.locator("button:has-text('Preview Update Set')").first.click()
        page.wait_for_selector("text=Succeeded")
        # click escape to close popup
        page.keyboard.press("Escape")
        page.locator("button:has-text('Commit Update Set')").first.click()
        page.wait_for_selector("text=Succeeded")

        browser.close()


def check_knowledge_base(
    instance: SNowInstance, kb_name: str, kb_data: dict, disable_commenting: bool = True
):
    """
    Verify the integrity of the knowledge base in the instance.
    Args:
    -----
    instance: SNowInstance
        The ServiceNow instance to check the knowledge base in
    kb_name: str
        The name of the knowledge base to check
    kb_data: dict
        The knowledge base data to check
    disable_commenting: bool
        Whether to disable commenting on the knowledge base

    """

    def _extract_text(article):
        article = html.unescape(article)  # replace special chars
        article = re.sub(r"<[^>]+>", "", article)  # remove html tags
        article = "".join([c for c in article if c.isalnum()])  # extract alphanum only
        return article

    # Check that a knowledge base with the correct name exists
    kb = table_api_call(
        instance=instance,
        table="kb_knowledge_base",
        params={"sysparm_query": f"title={kb_name}"},
    )["result"]

    # The KB exists
    if len(kb) == 1:
        requires_install = False
        requires_delete = False

        # Check that the KB has the correct settings
        if disable_commenting and (
            kb[0]["disable_commenting"] != "true"
            or kb[0]["disable_mark_as_helpful"] != "true"
            or kb[0]["disable_rating"] != "true"
            or kb[0]["disable_suggesting"] != "true"
            or kb[0]["disable_category_editing"] != "true"
        ):
            requires_install = True
            requires_delete = True

        # Get all articles in the KB
        articles = table_api_call(
            instance=instance,
            table="kb_knowledge",
            params={"sysparm_query": f"kb_knowledge_base={kb[0]['sys_id']}"},
        )["result"]
        if len(articles) != len(kb_data):
            requires_install = True
            requires_delete = True
        else:
            for a in articles:
                try:
                    # Parse the article title (by convention, articles are named "Article <number>" and 1-indexed)
                    idx = int(a["short_description"].split(" ")[1]) - 1
                except:
                    # Invalid article title, the KB is corrupt and must be reinstalled
                    requires_install = True
                    requires_delete = True
                    break

                # Check that the articles match (preprocess the text because ServiceNow adds some HTML tags)
                if _extract_text(kb_data[idx]["article"]) != _extract_text(a["text"]):
                    requires_install = True
                    requires_delete = True
                    break

    # There are more than one KB with the expected name (corrupt install)
    elif len(kb) > 1:
        raise Exception(
            "Multiple knowledge bases with the same name found. The instance is in an unexpected state."
        )

    # The KB doesn't exist and must be installed
    else:
        requires_install = True
        requires_delete = False

    return (
        kb[0]["sys_id"] if len(kb) == 1 else None,
        requires_install,
        requires_delete,
    )


def delete_knowledge_base(instance: SNowInstance, kb_id: str, kb_name: str):
    """
    Delete a knowledge base from the instance.

    Notes: will delete all content, but will only archive the KB since ServiceNow prevents deletion.

    """
    articles = table_api_call(
        instance=instance,
        table="kb_knowledge",
        params={"sysparm_query": f"kb_knowledge_base={kb_id}"},
    )["result"]

    # Delete the knowledge base
    logging.info(f"Knowledge base {kb_name}: deleting knowledge base content")
    for a_ in articles:
        table_api_call(instance=instance, table=f"kb_knowledge/{a_['sys_id']}", method="DELETE")

    # Rename the KB and set active=False (ServiceNow prevents deletion)
    logging.info(f"Knowledge base {kb_name}: archiving knowledge base")
    table_api_call(
        instance=instance,
        table=f"kb_knowledge_base/{kb_id}",
        method="PATCH",
        json={"title": f"archived_{kb_id}", "active": "false"},
    )


def create_knowledge_base(
    instance: SNowInstance,
    kb_name: str,
    kb_data: dict,
    disable_commenting: bool = True,
    add_article_name: bool = False,
):
    """
    Create knowledge base and upload all articles.
    Params:
    -------
    instance: SNowInstance
        The ServiceNow instance to install the knowledge base in
    kb_name: str
        The name of the knowledge base that will be created
    kb_data: dict
        The knowledge base data to upload
    disable_commenting: bool
        Whether to disable commenting on the knowledge base
    add_article_name: bool
        Whether to add the article name to the article text. If False, the articles will be named "Article <number>"
        Otherwise, we will extract the article title from the 'item' field in the JSON file.

    """
    logging.info(f"Installing knowledge base {kb_name}...")

    # Create the knowledge base
    logging.info(f"... creating knowledge base {kb_name}")
    disable_commenting = "true" if disable_commenting else "false"

    kb = table_api_call(
        instance=instance,
        table="kb_knowledge_base",
        method="POST",
        data=json.dumps(
            {
                "title": kb_name,
                "disable_commenting": disable_commenting,
                "disable_mark_as_helpful": disable_commenting,
                "disable_rating": disable_commenting,
                "disable_suggesting": disable_commenting,
                "disable_category_editing": disable_commenting,
            }
        ),
    )["result"]
    kb_id = kb["sys_id"]

    for i, kb_entry in enumerate(kb_data):
        logging.info(f"... Knowledge Base {kb_name} uploading article {i + 1}/{len(kb_data)}")
        article = kb_entry["article"]
        if add_article_name:
            short_description = kb_entry["item"]
        else:
            short_description = f"Article {i + 1}"
        # Plant a new article in kb_knowledge table
        table_api_call(
            instance,
            table="kb_knowledge",
            method="POST",
            data=json.dumps(
                {
                    "short_description": short_description,
                    "sys_class_name": "kb_knowledge",
                    "text": article,
                    "article_type": "text",
                    "kb_knowledge_base": kb_id,
                }
            ),
        )


def setup_knowledge_bases():
    """
    Verify that the knowledge base is installed correctly in the instance.
    If it is not, it will be installed.

    """
    # Get the ServiceNow instance
    instance = SNowInstance()
    # Mapping between knowledge base name and filepath + whether or not to disable comments + whether or not to add article name
    knowledge_bases = {
        KB_NAME: (KB_FILEPATH, True, False),
        PROTOCOL_KB_NAME: (PROTOCOL_KB_FILEPATH, True, True),
    }
    for kb_name, (kb_filepath, disable_commenting, add_article_name) in knowledge_bases.items():
        # Load the knowledge base
        with open(kb_filepath, "r") as f:
            kb_data = json.load(f)

        kb_id, requires_install, requires_delete = check_knowledge_base(
            instance=instance,
            kb_name=kb_name,
            kb_data=kb_data,
            disable_commenting=disable_commenting,
        )

        # Delete knowledge base if needed
        if requires_delete:
            logging.info(f"Knowledge base {kb_name} is corrupt. Reinstalling...")
            delete_knowledge_base(instance=instance, kb_id=kb_id, kb_name=kb_name)

        # Install the knowledge base
        if requires_install:
            create_knowledge_base(
                instance=instance,
                kb_name=kb_name,
                kb_data=kb_data,
                disable_commenting=disable_commenting,
                add_article_name=add_article_name,
            )

            # Confirm that the knowledge base was installed correctly
            kb_id, requires_install, requires_delete = check_knowledge_base(
                instance=instance, kb_name=kb_name, kb_data=kb_data
            )
            assert (
                not requires_install or requires_delete
            ), f"Knowledge base {kb_name} installation failed."
            logging.info(f"Knowledge base {kb_name} installation succeeded.")

        if not requires_delete and not requires_install:
            logging.info(f"Knowledge base {kb_name} is already installed.")


def setup_workflows():
    """
    Verify that workflows are correctly installed.
    If not, install them.

    """
    if not check_workflows_installed():
        install_workflows()
        assert check_workflows_installed(), "Workflow installation failed."
        logging.info("Workflow installation succeeded.")


def check_workflows_installed():
    """
    Check if the workflows are installed in the instance.

    Will return False if workflows need to be (re)installed. True if all is good.

    """
    expected_workflow_names = [x["name"] for x in WORKFLOWS.values()]
    workflows = table_api_call(
        instance=SNowInstance(),
        table="wf_workflow",
        params={
            "sysparm_query": "nameIN" + ",".join(expected_workflow_names),
        },
    )["result"]

    # Verify that all workflows are installed
    if len(workflows) != len(WORKFLOWS):
        logging.info(
            f"Missing workflows: {set(expected_workflow_names) - set([w['name'] for w in workflows])}."
        )
        return False

    logging.info("All workflows are installed properly.")
    return True


def install_workflows():
    """
    Install workflows using ServiceNow update sets.

    Notes: requires interacting with the UI, so we use playwright instead of the API

    """
    logging.info("Installing workflow update sets...")
    for wf in WORKFLOWS.values():
        _install_update_set(path=wf["update_set"], name=wf["name"])


def display_all_expected_columns(
    instance: SNowInstance, list_name: str, expected_columns: list[str]
):
    """
    Display all expected columns in a given list view.

    Parameters:
    -----------
    instance: SNowInstance
        The ServiceNow instance to configure.
    list_name: str
        The name of the list to display columns for.
    expected_columns: list[str]
        The list of columns to display.

    """
    logging.info(f"... Setting up default view for list {list_name}")

    # Get the default view (for all users)
    logging.info(f"...... Fetching default view for list {list_name}...")
    default_view = table_api_call(
        instance=instance,
        table="sys_ui_list",
        params={
            "sysparm_query": f"name={list_name}^view.title=Default View^sys_userISEMPTY^parentISEMPTY",
            "sysparm_fields": "sys_id,name,view.title,sys_user",
        },
    )["result"]

    # If there is more than one, delete all but the one with the most recently updated
    if len(default_view) > 1:
        logging.info(
            f"......... Multiple default views found for list {list_name}. Deleting all but the most recent one."
        )
        default_view = sorted(default_view, key=lambda x: x["sys_updated_on"], reverse=True)
        # Delete all but the first one
        for view in default_view[1:]:
            logging.info(f"............ Deleting view {view['sys_id']}")
            table_api_call(
                instance=instance, table=f"sys_ui_list/{view['sys_id']}", method="DELETE"
            )
    default_view = default_view[0]

    # Find all columns in the view (get their sysid)
    logging.info(f"...... Fetching existing columns for default view of list {list_name}...")
    columns = table_api_call(
        instance=instance,
        table="sys_ui_list_element",
        params={"sysparm_query": f"list_id={default_view['sys_id']}", "sysparm_fields": "sys_id"},
    )["result"]

    # Delete all columns in the default view
    logging.info(f"...... Deleting existing columns for default view of list {list_name}...")
    for column in columns:
        table_api_call(
            instance=instance, table=f"sys_ui_list_element/{column['sys_id']}", method="DELETE"
        )

    # Add all expected columns to the default view
    logging.info(f"...... Adding expected columns to default view of list {list_name}...")
    for i, column in enumerate(expected_columns):
        logging.info(f"......... {column}")
        table_api_call(
            instance=instance,
            table="sys_ui_list_element",
            method="POST",
            data=json.dumps({"list_id": default_view["sys_id"], "element": column, "position": i}),
        )
    logging.info(f"...... Done.")


def check_all_columns_displayed(
    instance: SNowInstance, url: str, expected_columns: list[str]
) -> bool:
    """
    Get the visible columns and checks that all expected columns are displayed.

    Parameters:
    -----------
    instance: SNowInstance
        The ServiceNow instance to configure.
    url: str
        The URL of the list view to check.
    expected_columns: list[str]
        The set of columns to check for.

    Returns:
    --------
    bool: True if all expected columns are displayed, False otherwise.

    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, slow_mo=1000)
        page = browser.new_page()
        url_login(instance, page)
        page.goto(instance.snow_url + url)
        iframe = page.wait_for_selector("iframe#gsft_main").content_frame()
        # Wait for gsft_main.GlideList2 to be available
        page.wait_for_function("typeof gsft_main.GlideList2 !== 'undefined'")
        lst = iframe.locator("table.data_list_table")

        # Validate the number of lists on the page
        lst = lst.nth(0)
        js_selector = f"gsft_main.GlideList2.get('{lst.get_attribute('data-list_id')}')"
        visible_columns = set(page.evaluate(f"{js_selector}.fields").split(","))

        # check if expected columns is contained in the visible columns
        if not set(expected_columns).issubset(visible_columns):
            logging.info(
                f"Error setting up list at {url} \n Expected {expected_columns} columns, but got {visible_columns}."
            )
            return False
        logging.info(f"All columns properly displayed for {url}.")
        return True


def setup_list_columns():
    """
    Setup the list view to display the expected number of columns.

    """
    logging.info("Setting up visible list columns...")
    list_mappings = {
        "alm_asset": {
            "url": "/now/nav/ui/classic/params/target/alm_asset_list.do",
            "expected_columns_path": EXPECTED_ASSET_LIST_COLUMNS_PATH,
        },
        "alm_hardware": {
            "url": "/now/nav/ui/classic/params/target/alm_hardware_list.do",
            "expected_columns_path": EXPECTED_HARDWARE_COLUMNS_PATH,
        },
        "change_request": {
            "url": "/now/nav/ui/classic/params/target/change_request_list.do",
            "expected_columns_path": EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
        },
        "incident": {
            "url": "/now/nav/ui/classic/params/target/incident_list.do",
            "expected_columns_path": EXPECTED_INCIDENT_COLUMNS_PATH,
        },
        "problem": {
            "url": "/now/nav/ui/classic/params/target/problem_list.do",
            "expected_columns_path": EXPECTED_PROBLEM_COLUMNS_PATH,
        },
        "sys_user": {
            "url": "/now/nav/ui/classic/params/target/sys_user_list.do",
            "expected_columns_path": EXPECTED_USER_COLUMNS_PATH,
        },
        "sc_req_item": {
            "url": "/now/nav/ui/classic/params/target/sc_req_item_list.do",
            "expected_columns_path": EXPECTED_REQUESTED_ITEMS_COLUMNS_PATH,
        },
        "fm_expense_line": {
            "url": "/now/nav/ui/classic/params/target/fm_expense_line_list.do",
            "expected_columns_path": EXPECTED_EXPENSE_LINE_COLUMNS_PATH,
        },
        "sc_cat_item": {
            "url": "/now/nav/ui/classic/params/target/sc_cat_item_list.do",
            "expected_columns_path": EXPECTED_SERVICE_CATALOG_COLUMNS_PATH,
        },
    }

    logging.info("... Creating a new user account to validate list columns")
    admin_instance = SNowInstance()
    username, password, usysid = create_user(instance=admin_instance)
    user_instance = SNowInstance(snow_credentials=(username, password))

    for task, task_info in list_mappings.items():
        expected_columns_path = task_info["expected_columns_path"]
        with open(expected_columns_path, "r") as f:
            expected_columns = list(json.load(f))

        # Configuration is done via API (with admin credentials)
        display_all_expected_columns(admin_instance, task, expected_columns=expected_columns)

        # Validation is done via UI (with normal user credentials to see if changes have propagated)
        assert check_all_columns_displayed(
            user_instance, task_info["url"], expected_columns=expected_columns
        ), f"Error setting up list columns at {task_info['url']}"

    # Delete the user account
    logging.info("... Deleting the test user account")
    table_api_call(instance=admin_instance, table=f"sys_user/{usysid}", method="DELETE")


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
def process_form_fields(instance: SNowInstance, url: str, expected_fields: list[str], action: str):
    """Process form fields based on the given action."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, slow_mo=1000)
        page = browser.new_page()
        url_login(instance, page)
        page.goto(instance.snow_url + url)
        frame = page.wait_for_selector("iframe#gsft_main").content_frame()
        page.wait_for_function("typeof gsft_main.GlideList2 !== 'undefined'")
        # Open form personalization view if not expanded
        form_personalization_expanded = frame.locator(
            'button:has-text("Personalize Form")'
        ).get_attribute("aria-expanded")
        if form_personalization_expanded == "false":
            frame.click('button:has-text("Personalize Form")')
        available_options = (
            frame.get_by_label("Personalize Form").locator('li[role="presentation"] >> input').all()
        )

        for option in available_options:
            id = option.get_attribute("id")
            disabled = option.get_attribute("disabled")
            if disabled == "disabled":
                continue
            checked = option.get_attribute("aria-checked")
            if action == "display":
                if id in expected_fields and checked == "false":
                    option.evaluate("e => e.click()")  # playwright clicking doesn't work
                elif id not in expected_fields and checked == "true":
                    option.evaluate("e => e.click()")  # playwright clicking doesn't work
            elif action == "check":
                if id in expected_fields and checked == "false":
                    logging.info(
                        f"Error setting up form fields at {url} \n Field {id} was supposed to be checked, but was not."
                    )
                    return False
                elif id not in expected_fields and checked == "true":
                    logging.info(
                        f"Error setting up form fields at {url} \n Field {id} was not supposed to be checked, but was."
                    )
                    return False
        if action == "check":
            logging.info(f"All fields properly displayed for {url}.")

        # Close the form personalization view
        frame.click('button:has-text("Personalize Form")')
        return True


def setup_form_fields():
    task_mapping = {
        "create_change_request": {
            "expected_fields_path": EXPECTED_CHANGE_REQUEST_FORM_FIELDS_PATH,
            "url": "/now/nav/ui/classic/params/target/change_request.do",
        },
        "create_incident": {
            "expected_fields_path": EXPECTED_INCIDENT_FORM_FIELDS_PATH,
            "url": "/now/nav/ui/classic/params/target/incident.do",
        },
        "create_hardware": {
            "expected_fields_path": EXPECTED_HARDWARE_FORM_FIELDS_PATH,
            "url": "/now/nav/ui/classic/params/target/alm_hardware.do",
        },
        "create_problem": {
            "expected_fields_path": EXPECTED_PROBLEM_FORM_FIELDS_PATH,
            "url": "/now/nav/ui/classic/params/target/problem.do",
        },
        "create_user": {
            "expected_fields_path": EXPECTED_USER_FORM_FIELDS_PATH,
            "url": "/now/nav/ui/classic/params/target/sys_user.do",
        },
        "create_request_item": {
            "expected_fields_path": EXPECTED_REQUEST_ITEM_FORM_FIELDS_PATH,
            "url": "/now/nav/ui/classic/params/target/sc_req_item.do",
        },
    }

    logging.info("... Creating a new user account to validate form fields")
    admin_instance = SNowInstance()
    username, password, usysid = create_user(instance=admin_instance)
    user_instance = SNowInstance(snow_credentials=(username, password))

    for task, task_info in task_mapping.items():
        expected_fields_path = task_info["expected_fields_path"]
        with open(expected_fields_path, "r") as f:
            expected_fields = json.load(f)

        logging.info(f"Setting up form fields for {task}...")
        process_form_fields(
            admin_instance, task_info["url"], expected_fields=expected_fields, action="display"
        )
        sleep(5)

        # If the view was edited, a new user preference was created for the admin user
        # We want to apply it to all users so we need to edit the record to set sys_user to empty
        # and system to true.
        logging.info(f"Checking for new user preferences for {task} form fields")
        user_preferences = table_api_call(
            instance=admin_instance,
            table="sys_user_preference",
            params={
                "sysparm_query": f"name=personalize_{task_info['url'].split('/')[-1].strip().replace('.do', '')}_default"
            },
        )["result"]
        if len(user_preferences) > 0:
            logging.info(f"Generalizing new settings to all users for {task} form fields")
            # Get the most recent user preference
            user_preference = sorted(
                user_preferences, key=lambda x: x["sys_updated_on"], reverse=True
            )[0]
            # Update the user preference
            table_api_call(
                instance=admin_instance,
                table=f"sys_user_preference/{user_preference['sys_id']}",
                method="PATCH",
                json={"user": "", "system": "true"},
            )

        # Validation is done with a new user to make sure the changes have propagated
        logging.info(f"Validating form fields for {task}...")
        assert process_form_fields(
            user_instance, task_info["url"], expected_fields=expected_fields, action="check"
        ), f"Error setting up form fields at {task_info['url']}"

    # Delete the user account
    logging.info("... Deleting the test user account")
    table_api_call(instance=admin_instance, table=f"sys_user/{usysid}", method="DELETE")

    logging.info("All form fields properly displayed.")


def check_instance_release_support():
    """
    Check that the instance is running a compatible version of ServiceNow.

    Returns:
    --------
    bool: True if the version is supported, False otherwise.

    """
    instance = SNowInstance()
    version_info = instance.release_version
    if version_info["build name"] not in SNOW_SUPPORTED_RELEASES:
        logging.error(
            f"The ServiceNow release version of your instance is not supported. "
            f"Supported versions: {SNOW_SUPPORTED_RELEASES}. "
            f"You are running {version_info['build name']} {version_info}."
        )
        return False
    return True


def enable_url_login():
    """
    Configure the instance to allow login via URL.

    """
    _set_sys_property(property_name="glide.security.restrict.get.login", value="false")
    logging.info("URL login enabled.")


def disable_guided_tours():
    """
    Hide guided tour popups

    """
    _set_sys_property(property_name="com.snc.guided_tours.sp.enable", value="false")
    _set_sys_property(property_name="com.snc.guided_tours.standard_ui.enable", value="false")
    logging.info("Guided tours disabled.")


def disable_welcome_help_popup():
    """
    Disable the welcome help popup

    """
    set_user_preference(instance=SNowInstance(), key="overview_help.visited.navui", value="true")
    logging.info("Welcome help popup disabled.")


def disable_analytics_popups():
    """
    Disable analytics popups (needs to be done through UI since Vancouver release)

    """
    _set_sys_property(property_name="glide.analytics.enabled", value="false")
    logging.info("Analytics popups disabled.")


def setup_ui_themes():
    """
    Install custom UI themes and set it as default

    """
    logging.info("Installing custom UI themes...")
    _install_update_set(path=UI_THEMES_UPDATE_SET["update_set"], name=UI_THEMES_UPDATE_SET["name"])
    check_ui_themes_installed()

    logging.info("Setting default UI theme")
    _set_sys_property(
        property_name="glide.ui.polaris.theme.custom",
        value=get_workarena_theme_variants(SNowInstance())[0]["theme.sys_id"],
    )

    # Set admin user's theme variant
    # ... get user's sysid
    admin_user = table_api_call(
        instance=SNowInstance(),
        table="sys_user",
        params={"sysparm_query": "user_name=admin", "sysparm_fields": "sys_id"},
    )["result"][0]
    # ... set user preference
    set_user_preference(
        instance=SNowInstance(),
        user=admin_user["sys_id"],
        key="glide.ui.polaris.theme.variant",
        value=[
            x["style.sys_id"]
            for x in get_workarena_theme_variants(SNowInstance())
            if x["style.name"] == "Workarena"
        ][0],
    )


def check_ui_themes_installed():
    """
    Check if the UI themes are installed in the instance.

    """
    expected_variants = set([v.lower() for v in UI_THEMES_UPDATE_SET["variants"]])
    installed_themes = get_workarena_theme_variants(SNowInstance())
    installed_themes = set([t["style.name"].lower() for t in installed_themes])

    assert (
        installed_themes == expected_variants
    ), f"""UI theme installation failed.
        Expected: {expected_variants}
        Installed: {installed_themes}
        """


def set_home_page():
    logging.info("Setting default home page")
    _set_sys_property(property_name="glide.login.home", value="/now/nav/ui/home")


def wipe_system_admin_preferences():
    """
    Wipe all system admin preferences

    """
    logging.info("Wiping all system admin preferences")
    sys_admin_prefs = table_api_call(
        instance=SNowInstance(),
        table="sys_user_preference",
        params={"sysparm_query": "user.user_name=admin", "sysparm_fields": "sys_id,name"},
    )["result"]

    # Delete all sysadmin preferences
    logging.info("... Deleting all preferences")
    for pref in sys_admin_prefs:
        logging.info(f"...... deleting {pref['name']}")
        table_api_call(
            instance=SNowInstance(), table=f"sys_user_preference/{pref['sys_id']}", method="DELETE"
        )


def is_report_filter_using_time(filter):
    """
    Heuristic to check if a report is filtering based on time

    This aims to detect the use of functions like "gs.endOfToday()". To avoid hardcoding all of them,
    we simply check for the use of keywords. Our filter is definitely too wide, but that's ok.

    """
    return "javascript:gs." in filter or "@ago" in filter


def patch_report_filters():
    """
    Add filters to reports to make sure they stay frozen in time and don't show new data
    as then instance's life cycle progresses.

    """
    logging.info("Patching reports with date filter...")

    instance = SNowInstance()

    # Get all reports that are not already patched
    reports = table_api_call(
        instance=instance,
        table="sys_report",
        params={
            "sysparm_query": f"sys_class_name=sys_report^active=true^descriptionNOT LIKE{REPORT_PATCH_FLAG}^ORdescriptionISEMPTY"
        },
    )["result"]

    for report in reports:
        # Find all sys_created_on columns of this record. Some have many.
        sys_created_on_cols = [
            c for c in table_column_info(instance, report["table"]).keys() if "sys_created_on" in c
        ]
        try:
            # XXX: We purposely do not support reports with multiple filter conditions for simplicity
            if len(sys_created_on_cols) == 0 or "^NQ" in report["filter"]:
                logging.info(f"Discarding report {report['title']} {report['sys_id']}...")
                raise NotImplementedError()  # Mark for deletion

            if not is_report_filter_using_time(report["filter"]):
                # That's a report we want to keep (use date cutoff filter)
                filter_date = REPORT_DATE_FILTER
                logging.info(
                    f"Keeping report {report['title']} {report['sys_id']} (columns: {sys_created_on_cols})..."
                )
            else:
                # XXX: We do not support reports with filters that rely on time (e.g., last 10 days) because
                #      there are not stable. In this case, we don't delete them but add a filter to make
                #      them empty. They will be shown as "No data available".
                logging.info(
                    f"Disabling report {report['title']} {report['sys_id']} because it uses time filters..."
                )
                filter_date = "1900-01-01"

            filter = "".join(
                [
                    f"^{col}<javascript:gs.dateGenerate('{filter_date}','00:00:00')"
                    for col in sys_created_on_cols
                ]
            ) + ("^" if len(report["filter"]) > 0 and not report["filter"].startswith("^") else "")
            table_api_call(
                instance=instance,
                table=f"sys_report/{report['sys_id']}",
                method="PATCH",
                json={
                    "filter": filter + report["filter"],
                    "description": report["description"] + " " + REPORT_PATCH_FLAG,
                },
            )
            logging.info(f"... done")

        except (NotImplementedError, HTTPError):
            # HTTPError occurs when some reports simply cannot be patched because they are critical and protected
            logging.info(f"...failed to patch report. Attempting delete...")

            # Delete the report if it cannot be patched
            # This might fail sometimes, but it's the best we can do.
            try:
                table_api_call(
                    instance=instance, table=f"sys_report/{report['sys_id']}", method="DELETE"
                )
                logging.info(f"...... deleted.")
            except:
                logging.error(f"...... could not delete.")


@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    reraise=True,
    before_sleep=lambda _: logging.info("An error occurred. Retrying..."),
)
def setup():
    """
    Check that WorkArena is installed correctly in the instance.

    """
    if not check_instance_release_support():
        return  # Don't continue if the instance is not supported

    # Enable URL login (XXX: Do this first since other functions can use URL login)
    enable_url_login()

    # Set default landing page
    set_home_page()

    # Disable popups for new users
    # ... guided tours
    disable_guided_tours()
    # ... analytics
    disable_analytics_popups()
    # ... help
    disable_welcome_help_popup()

    # Install custom UI themes (needs to be after disabling popups)
    setup_ui_themes()

    # Clear all predefined system admin preferences (e.g., default list views, etc.)
    wipe_system_admin_preferences()

    # Patch all reports to only show data <= April 1, 2024
    patch_report_filters()

    # XXX: Install workflows first because they may automate some downstream installations
    setup_workflows()
    setup_knowledge_bases()

    # Setup the user list columns by displaying all columns and checking that the expected number are displayed
    setup_form_fields()
    setup_list_columns()

    # Save installation date
    logging.info("Saving installation date")
    _set_sys_property(property_name="workarena.installation.date", value=datetime.now().isoformat())

    logging.info("WorkArena setup complete.")


def main():
    """
    Entrypoint for package CLI installation command

    """
    logging.basicConfig(level=logging.INFO)

    try:
        past_install_date = _get_sys_property("workarena.installation.date")
        logging.info(f"Detected previous installation on {past_install_date}. Reinstalling...")
    except:
        past_install_date = "never"

    logging.info(
        f"""

██     ██  ██████  ██████  ██   ██  █████  ██████  ███████ ███    ██  █████
██     ██ ██    ██ ██   ██ ██  ██  ██   ██ ██   ██ ██      ████   ██ ██   ██
██  █  ██ ██    ██ ██████  █████   ███████ ██████  █████   ██ ██  ██ ███████
██ ███ ██ ██    ██ ██   ██ ██  ██  ██   ██ ██   ██ ██      ██  ██ ██ ██   ██
 ███ ███   ██████  ██   ██ ██   ██ ██   ██ ██   ██ ███████ ██   ████ ██   ██

Instance: {SNowInstance().snow_url}
Previous installation: {past_install_date}

"""
    )
    setup()
