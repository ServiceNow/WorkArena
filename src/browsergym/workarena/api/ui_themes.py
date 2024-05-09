"""
Utility functions for UI themes

"""

from .utils import table_api_call


def get_workarena_theme_variants(instance):
    """
    Get the list of available WorkArena UI themes

    Parameters:
    -----------
    instance: SNowInstance
        The ServiceNow instance to get the UI themes from

    Returns:
    --------
    list[dict]
        The list of available WorkArena UI themes and their information

    """
    themes = table_api_call(
        instance=instance,
        table="m2m_theme_style",
        params={
            "sysparm_query": "style.type=variant",
            "sysparm_fields": "theme.name,theme.sys_id,style.name,style.sys_id",
            "sysparm_display_value": True,
        },
        method="GET",
    )["result"]
    themes = [t for t in themes if t["theme.name"] == "WorkArena"]
    return themes
