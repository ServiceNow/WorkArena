from faker import Faker

fake = Faker()
from functools import partial

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

from .base import HumanEvalTask, InfeasibleCompositionalTask
from .utils.infeasible_configs import (
    get_infeasible_form_config,
    get_infeasible_service_catalog_config,
    get_infeasible_filter_config,
    get_infeasible_sort_config,
)

from ..base import AbstractServiceNowTask

from ...instance import SNowInstance


class InfeasibleNavigateAndDoTask(InfeasibleCompositionalTask, HumanEvalTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        function: callable = None,
        provide_reason: bool = True,
        navigation_config: dict = None,
        level: int = 2,
        task_class: AbstractServiceNowTask = None,
    ) -> None:
        """
        Generic task to navigate to a specific page and perform a task.

        Parameters:
        -----------
        instance: SNowInstance
            The ServiceNow instance to run the task on.
        fixed_config: list[AbstractServiceNowTask]
            A list of tuples, each containing a subtask
        function: callable
            Function that takes a valid config and renders it infeasible.
        provide_reason: bool
            Whether to provide a reason for the infeasibility. If False, the list of reasons will be [""] so that
            any infeasibility can be detected by the absence of a reason.
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
        self.task_class = task_class
        self.task_description = None
        self.short_description = None
        # Get the navigation configuration; there is only one configuration for each application and module combo
        self.navigation_config = navigation_config
        self.function = partial(function, provide_reason=provide_reason)

    def setup_goal(self, page: Page) -> tuple[str, dict]:
        config = self.fixed_config if self.fixed_config else self._get_config()
        goal, info = super().setup_goal(page=page, config=config)

        return goal, info

    def _get_config(self) -> list[AbstractServiceNowTask]:
        valid_task_config = self.random.choice(self.task_class.all_configs())
        infeasible_task_config, self.infeasible_reasons = self.function(
            config=valid_task_config, random=self.random
        )
        config = [
            # Infeasible version of navigate to the task start page
            AllMenuTask(
                instance=self.instance,
                fixed_config=self.navigation_config,
                is_validated=False,
                used_in_level_2=True,
                has_description=True,
            ),
            self.task_class(
                seed=self.seed,
                instance=self.instance,
                fixed_config=infeasible_task_config,
                is_validated=False,
                has_description=True,
                used_in_level_2=self.used_in_level_2,
            ),
        ]

        return config


class InfeasibleNavigateAndCreateUserWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the user list page and create a new user.

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
            function=get_infeasible_form_config,
            task_class=CreateUserTask,
            provide_reason=True,
        )
        self.task_description = "Create a new user with the required information. \n"
        self.short_description = "Create a new user"


class InfeasibleNavigateAndCreateUserTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the user list page and create a new user.

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
            provide_reason=False,
            function=get_infeasible_form_config,
            task_class=CreateUserTask,
        )
        self.task_description = "Create a new user with the required information. \n"
        self.short_description = "Create a new user"


class InfeasibleNavigateAndCreateIncidentWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the incident list page and create a new incident.

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
            function=get_infeasible_form_config,
            task_class=CreateIncidentTask,
            provide_reason=True,
        )
        self.task_description = "Create a new incident with the required information. \n"
        self.short_description = "Create a new incident"


class InfeasibleNavigateAndCreateIncidentTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the incident list page and create a new incident.

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
            provide_reason=False,
            function=get_infeasible_form_config,
            task_class=CreateIncidentTask,
        )
        self.task_description = "Create a new incident with the required information. \n"
        self.short_description = "Create a new incident"


class InfeasibleNavigateAndCreateChangeRequestWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the change request list page and create a new change request.

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
            function=get_infeasible_form_config,
            task_class=CreateChangeRequestTask,
            provide_reason=True,
        )
        self.task_description = (
            'Create a new "Normal" change request with the required information. \n'
        )
        self.short_description = 'Create a new "Normal" change request'


class InfeasibleNavigateAndCreateChangeRequestTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the change request list page and create a new change request.

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
            provide_reason=False,
            function=get_infeasible_form_config,
            task_class=CreateChangeRequestTask,
        )
        self.task_description = (
            'Create a new "Normal" change request with the required information. \n'
        )
        self.short_description = 'Create a new "Normal" change request'


class InfeasibleNavigateAndCreateProblemWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the problem list page and create a new problem.

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
            function=get_infeasible_form_config,
            task_class=CreateProblemTask,
            provide_reason=True,
        )
        self.task_description = "Create a new problem with the required information. \n"
        self.short_description = "Create a new problem"


class InfeasibleNavigateAndCreateProblemTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the problem list page and create a new problem.

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
            provide_reason=False,
            function=get_infeasible_form_config,
            task_class=CreateProblemTask,
        )
        self.task_description = "Create a new problem with the required information. \n"
        self.short_description = "Create a new problem"


class InfeasibleNavigateAndCreateHardwareAssetWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the hardware asset list page and create a new hardware asset.

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
            function=get_infeasible_form_config,
            task_class=CreateHardwareAssetTask,
            provide_reason=True,
        )
        self.task_description = "Create a new hardware asset with the required information. \n"
        self.short_description = "Create a new hardware asset"


class InfeasibleNavigateAndCreateHardwareAssetTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the hardware asset list page and create a new hardware asset.

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
            provide_reason=False,
            function=get_infeasible_form_config,
            task_class=CreateHardwareAssetTask,
        )
        self.task_description = "Create a new hardware asset with the required information. \n"
        self.short_description = "Create a new hardware asset"


class InfeasibleNavigateAndOrderStandardLaptopWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a standard laptop.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderStandardLaptopTask,
            provide_reason=True,
        )
        self.task_description = "Order a standard laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a standard laptop from the service catalog"


class InfeasibleNavigateAndOrderStandardLaptopTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a standard laptop.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderStandardLaptopTask,
        )
        self.task_description = "Order a standard laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a standard laptop from the service catalog"


class InfeasibleNavigateAndOrderSalesLaptopWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a sales laptop.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderSalesLaptopTask,
            provide_reason=True,
        )
        self.task_description = "Order a sales laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a sales laptop from the service catalog"


class InfeasibleNavigateAndOrderSalesLaptopTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a sales laptop.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderSalesLaptopTask,
        )
        self.task_description = "Order a sales laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a sales laptop from the service catalog"


class InfeasibleNavigateAndOrderDeveloperLaptopWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a developer laptop.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderDeveloperLaptopTask,
            provide_reason=True,
        )
        self.task_description = "Order a developer laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a developer laptop from the service catalog"


class InfeasibleNavigateAndOrderDeveloperLaptopTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a developer laptop.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderDeveloperLaptopTask,
        )
        self.task_description = "Order a developer laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a developer laptop from the service catalog"


class InfeasibleNavigateAndOrderIpadProWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an iPad Pro.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderIpadProTask,
            provide_reason=True,
        )
        self.task_description = "Order an iPad Pro from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an iPad Pro from the service catalog"


class InfeasibleNavigateAndOrderIpadProTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an iPad Pro.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderIpadProTask,
        )
        self.task_description = "Order an iPad Pro from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an iPad Pro from the service catalog"


class InfeasibleNavigateAndOrderIpadMiniWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an iPad Mini.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderIpadMiniTask,
            provide_reason=True,
        )
        self.task_description = "Order an iPad Mini from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an iPad Mini from the service catalog"


class InfeasibleNavigateAndOrderIpadMiniTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an iPad Mini.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderIpadMiniTask,
        )
        self.task_description = "Order an iPad Mini from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an iPad Mini from the service catalog"


class InfeasibleNavigateAndOrderAppleWatchWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an Apple Watch.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderAppleWatchTask,
            provide_reason=True,
        )
        self.task_description = "Order an Apple Watch from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an Apple Watch from the service catalog"


class InfeasibleNavigateAndOrderAppleWatchTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an Apple Watch.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderAppleWatchTask,
        )
        self.task_description = "Order an Apple Watch from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order an Apple Watch from the service catalog"


class InfeasibleNavigateAndOrderAppleMacBookPro15WithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an Apple MacBook Pro 15".

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderAppleMacBookPro15Task,
            provide_reason=True,
        )
        self.task_description = 'Order an Apple MacBook Pro 15" from the service catalog with the required configuration if applicable. \n'
        self.short_description = 'Order an Apple MacBook Pro 15" from the service catalog'


class InfeasibleNavigateAndOrderAppleMacBookPro15Task(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order an Apple MacBook Pro 15".

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderAppleMacBookPro15Task,
        )
        self.task_description = 'Order an Apple MacBook Pro 15" from the service catalog with the required configuration if applicable. \n'
        self.short_description = 'Order an Apple MacBook Pro 15" from the service catalog'


class InfeasibleNavigateAndOrderDevelopmentLaptopPCWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a development laptop PC.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderDevelopmentLaptopPCTask,
            provide_reason=True,
        )
        self.task_description = "Order a development laptop PC from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a development laptop PC from the service catalog"


class InfeasibleNavigateAndOrderDevelopmentLaptopPCTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a development laptop PC.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderDevelopmentLaptopPCTask,
        )
        self.task_description = "Order a development laptop PC from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a development laptop PC from the service catalog"


class InfeasibleNavigateAndOrderLoanerLaptopWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a loaner laptop.

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
            function=get_infeasible_service_catalog_config,
            task_class=OrderLoanerLaptopTask,
            provide_reason=True,
        )
        self.task_description = "Order a loaner laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a loaner laptop from the service catalog"


class InfeasibleNavigateAndOrderLoanerLaptopTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and order a loaner laptop.

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
            provide_reason=False,
            function=get_infeasible_service_catalog_config,
            task_class=OrderLoanerLaptopTask,
        )
        self.task_description = "Order a loaner laptop from the service catalog with the required configuration if applicable. \n"
        self.short_description = "Order a loaner laptop from the service catalog"


class InfeasibleNavigateAndFilterAssetListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "alm_asset",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and filter the list based on a specific criteria.

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
            function=get_infeasible_filter_config,
            task_class=FilterAssetListTask,
            provide_reason=True,
        )
        self.task_description = "Filter the asset list - in Asset > Portflios > All Assets - based on specific criteria. \n"
        self.short_description = "Filter the asset list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterAssetListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "alm_asset",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and filter the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_filter_config,
            task_class=FilterAssetListTask,
        )
        self.task_description = "Filter the asset list - in Asset > Portflios > All Assets - based on specific criteria. \n"
        self.short_description = "Filter the asset list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterUserListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "user",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and filter the list based on a specific criteria.

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
            function=get_infeasible_filter_config,
            task_class=FilterUserListTask,
            provide_reason=True,
        )
        self.task_description = "Filter the user list based on specific criteria. \n"
        self.short_description = "Filter the user list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterUserListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "user",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and filter the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_filter_config,
            task_class=FilterUserListTask,
        )
        self.task_description = "Filter the user list based on specific criteria. \n"
        self.short_description = "Filter the user list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterIncidentListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "incident",
    ) -> None:
        """
        Infeasible version of navigate to the incident list page and filter the list based on a specific criteria.

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
            function=get_infeasible_filter_config,
            task_class=FilterIncidentListTask,
            provide_reason=True,
        )
        self.task_description = "Filter the incident list based on specific criteria. \n"
        self.short_description = "Filter the incident list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterIncidentListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "incident",
    ) -> None:
        """
        Infeasible version of navigate to the incident list page and filter the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_filter_config,
            task_class=FilterIncidentListTask,
        )
        self.task_description = "Filter the incident list based on specific criteria. \n"
        self.short_description = "Filter the incident list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterChangeRequestListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "change_request",
    ) -> None:
        """
        Infeasible version of navigate to the change request list page and filter the list based on a specific criteria.

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
            function=get_infeasible_filter_config,
            task_class=FilterChangeRequestListTask,
            provide_reason=True,
        )
        self.task_description = "Filter the change request list based on specific criteria. \n"
        self.short_description = "Filter the change request list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterChangeRequestListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "change_request",
    ) -> None:
        """
        Infeasible version of navigate to the change request list page and filter the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_filter_config,
            task_class=FilterChangeRequestListTask,
        )
        self.task_description = "Filter the change request list based on specific criteria. \n"
        self.short_description = "Filter the change request list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterHardwareListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "hardware_asset",
    ) -> None:
        """
        Infeasible version of navigate to the hardware asset list page and filter the list based on a specific criteria.

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
            function=get_infeasible_filter_config,
            task_class=FilterHardwareListTask,
            provide_reason=True,
        )
        self.task_description = "Filter the hardware asset list based on specific criteria. \n"
        self.short_description = "Filter the hardware asset list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterHardwareListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "hardware_asset",
    ) -> None:
        """
        Infeasible version of navigate to the hardware asset list page and filter the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_filter_config,
            task_class=FilterHardwareListTask,
        )
        self.task_description = "Filter the hardware asset list based on specific criteria. \n"
        self.short_description = "Filter the hardware asset list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterServiceCatalogItemListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "service_catalog_item",
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and filter the list based on a specific criteria.

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
            function=get_infeasible_filter_config,
            task_class=FilterServiceCatalogItemListTask,
            provide_reason=True,
        )
        self.task_description = (
            "Filter the service catalog item list based on specific criteria. \n"
        )
        self.short_description = "Filter the service catalog item list."
        self.list_name = list_name


class InfeasibleNavigateAndFilterServiceCatalogItemListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "service_catalog_item",
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and filter the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_filter_config,
            task_class=FilterServiceCatalogItemListTask,
        )
        self.task_description = (
            "Filter the service catalog item list based on specific criteria. \n"
        )
        self.short_description = "Filter the service catalog item list."
        self.list_name = list_name


class InfeasibleNavigateAndSortAssetListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "alm_asset",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and sort the list based on a specific criteria.

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
            function=get_infeasible_sort_config,
            task_class=SortAssetListTask,
            provide_reason=True,
        )
        self.task_description = "Sort the asset list - in Asset > Portflios > All Assets - based on specific criteria. \n"
        self.short_description = "Sort the asset list."
        self.list_name = list_name


class InfeasibleNavigateAndSortAssetListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "alm_asset",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and sort the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_sort_config,
            task_class=SortAssetListTask,
        )
        self.task_description = "Sort the asset list - in Asset > Portflios > All Assets - based on specific criteria. \n"
        self.short_description = "Sort the asset list."
        self.list_name = list_name


class InfeasibleNavigateAndSortUserListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "user",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and sort the list based on a specific criteria.

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
            function=get_infeasible_sort_config,
            task_class=SortUserListTask,
            provide_reason=True,
        )
        self.task_description = "Sort the user list based on specific criteria. \n"
        self.short_description = "Sort the user list."
        self.list_name = list_name


class InfeasibleNavigateAndSortUserListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "user",
    ) -> None:
        """
        Infeasible version of navigate to the user list page and sort the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_sort_config,
            task_class=SortUserListTask,
        )
        self.task_description = "Sort the user list based on specific criteria. \n"
        self.short_description = "Sort the user list."
        self.list_name = list_name


class InfeasibleNavigateAndSortIncidentListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "incident",
    ) -> None:
        """
        Infeasible version of navigate to the incident list page and sort the list based on a specific criteria.

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
            function=get_infeasible_sort_config,
            task_class=SortIncidentListTask,
            provide_reason=True,
        )
        self.task_description = "Sort the incident list based on specific criteria. \n"
        self.short_description = "Sort the incident list."
        self.list_name = list_name


class InfeasibleNavigateAndSortIncidentListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "incident",
    ) -> None:
        """
        Infeasible version of navigate to the incident list page and sort the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_sort_config,
            task_class=SortIncidentListTask,
        )
        self.task_description = "Sort the incident list based on specific criteria. \n"
        self.short_description = "Sort the incident list."
        self.list_name = list_name


class InfeasibleNavigateAndSortChangeRequestListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "change_request",
    ) -> None:
        """
        Infeasible version of navigate to the change request list page and sort the list based on a specific criteria.

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
            function=get_infeasible_sort_config,
            task_class=SortChangeRequestListTask,
            provide_reason=True,
        )
        self.task_description = "Sort the change request list based on specific criteria. \n"
        self.short_description = "Sort the change request list."
        self.list_name = list_name


class InfeasibleNavigateAndSortChangeRequestListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "change_request",
    ) -> None:
        """
        Infeasible version of navigate to the change request list page and sort the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_sort_config,
            task_class=SortChangeRequestListTask,
        )
        self.task_description = "Sort the change request list based on specific criteria. \n"
        self.short_description = "Sort the change request list."
        self.list_name = list_name


class InfeasibleNavigateAndSortHardwareListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "hardware_asset",
    ) -> None:
        """
        Infeasible version of navigate to the hardware asset list page and sort the list based on a specific criteria.

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
            function=get_infeasible_sort_config,
            task_class=SortHardwareListTask,
            provide_reason=True,
        )
        self.task_description = "Sort the hardware asset list based on specific criteria. \n"
        self.short_description = "Sort the hardware asset list."
        self.list_name = list_name


class InfeasibleNavigateAndSortHardwareListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "hardware_asset",
    ) -> None:
        """
        Infeasible version of navigate to the hardware asset list page and sort the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_sort_config,
            task_class=SortHardwareListTask,
        )
        self.task_description = "Sort the hardware asset list based on specific criteria. \n"
        self.short_description = "Sort the hardware asset list."
        self.list_name = list_name


class InfeasibleNavigateAndSortServiceCatalogItemListWithReasonTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "service_catalog_item",
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and sort the list based on a specific criteria.

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
            function=get_infeasible_sort_config,
            task_class=SortServiceCatalogItemListTask,
            provide_reason=True,
        )
        self.task_description = "Sort the service catalog item list based on specific criteria. \n"
        self.short_description = "Sort the service catalog item list."
        self.list_name = list_name


class InfeasibleNavigateAndSortServiceCatalogItemListTask(InfeasibleNavigateAndDoTask):
    def __init__(
        self,
        seed: int = None,
        instance: SNowInstance = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        list_name: str = "service_catalog_item",
    ) -> None:
        """
        Infeasible version of navigate to the service catalog item list page and sort the list based on a specific criteria.

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
            provide_reason=False,
            function=get_infeasible_sort_config,
            task_class=SortServiceCatalogItemListTask,
        )
        self.task_description = "Sort the service catalog item list based on specific criteria. \n"
        self.short_description = "Sort the service catalog item list."
        self.list_name = list_name


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type)
    and issubclass(var, InfeasibleNavigateAndDoTask)
    and var is not InfeasibleNavigateAndDoTask
]

INFEASIBLE_NAVIGATE_AND_CREATE_WITH_REASON = [
    InfeasibleNavigateAndCreateUserWithReasonTask,
    InfeasibleNavigateAndCreateIncidentWithReasonTask,
    InfeasibleNavigateAndCreateChangeRequestWithReasonTask,
    InfeasibleNavigateAndCreateProblemWithReasonTask,
    InfeasibleNavigateAndCreateHardwareAssetWithReasonTask,
]
INFEASIBLE_NAVIGATE_AND_CREATE = [
    InfeasibleNavigateAndCreateUserTask,
    InfeasibleNavigateAndCreateIncidentTask,
    InfeasibleNavigateAndCreateChangeRequestTask,
    InfeasibleNavigateAndCreateProblemTask,
    InfeasibleNavigateAndCreateHardwareAssetTask,
]
INFEASIBLE_NAVIGATE_AND_ORDER_WITH_REASON = [
    InfeasibleNavigateAndOrderStandardLaptopWithReasonTask,
    InfeasibleNavigateAndOrderSalesLaptopWithReasonTask,
    InfeasibleNavigateAndOrderDeveloperLaptopWithReasonTask,
    InfeasibleNavigateAndOrderIpadProWithReasonTask,
    InfeasibleNavigateAndOrderIpadMiniWithReasonTask,
    InfeasibleNavigateAndOrderAppleWatchWithReasonTask,
    InfeasibleNavigateAndOrderAppleMacBookPro15WithReasonTask,
    InfeasibleNavigateAndOrderDevelopmentLaptopPCWithReasonTask,
    InfeasibleNavigateAndOrderLoanerLaptopWithReasonTask,
]
INFEASIBLE_NAVIGATE_AND_ORDER = [
    InfeasibleNavigateAndOrderStandardLaptopTask,
    InfeasibleNavigateAndOrderSalesLaptopTask,
    InfeasibleNavigateAndOrderDeveloperLaptopTask,
    InfeasibleNavigateAndOrderIpadProTask,
    InfeasibleNavigateAndOrderIpadMiniTask,
    InfeasibleNavigateAndOrderAppleWatchTask,
    InfeasibleNavigateAndOrderAppleMacBookPro15Task,
    InfeasibleNavigateAndOrderDevelopmentLaptopPCTask,
    InfeasibleNavigateAndOrderLoanerLaptopTask,
]
INFEASIBLE_NAVIGATE_AND_FILTER_WITH_REASON = [
    InfeasibleNavigateAndFilterAssetListWithReasonTask,
    InfeasibleNavigateAndFilterUserListWithReasonTask,
    InfeasibleNavigateAndFilterIncidentListWithReasonTask,
    InfeasibleNavigateAndFilterChangeRequestListWithReasonTask,
    InfeasibleNavigateAndFilterHardwareListWithReasonTask,
    InfeasibleNavigateAndFilterServiceCatalogItemListWithReasonTask,
]
INFEASIBLE_NAVIGATE_AND_FILTER = [
    InfeasibleNavigateAndFilterAssetListTask,
    InfeasibleNavigateAndFilterUserListTask,
    InfeasibleNavigateAndFilterIncidentListTask,
    InfeasibleNavigateAndFilterChangeRequestListTask,
    InfeasibleNavigateAndFilterHardwareListTask,
    InfeasibleNavigateAndFilterServiceCatalogItemListTask,
]
INFEASIBLE_NAVIGATE_AND_SORT_WITH_REASON = [
    InfeasibleNavigateAndSortAssetListWithReasonTask,
    InfeasibleNavigateAndSortUserListWithReasonTask,
    InfeasibleNavigateAndSortIncidentListWithReasonTask,
    InfeasibleNavigateAndSortChangeRequestListWithReasonTask,
    InfeasibleNavigateAndSortHardwareListWithReasonTask,
    InfeasibleNavigateAndSortServiceCatalogItemListWithReasonTask,
]
INFEASIBLE_NAVIGATE_AND_SORT = [
    InfeasibleNavigateAndSortAssetListTask,
    InfeasibleNavigateAndSortUserListTask,
    InfeasibleNavigateAndSortIncidentListTask,
    InfeasibleNavigateAndSortChangeRequestListTask,
    InfeasibleNavigateAndSortHardwareListTask,
    InfeasibleNavigateAndSortServiceCatalogItemListTask,
]
