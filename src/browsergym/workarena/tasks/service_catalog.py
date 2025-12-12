"""
Tasks that require interacting with the service catalog

"""

import json
import logging
from typing import List
import numpy as np
import playwright.sync_api
import requests
from playwright.sync_api import Page
import re
from time import sleep
from urllib import parse

from .base import AbstractServiceNowTask
from .utils.form import fill_text
from ..api.requests import (
    get_request_by_id,
    db_delete_from_table,
)
from ..config import (
    ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH,
    ORDER_IPAD_MINI_TASK_CONFIG_PATH,
    ORDER_IPAD_PRO_TASK_CONFIG_PATH,
    ORDER_SALES_LAPTOP_TASK_CONFIG_PATH,
    ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH,
    ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
    ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH,
    ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH,
    # dynamic guidance tasks
    ORDER_IPHONE_TASK_CONFIG_PATH,
    ORDER_MOBILE_PHONE_TASK_CONFIG_PATH,
    ORDER_MISC_HARDWARE_TASK_CONFIG_PATH,
    ORDER_MISC_HARDWARE_WITH_BUSINESS_JUSTIFICATION_TASK_CONFIG_PATH,
    ORDER_PACKAGING_AND_SHIPPING_TASK_CONFIG_PATH,
    ORDER_RESET_PASSWORD_TASK_CONFIG_PATH,
    ORDER_PAPER_SUPPLIES_TASK_CONFIG_PATH,
    ORDER_SOFTWARE_TASK_CONFIG_PATH,
    ORDER_SOFTWARE_ACCESS_TASK_CONFIG_PATH,
)
from ..instance import SNowInstance
from .utils.utils import check_url_suffix_match

ADDITIONAL_SOFTWARE = [
    "Slack",
    "Trello",
    "Salesforce",
    "QuickBooks",
    "Zoom",
    "Microsoft Office 365",
    "Google Workspace",
    "Asana",
    "HubSpot",
    "Adobe Creative Cloud",
]

META_CONFIGS = {
    "Developer Laptop (Mac)": {
        "desc": "Macbook Pro",
        "options": {
            "Adobe Acrobat": ("checkbox", [True, False]),
            "Eclipse IDE": ("checkbox", [True, False]),
            "Adobe Photoshop": ("checkbox", [True, False]),
            "Additional software requirements": ("textarea", ADDITIONAL_SOFTWARE),
        },
    },
    "iPad mini": {
        "desc": "Request for iPad mini",
        "options": {
            "Choose the colour": (
                "radio",
                ["Space Grey", "Pink", "Purple", "Starlight"],
            ),
            "Choose the storage": ("radio", ["64", "256"]),
        },
    },
    "iPad pro": {
        "desc": "Request for iPad pro",
        "options": {
            "Choose the colour": ("radio", ["Space Grey", "Silver"]),
            "Choose the storage": ("radio", ["128", "256", "512"]),
        },
    },
    "Sales Laptop": {
        "desc": "Acer Aspire NX",
        "options": {
            "Microsoft Powerpoint": ("checkbox", [True, False]),
            "Adobe Acrobat": ("checkbox", [True, False]),
            "Adobe Photoshop": ("checkbox", [True, False]),
            "Siebel Client": ("checkbox", [True, False]),
            "Additional software requirements": ("textarea", ADDITIONAL_SOFTWARE),
        },
    },
    "Standard Laptop": {
        "desc": "Lenovo - Carbon x1",
        "options": {
            "Adobe Acrobat": ("checkbox", [True, False]),
            "Adobe Photoshop": ("checkbox", [True, False]),
            "Additional software requirements": ("textarea", ADDITIONAL_SOFTWARE),
        },
    },
    "Apple Watch": {
        "desc": "Apple Watch - Their most personal device ever",
        "options": {},
    },
    "Apple MacBook Pro 15": {
        "desc": "Apple MacBook Pro",
        "options": {},
    },
    "Development Laptop (PC)": {
        "desc": "Dell XPS 13",
        "options": {
            "What size solid state drive do you want?": (
                "radio",
                [
                    "250",  # This needs to match both the radio option (250 GB [subtract 300$]) and db request (250)
                    "500",  # Similar as above
                ],
            ),
            "Please specify an operating system": ("radio", ["Windows 8", "Ubuntu"]),
        },
    },
    "Loaner Laptop": {
        "desc": "Short term, while computer is repaired/imaged. Waiting for computer order, special projects, etc. Training, special events, check-in process",
        "options": {
            "When do you need it ?": (
                "textarea",
                [
                    "ASAP",
                    "In 2 weeks",
                    "By the end of the month",
                    "On time for the next meeting",
                    "I needed it yesterday but since you are asking I guess I can wait a bit more",
                    "Do your best, I know you are busy",
                    "I don't need it anymore, I just wanted to see what would happen if I clicked on this button",
                ],
            ),
            "How long do you need it for ?": (
                "radio",
                [
                    "1 day",
                    "1 month",
                    "1 week",
                    "2 weeks",
                    "3 days",
                ],
            ),
        },
    },
}


class OrderHardwareTask(AbstractServiceNowTask):
    """
    Order an item from the service catalog.

    Parameters:
    -----------
    seed: int
        Random seed
    instance: SNowInstance
        The instance to use.
    fixed_request_item: str
        The item to order. If provided, the task will always order this item.
    fixed_config: dict
        Configuration to use for the task. If provided, the task will use the provided configuration instead of
        selecting a random one. See browsergym/workarena/data_files/task_configs/order_ipda_pro_task.json
        for an example of a configuration file.
    config_only_in_desc: bool
        If True, the model to order will be omitted from the task description in comp tasks.

    """

    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_request_item: str = None,
        fixed_config: dict = None,
        config_only_in_desc: bool = False,
        **kwargs,
    ):
        super().__init__(
            seed=seed,
            instance=instance,
            start_rel_url="/now/nav/ui/classic/params/target/catalog_home.do%3Fsysparm_view%3Dcatalog_default",
            final_rel_url="/now/nav/ui/classic/params/target/com.glideapp.servicecatalog_checkout_view_v2.do",
        )

        if fixed_request_item is not None and fixed_config is not None:
            if fixed_request_item != fixed_config["item"]:
                raise ValueError(f"'fixed_request_item' and 'fixed_config[\"item\"]' do not match")

        self.fixed_config = fixed_config
        self.config = None
        self.fixed_request_item = fixed_request_item
        self.config_only_in_desc = config_only_in_desc

        self.js_prefix = "gsft_main"
        self.js_api_forms = "g_form"
        self.all_configs = self.all_configs()
        self.__dict__.update(kwargs)

    @classmethod
    def all_configs(cls) -> List[dict]:
        with open(cls.config_path, "r") as f:
            return json.load(f)

    def _wait_for_ready(self, page: Page, wait_for_form_api: bool = False) -> None:
        """
        Waits for the the main iframe to be loaded

        """
        logging.debug(f"Waiting for {self.js_prefix} to be fully loaded")
        page.wait_for_function(
            f"typeof window.{self.js_prefix} !== 'undefined' && window.{self.js_prefix}.WORKARENA_LOAD_COMPLETE"
        )
        logging.debug(f"Detected {self.js_prefix} ready")

        if wait_for_form_api:
            logging.debug("Waiting for Glide form API to be available")
            page.wait_for_function(f"window.{self.form_js_selector}")
            logging.debug("Detected Glide form API ready")

    @property
    def form_js_selector(self):
        return self.js_prefix + "." + self.js_api_forms

    def get_init_scripts(self) -> List[str]:
        return super().get_init_scripts() + [
            "registerGsftMainLoaded()",
            self._get_disable_add_to_cart_script(),
            self._get_remove_top_items_panel_script(),
        ]

    def _get_disable_add_to_cart_script(self):
        """
        Disables the 'Add to Cart' button on the service catalog page
        This is necessary so that agents running in parallel do not interfere with each other (cart is shared between sessions)

        """
        script = """
            function disableAddToCartButton() {
                waLog('Searching for top items panel...', 'disableAddToCartButton');
                let button = document.querySelector('button[aria-label="Add to Cart"]');
                if (button) {
                    button.disabled = true;
                    waLog('WorkArena: Disabled the "Add to Cart" button', 'disableAddToCartButton');
                } else {
                    waLog('WorkArena: Could not find the "Add to Cart" button', 'disableAddToCartButton');
                }
            }

            runInGsftMainOnlyAndProtectByURL(disableAddToCartButton, 'glideapp.servicecatalog_cat_item_view.do');
        """
        return script

    def _get_remove_top_items_panel_script(self):
        """Get script that removes the 'top items' panel that sometimes on the landing page of service catalog
        Disables the 'Top Requests' panel that sometimes appears on the landing page of the service catalog
        Runs in a loop to keep checking for the host element and shadow root
        URL is secured by running only on the catalog_home page; this is a heuristic to avoid running on other pages
        and does not check that the URL is an exact match, as moving back and forth between pages can cause the URL
        to change, but catalog_home will always be present.
        """
        script = """
            function removeTopItemsPanel() {
                waLog('Searching for top items panel...', 'removeTopItemsPanel');
                let headings = Array.from(document.querySelectorAll('[role="heading"]'));
                headings.forEach((heading) => {
                    if (heading.textContent.includes("Top Requests")) {
                        let parentDiv = heading.closest('div.drag_section');
                        if (parentDiv) {
                            parentDiv.remove();
                            waLog('Removed parent div for heading: ' + heading.textContent, 'removeTopItemsPanel');
                        }
                    }
                });
            }

            runInGsftMainOnlyAndProtectByURL(removeTopItemsPanel, `catalog_home`);
            """
        return script

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        assert self.all_configs is not None, "No configuration available for the task."
        self.config = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        )
        self.requested_item = self.config["item"]
        self.short_description = self.config["description"]
        self.quantity = self.config["quantity"]
        self.requested_configuration = self.config["configuration"]

        # Generate goal
        if self.config_only_in_desc:
            goal = self.get_pretty_printed_description()
        else:
            goal = f'Go to the hardware store and order {self.quantity} "{self.requested_item}"'
        if len(self.requested_configuration) > 0:
            goal += f" with configuration {dict((k, v[1]) for k, v in self.requested_configuration.items())}"
        info = {}

        # Used to keep track of the sysid of the request for validation
        self.request_sysid = None

        return goal, info

    def cheat(self, page: Page, chat_messages: list[str]) -> None:
        super().cheat(page=page, chat_messages=chat_messages)
        self._wait_for_ready(page=page)

        iframe = page.frame(self.js_prefix)

        # Find hardware buttons
        element = iframe.wait_for_selector("a:text('Hardware')", strict=True)
        element.click()
        self._wait_for_ready(page=page)

        element = iframe.wait_for_selector(f"h2:has-text('{self.requested_item}')", strict=True)
        element.click()
        self._wait_for_ready(page=page, wait_for_form_api=True)

        quantity_input = iframe.wait_for_selector("#quantity", strict=True)
        quantity_input.select_option(str(self.quantity))

        editable_fields = page.evaluate(f"{self.form_js_selector}.getEditableFields()")

        lookup_map = {}
        for idx, field in enumerate(editable_fields):
            control_text = self._get_control_description(page, field)
            lookup_map[control_text] = field

        for field_label, (element, value) in self.requested_configuration.items():
            element_id = lookup_map[field_label]
            control_type = page.evaluate(f"{self.form_js_selector}.getControl('{element_id}').type")

            if control_type in ("radio",):
                num_options = page.evaluate(
                    f"{self.form_js_selector}.getControls('{element_id}').length"
                )
                for i in range(num_options):
                    control_handle = page.evaluate_handle(
                        f"{self.form_js_selector}.getControls('{element_id}')[{i}]"
                    )
                    control_text = control_handle.evaluate("e => e.parentElement.innerText")
                    if control_text.startswith(
                        value
                    ):  # the page changes the text dynamically adding subtract/add to the text
                        control_id = control_handle.get_attribute("id")
                        iframe.wait_for_selector(f'label[for="{control_id}"]', strict=True).click()
                        break
            elif control_type == "hidden":
                element_control = page.evaluate_handle(
                    f"{self.form_js_selector}.getControl('{element_id}')"
                )
                element_value = element_control.evaluate("e => e.value")
                if element_value != str(value).lower():
                    label_id = f"ni.{element_id}_label"
                    element_label = iframe.wait_for_selector(
                        f'label[id="{label_id}"]', strict=True, timeout=1_000
                    )
                    element_label.click()
            elif control_type in ("textarea", "text"):
                element_control = page.evaluate_handle(
                    f"{self.form_js_selector}.getControl('{element_id}')"
                ).as_element()  # this look superfluous
                element_id = element_control.get_attribute("id")  # this look superfluous
                text_element = iframe.query_selector(f'[id="{element_id}"]')
                text_element.click()
                fill_text(page=page, input_field=text_element, value=value, iframe=iframe)

            elif control_type == "select-one":
                iframe.locator(f"id={element_id}").select_option(value)
            else:
                raise ValueError(f"Unknown control type {control_type}")

        order_now_button = iframe.wait_for_selector("#oi_order_now_button", strict=True)

        with page.expect_navigation():
            order_now_button.click()

    def _generate_random_config(self, page: Page):
        """Generate a random configuration for the task"""
        self.task_is_setup = (
            False  # This is a hack to avoid raising an exception in the setup method
        )
        self.setup(page=page, do_start=False)
        if self.fixed_request_item:
            self.requested_item = self.fixed_request_item
        else:
            # ... choose a random item to order
            self.requested_item = self.random.choice(list(META_CONFIGS.keys()))

        meta_config = META_CONFIGS[self.requested_item]
        self.fixed_config = {
            "item": self.requested_item,
            "description": meta_config["desc"],
            "quantity": self.random.randint(1, 11),
            "configuration": {
                ctrl_name: (ctrl_type, self.random.choice(values))
                for ctrl_name, (ctrl_type, values) in meta_config["options"].items()
            },
        }
        self.setup(page=page, do_start=True)

    def _get_control_description(self, page, field):
        """
        Get the description of a control (e.g., the text of a radio button)
        """
        # Wait for everything to be ready
        self._wait_for_ready(page, wait_for_form_api=True)

        control_type = page.evaluate(f"{self.form_js_selector}.getControl('{field}').type")
        if control_type in ("radio", "select-one"):
            return page.evaluate(f"{self.form_js_selector}.getLabelOf('{field}')")
        elif control_type in ("textarea", "hidden", "text"):
            control_handle = page.evaluate_handle(f"{self.form_js_selector}.getControl('{field}')")
            # The control text is not always in the control itself, but in a parent element.
            # Being a heuristic, we try to find it by going up the DOM tree.
            # This is up to the page implementation, 5 is an arbitrary number.
            for depth in range(5):
                control_text = control_handle.evaluate("e => e.innerText")
                if control_text != "":
                    break
                control_handle = control_handle.evaluate_handle("e => e.parentElement")
            else:
                raise ValueError(f"Could not find control text for {field}")
        else:
            raise ValueError(f"Unknown control type {control_type}")
        return control_text

    def get_pretty_printed_description(self) -> str:
        """
        Get the task info for this task when used in a private task; Used in L3 compositional tasks.
        called by subclasses
        """
        class_name = self.__class__.__name__
        class_name = class_name.replace("Task", "")
        # Split the words
        words = re.findall(r"[A-Z][^A-Z]*", class_name)
        class_name_formatted = " ".join(words)
        task_specs = {
            "Quantity": self.config["quantity"],
            "Configuration": self.config["configuration"],
        }
        if self.config_only_in_desc:
            task_info = f"- Order the item in the following quantities and with the following configuration:\n"
        else:
            task_specs["Description"] = self.config["description"]
            task_info = f"- {class_name_formatted} with the following specifications:\n"
        for k, v in task_specs.items():
            # Some values might be empty - like the configuration of the apple watch. It is more natural to exclude them
            if not v:
                continue
            # If the value is a dictionary, print it in a nested way
            if isinstance(v, dict):
                task_info += f"    - {k}:\n"
                for k2, v2 in v.items():
                    task_info += f"        - {k2}: {v2[1]}\n"
            else:
                task_info += f"    - {k}: {v}\n"

        return task_info

    def teardown(self) -> None:
        """
        Deletes the request (and automatically all its items)
        """
        self._wait_for_ready(self.page)

        if hasattr(self, "request_sysid") and self.request_sysid is not None:
            db_delete_from_table(
                instance=self.instance, sys_id=self.request_sysid, table="sc_request"
            )

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:

        # Retrieve the request sysid from the URL
        current_url = parse.urlparse(parse.unquote(page.evaluate("() => window.location.href")))
        (self.request_sysid,) = parse.parse_qs(current_url.query).get("sysparm_sys_id", [None])
        if self.request_sysid is None:
            return (
                0,
                False,
                "",
                {"message": "The request was not created, the sysid is not in the URL."},
            )

        # Short sleep to make sure the data is saved in the DB
        # TODO: improve this (noted in issue 291)
        sleep(3)
        r = get_request_by_id(instance=self.instance, sysid=self.request_sysid)
        if r is None:
            return 0, False, "", {"message": "The request is not in the database."}

        if len(r["items"]) == 0:
            return 0, False, "", {"message": "No items were requested."}

        if len(r["items"]) > 1:
            error_msg = (
                "Multiple kinds of items were requested, but only a single one was expected."
            )
            return (
                0,
                True,
                error_msg,
                {"message": error_msg},
            )
        else:
            (first_item,) = r["items"]

        if first_item["short_description"].lower() != self.short_description.lower():
            error_msg = "The requested item is incorrect."
            return 0, True, error_msg, {"message": error_msg}

        if first_item["quantity"] != str(self.quantity):
            error_msg = "The requested quantity is incorrect."
            return 0, True, error_msg, {"message": error_msg}

        options = first_item["options"]
        for k, (element_type, value) in self.requested_configuration.items():
            if element_type == "checkbox" or element_type == "radio":
                if not option_match_heuristic(value, options[k]):
                    error_msg = (
                        f"The requested {k} is incorrect, expected {value} but got {options[k]}."
                    )
                    return (
                        0,
                        True,
                        error_msg,
                        {"message": error_msg},
                    )
            elif element_type == "textarea":
                if value.lower() not in options[k].lower():
                    error_msg = (
                        f"The requested {k} is incorrect, expected {value} but got {options[k]}."
                    )
                    return (
                        0,
                        True,
                        error_msg,
                        {"message": error_msg},
                    )

        return (
            1,
            True,
            "Nice work, thank you!",
            {"message": "Task completed successfully."},
        )


def option_match_heuristic(value, option):
    def _process(x):
        x = str(x).lower()
        x = x.replace("_", "")
        x = x.replace(" ", "")
        return x

    return _process(value) == _process(option)


class OrderDeveloperLaptopTask(OrderHardwareTask):
    config_path = ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="Developer Laptop (Mac)",
            **kwargs,
        )


class OrderIpadMiniTask(OrderHardwareTask):
    config_path = ORDER_IPAD_MINI_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="iPad mini",
            **kwargs,
        )


class OrderIpadProTask(OrderHardwareTask):
    config_path = ORDER_IPAD_PRO_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="iPad pro",
            **kwargs,
        )


class OrderSalesLaptopTask(OrderHardwareTask):
    config_path = ORDER_SALES_LAPTOP_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="Sales Laptop",
            **kwargs,
        )


class OrderStandardLaptopTask(OrderHardwareTask):
    config_path = ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="Standard Laptop",
            **kwargs,
        )


class OrderAppleWatchTask(OrderHardwareTask):
    config_path = ORDER_APPLE_WATCH_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="Apple Watch",
            **kwargs,
        )


class OrderAppleMacBookPro15Task(OrderHardwareTask):
    config_path = ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="Apple MacBook Pro 15",
            **kwargs,
        )


class OrderDevelopmentLaptopPCTask(OrderHardwareTask):
    config_path = ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="Development Laptop (PC)",
            **kwargs,
        )


class OrderLoanerLaptopTask(OrderHardwareTask):
    config_path = ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            fixed_request_item="Loaner Laptop",
            **kwargs,
        )


class OrderFromServiceCatalogTask(OrderHardwareTask):
    """These tasks are organized slightly differently from the OrderHardwareTask tasks since we also sample the catalog item."""

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        super().setup_goal(page=page)

        # Get the task configuration
        assert self.all_configs is not None, "No configuration available for the task."
        self.config = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs)
        )

        # Get goal from config
        goal = self.config["goal"]
        info = {}

        # Used to keep track of the sysid of the request for validation
        self.request_sysid = None

        return goal, info

    def _get_requested_item(self, page: Page) -> dict | None:

        # Retrieve the request sysid from the URL
        current_url = parse.urlparse(parse.unquote(page.evaluate("() => window.location.href")))
        (self.request_sysid,) = parse.parse_qs(current_url.query).get("sysparm_sys_id", [None])
        if self.request_sysid is None:
            return None

        # Short sleep to make sure the data is saved in the DB
        # TODO: improve this (noted in issue 291)
        sleep(3)
        r = get_request_by_id(instance=self.instance, sysid=self.request_sysid)
        if r is None:
            return None

        if len(r["items"]) != 1:
            return None
        (first_item,) = r["items"]

        return first_item


class OrderIphoneTask(OrderFromServiceCatalogTask):
    config_path = ORDER_IPHONE_TASK_CONFIG_PATH

    FIELD_NAME_MAPPING = {
        "Is this a replacement for a lost or broken iPhone?": "replacement",
        "What was the original phone number?": "original_phone_number",
        "Choose the colour": "color",
        "Choose the storage": "storage",
        "Monthly data allowance": "monthly_data_allowance",
    }

    COLOR_MAPPING = {
        # iphone 13 pro
        "Alpine Green": "green",
        "Silver": "silver",
        "Gold": "gold",
        "Graphite": "graphite",
        "Sierra Blue": "sierra_blue",
        # iphone 13
        "Green": "green",
        "Pink": "pink",
        "Blue": "blue",
        "Midnight": "midnight",
        "Starlight": "starlight",
        "Red": "red",
    }

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)
        
        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        # go over values
        if requested_item["options"][self.FIELD_NAME_MAPPING["Monthly data allowance"]] != self.config["monthly_data_allowance"]:
            return 0, False, "", {"message": "The requested monthly data allowance is incorrect."}

        if requested_item["options"][self.FIELD_NAME_MAPPING["Is this a replacement for a lost or broken iPhone?"]] != self.config["replacement"]:
            return 0, False, "", {"message": "The requested replacement status is incorrect."}

        # TODO: add replacement phone number in data
        if requested_item["options"][self.FIELD_NAME_MAPPING["What was the original phone number?"]] != self.config["original_phone_number"]:
            return 0, False, "", {"message": "The requested original phone number is incorrect."}

        if requested_item["options"][self.FIELD_NAME_MAPPING["color"]] != self.COLOR_MAPPING[self.config["color"]]:
            # TODO: display color and config color is not the same
            return 0, False, "", {"message": "The requested color is incorrect."}

        if requested_item["options"][self.FIELD_NAME_MAPPING["storage"]] != self.config["storage"].removesuffix(" GB"):
            return 0, False, "", {"message": "The requested storage is incorrect."}

        return 1, True, "", {"message": "Task completed successfully."}
        
    
class OrderMobilePhoneTask(OrderFromServiceCatalogTask):
    config_path = ORDER_MOBILE_PHONE_TASK_CONFIG_PATH

    FIELD_NAME_MAPPING = {
        "Choose the colour": "color",
        "Choose the storage": "storage",
    }

    COLOR_MAPPING = {
        "Just Black": "black",
        "White": "white",
        "Mystic Green": "green",
        "Mystic Blue": "blue",
        "Mystic Bronze": "bronze",
    }

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)

        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        # go over values

        if requested_item["options"][self.FIELD_NAME_MAPPING["color"]] != self.COLOR_MAPPING[self.config["color"]]:
            return 0, False, "", {"message": "The requested color is incorrect."}

        if requested_item["options"][self.FIELD_NAME_MAPPING["storage"]] != self.config["storage"].removesuffix(" GB"):
            return 0, False, "", {"message": "The requested storage is incorrect."}

        return 1, True, "", {"message": "Task completed successfully."}


class OrderMiscHardwareTask(OrderFromServiceCatalogTask):
    config_path = ORDER_MISC_HARDWARE_TASK_CONFIG_PATH

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)

        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        return 1, True, "", {"message": "Task completed successfully."}

class OrderMiscHardwareWithBusinessJustificationTask(OrderFromServiceCatalogTask):
    config_path = ORDER_MISC_HARDWARE_WITH_BUSINESS_JUSTIFICATION_TASK_CONFIG_PATH

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)

        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        # NOTE: we don't check for `requested for` field.

        # business justification
        if requested_item["options"]["Business justification"] != self.config["business_justification"]:
            return 0, False, "", {"message": "The requested business justification is incorrect."}

        return 1, True, "", {"message": "Task completed successfully."}


class OrderPaperSuppliesTask(OrderFromServiceCatalogTask):
    config_path = ORDER_PAPER_SUPPLIES_TASK_CONFIG_PATH

    ITEM_NAME_MAPPING = {
        "Pens (box of 10)": "boxes of pens",
        "Copier paper (reams)": "reams of paper",
        "Screen wipes (tube of 20)": "tubes of screen wipes",
    }

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)

        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        # check values
        # we check only for 1 value.
        # TODO: expand to multiple items at once
        if str(requested_item["options"][self.ITEM_NAME_MAPPING[self.config["item"]]]) != str(self.config["number"]):
            return 0, False, "", {"message": "The requested item and number is incorrect."}

        # NOTE: we don't look at `Additional requirements` field.

        return 1, True, "", {"message": "Task completed successfully."}

class OrderResetPasswordTask(OrderFromServiceCatalogTask):
    config_path = ORDER_RESET_PASSWORD_TASK_CONFIG_PATH

    def _get_incident_sys_id(self, page: Page) -> str | None:
        # Retrieve the incident sysid from the URL
        current_url = parse.urlparse(parse.unquote(page.evaluate("() => window.location.href")))
        (self.incident_sysid,) = parse.parse_qs(current_url.query).get("sys_id", [None])
        sleep(3)

    def _get_incident_short_description(self) -> str | None:
        # get incident short description
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/incident",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"sys_id={self.incident_sysid}",
                "sysparm_fields": "short_description",
            },
        )
        response.raise_for_status()
        result = response.json().get("result", {})
        return result.get("short_description")

    def _get_incident_work_notes(self) -> dict | None:
        # get incident work notes
        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/sys_journal_field",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"element_id={self.incident_sysid}^element=work_notes",
                "sysparm_fields": "sys_id,value",
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        if len(result) != 1:
            return None

        return result[0]["value"]

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        self._get_incident_sys_id(page)
        if self.incident_sysid is None:
            return 0, False, "", {"message": "The incident sysid is not found."}

        incident_short_description = self._get_incident_short_description()
        incident_work_notes = self._get_incident_work_notes()

        # sanity check short description
        if not incident_short_description.startswith("Reset the password"):
            return 0, False, "", {"message": "The incident short description should start with 'Reset the password'."}
        if not incident_short_description.endswith(self.config["item"]):
            return 0, False, "", {"message": "The incident short description should end with the item name."}
        
        # sanity check work notes
        if not f"System : {self.config["item"]}" in incident_work_notes:
            return 0, False, "", {"message": "The incident work notes should contain the item name."}
        if not f"Contact: {self.config["contact"]}" in incident_work_notes:
            return 0, False, "", {"message": "The incident work notes should contain the contact method."}

        return 1, True, "", {"message": "Task completed successfully."}

class OrderPackagingAndShippingTask(OrderFromServiceCatalogTask):
    config_path = ORDER_PACKAGING_AND_SHIPPING_TASK_CONFIG_PATH

    FIELD_NAME_MAPPING = {
        "Parcel details": "parcel_details",
        "Shipping type": "shipping_type",
        "Destination": "destination",
    }

    SHIPPING_TYPE_MAPPING = {
        "Inter-office": "internal",
        "External Address": "external",
    }

    def _get_location(self, location_sys_id: str):

        response = requests.get(
            f"{self.instance.snow_url}/api/now/table/cmn_location",
            auth=self.instance.snow_credentials,
            headers={"Accept": "application/json"},
            params={
                "sysparm_query": f"sys_id={location_sys_id}",
                "sysparm_fields": "sys_id,name",
            },
        )
        response.raise_for_status()
        result = response.json().get("result", [])
        return result[0]["name"]

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)

        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        # validate values
        if not requested_item[self.FIELD_NAME_MAPPING["shipping_type"]].lower() == self.SHIPPING_TYPE_MAPPING[self.config["shipping_type"]].lower():
            return 0, False, "", {"message": "The requested shipping type is incorrect."}

        # for destination, we need to do a lookup
        # TODO: for now we only look at the destination field, but we could also setup the postcode, city, address line 1/2, etc.
        destination = self._get_location(requested_item[self.FIELD_NAME_MAPPING["destination"]])
        if not destination.lower() == self.config["destination"].lower():
            return 0, False, "", {"message": "The requested destination is incorrect."}

        for keyword in self.config["keywords"].split(" "):
            if not keyword.lower() in requested_item[self.FIELD_NAME_MAPPING["parcel_details"]].lower():
                return 0, False, "", {"message": "The requested parcel details does not contain the expected keyword."}

        return 1, True, "", {"message": "Task completed successfully."}

class OrderSoftwareTask(OrderFromServiceCatalogTask):
    config_path = ORDER_SOFTWARE_TASK_CONFIG_PATH

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)

        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        return 1, True, "", {"message": "Task completed successfully."}

class OrderSoftwareAccessTask(OrderFromServiceCatalogTask):
    config_path = ORDER_SOFTWARE_ACCESS_TASK_CONFIG_PATH

    def validate(self, page: Page, chat_messages: list[str]) -> tuple[int, bool, str, dict]:
        requested_item = self._get_requested_item(page)

        if not requested_item["cat_item"]["display_value"].lower() == self.config["item"].lower():
            return 0, False, "", {"message": "The requested item is incorrect."}

        if not requested_item["quantity"] == self.config["quantity"]:
            return 0, False, "", {"message": "The requested quantity is incorrect."}

        # NOTE: we don't check for `requested for` field.

        # business justification
        if requested_item["options"]["Business justification"] != self.config["business_justification"]:
            return 0, False, "", {"message": "The requested business justification is incorrect."}

        return 1, True, "", {"message": "Task completed successfully."}


__TASKS__ = [
    var
    for var in locals().values()
    if isinstance(var, type) and issubclass(var, OrderHardwareTask) and var is not OrderHardwareTask
]

__DYNAMIC_GUIDANCE_TASKS__ = [
    OrderAppleWatchTask,
    OrderDeveloperLaptopTask,
    OrderIpadProTask,
    OrderIphoneTask,
    OrderMobilePhoneTask,
    OrderSoftwareAccessTask,
    OrderSoftwareTask,
    OrderResetPasswordTask,
    OrderPackagingAndShippingTask,
    OrderPaperSuppliesTask,
    OrderMiscHardwareTask,
    OrderMiscHardwareWithBusinessJustificationTask,
]