from .dash_do_base import DashboardRetrieveCatalogAndDoTask, DashDoFinalTask

from ..base import AbstractServiceNowTask
from ..dashboard import SingleChartMinMaxRetrievalTask, SingleChartMeanMedianModeRetrievalTask

from ...instance import SNowInstance

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


class DashboardRetrieveCatalogAndOrderDeveloperLaptopTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderDeveloperLaptopTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderDeveloperLaptopTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 3,
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
        )


class DashboardRetrieveCatalogAndMedianOrderDeveloperLaptopTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderDeveloperLaptopTask(
    DashboardRetrieveCatalogAndOrderDeveloperLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndOrderiPadMiniTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderiPadMiniTask(
    DashboardRetrieveCatalogAndOrderiPadMiniTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderiPadMiniTask(
    DashboardRetrieveCatalogAndOrderiPadMiniTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderiPadMiniTask(
    DashboardRetrieveCatalogAndOrderiPadMiniTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderiPadMiniTask(
    DashboardRetrieveCatalogAndOrderiPadMiniTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndOrderiPadProTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderiPadProTask(
    DashboardRetrieveCatalogAndOrderiPadProTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderiPadProTask(
    DashboardRetrieveCatalogAndOrderiPadProTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderiPadProTask(
    DashboardRetrieveCatalogAndOrderiPadProTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderiPadProTask(
    DashboardRetrieveCatalogAndOrderiPadProTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndOrderSalesLaptopTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderSalesLaptopTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderSalesLaptopTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderSalesLaptopTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderSalesLaptopTask(
    DashboardRetrieveCatalogAndOrderSalesLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndOrderStandardLaptopTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderStandardLaptopTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderStandardLaptopTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderStandardLaptopTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderStandardLaptopTask(
    DashboardRetrieveCatalogAndOrderStandardLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndOrderAppleWatchTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderAppleWatchTask(
    DashboardRetrieveCatalogAndOrderAppleWatchTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderAppleWatchTask(
    DashboardRetrieveCatalogAndOrderAppleWatchTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderAppleWatchTask(
    DashboardRetrieveCatalogAndOrderAppleWatchTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderAppleWatchTask(
    DashboardRetrieveCatalogAndOrderAppleWatchTask, DashDoFinalTask
):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = 0,
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
        )


class DashboardRetrieveCatalogAndOrderAppleMacbookPro15Task(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderAppleMacbookPro15Task(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15Task, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderAppleMacbookPro15Task(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15Task, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderAppleMacbookPro15Task(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15Task, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderAppleMacbookPro15Task(
    DashboardRetrieveCatalogAndOrderAppleMacbookPro15Task, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderDevelopmentLaptopPCTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderDevelopmentLaptopPCTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderDevelopmentLaptopPCTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderDevelopmentLaptopPCTask(
    DashboardRetrieveCatalogAndOrderDevelopmentLaptopPCTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndOrderLoanerLaptopTask(DashboardRetrieveCatalogAndDoTask):
    def __init__(
        self,
        instance: SNowInstance = None,
        seed: int = None,
        fixed_config: list[AbstractServiceNowTask] = None,
        level: int = 2,
        dashboard_class: AbstractServiceNowTask = SingleChartMinMaxRetrievalTask,
        question: str = None,
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
        )


class DashboardRetrieveCatalogAndMaxOrderLoanerLaptopTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMeanOrderLoanerLaptopTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndMedianOrderLoanerLaptopTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopTask, DashDoFinalTask
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
        )


class DashboardRetrieveCatalogAndModeOrderLoanerLaptopTask(
    DashboardRetrieveCatalogAndOrderLoanerLaptopTask, DashDoFinalTask
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
        )


local_vars = locals().copy()

__TASKS__ = [
    var
    for var in local_vars.values()
    if isinstance(var, type) and issubclass(var, DashDoFinalTask) and var is not DashDoFinalTask
]

DASH_AND_ORDER = [
    DashboardRetrieveCatalogAndMaxOrderDeveloperLaptopTask,
    DashboardRetrieveCatalogAndMaxOrderiPadMiniTask,
    DashboardRetrieveCatalogAndMaxOrderiPadProTask,
    DashboardRetrieveCatalogAndMaxOrderSalesLaptopTask,
    DashboardRetrieveCatalogAndMaxOrderStandardLaptopTask,
    DashboardRetrieveCatalogAndMaxOrderAppleWatchTask,
    DashboardRetrieveCatalogAndMaxOrderAppleMacbookPro15Task,
    DashboardRetrieveCatalogAndMaxOrderDevelopmentLaptopPCTask,
    DashboardRetrieveCatalogAndMaxOrderLoanerLaptopTask,
]
DASH_COMPUTE_MEAN_AND_ORDER = [
    DashboardRetrieveCatalogAndMeanOrderDeveloperLaptopTask,
    DashboardRetrieveCatalogAndMeanOrderiPadMiniTask,
    DashboardRetrieveCatalogAndMeanOrderiPadProTask,
    DashboardRetrieveCatalogAndMeanOrderSalesLaptopTask,
    DashboardRetrieveCatalogAndMeanOrderStandardLaptopTask,
    DashboardRetrieveCatalogAndMeanOrderAppleWatchTask,
    DashboardRetrieveCatalogAndMeanOrderAppleMacbookPro15Task,
    DashboardRetrieveCatalogAndMeanOrderDevelopmentLaptopPCTask,
    DashboardRetrieveCatalogAndMeanOrderLoanerLaptopTask,
]

DASH_COMPUTE_MEDIAN_AND_ORDER = [
    DashboardRetrieveCatalogAndMedianOrderDeveloperLaptopTask,
    DashboardRetrieveCatalogAndMedianOrderiPadMiniTask,
    DashboardRetrieveCatalogAndMedianOrderiPadProTask,
    DashboardRetrieveCatalogAndMedianOrderSalesLaptopTask,
    DashboardRetrieveCatalogAndMedianOrderStandardLaptopTask,
    DashboardRetrieveCatalogAndMedianOrderAppleWatchTask,
    DashboardRetrieveCatalogAndMedianOrderAppleMacbookPro15Task,
    DashboardRetrieveCatalogAndMedianOrderDevelopmentLaptopPCTask,
    DashboardRetrieveCatalogAndMedianOrderLoanerLaptopTask,
]

DASH_COMPUTE_MODE_AND_ORDER = [
    DashboardRetrieveCatalogAndModeOrderDeveloperLaptopTask,
    DashboardRetrieveCatalogAndModeOrderiPadMiniTask,
    DashboardRetrieveCatalogAndModeOrderiPadProTask,
    DashboardRetrieveCatalogAndModeOrderSalesLaptopTask,
    DashboardRetrieveCatalogAndModeOrderStandardLaptopTask,
    DashboardRetrieveCatalogAndModeOrderAppleWatchTask,
    DashboardRetrieveCatalogAndModeOrderAppleMacbookPro15Task,
    DashboardRetrieveCatalogAndModeOrderDevelopmentLaptopPCTask,
    DashboardRetrieveCatalogAndModeOrderLoanerLaptopTask,
]
