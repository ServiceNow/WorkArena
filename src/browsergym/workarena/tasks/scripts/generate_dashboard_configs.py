"""
Generate configurations for the report and dashboard tasks

Notes: sometimes it crashes (e.g., timeout, etc.). Just relaunch and it will be fine.

"""

import json
import multiprocessing
import random
import tenacity

from functools import partial
from playwright.sync_api import sync_playwright

from browsergym.workarena.api.utils import table_api_call, table_column_info
from browsergym.workarena.config import (
    REPORT_DATE_FILTER,
    REPORT_PATCH_FLAG,
    REPORT_RETRIEVAL_MINMAX_CONFIG_PATH,
    REPORT_RETRIEVAL_VALUE_CONFIG_PATH,
    DASHBOARD_RETRIEVAL_MINMAX_CONFIG_PATH,
    DASHBOARD_RETRIEVAL_VALUE_CONFIG_PATH,
)
from browsergym.workarena.instance import SNowInstance
from browsergym.workarena.tasks.dashboard import DashboardRetrievalTask


N_CPU = 20
MAX_CONFIGS = 1000
REPORT = False  # Set to True for reports, False for dashboards


class DummyDashboard(DashboardRetrievalTask):
    def all_configs(self):
        return [
            {
                "url": "",
                "chart_title": "",
                "chart_series": "",
                "question": "max",
            }
        ]


def get_report_urls(instance):
    # Generate a bunch of reports on the fly based on valid table fields
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
            for x, y in table_column_info(instance=instance, table=table).items()
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
        instance=instance,
        table="sys_report",
        params={
            "sysparm_query": f"sys_class_name=sys_report^active=true^typeINtrend,donut,vertical_bar,line,horizontal_bar,pie,bar,spline,area^descriptionLIKE{REPORT_PATCH_FLAG}^tableIN{system_report_tables}",
            "sysparm_fields": "sys_id",
        },
    )["result"]

    REPORTS = ON_THE_FLY_REPORTS + SYSTEM_REPORTS

    return [
        (
            f"/now/nav/ui/classic/params/target/sys_report_template.do%3Fsysparm_field%3D{report['field']}%26sysparm_type%3D{report['type']}%26sysparm_table%3D{report['table']}%26sysparm_from_list%3Dtrue%26sysparm_chart_size%3Dlarge%26sysparm_manual_labor%3Dtrue%26sysparm_query=sys_created_on<javascript:gs.dateGenerate('{REPORT_DATE_FILTER}','00:00:00')^EQ"
            if report.get("sys_id", None) is None
            else f"/now/nav/ui/classic/params/target/sys_report_template.do%3Fjvar_report_id={report['sys_id']}"
        )
        for report in REPORTS
    ]


def get_dashboard_urls(instance):
    # XXX: It's not ideal to use sys_ids but I couldn't find a better way
    DASHBOARDS = [
        "812fa4400f1130101527008c07767e1a",  # Assessment overview
        "fa5fe3e1773130107384c087cc5a99d5",  # Asset overview
        "68ee1f30770230107384c087cc5a992e",  # Asset contract overview
        "05b0a8b7c3123010a282a539e540dd69",  # Change overview
        "18b1f472533130104c90ddeeff7b12a6",  # Incident overview
        "287d07d1ff3130106c1ef9a7cddcbd5d",  # Request overview
        "7ab78953eb32011008f2951ff15228e6",  # Service catalog overview
        # "2d297c880f1130101527008c07767e27",  # Survey overview (almost empty post deleting reports that rely on time)
        "6b706f448f231110953ddffc9071a4f3",  # Telemetry - Table growth
        # "15c5d2d377213010a435478c4f5a993c",  # Usage overview
        # "85a57f9677100110ba155631dc5a9905",  # Web api usage overview (empty post deleting reports that rely on time)
        "c38ca3a273031010ae8dd21efaf6a747",  # Data classification
        "3d48f669538223008329ddeeff7b1253",  # Problem overview
    ]
    return [
        f"/now/nav/ui/classic/params/target/%24pa_dashboard.do%3Fsysparm_dashboard%3D{dashboard}"
        for dashboard in DASHBOARDS
    ]


@tenacity.retry(
    wait=tenacity.wait_fixed(1),
    stop=tenacity.stop_after_attempt(10),
)
def get_all_configs_by_url(url, is_report):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        task = DummyDashboard(
            instance=SNowInstance(),
            fixed_config={
                "url": url,
                "chart_title": "",
                "chart_series": "",
                "question": "max",
            },
            seed=0,
        )
        task.setup(page=page)

        # Handle the case where a dashboard is not found
        task._wait_for_ready(page)
        iframe = page.frame(name=task.iframe_id)
        assert iframe.get_by_text("not found").count() == 0, "Report or dashboard not found"

        # Find all the charts
        charts = task._get_charts(page)

        # Check enough charts
        if len(charts) == 0:
            return []

        questions = []
        for chart in charts:
            try:
                chart_title = chart[0] if not is_report else ""  # No title for reports
                _, chart_data, _ = task._get_chart_by_title(page, chart_title)

                # Select a series randomly
                for series_idx in range(len(chart_data)):
                    series_name = chart_data[series_idx]["name"] if len(chart_data) > 1 else ""
                    data = chart_data[series_idx]["data"]

                    # Check if the data is interesting
                    labels = [point["label"] for point in data]
                    if len(labels) <= 1:
                        continue

                    if any(l.isdigit() for l in labels):
                        continue

                    # Generate all value questions
                    for format in ["count", "percent"]:
                        for label in labels:
                            questions.append(
                                {
                                    "url": url,
                                    "chart_title": chart_title,
                                    "chart_series": series_name,
                                    "question": f"value; {format}; {label}",
                                }
                            )

                    # Generate all other questions
                    questions.append(
                        {
                            "url": url,
                            "chart_title": chart_title,
                            "chart_series": series_name,
                            "question": "min",
                        }
                    )
                    questions.append(
                        {
                            "url": url,
                            "chart_title": chart_title,
                            "chart_series": series_name,
                            "question": "max",
                        }
                    )
            except Exception as e:
                print("Exception in worker", url, chart_title, e)
                continue  # Skip this chart

        if len(questions) == 0:
            return []

        # Test out all questions and keep only those that work
        valid_questions = []
        for question in questions:
            chat_messages = []
            task.config = question

            try:
                task.cheat(page=page, chat_messages=chat_messages)
                valid = task.validate(page=page, chat_messages=chat_messages)[0]
            except Exception as e:
                # raise e
                print("Exception in worker config validations", url, question, e)
                valid = 0

            if valid == 1:
                valid_questions.append(question)
            else:
                print(f"Failed to validate question {question}")

    print("Worker found", len(valid_questions), "valid questions")
    return valid_questions


if __name__ == "__main__":
    instance = SNowInstance()
    reports = get_report_urls(instance)
    gen_func = partial(get_all_configs_by_url, is_report=REPORT)

    if REPORT:
        urls = get_report_urls(instance)
        output_by_question = {
            "value": REPORT_RETRIEVAL_VALUE_CONFIG_PATH,
            "min,max": REPORT_RETRIEVAL_MINMAX_CONFIG_PATH,
        }
    else:
        urls = get_dashboard_urls(instance)
        output_by_question = {
            "value": DASHBOARD_RETRIEVAL_VALUE_CONFIG_PATH,
            "min,max": DASHBOARD_RETRIEVAL_MINMAX_CONFIG_PATH,
        }

    print(f"Generating configs for {len(urls)} URLs")
    configs = []
    with multiprocessing.Pool(processes=N_CPU) as pool:
        results = pool.map(gen_func, urls)
        pool.close()
        pool.join()

        # Flatten results list into config
        for result in results:
            configs += result

    # Post-process the configs and save them
    for question_type in output_by_question:
        types = [x.strip() for x in question_type.split(",")]

        type_configs = [
            config for config in configs if config["question"].split(";")[0].strip() in types
        ]
        type_configs = set(
            json.dumps(c) for c in type_configs
        )  # Serialize to string to make unique
        type_configs = [json.loads(c) for c in type_configs]
        random.shuffle(type_configs)
        type_configs = type_configs[:MAX_CONFIGS]

        print("Saving", len(type_configs), "configs for", question_type)
        with open(output_by_question[question_type], "w") as f:
            json.dump(type_configs, f)
