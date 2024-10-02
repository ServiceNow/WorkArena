import json
import logging
import numpy as np
import playwright.sync_api
import re

from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import List, Tuple
from urllib import parse

from .base import AbstractServiceNowTask
from .comp_building_block import CompositionalBuildingBlockTask
from .utils.utils import check_url_suffix_match

from ..api.utils import table_api_call, table_column_info
from ..config import (
    DASHBOARD_RETRIEVAL_MINMAX_CONFIG_PATH,
    DASHBOARD_RETRIEVAL_VALUE_CONFIG_PATH,
    REPORT_RETRIEVAL_MINMAX_CONFIG_PATH,
    REPORT_RETRIEVAL_VALUE_CONFIG_PATH,
    REPORT_DATE_FILTER,
    REPORT_PATCH_FLAG,
)
from ..instance import SNowInstance
from .utils.string import share_tri_gram
from .utils.utils import check_url_suffix_match

# XXX: Some notes on plot types
#      - We currently don't support maps because they are clickable and would require a more evolved cheat function
SUPPORTED_PLOT_TYPES = ["area", "bar", "column", "line", "pie", "spline"]


class DashboardRetrievalTask(AbstractServiceNowTask, ABC):
    """
    A task to retrieve information from a ServiceNow dashboard

    """

    def __init__(
        self, seed: int = None, instance: SNowInstance = None, fixed_config: dict = None, **kwargs
    ) -> None:
        super().__init__(seed=seed, instance=instance, start_rel_url="")
        self.iframe_id = "gsft_main"
        self.fixed_config = fixed_config
        self.__dict__.update(kwargs)

    @abstractmethod
    def all_configs(self) -> List[dict]:
        pass

    @abstractmethod
    def all_configs(self) -> List[dict]:
        pass

    def _get_charts(self, page: playwright.sync_api.Page) -> None:
        """
        Extract all charts on the page

        Parameters:
        -----------
        page: playwright.sync_api.Page
            The playright page on which the charts are to be extracted

        Returns:
        --------
        charts: list
            A list of charts where the chart is represented as a tuple of the chart title and the id of the
            element that contains the chart.

        """
        iframe = page.frame(name=self.iframe_id)

        charts = page.evaluate(
            f"{self.iframe_id}.Highcharts.charts.map((x) => {{if(x){{return [x.renderTo.ariaLabel, x.renderTo.id];}}}})"
        )
        charts = [
            (title.replace("Highcharts interactive chart.", "").replace(".", "").strip(), id)
            for title, id in charts
            if title
            and iframe.locator(f"#{id}").count()
            > 0  # Check if the element is actually on page (sometime rendering breaks)
        ]

        return charts

    def _read_chart(self, page: playwright.sync_api.Page, element_id: str) -> str:
        """
        Read the chart at the specified index

        Parameters:
        -----------
        page: playwright.sync_api.Page
            The playright page on which the charts are to be extracted
        element_id: str
            The ID of the element that contains the chart

        Returns:
        --------
        chart_type: str
            The type of the chart
        chart_data: dict
            The data of the chart

        """
        self._wait_for_ready(page)

        # Validate plot type
        types = page.evaluate(
            f"{self.iframe_id}.Highcharts.charts.find(chart => chart && chart.renderTo.id === '{element_id}').types"
        )
        if len(set(types)) > 1:
            raise NotImplementedError("Multiple chart types in the same chart not supported")
        type = types[0]
        if type not in SUPPORTED_PLOT_TYPES:
            raise NotImplementedError(f"Chart type {type} not supported")

        # Get data
        data = page.evaluate(
            f"""
            {self.iframe_id}.Highcharts.charts.find(chart => chart && chart.renderTo.id === "{element_id}")
            .series.map(series => ({{
                name: series.name,
                data: series.data.map(
                              point => ({{
                                 label_cat: point.category,
                                 label_name: point.name,
                                 label_origx: point.origXValue,
                                 count: point.y,
                                 percent: point.percent
                              }}))
                }}));
            """
        )

        # Post-process each series
        for i in range(len(data)):
            # For each data point in the series
            for j in range(len(data[i]["data"])):
                data_point = data[i]["data"][j]

                # Remove None percent values when count is 0
                if data_point["count"] == 0:
                    data_point["percent"] = 0

                # Strip trailing spaces from labels
                data_point["label_cat"] = (
                    data_point["label_cat"].strip() if data_point["label_cat"] else ""
                )
                data_point["label_name"] = (
                    data_point["label_name"].strip() if data_point["label_name"] else ""
                )
                data_point["label_origx"] = (
                    data_point["label_origx"].strip() if data_point["label_origx"] else ""
                )

                # Determine which label to use (this is a heuristic)
                # Usually, when the origx value is present, it is more detailed than the other labels.
                # However, in some rare cases, it corresponds to some strange value that doesn't get rendered.
                # As a heuristic for the last point, let's just make sure that origx has at least a one trigram
                # overlap with any of the other labels.
                if data_point["label_origx"] != "" and any(
                    share_tri_gram(data_point["label_origx"], data_point[x])
                    for x in ["label_cat", "label_name"]
                ):
                    data_point["label"] = data_point["label_origx"]
                else:
                    if type in ["bar", "column", "spline"]:
                        data_point["label"] = data_point["label_cat"]
                    else:
                        data_point["label"] = data_point["label_name"]
                del data_point["label_cat"]
                del data_point["label_name"]
                del data_point["label_origx"]

            assert len(set([dp["label"] for dp in data[i]["data"]])) == len(
                data[i]["data"]
            ), "Detected duplicate labels in the same series"

        return type, data

    # retry because sometimes the page is not fully loaded
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _get_chart_by_title(
        self, page: playwright.sync_api.Page, title: str = None
    ) -> Tuple[str, dict]:
        """
        Get the chart data by title

        Parameters:
        -----------
        page: playwright.sync_api.Page
            The playright page on which the charts are to be extracted
        title: str
            The title of the chart to be read. If None, returns the first chart.

        Returns:
        --------
        chart_type: str
            The type of the chart
        chart_data: dict
            The data of the chart
        element_id: str
            The ID of the element that contains the chart

        """
        # Get chart titles and element IDs
        charts = self._get_charts(page)

        if not title:
            title = charts[0][0]

        # Find chart index by title
        chart_idx = [title.lower() for title, _ in charts].index(title.lower())

        # Load chart data
        return *self._read_chart(page, element_id=charts[chart_idx][1]), charts[chart_idx][1]

    def _wait_for_ready(self, page: playwright.sync_api.Page) -> None:
        """
        Wait for the page to be ready for task execution

        Parameters:
        -----------
        page: playwright.sync_api.Page
            The page to wait on

        """
        logging.debug(f"Waiting for {self.iframe_id} to be fully loaded")
        page.wait_for_function(
            f"typeof window.{self.iframe_id} !== 'undefined' && window.{self.iframe_id}.WORKARENA_LOAD_COMPLETE",
        )
        logging.debug(f"Detected {self.iframe_id} ready")

        logging.debug("Waiting for Highcharts API to be available")
        page.wait_for_function(f"window.{self.iframe_id}.Highcharts")
        logging.debug("Detected Highcharts API ready")

        logging.debug("Waiting for all plots to be loaded available")
        page.wait_for_function(f"window.{self.iframe_id}.WORKARENA_HIGHCHARTS_ALL_LOADED")
        logging.debug("All plots loaded")

    def get_init_scripts(self) -> List[str]:
        return super().get_init_scripts() + [
            "registerGsftMainLoaded();",
            f"""
            async function renderAllCharts() {{
                waLog('Forcing load of all charts', 'loadAllCharts');

                await waitForCondition(() => window.WORKARENA_LOAD_COMPLETE, 100);

                const canvas = window.SNC.canvas;
                if (canvas) {{
                    waLog('This is a dashboard page.', 'loadAllCharts');
                    // Trigger the rendering of each widget
                    canvas.layoutJson.panes.forEach((p) => canvas.canvasUtils.renderSlowWidget(canvas.canvasUtils.getWidgetContainer(p.uuid)));
                    // Wait for all widgets to be rendered
                    await waitForCondition(() => window.SNC.canvas.layoutJson.panes.map((p) => p.isRendered).every(value => value == true), 100);
                }}
                else {{
                    waLog('This is a report page.', 'loadAllCharts');
                    // Wait for axes to be visible (we need to use this approach since there is no canvas to help us)
                    await waitForCondition(() => document.body.innerText.toLowerCase().includes("no data to display") || document.querySelectorAll(".highcharts-point").length > 0, 100);
                }}

                // Wait for Highcharts to say that the charts are rendered
                waitForCondition(() => Highcharts.charts.all((c) => c.hasLoaded), 100)
                .then(() => {{
                            window.WORKARENA_HIGHCHARTS_ALL_LOADED = true;
                            waLog('All charts loaded', 'loadAllCharts');
                        }});
            }}
            // Run on both dashboard and reports pages
            runInGsftMainOnlyAndProtectByURL(renderAllCharts, 'pa_dashboard.do');
            runInGsftMainOnlyAndProtectByURL(renderAllCharts, 'sys_report_template.do');
            """,
            f"""
            function purifyReportUIButtons() {{
                // Delete a lot of UI features that were causing issues due to the report refreshing without
                // reloading the page. This makes the task easier, but it doesn't matter because we really
                // want to evaluate retrieval and this doesn't prevent that.
                document.querySelectorAll('[ng-click*="main.runReport"], #sidebar, #nlq-over-cb, #open-tree-navigation-button, .data-filtering-wrap').forEach(element => {{
                    if (element && element.parentNode) {{
                        element.parentNode.removeChild(element);
                    }}
                }});
                document.addEventListener('click', function(event) {{
                    event.stopPropagation();
                    event.preventDefault();
                }}, true);
                waLog('Purified report UI.', 'purifyReportUIButtons');
            }}
            // Run it only on the reports page
            runInGsftMainOnlyAndProtectByURL(purifyReportUIButtons, 'sys_report_template.do');
            """,
        ]

    def setup_goal(self, page: playwright.sync_api.Page) -> Tuple[str | dict]:
        super().setup_goal(page=page)

        # Configure task
        # ... sample a configuration
        self.config = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs())
        )
        # ... set start URL based on config
        self.start_url = self.instance.snow_url + self.config["url"]

        # Produce goal string based on question type
        chart_locator = (
            f"the \"{self.config['chart_series']}\" series of "
            if self.config["chart_series"]
            else ""
        ) + (
            f"the \"{self.config['chart_title']}\" chart"
            if self.config["chart_title"]
            else "the chart"
        )
        if self.config["question"].startswith("value"):
            q_info = [x.strip() for x in self.config["question"].split(";")]
            goal = f'What is the value of "{q_info[2]}" in {chart_locator} (in {q_info[1]})?'
        elif self.config["question"] == "max":
            goal = f"What is the maximum value in {chart_locator}? Give me both the label and the count. If there are many, pick one."
        elif self.config["question"] == "min":
            goal = f"What is the minimum value in {chart_locator}? Give me both the label and the count. If there are many, pick one."
        elif self.config["question"] == "mean":
            goal = f"What is the average value in {chart_locator}? Round off to the next highest integer."
        elif self.config["question"] == "median":
            goal = f"What is the median value in {chart_locator}?"
        elif self.config["question"] == "mode":
            goal = f"What is the mode value in {chart_locator}?"
        else:
            raise NotImplementedError(f"Question type {self.config['question']} not supported")

        return goal, {}

    def cheat(self, page: playwright.sync_api.Page, chat_messages: list[str]) -> None:
        super().cheat(page, chat_messages)
        # Check if the page is the report list view. If so, open the report
        page_is_report_list_view = check_url_suffix_match(
            page, "/now/nav/ui/classic/params/target/sys_report_list.do", self
        )
        chart_title = self.config["chart_title"]
        if page_is_report_list_view:
            # Open the report
            frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
            # Search for the report by title
            frame.get_by_label("Search a specific field of the Reports list").select_option("Title")
            search_input = frame.locator('input[aria-label="Search"]')
            search_input.click()
            search_input.fill(chart_title)
            search_input.press("Enter")
            page.wait_for_function(
                "typeof window.gsft_main !== 'undefined' && window.gsft_main.WORKARENA_LOAD_COMPLETE"
            )
            # Click on the chart preview to open it
            frame.wait_for_selector(f'a[aria-label="Preview record: {chart_title}"]').click()
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            # Now in the form view, wait for the page to load and click to view the report
            page.wait_for_function(
                "typeof window.gsft_main !== 'undefined' && window.gsft_main.WORKARENA_LOAD_COMPLETE"
            )
            frame = page.wait_for_selector('iframe[name="gsft_main"]').content_frame()
            frame.get_by_text("View Report").first.click()

        self._wait_for_ready(page)

        # Get the chart data
        chart_type, chart_data, chart_element_id = self._get_chart_by_title(
            page, self.config["chart_title"]
        )

        # Extract the series
        if len(chart_data) == 1:
            chart_data = chart_data[0]["data"]
        else:
            chart_data = [
                series["data"]
                for series in chart_data
                if series["name"] == self.config["chart_series"]
            ][0]

        # Scroll to the chart
        iframe = page.frame(name=self.iframe_id)
        iframe.evaluate_handle(
            f"findElementInShadowDOM('#{chart_element_id}')"
        ).scroll_into_view_if_needed()

        # Extract the value and add it to the chat
        if self.config["question"].startswith("value"):
            format = self.config["question"].split(";")[1].strip()
            label = self.config["question"].split(";")[2].strip()
            value = [
                point["count" if format == "count" else "percent"]
                for point in chart_data
                if point["label"] == label
            ][0]
            chat_messages.append({"message": str(value), "role": "assistant"})
        elif self.config["question"] == "max":
            max_point = max(chart_data, key=lambda x: x["count"])
            chat_messages.append(
                {"message": f"{max_point['label']}, {max_point['count']}", "role": "assistant"}
            )
        elif self.config["question"] == "min":
            min_point = min(chart_data, key=lambda x: x["count"])
            chat_messages.append(
                {"message": f"{min_point['label']}, {min_point['count']}", "role": "assistant"}
            )
        elif self.config["question"] == "mean":
            counts = [data["count"] for data in chart_data]
            target_count = np.mean(counts)
            chat_messages.append({"message": f"Mean / Average {target_count}", "role": "assistant"})
        elif self.config["question"] == "median":
            counts = [data["count"] for data in chart_data]
            target_count = np.median(counts)
            chat_messages.append({"message": f"Median {target_count}", "role": "assistant"})
        elif self.config["question"] == "mode":
            counts = [data["count"] for data in chart_data]
            # We select the maximum value if there are two or more modes
            frequencies = {}
            for count in counts:
                if count not in frequencies:
                    frequencies[count] = 1
                else:
                    frequencies[count] += 1
            sorted_frequencies = {
                count: frequency
                for count, frequency in sorted(
                    frequencies.items(), key=lambda item: item[1], reverse=True
                )
            }
            max_frequency = list(sorted_frequencies.values())[0]
            max_frequencies = [
                count
                for count, frequency in sorted_frequencies.items()
                if frequency == max_frequency
            ]
            target_count = max(max_frequencies)
            chat_messages.append({"message": f"Mode {target_count}", "role": "assistant"})
        else:
            raise NotImplementedError(f"Question type \"{self.config['question']}\" not supported")

    def validate(
        self, page: playwright.sync_api.Page, chat_messages: list[str]
    ) -> Tuple[float, bool, str, dict]:
        super().validate(page, chat_messages)

        # Check if the page is in the right URL
        logging.debug("Checking if the page is in the right URL to validate the task")
        right_url = check_url_suffix_match(page, expected_url=self.start_url, task=self)
        if not right_url:
            return (
                0,
                False,
                "",
                {
                    "message": f"The page is not in the right URL to validate task {self.__class__.__name__}."
                },
            )

        self._wait_for_ready(page)

        # Get the chart data
        logging.debug("Extracting chart data")
        _, chart_data, _ = self._get_chart_by_title(page, self.config["chart_title"])

        # Extract the series
        logging.debug("Extracting the series")
        if len(chart_data) == 1:
            chart_data = chart_data[0]["data"]
        else:
            chart_data = [
                series["data"]
                for series in chart_data
                if series["name"] == self.config["chart_series"]
            ][0]

        # Extract the agent's response
        logging.debug("Extracting the agent's response")
        if chat_messages and chat_messages[-1]["role"] == "assistant":
            response = chat_messages[-1]["message"]
        else:
            return (
                0,
                False,
                "",
                {"message": "The assistant did not provide an answer."},
            )

        # Extract all numbers mentioned by the agent
        logging.debug("Extracting all numbers mentioned by the agent")
        # ... some value labels may contain numbers so we need to remove the labels from the response first
        labels = set([point["label"] for point in chart_data])
        response_ = str(response)
        for label in labels:
            response_ = response_.replace(label, "")
        # ... then we extract numbers
        response_floats = np.unique(
            [float(x) for x in re.findall(r"[\d]+(?:[.,]\d+)?", response_.replace(",", ""))]
        )
        del response_

        if len(response_floats) == 0:
            return (
                0.0,
                False,
                "No number detected in the response.",
                {"message": "No number detected in the response."},
            )

        # Validate the response
        logging.debug("Validating the response based on the question type")
        if self.config["question"].startswith("value"):
            logging.debug("The question is a value question")
            # if more than one number is in the prompt, there is necessarily a false positive
            if len(response_floats) > 1:
                error_msg = "Incorrect answer. More than one number detected in the response."
                return 0.0, True, error_msg, {"message": error_msg}

            logging.debug(
                f"Extracting expected format and label from question for validation: {self.config['question']}"
            )
            format = self.config["question"].split(";")[1].strip()
            label = self.config["question"].split(";")[2].strip()
            logging.debug(f"Extracted format: {format}, label: {label}")

            expected_value = float(
                [
                    point["count" if format == "count" else "percent"]
                    for point in chart_data
                    if point["label"] == label
                ][0]
            )
            if np.isclose(expected_value, response_floats[0]):
                return 1.0, True, "Nice work, thank you!", {"message": "Correct answer."}
            else:
                return 0.0, True, f"Incorrect answer.", {"message": "Incorrect answer."}

        # ... validate max/min responses
        elif "max" in self.config["question"] or "min" in self.config["question"]:
            # Determine whether to find max or min based on configuration
            target_func = max if self.config["question"] == "max" else min
            logging.debug(f"The question is a {str(target_func)} question")

            # Get the target count value (max or min)
            target_count = float(target_func(chart_data, key=lambda x: x["count"])["count"])

            # Find all points with the target count value
            target_points = [point for point in chart_data if point["count"] == target_count]

            # if more than one number is in the prompt, there is necessarily a false positive
            if len(response_floats) > 1:
                error_msg = "Incorrect answer. More than one number detected in the response."
                return 0.0, True, error_msg, {"message": error_msg}

            # Check if any of these points are mentioned in the response
            for point in target_points:
                if point["label"].lower() in response.lower() and np.isclose(
                    target_count, response_floats[0]
                ):
                    return 1.0, True, "Nice work, thank you!", {"message": "Correct answer."}

            # If no correct point is mentioned in the response
            return 0.0, True, "Incorrect answer.", {"message": "Incorrect answer."}
        # ... validate mean/median/mode responses
        elif (
            "mean" in self.config["question"]
            or "median" in self.config["question"]
            or "mode" in self.config["question"]
        ):
            counts = [data["count"] for data in chart_data]
            if self.config["question"] == "mean":
                target_count = np.mean(counts)
            elif self.config["question"] == "median":
                target_count = np.median(counts)
            elif self.config["question"] == "mode":
                _vals, _counts = np.unique(counts, return_counts=True)
                max_frequency_index = np.argmax(_counts)
                target_count = -_vals[max_frequency_index]

            # if more than one number is in the prompt, there is necessarily a false positive
            if len(response_floats) > 1:
                error_msg = "Incorrect answer. More than one number detected in the response."
                return 0.0, True, error_msg, {"message": error_msg}

            # Check if any of these points are mentioned in the response
            if np.isclose(target_count, response_floats[0]):
                return 1.0, True, "Nice work, thank you!", {"message": "Correct answer."}

            # If no correct point is mentioned in the response
            return 0.0, True, "Incorrect answer.", {"message": "Incorrect answer."}

        else:
            raise NotImplementedError(f"Question type \"{self.config['question']}\" not supported")

    def teardown(self) -> None:
        return super().teardown()

    def _generate_random_config(
        self, page: playwright.sync_api.Page, is_report=True, question_types=["value"]
    ) -> dict:
        """
        Generate a random configuration for the task

        Parameters:
        -----------
        page: playwright.sync_api.Page
            The page on which the task is to be executed
        is_report: bool
            Whether to sample a report or a dashboard task configuration
        question_types: list
            The types of questions to sample from (uniformely)

        """
        # Generate a bunch of reports based on valid table fields
        ON_THE_FLY_REPORTS = []
        for table in [
            "alm_asset",
            "alm_hardware",
            "asmt_assessment_instance_question",
            "asmt_m2m_stakeholder",
            "ast_contract",
            "change_request",
            "cmdb_ci_computer",
            "incident",
            "sc_cat_item",
            "sys_user",
        ]:
            cols = [
                x
                for x, y in table_column_info(instance=self.instance, table=table).items()
                if y.get("cangroup", False)
                and y.get("type", None) == "choice"
                and "upon" not in x.lower()
            ]
            for col in cols:
                ON_THE_FLY_REPORTS.append({"table": table, "field": col, "type": "pie"})
                ON_THE_FLY_REPORTS.append({"table": table, "field": col, "type": "bar"})

        # Reports that are already in the instance
        system_report_tables = "alm_asset,alm_hardware,asmt_assessment_instance_question,asmt_m2m_stakeholder,ast_contract,change_request,cmdb_ci_computer"
        SYSTEM_REPORTS = table_api_call(
            instance=self.instance,
            table="sys_report",
            params={
                "sysparm_query": f"sys_class_name=sys_report^active=true^typeINtrend,donut,vertical_bar,line,horizontal_bar,pie,bar,spline,area^descriptionLIKE{REPORT_PATCH_FLAG}^tableIN{system_report_tables}",
                "sysparm_fields": "sys_id",
            },
        )["result"]

        REPORTS = ON_THE_FLY_REPORTS + SYSTEM_REPORTS

        # XXX: It's not ideal to use sys_ids but I couldn't find a better way
        DASHBOARDS = [
            "812fa4400f1130101527008c07767e1a",  # Assessment overview
            "fa5fe3e1773130107384c087cc5a99d5",  # Asset overview
            "68ee1f30770230107384c087cc5a992e",  # Asset contract overview
            "05b0a8b7c3123010a282a539e540dd69",  # Change overview
            "18b1f472533130104c90ddeeff7b12a6",  # Incident overview
            "287d07d1ff3130106c1ef9a7cddcbd5d",  # Request overview
            "7ab78953eb32011008f2951ff15228e6",  # Service catalog overview
            "2d297c880f1130101527008c07767e27",  # Survey overview
            "6b706f448f231110953ddffc9071a4f3",  # Telemetry - Table growth
            "15c5d2d377213010a435478c4f5a993c",  # Usage overview
            "85a57f9677100110ba155631dc5a9905",  # Web api usage overview
            "c38ca3a273031010ae8dd21efaf6a747",  # Data classification
            "3d48f669538223008329ddeeff7b1253",  # Problem overview
        ]

        # Select between a full dashboard and a report
        if is_report:
            report = REPORTS[self.random.randint(0, len(REPORTS))]

            # On the fly generated report
            if not report.get("sys_id", None):
                url = f"/now/nav/ui/classic/params/target/sys_report_template.do%3Fsysparm_field%3D{report['field']}%26sysparm_type%3D{report['type']}%26sysparm_table%3D{report['table']}%26sysparm_from_list%3Dtrue%26sysparm_chart_size%3Dlarge%26sysparm_manual_labor%3Dtrue%26sysparm_query=sys_created_on<javascript:gs.dateGenerate('{REPORT_DATE_FILTER}','00:00:00')^EQ"
            # Report from the database
            else:
                url = f"/now/nav/ui/classic/params/target/sys_report_template.do%3Fjvar_report_id={report['sys_id']}"
        else:
            # Dashboard from the database
            dashboard = self.random.choice(DASHBOARDS)
            url = f"/now/nav/ui/classic/params/target/%24pa_dashboard.do%3Fsysparm_dashboard%3D{dashboard}"

        # We need to do this to bypass the init script protection by URL
        self.fixed_config = {
            "url": url,
            "chart_title": "",
            "chart_series": "",
            "question": "max",
        }  # Dummy config
        self.setup(page=page)

        # Handle the case where a dashboard is not found
        page.wait_for_load_state("networkidle")
        iframe = page.frame(name=self.iframe_id)
        assert iframe.get_by_text("not found").count() == 0, "Report or dashboard not found"

        # Find all the charts
        self._wait_for_ready(page)
        charts = self._get_charts(page)

        # Randomly select a chart
        assert len(charts) > 0, f"No charts found on the page {self.instance.snow_url}{url}"
        chart_idx = self.random.randint(0, len(charts))
        chart_title = charts[chart_idx][0] if not is_report else ""  # No title for reports
        _, chart_data, _ = self._get_chart_by_title(page, chart_title)

        # Select a series randomly
        series_idx = self.random.randint(len(chart_data))
        chart_series = chart_data[series_idx]["name"] if len(chart_data) > 1 else ""
        chart_data = chart_data[series_idx]["data"]

        # Check if the data is interesting
        labels = [point["label"] for point in chart_data]
        assert len(labels) > 1, f"Not enough data in the chart (only {len(labels)} label)"
        assert not any(
            l.isdigit() for l in labels
        ), "Some chart labels are digits, which would cause errors in validation. Skipping."

        # Sample a type of question
        question = self.random.choice(question_types)

        if question == "value":
            # Sample a random type of value to ask for
            format = self.random.choice(["count", "percent"])

            # Select a random label from the chart data
            label = self.random.choice(labels)

            return {
                "url": url,
                "chart_title": chart_title,
                "chart_series": chart_series,
                "question": f"{question}; {format}; {label}",
            }
        else:
            return {
                "url": url,
                "chart_title": chart_title,
                "chart_series": chart_series,
                "question": question,
            }


class MultiChartValueRetrievalTask(DashboardRetrievalTask):
    def all_configs(self):
        return json.load(open(DASHBOARD_RETRIEVAL_VALUE_CONFIG_PATH, "r"))


class MultiChartMinMaxRetrievalTask(DashboardRetrievalTask):
    def all_configs(self):
        return json.load(open(DASHBOARD_RETRIEVAL_MINMAX_CONFIG_PATH, "r"))


class SingleChartValueRetrievalTask(DashboardRetrievalTask):
    def all_configs(self):
        return json.load(open(REPORT_RETRIEVAL_VALUE_CONFIG_PATH, "r"))


class SingleChartMinMaxRetrievalTask(DashboardRetrievalTask):
    def all_configs(self):
        return json.load(open(REPORT_RETRIEVAL_MINMAX_CONFIG_PATH, "r"))


class SingleChartMeanMedianModeRetrievalTask(
    DashboardRetrievalTask, CompositionalBuildingBlockTask
):
    def all_configs(self):
        return json.load(open(REPORT_RETRIEVAL_MINMAX_CONFIG_PATH, "r"))


class WorkLoadBalancingMinMaxRetrievalTask(
    MultiChartMinMaxRetrievalTask, CompositionalBuildingBlockTask
):
    def all_configs(self):
        return json.load(open(REPORT_RETRIEVAL_MINMAX_CONFIG_PATH, "r"))

    def setup_goal(self, page: playwright.sync_api.Page) -> Tuple[str | dict]:
        super().setup_goal(page=page)

        # Configure task
        # ... sample a configuration
        self.config = (
            self.fixed_config if self.fixed_config else self.random.choice(self.all_configs())
        )
        # ... set start URL based on config
        self.start_url = self.instance.snow_url + self.config["url"]

        goal = f"Create a filter to find reports whose title contains hashtag {self.problem_hashtag} and open the report."
        goal += " From the report, identify the user with the most assigned problems and the user with the least assigned problems."

        return goal, {}


__TASKS__ = [
    var
    for var in locals().values()
    if isinstance(var, type)
    and issubclass(var, DashboardRetrievalTask)
    and not issubclass(var, CompositionalBuildingBlockTask)
    and var is not DashboardRetrievalTask
]
