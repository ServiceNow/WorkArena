import json

from faker import Faker

fake = Faker()

from playwright.sync_api._generated import Page

from browsergym.workarena.tasks.form import (
    CreateChangeRequestTask,
    CreateHardwareAssetTask,
    CreateIncidentTask,
    CreateProblemTask,
    CreateUserTask,
)
from browsergym.workarena.tasks.list import (
    FilterAssetListTask,
    FilterChangeRequestListTask,
    FilterHardwareListTask,
    FilterIncidentListTask,
    FilterServiceCatalogItemListTask,
    FilterUserListTask,
    SortAssetListTask,
    SortChangeRequestListTask,
    SortHardwareListTask,
    SortIncidentListTask,
    SortServiceCatalogItemListTask,
    SortUserListTask,
)
from browsergym.workarena.tasks.navigation import AllMenuTask
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

from .base import CompositionalTask, HumanEvalTask

from ..base import AbstractServiceNowTask

from ...instance import SNowInstance


class NavigateAndDoTask(CompositionalTask, HumanEvalTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        navigation_config: dict = None,
        level: int = 2,
        task: AbstractServiceNowTask = None,
    ) -> None:
        """
        Generic task to navigate to a specific page and perform a task.

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of tuples, each containing a subtask
        navigation_config: dict
            Configuration to use for the navigation task. Contains the application and the module; the URL is not necessary as the
            nav step is not validated.
        level: int
            The level of the task; choice between 2 and 3. L2 will have all the info in the the goal and start in the SNOW home page.
            L3 will start in a private task page describing the information needed to complete the task and the related company protocol
            to complete it.
        task: AbstractServiceNowTask
            The task to perform after navigating to the page.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed. Provided by the child class.
        short_description: str
            A short description of the task to be completed. "Create a new user". Provided by the child class.
        """
        assert level in [2, 3], "Level must be either 2 or 3"
        self.level = level
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            level=level,
        )
        self.used_in_level_2 = self.level == 2
        self.task = task
        self.task_description = None
        self.short_description = None
        # Get the navigation configuration; there is only one configuration for each application and module combo
        self.navigation_config = navigation_config

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        config = self.fixed_config if self.fixed_config else self._get_config()
        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[AbstractServiceNowTask]:

        config = [
            # Navigate to the task start page
            AllMenuTask(
                instance=self.instance,
                fixed_config=self.navigation_config,
                is_validated=False,
                used_in_level_2=True,
                has_description=True,
            ),
            self.task,
        ]

        return config


class NavigateAndCreateUserTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the user list page and create a new user.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a new user"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Organization",
                "module": "Users",
            },
            level=level,
            task=CreateUserTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Create a new user with the required information. \n"
        self.short_description = "Create a new user"


class NavigateAndCreateIncidentTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the incident list page and create a new incident.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a new incident"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Service Desk",
                "module": "Incidents",
            },
            level=level,
            task=CreateIncidentTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Create a new incident with the required information. \n"
        self.short_description = "Create a new incident"


class NavigateAndCreateChangeRequestTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the change request list page and create a new change request.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a new change request"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Change",
                "module": "All",
            },
            level=level,
            task=CreateChangeRequestTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = (
            'Create a new "Normal" change request with the required information. \n'
        )
        self.short_description = 'Create a new "Normal" change request'


class NavigateAndCreateProblemTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the problem list page and create a new problem.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a new problem"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Problem",
                "module": "All",
            },
            level=level,
            task=CreateProblemTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Create a new problem with the required information. \n"
        self.short_description = "Create a new problem"


class NavigateAndCreateHardwareAssetTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the hardware asset list page and create a new hardware asset.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Create a new hardware asset"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Asset",
                "module": "Portfolios > Hardware Assets",
            },
            level=level,
            task=CreateHardwareAssetTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Create a new hardware asset with the required information. \n"
        self.short_description = "Create a new hardware asset"


class NavigateAndOrderStandardLaptopTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order a standard laptop.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order a standard laptop"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderStandardLaptopTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order a standard laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a standard laptop from the service catalog"


class NavigateAndOrderSalesLaptopTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order a sales laptop.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order a sales laptop"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderSalesLaptopTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order a sales laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a sales laptop from the service catalog"


class NavigateAndOrderDeveloperLaptopTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order a developer laptop.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order a developer laptop"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderDeveloperLaptopTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order a developer laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a developer laptop from the service catalog"


class NavigateAndOrderIpadProTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order an iPad Pro.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order an iPad Pro"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderIpadProTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order an iPad Pro from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an iPad Pro from the service catalog"


class NavigateAndOrderIpadMiniTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order an iPad Mini.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order an iPad Mini"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderIpadMiniTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order an iPad Mini from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an iPad Mini from the service catalog"


class NavigateAndOrderAppleWatchTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order an Apple Watch.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order an Apple Watch"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderAppleWatchTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order an Apple Watch from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an Apple Watch from the service catalog"


class NavigateAndOrderAppleMacBookPro15Task(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order an Apple MacBook Pro 15".

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order an Apple MacBook Pro 15"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderAppleMacBookPro15Task(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = 'Order an Apple MacBook Pro 15" from the service catalog with the required configuration if applicable. \n'
        self.short_description = 'Order an Apple MacBook Pro 15" from the service catalog'


class NavigateAndOrderDevelopmentLaptopPCTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order a development laptop PC.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order a development laptop PC"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderDevelopmentLaptopPCTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order a development laptop PC from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a development laptop PC from the service catalog"


class NavigateAndOrderLoanerLaptopTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Navigate to the service catalog item list page and order a loaner laptop.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Order a loaner laptop"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Self-Service",
                "module": "Service Catalog",
            },
            level=level,
            task=OrderLoanerLaptopTask(
                seed=seed, instance=instance, used_in_level_2=(level == 2), is_validated=True
            ),
        )
        self.task_description = "Order a loaner laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a loaner laptop from the service catalog"


class NavigateAndFilterAssetListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "alm_asset",
    ) -> None:
        """
        Navigate to the user list page and filter the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the asset list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Asset",
                "module": "Portfolios > All Assets",
            },
            level=level,
            task=FilterAssetListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Filter the asset list - in Asset > Portflios > All Assets - based on specific criteria. \n"
        self.short_description = "Filter the asset list."
        self.list_name = list_name


class NavigateAndFilterUserListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "user",
    ) -> None:
        """
        Navigate to the user list page and filter the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the user list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Organization",
                "module": "Users",
            },
            level=level,
            task=FilterUserListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Filter the user list based on specific criteria. \n"
        self.short_description = "Filter the user list."
        self.list_name = list_name


class NavigateAndFilterIncidentListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "incident",
    ) -> None:
        """
        Navigate to the incident list page and filter the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the incident list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Service Desk",
                "module": "Incidents",
            },
            level=level,
            task=FilterIncidentListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Filter the incident list based on specific criteria. \n"
        self.short_description = "Filter the incident list."
        self.list_name = list_name


class NavigateAndFilterChangeRequestListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "change_request",
    ) -> None:
        """
        Navigate to the change request list page and filter the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the change request list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Change",
                "module": "All",
            },
            level=level,
            task=FilterChangeRequestListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Filter the change request list based on specific criteria. \n"
        self.short_description = "Filter the change request list."
        self.list_name = list_name


class NavigateAndFilterHardwareListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "hardware_asset",
    ) -> None:
        """
        Navigate to the hardware asset list page and filter the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the hardware asset list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Asset",
                "module": "Portfolios > Hardware Assets",
            },
            level=level,
            task=FilterHardwareListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Filter the hardware asset list based on specific criteria. \n"
        self.short_description = "Filter the hardware asset list."
        self.list_name = list_name


class NavigateAndFilterServiceCatalogItemListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "service_catalog_item",
    ) -> None:
        """
        Navigate to the service catalog item list page and filter the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Filter the service catalog item list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Service Catalog",
                "module": "Catalog Definitions > Maintain Items",
            },
            level=level,
            task=FilterServiceCatalogItemListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = (
            "Filter the service catalog item list based on specific criteria. \n"
        )
        self.short_description = "Filter the service catalog item list."
        self.list_name = list_name


class NavigateAndSortAssetListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "alm_asset",
    ) -> None:
        """
        Navigate to the user list page and sort the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Sort the asset list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Asset",
                "module": "Portfolios > All Assets",
            },
            level=level,
            task=SortAssetListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Sort the asset list - in Asset > Portflios > All Assets - based on specific criteria. \n"
        self.short_description = "Sort the asset list."
        self.list_name = list_name


class NavigateAndSortUserListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "user",
    ) -> None:
        """
        Navigate to the user list page and sort the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Sort the user list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Organization",
                "module": "Users",
            },
            level=level,
            task=SortUserListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Sort the user list based on specific criteria. \n"
        self.short_description = "Sort the user list."
        self.list_name = list_name


class NavigateAndSortIncidentListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "incident",
    ) -> None:
        """
        Navigate to the incident list page and sort the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Sort the incident list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Service Desk",
                "module": "Incidents",
            },
            level=level,
            task=SortIncidentListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Sort the incident list based on specific criteria. \n"
        self.short_description = "Sort the incident list."
        self.list_name = list_name


class NavigateAndSortChangeRequestListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "change_request",
    ) -> None:
        """
        Navigate to the change request list page and sort the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Sort the change request list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Change",
                "module": "All",
            },
            level=level,
            task=SortChangeRequestListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Sort the change request list based on specific criteria. \n"
        self.short_description = "Sort the change request list."
        self.list_name = list_name


class NavigateAndSortHardwareListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "hardware_asset",
    ) -> None:
        """
        Navigate to the hardware asset list page and sort the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Sort the hardware asset list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Asset",
                "module": "Portfolios > Hardware Assets",
            },
            level=level,
            task=SortHardwareListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Sort the hardware asset list based on specific criteria. \n"
        self.short_description = "Sort the hardware asset list."
        self.list_name = list_name


class NavigateAndSortServiceCatalogItemListTask(NavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "service_catalog_item",
    ) -> None:
        """
        Navigate to the service catalog item list page and sort the list based on a specific criteria.

        Attributes:
        -----------
        task_description: str
            The start of the task description to be completed.
        short_description: str
            A short description of the task to be completed. "Sort the service catalog item list"
        """
        super().__init__(
            seed=seed,
            instance=instance,
            fixed_config=fixed_config,
            navigation_config={
                "application": "Service Catalog",
                "module": "Catalog Definitions > Maintain Items",
            },
            level=level,
            task=SortServiceCatalogItemListTask(
                seed=seed,
                instance=instance,
                used_in_level_2=(level == 2),
                is_validated=True,
                list_name=list_name,
            ),
        )
        self.task_description = "Sort the service catalog item list based on specific criteria. \n"
        self.short_description = "Sort the service catalog item list."
        self.list_name = list_name


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, NavigateAndDoTask) and var is not NavigateAndDoTask
]

NAVIGATE_AND_CREATE_TASKS = [
    NavigateAndCreateUserTask,
    NavigateAndCreateIncidentTask,
    NavigateAndCreateChangeRequestTask,
    NavigateAndCreateProblemTask,
    NavigateAndCreateHardwareAssetTask,
]
NAVIGATE_AND_ORDER_TASKS = [
    NavigateAndOrderStandardLaptopTask,
    NavigateAndOrderSalesLaptopTask,
    NavigateAndOrderDeveloperLaptopTask,
    NavigateAndOrderIpadProTask,
    NavigateAndOrderIpadMiniTask,
    NavigateAndOrderAppleWatchTask,
    NavigateAndOrderAppleMacBookPro15Task,
    NavigateAndOrderDevelopmentLaptopPCTask,
    NavigateAndOrderLoanerLaptopTask,
]
NAVIGATE_AND_FILTER_TASKS = [
    NavigateAndFilterAssetListTask,
    NavigateAndFilterUserListTask,
    NavigateAndFilterIncidentListTask,
    NavigateAndFilterChangeRequestListTask,
    NavigateAndFilterHardwareListTask,
    NavigateAndFilterServiceCatalogItemListTask,
]
NAVIGATE_AND_SORT_TASKS = [
    NavigateAndSortAssetListTask,
    NavigateAndSortUserListTask,
    NavigateAndSortIncidentListTask,
    NavigateAndSortChangeRequestListTask,
    NavigateAndSortHardwareListTask,
    NavigateAndSortServiceCatalogItemListTask,
]
