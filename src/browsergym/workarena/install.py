import html
import json
import logging
import re

from playwright.sync_api import sync_playwright
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from .api.utils import table_api_call
from .config import (
    # for knowledge base setup
    KB_FILEPATH,
    KB_NAME,
    # For list setup
    EXPECTED_ASSET_LIST_COLUMNS_PATH,
    EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
    EXPECTED_HARDWARE_COLUMNS_PATH,
    EXPECTED_INCIDENT_COLUMNS_PATH,
    EXPECTED_SERVICE_CATALOG_COLUMNS_PATH,
    EXPECTED_USER_COLUMNS_PATH,
    # for form setup
    EXPECTED_CHANGE_REQUEST_FORM_FIELDS_PATH,
    EXPECTED_HARDWARE_FORM_FIELDS_PATH,
    EXPECTED_INCIDENT_FORM_FIELDS_PATH,
    EXPECTED_PROBLEM_FORM_FIELDS_PATH,
    EXPECTED_USER_FORM_FIELDS_PATH,
    # For workflows setup
    WORKFLOWS,
)
from .instance import SNowInstance
from .utils import ui_login


def check_knowledge_base(instance: SNowInstance, kb_data: dict):
    """
    Verify the integrity of the knowledge base in the instance.

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
        params={"sysparm_query": f"title={KB_NAME}"},
    )["result"]

    # The KB exists
    if len(kb) == 1:
        requires_install = False
        requires_delete = False

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


def delete_knowledge_base(instance: SNowInstance, kb_id: str):
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
    logging.info("... deleting knowledge base content")
    for a_ in articles:
        table_api_call(instance=instance, table=f"kb_knowledge/{a_['sys_id']}", method="DELETE")

    # Rename the KB and set active=False (ServiceNow prevents deletion)
    logging.info("... archiving knowledge base")
    table_api_call(
        instance=instance,
        table=f"kb_knowledge_base/{kb_id}",
        method="PATCH",
        json={"title": f"archived_{kb_id}", "active": "false"},
    )


def create_knowledge_base(instance: SNowInstance, kb_data: dict):
    """
    Create knowledge base and upload all articles

    """
    logging.info("Installing knowledge base...")

    # Create the knowledge base
    logging.info("... creating knowledge base")
    kb = table_api_call(
        instance=instance,
        table="kb_knowledge_base",
        method="POST",
        data=json.dumps({"title": KB_NAME}),
    )["result"]
    kb_id = kb["sys_id"]

    for i, kb_entry in enumerate(kb_data):
        logging.info(f"... uploading article {i + 1}/{len(kb_data)}")
        article = kb_entry["article"]

        # Plant a new article in kb_knowledge table
        table_api_call(
            instance,
            table="kb_knowledge",
            method="POST",
            data=json.dumps(
                {
                    "short_description": f"Article {i + 1}",
                    "sys_class_name": "kb_knowledge",
                    "text": article,
                    "article_type": "text",
                    "kb_knowledge_base": kb_id,
                }
            ),
        )


def setup_knowledge_base():
    """
    Verify that the knowledge base is installed correctly in the instance.
    If it is not, it will be installed.

    """
    # Get the ServiceNow instance
    instance = SNowInstance()

    # Load the knowledge base
    with open(KB_FILEPATH, "r") as f:
        kb_data = json.load(f)

    kb_id, requires_install, requires_delete = check_knowledge_base(
        instance=instance, kb_data=kb_data
    )

    # Delete knowledge base if needed
    if requires_delete:
        logging.info("Knowledge base is corrupt. Reinstalling...")
        delete_knowledge_base(instance=instance, kb_id=kb_id)

    # Install the knowledge base
    if requires_install:
        create_knowledge_base(instance=instance, kb_data=kb_data)

        # Confirm that the knowledge base was installed correctly
        kb_id, requires_install, requires_delete = check_knowledge_base(
            instance=instance, kb_data=kb_data
        )
        assert not requires_install or requires_delete, "Knowledge base installation failed."
        logging.info("Knowledge base installation succeeded.")

    if not requires_delete and not requires_install:
        logging.info("Knowledge base is already installed.")


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
    with sync_playwright() as playwright:
        instance = SNowInstance()
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        ui_login(instance, page)

        # Navigate to the update set upload page and upload all update sets
        logging.info("Uploading workflow update sets...")
        for wf in WORKFLOWS.values():
            logging.info(f"... {wf['name']}")
            page.goto(
                instance.snow_url
                + "/now/nav/ui/classic/params/target/upload.do%3Fsysparm_referring_url%3Dsys_remote_update_set_list.do%253Fsysparm_fixed_query%253Dsys_class_name%253Dsys_remote_update_set%26sysparm_target%3Dsys_remote_update_set"
            )
            iframe = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
            with page.expect_file_chooser() as fc_info:
                iframe.locator("#attachFile").click()
            file_chooser = fc_info.value
            file_chooser.set_files(wf["update_set"])
            iframe.locator("input:text('Upload')").click()

        # Apply all update sets
        logging.info("Applying workflow update sets...")
        # ... retrieve all update sets that are ready to be applied
        sys_remote_update_set = table_api_call(
            instance=instance,
            table="sys_remote_update_set",
            params={
                # Name matches workflows and update set status is loaded
                "sysparm_query": "nameIN"
                + ",".join([x["name"] for x in WORKFLOWS.values()])
                + "^state=loaded",
            },
        )["result"]
        # ... apply them
        for update_set in sys_remote_update_set:
            logging.info(f"... {update_set['name']}")
            page.goto(
                instance.snow_url + "/sys_remote_update_set.do?sys_id=" + update_set["sys_id"]
            )
            page.locator("button:has-text('Preview Update Set')").first.click()
            page.wait_for_selector("text=success")
            # click escape to close popup
            page.keyboard.press("Escape")
            page.locator("button:has-text('Commit Update Set')").first.click()
            page.wait_for_selector("text=Succeeded")

        browser.close()


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
def display_all_expected_columns(url: str, expected_columns: set[str]):
    """Display all expected columns in a given list view."""
    with sync_playwright() as playwright:
        instance = SNowInstance()
        browser = playwright.chromium.launch(headless=True, slow_mo=1000)
        page = browser.new_page()
        ui_login(instance, page)
        page.goto(instance.snow_url + url)
        frame = page.wait_for_selector("iframe#gsft_main").content_frame()
        # Open list personalization view
        frame.click(
            'i[data-title="Personalize List Columns"]'
        )  # CSS selector to support both unmodified and modified list views
        selected_columns = frame.get_by_label("Selected", exact=True)
        selected_columns_required = set()
        # Required columns that are already added
        for option in selected_columns.get_by_role("option").all():
            value = option.get_attribute("value")
            if value:
                if value in expected_columns:
                    selected_columns_required.add(value)
                # Remove extra columns
                else:
                    option.click()
                    frame.get_by_text("Remove", exact=True).click()
        columns_to_add = set(expected_columns) - selected_columns_required

        # Add required columns
        for column in columns_to_add:
            # Using CSS selector because some elements can't be selected otherwise (e.g. "sys_class_name")
            frame.click(f'option[value="{column}"]')
            frame.get_by_text("Add").click()
        frame.click("#ok_button")


def check_all_columns_displayed(url: str, expected_columns: set[str]) -> bool:
    """Get the visible columns and checks that all expected columns are displayed."""
    with sync_playwright() as playwright:
        instance = SNowInstance()
        browser = playwright.chromium.launch(headless=True, slow_mo=1000)
        page = browser.new_page()
        ui_login(instance, page)
        page.goto(instance.snow_url + url)
        iframe = page.frame("gsft_main")
        lst = iframe.locator("table.data_list_table")
        lst.wait_for()

        # Validate the number of lists on the page
        lst = lst.nth(0)
        js_selector = f"gsft_main.GlideList2.get('{lst.get_attribute('data-list_id')}')"
        # Wait for gsft_main.GlideList2 to be available
        page.wait_for_function("typeof gsft_main.GlideList2 !== 'undefined'")
        visible_columns = set(page.evaluate(f"{js_selector}.fields").split(","))

        # check if expected columns is contained in the visible columns
        if not expected_columns.issubset(visible_columns):
            logging.info(
                f"Error setting up list at {url} \n Expected {expected_columns} columns, but got {visible_columns}."
            )
            return False
        logging.info(f"All columns properly displayed for {url}.")
        return True


def setup_list_columns():
    """Setup the list view to display the expected number of columns."""
    list_mappings = {
        "alm_asset": {
            "url": "/now/nav/ui/classic/params/target/alm_asset_list.do%3Fsysparm_view%3Ditam_workspace%26sysparm_userpref.alm_asset_list.view%3Ditam_workspace%26sysparm_userpref.alm_asset.view%3Ditam_workspace%26sysparm_query%3D%26sysparm_fixed_query%3D",
            "expected_columns_path": EXPECTED_ASSET_LIST_COLUMNS_PATH,
        },
        "alm_hardware": {
            "url": "/now/nav/ui/classic/params/target/alm_hardware_list.do%3Fsysparm_view%3Ditam_workspace%26sysparm_userpref.alm_hardware_list.view%3Ditam_workspace%26sysparm_userpref.alm_hardware.view%3Ditam_workspace%3D%26sysparm_query%3Dinstall_status%253D6%255Esubstatus%253Dpre_allocated",
            "expected_columns_path": EXPECTED_HARDWARE_COLUMNS_PATH,
        },
        "change_request": {
            "url": "/now/nav/ui/classic/params/target/change_request_list.do%3Fsysparm_view%3Dsow%26sysparm_userpref.change_request_list.view%3Dsow%26sysparm_userpref.change_request.view%3Dsow%26sysparm_query%3D%26sysparm_fixed_query%3D",
            "expected_columns_path": EXPECTED_CHANGE_REQUEST_COLUMNS_PATH,
        },
        "incident": {
            "url": "/now/nav/ui/classic/params/target/incident_list.do%3Fsysparm_query%3Dactive%253Dtrue%26sysparm_first_row%3D1%26sysparm_view%3DMajor%2520Incidents",
            "expected_columns_path": EXPECTED_INCIDENT_COLUMNS_PATH,
        },
        "sys_user": {
            "url": "/now/nav/ui/classic/params/target/sys_user_list.do%3Fsysparm_view%3D%26sysparm_userpref.sys_user_list.view%3D%26sysparm_userpref.sys_user.view%3D%26sysparm_query%3Dactive%253Dtrue%255Ecompany%253D81fd65ecac1d55eb42a426568fc87a63",
            "expected_columns_path": EXPECTED_USER_COLUMNS_PATH,
        },
        "sc_cat_item": {
            "url": "/now/nav/ui/classic/params/target/sc_cat_item_list.do%3Fsysparm_view%3D%26sysparm_userpref.sc_cat_item_list.view%3D%26sysparm_userpref.sc_cat_item.view%3D%26sysparm_query%3D%26sysparm_fixed_query%3D",
            "expected_columns_path": EXPECTED_SERVICE_CATALOG_COLUMNS_PATH,
        },
    }
    for task, task_info in list_mappings.items():
        expected_columns_path = task_info["expected_columns_path"]
        with open(expected_columns_path, "r") as f:
            expected_columns = set(json.load(f))
        display_all_expected_columns(task_info["url"], expected_columns=expected_columns)
        assert check_all_columns_displayed(
            task_info["url"], expected_columns=expected_columns
        ), f"Error setting up list columns at {task_info['url']}"


@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(TimeoutError),
    reraise=True,
    before_sleep=lambda _: logging.info("Retrying due to a TimeoutError..."),
)
def process_form_fields(url: str, expected_fields: list[str], action: str):
    """Process form fields based on the given action."""
    with sync_playwright() as playwright:
        instance = SNowInstance()
        browser = playwright.chromium.launch(headless=True, slow_mo=1000)
        page = browser.new_page()
        ui_login(instance, page)
        page.goto(instance.snow_url + url)
        frame = page.wait_for_selector("iframe#gsft_main").content_frame()
        # Open form personalization view if not expanded
        form_personalization_expanded = frame.locator(
            'button:has-text("Personalize Form")'
        ).get_attribute("aria-expanded")
        if form_personalization_expanded == "false":
            frame.click('button:has-text("Personalize Form")')
        available_options = (
            frame.get_by_label("Personalize Form").locator('li[role="presentation"] input').all()
        )

        for option in available_options:
            id = option.get_attribute("id")
            disabled = option.get_attribute("disabled")
            if disabled == "disabled":
                continue
            checked = option.get_attribute("aria-checked")
            if action == "display":
                if id in expected_fields and checked == "false":
                    option.click()
                elif id not in expected_fields and checked == "true":
                    option.click()
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
    }
    for task, task_info in task_mapping.items():
        expected_fields_path = task_info["expected_fields_path"]
        with open(expected_fields_path, "r") as f:
            expected_fields = json.load(f)
        process_form_fields(task_info["url"], expected_fields=expected_fields, action="display")
        assert process_form_fields(
            task_info["url"], expected_fields=expected_fields, action="check"
        ), f"Error setting up form fields at {task_info['url']}"
    logging.info("All form fields properly displayed.")
    print("all columns displayed")


from .config import SNOW_SUPPORTED_RELEASES


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


def setup():
    """
    Check that WorkArena is installed correctly in the instance.

    """
    if not check_instance_release_support():
        return  # Don't continue if the instance is not supported

    # XXX: Install workflows first because they may automate some downstream installations
    setup_workflows()
    setup_knowledge_base()
    # Setup the user list columns by displaying all columns and checking that the expected number are displayed
    setup_list_columns()
    setup_form_fields()


def main():
    """
    Entrypoint for package CLI installation command

    """
    logging.basicConfig(level=logging.INFO)
    setup()
