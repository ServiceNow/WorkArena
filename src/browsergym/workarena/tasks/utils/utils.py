import logging
import playwright.sync_api

from urllib import parse


def check_url_suffix_match(page: playwright.sync_api.Page, expected_url: str, task) -> bool:
    """
    Check if the current page URL matches the expected URL
    """
    expected_url = parse.unquote(expected_url)
    expected_url_suffix = parse.urlparse(expected_url).path

    page_url = page.evaluate("window.location.href")
    page_url = parse.unquote(page_url)
    page_suffix = parse.urlparse(page_url).path
    if expected_url_suffix not in page_suffix:
        logging.debug(f"Not in the expected URL for {task.__class__.__name__}, but in {page.url}")
        return False
    return True
