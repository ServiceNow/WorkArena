import html
import json
import logging
import re

from playwright.sync_api import sync_playwright

from .api.utils import table_api_call
from .config import KB_FILEPATH, KB_NAME, WORKFLOWS
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


def setup():
    """
    Check that WorkArena is installed correctly in the instance.

    """
    # XXX: Install workflows first because they may automate some downstream installations
    setup_workflows()
    setup_knowledge_base()
