from .dash_do_base import DashboardRetrieveCatalogAndDoInfeasibleTask, DashDoFinalTask

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask, SingleChartMeanMedianModeRetrievalTask

from ...api.utils import table_api_call, db_delete_from_table
from ...config import (
    ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH,
    ORDER_IPAD_MINI_TASK_CONFIG_PATH,
    ORDER_IPAD_PRO_TASK_CONFIG_PATH,
    ORDER_SALES_LAPTOP_TASK_CONFIG_PATH,
    ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH,
    ORDER_APPLE_WATCH_TASK_CONFIG_PATH,
    ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH,
    ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH,
    ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH,
)
from ...instance import SNowInstance

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


class DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_DEVELOPER_LAPTOP_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderDeveloperLaptopTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="Developer Laptop (Mac)",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderDeveloperLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderDeveloperLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderDeveloperLaptopWithReasonInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderDeveloperLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderDeveloperLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderDeveloperLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderDeveloperLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderDeveloperLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_IPAD_MINI_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderIpadMiniTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="iPad mini",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderiPadMiniInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderiPadMiniInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderiPadMiniInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderiPadMiniInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderiPadMiniInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderiPadMiniInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderiPadMiniInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderiPadMiniInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadMiniInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_IPAD_PRO_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderIpadProTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="iPad pro",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderiPadProInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderiPadProInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderiPadProInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderiPadProInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderiPadProInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderiPadProInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderiPadProInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderiPadProInfeasibleTask(
    DashboardRetrieveCatalogAndOrderiPadProInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_SALES_LAPTOP_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderSalesLaptopTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="Sales Laptop",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderSalesLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderSalesLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderSalesLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderSalesLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderSalesLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderSalesLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderSalesLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderSalesLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_STANDARD_LAPTOP_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderStandardLaptopTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="Standard Laptop",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderStandardLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderStandardLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderStandardLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderStandardLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderStandardLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderStandardLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderStandardLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderStandardLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_APPLE_WATCH_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderAppleWatchTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="Apple Watch",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderAppleWatchInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderAppleWatchInfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderAppleWatchInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderAppleWatchInfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderAppleWatchInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderAppleWatchInfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderAppleWatchInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderAppleWatchInfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleWatchInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_APPLE_MAC_BOOK_PRO15_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderAppleMacBookPro15Task
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="Apple MacBook Pro 15",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderAppleMacbookPro15InfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderAppleMacbookPro15InfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderAppleMacbookPro15InfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderAppleMacbookPro15InfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderAppleMacbookPro15InfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderAppleMacbookPro15InfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderAppleMacbookPro15InfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderAppleMacbookPro15InfeasibleTask(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15InfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_DEVELOPMENT_LAPTOP_PC_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderDevelopmentLaptopPCTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="Development Laptop (PC)",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderDevelopmentLaptopPCInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderDevelopmentLaptopPCInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderDevelopmentLaptopPCInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderDevelopmentLaptopPCInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderDevelopmentLaptopPCInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderDevelopmentLaptopPCInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderDevelopmentLaptopPCInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderDevelopmentLaptopPCInfeasibleTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndDoInfeasibleTask
):
    config_path = ORDER_LOANER_LAPTOP_TASK_CONFIG_PATH

    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
        provide_reason: bool = None,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        self.order_item_class = OrderLoanerLaptopTask
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=dashboard_class,
            question=question,
            min_catalog_item="Loaner Laptop",
            provide_reason=provide_reason,
        )


class DashboardRetrieveCatalogAndMaxOrderLoanerLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMaxOrderLoanerLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMinMaxRetrievalTask,
            question="max",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMeanOrderLoanerLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMeanOrderLoanerLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mean",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndMedianOrderLoanerLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndMedianOrderLoanerLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="median",
            provide_reason=False,
        )


class DashboardRetrieveCatalogAndModeOrderLoanerLaptopInfeasibleWithReasonTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=True,
        )


class DashboardRetrieveCatalogAndModeOrderLoanerLaptopInfeasibleTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopInfeasibleTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
    ) -> None:
        """
        Retrieve information based on incidents from the dashboard and do the task.
        """
        super().__init__(
            instance=instance,
            seed=seed,
            fixed_config=fixed_config,
            level=level,
            dashboard_class=SingleChartMeanMedianModeRetrievalTask,
            question="mode",
            provide_reason=False,
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]
