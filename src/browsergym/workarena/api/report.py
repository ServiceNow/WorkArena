import numpy as np

from ..instance import SNowInstance
from .utils import table_api_call


def create_report(
    instance: SNowInstance,
    table: str,
    filter_hashtag: str,
    field: str,
    plot_title: str,
    filter_field: str = "short_description",
    random: np.random = None,
) -> list[str]:
    """
    Create a report for for the given table using a filter (str added to the short description).
    The report is created with a random color palette and colors and a random plot type (pie or bar).

    Parameters:
    -----------
    instance: SNowInstance
        The instance to create the category in
    table: str
        The name of the table used to make the plot
    field: str
        The field of the table used to make the plot
    filter_hashtag: str
        The name of the hashtag to filter the table with
    plot_title: str
        The title of the plot

    Returns:
    --------
    sys_id: str; sys_id of the report created
    plot_title: str; The title of the plot

    """
    # select a random color palette for the plot
    color_palettes = table_api_call(
        instance=instance,
        table="pa_chart_color_schemes",
        params={
            "sysparm_fields": "sys_id",
        },
        method="GET",
    )["result"]

    color_palette_sys_id = random.choice(color_palettes)["sys_id"]

    # Get available colors to eventually randomly select from them
    colors = table_api_call(
        instance=instance,
        table="sys_report_color",
        params={
            "sysparm_fields": "sys_id",
        },
        method="GET",
    )["result"]

    # Select a random plot type
    plot_types = ["pie", "bar"]
    plot_type = random.choice(plot_types)

    report_params = {
        "show_data_label_position_middle": False,
        "display_row_lines": False,
        "is_published": False,
        "chart_title_y_position": "0",
        "gauge_autoscale": True,
        "type": f"{plot_type}",
        "formatting_configuration": {
            "table": "incident",
            "stringFormattingProperties": {},
            "durationFormattingProperties": {},
            "dateFormattingProperties": {},
            "numberFormattingProperties": {},
        },
        "apply_alias": False,
        "chart_border_color": f"{random.choice(colors)['sys_id']}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "custom_chart_title_position": False,
        "other_threshold": "-2",
        "y_axis_title_color": f"{random.choice(colors)['sys_id']}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "show_legend_border": False,
        "donut_width_percent": "30",
        "y_axis_title_size": "12",
        "legend_border_color": f"{random.choice(colors)['sys_id']}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "y_axis_label_bold": False,
        "chart_title_size": "16",
        "x_axis_label_color": f"{random.choice(colors)['sys_id']}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "active": True,
        "source_type": "table",
        "x_axis_title_bold": True,
        "x_axis_opposite": False,
        "chart_height": "450",
        "legend_border_radius": "0",
        "field": field,
        "show_geographical_label": False,
        "legend_horizontal_alignment": "center",
        "interval": "year",
        "show_zero": False,
        "y_axis_grid_width": "1",
        "chart_subtitle_size": "14",
        "x_axis_display_grid": False,
        "show_chart_total": False,
        "chart_subtitle_style": "normal",
        "chart_title_style": "normal",
        "x_axis_grid_width": "1",
        "x_axis_label_tilt": "0",
        "show_chart_title": "report",
        "title_vertical_alignment": "top",
        "legend_border_width": "1",
        "compute_percent": "aggregate",
        "show_marker": False,
        "sys_scope": "global",
        "map": "93b8a3a2d7101200bd4a4ebfae61033a",
        "use_color_heatmap": False,
        "use_null_in_trend": False,
        "y_axis_label_tilt": "0",
        "table": table,
        "legend_vertical_alignment": "bottom",
        "x_axis_label_bold": False,
        "no_bulk_migration": False,
        "filter": f"{filter_field}LIKE{filter_hashtag}",
        "display_column_lines": False,
        "x_axis_allow_decimals": True,
        "custom_chart_size": False,
        "title_horizontal_alignment": "center",
        "bar_unstack": False,
        "y_axis_allow_decimals": True,
        "chart_width": "600",
        "x_axis_title_size": "12",
        "y_axis_opposite": False,
        "y_axis_title_bold": True,
        "decimal_precision": "2",
        "y_axis_label_size": "11",
        "x_axis_grid_color": f"{random.choice(colors)['sys_id']}",
        "legend_align_columns": True,
        "field_list": "active,short_description,incident_state,business_duration,calendar_duration,description,caller_id,location,closed_by,impact,cmdb_ci,priority,assigned_to,activity_due,task_effective_number,company,escalation,sys_created_on,closed_at,child_incidents,state,assignment_group,category,number,business_stc",
        "is_scheduled": False,
        "others": True,
        "x_axis_title_color": f"{random.choice(colors)['sys_id']}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "aggregation_source": "no_override",
        "chart_title_color": f"{random.choice(colors)['sys_id']}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "y_axis_grid_dotted": False,
        "chart_size": "large",
        "legend_items_left_align": False,
        "show_chart_data_label": False,
        "y_axis_grid_color": f"{random.choice(colors)['sys_id']}",
        "allow_data_label_overlap": False,
        "chart_border_radius": "0",
        "title": plot_title,
        "exp_report_attrs": True,
        "aggregate": "COUNT",
        "y_axis_display_grid": True,
        "score_color": f"{random.choice(colors)['sys_id']}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "axis_max_color": f"{random.choice(colors)['sys_id']}",  # default: "b0d449b3d7332100fa6c0c12ce610383"
        "is_real_time": False,
        "show_empty": False,
        "direction": "minimize",
        "display_grid": False,
        "chart_border_width": "1",
        "funnel_neck_percent": "30",
        "show_legend": True,
        "set_color": "one_color",
        "color_palette": f"{color_palette_sys_id}",  # default: "65b30218a9fe3dba0120df8611520d97"
        "x_axis_label_size": "11",
        "show_chart_border": False,
        "x_axis_grid_dotted": False,
        "chart_title_x_position": "0",
        "pivot_expanded": True,
    }

    result = table_api_call(
        instance=instance,
        table="sys_report",
        # The cmdb_model_category is the sys_id for the hardware category; computer in this case
        json=report_params,
        method="POST",
        wait_for_record=True,
    )["result"]

    return result["sys_id"], plot_title
