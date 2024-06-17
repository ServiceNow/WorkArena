from faker import Faker

fake = Faker()

from browsergym.workarena.tasks.navigation import AllMenuTask
from browsergym.workarena.tasks.send_chat_message import SendChatMessageGenericTask
from browsergym.workarena.tasks.service_catalog import (
    OrderDeveloperLaptopTask,
    OrderIpadMiniTask,
    OrderIpadProTask,
    OrderSalesLaptopTask,
    OrderStandardLaptopTask,
    OrderAppleWatchTask,
    OrderAppleMacBookPro15Task,
    OrderDevelopmentLaptopPCTask,
    OrderLoanerLaptopTask,
)

from .base import HumanEvalTask
from .filter_and_do import FilterAndDoTask

from ..base import AbstractServiceNowTask

from ...api.requested_items import create_requested_item
from ...api.user import create_user
from ...api.utils import db_delete_from_table, table_api_call
from ...config import (
    # Expected columns for the different lists
    EXPECTED_REQUESTED_ITEMS_COLUMNS_PATH,
)
from ...instance import SNowInstance


class FilterRequestedItemsAndOrderCatalogItemTask(FilterAndDoTask, HumanEvalTask):
    """Generic task to filter the requested items list to find what a given user has requested and order the same thing.
    Args:
    fixed_request_item: str
        The requested item to find and order.
    task_class: AbstractServiceNowTask
        The class of the task to order the item.
    """

    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        fixed_request_item: str = None,
        order_task_class: AbstractServiceNowTask = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "module": "Requested Items",
                "application": "Self-Service",
            },
            level=level,
            protocol_name="",
        )
        self.fixed_request_item = fixed_request_item
        self.order_task_class = order_task_class
        # name of the user the item will be assigned to
        self.user_full_name = (
            fake.first_name()
            + "-"
            + fake.first_name()
            + " "
            + fake.last_name()
            + "-"
            + fake.last_name()
        )
        self.short_description = f"Order same item as {self.user_full_name}"
        self.task_description = f'{self.user_full_name} has recently requested an item from the service catalog. You need to order the same. Find what it is from the "Requested Items" list and order it from the service catalog. If possible, set the item\'s configuration to match the following: \n'
        self.created_user_sys_id = None  # sys_id of the user to assign the item to
        self.requested_item_sys_id = None  # sys_id of the requested item to order
        self.tasks = []

    def _setup_list(self) -> None:
        self.filter_config = {
            "list_url": "/now/nav/ui/classic/params/target/sc_req_item_list.do",
            "expected_fields_path": EXPECTED_REQUESTED_ITEMS_COLUMNS_PATH,
            "filter_columns": [
                "requested_for",
            ],
            "filter_kind": "AND",
            "filter_operators": ["contains"],
            "filter_values": [
                f"{self.user_full_name}",
            ],
        }
        # Create a new user to assign the item to
        first_name = self.user_full_name.split(" ")[0]
        last_name = self.user_full_name.split(" ")[1]
        _, _, self.created_user_sys_id = create_user(
            self.instance, first_name=first_name, last_name=last_name, random=self.random
        )
        # Create a new requested item to order
        self.requested_item_sys_id, _ = create_requested_item(
            self.instance,
            system_name=self.fixed_request_item,
            user_sys_id=self.created_user_sys_id,
        )
        self.tasks.append(
            # After the filter has been made and the information retrieved, navigate to the catalog
            AllMenuTask(
                instance=self.instance,
                fixed_config={
                    "module": "Service Catalog",
                    "application": "Self-Service",
                },
                used_in_level_2=True,
                is_validated=False,
            )
        )
        self.tasks.append(
            SendChatMessageGenericTask(
                instance=self.instance,
                message="a",
                answer_format="a",
                level=self.level,
                description=f"Clear the existing filters on the page. \n",
                is_validated=False,
                use_description_in_l3=True,
                used_in_level_2=True,
            )
        )
        order_task_config = self.random.choice(self.order_task_class.all_configs())
        # task to order the item
        item_order_task = self.order_task_class(
            seed=self.seed,
            instance=self.instance,
            fixed_config=order_task_config,
            used_in_level_2=True,
            is_validated=True,
            config_only_in_desc=True,
        )
        self.tasks.append(item_order_task)

    def teardown(self) -> None:
        # Delete the requested item and the user if they exist
        requested_item_exists = table_api_call(
            instance=self.instance,
            table="sc_req_item",
            params={"sysparm_query": f"sys_id={self.requested_item_sys_id}"},
        )["result"]
        if requested_item_exists:
            db_delete_from_table(
                instance=self.instance,
                table="sc_req_item",
                sys_id=self.requested_item_sys_id,
            )
        user_exists = table_api_call(
            instance=self.instance,
            table="sys_user",
            params={"sysparm_query": f"sys_id={self.created_user_sys_id}"},
        )["result"]
        if user_exists:
            db_delete_from_table(
                instance=self.instance,
                table="sys_user",
                sys_id=self.created_user_sys_id,
            )

        super().teardown()


class FilterRequestedItemsAndOrderDeveloperLaptopTask(FilterRequestedItemsAndOrderCatalogItemTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="Developer Laptop (Mac)",
            level=level,
            order_task_class=OrderDeveloperLaptopTask,
        )


class FilterRequestedItemsAndOrderIpadMiniTask(FilterRequestedItemsAndOrderCatalogItemTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="iPad mini",
            level=level,
            order_task_class=OrderIpadMiniTask,
        )


class FilterRequestedItemsAndOrderIpadProTask(FilterRequestedItemsAndOrderCatalogItemTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="iPad pro",
            level=level,
            order_task_class=OrderIpadProTask,
        )


class FilterRequestedItemsAndOrderSalesLaptopTask(FilterRequestedItemsAndOrderCatalogItemTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="Sales Laptop",
            level=level,
            order_task_class=OrderSalesLaptopTask,
        )


class FilterRequestedItemsAndOrderStandardLaptopTask(FilterRequestedItemsAndOrderCatalogItemTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="Standard Laptop",
            level=level,
            order_task_class=OrderStandardLaptopTask,
        )


class FilterRequestedItemsAndOrderAppleWatchTask(FilterRequestedItemsAndOrderCatalogItemTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="Apple Watch",
            level=level,
            order_task_class=OrderAppleWatchTask,
        )


class FilterRequestedItemsAndOrderAppleMacBookPro15Task(
    FilterRequestedItemsAndOrderCatalogItemTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item='Apple MacBook Pro 15"',
            level=level,
            order_task_class=OrderAppleMacBookPro15Task,
        )


class FilterRequestedItemsAndOrderDevelopmentLaptopPCTask(
    FilterRequestedItemsAndOrderCatalogItemTask
):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="Development Laptop (PC)",
            level=level,
            order_task_class=OrderDevelopmentLaptopPCTask,
        )


class FilterRequestedItemsAndOrderLoanerLaptopTask(FilterRequestedItemsAndOrderCatalogItemTask):
    def __init__(
        self,
        seed: int,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            fixed_request_item="Notebook Computer Loaner",
            level=level,
            order_task_class=OrderLoanerLaptopTask,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type)
    and issubclass(var, FilterAndDoTask)
    and var is not FilterAndDoTask
    and var is not FilterRequestedItemsAndOrderCatalogItemTask
]
