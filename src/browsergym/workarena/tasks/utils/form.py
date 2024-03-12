import time
from ...config import SNOW_BROWSER_TIMEOUT


def fill_text(page, input_field, value, iframe=None):
    """
    Fills the value of text field, while handling autocomplete menus.

    Parameters
    ----------
    page : playwright.sync_api.page.Page
        The page object
    input_field : playwright locator
        The locator of the input field
    value : str
        The value to fill in
    iframe : playwright locator, optional
        The locator of the iframe that contains the input field, by default None

    """
    if value == "":
        return

    if iframe is None:
        iframe = page

    # Click into the field (this sometimes causes some aria autocompletion attributes to be set)
    input_field.click(force=True)

    # If the field uses autocomplete, we need to wait for Ajax to finish (and expand the menu)
    if input_field.get_attribute("aria-autocomplete") == "list":
        # Fill in the value using a procedure that triggers the autocomplete
        input_field.fill(value[:-1])
        page.keyboard.press(value[-1])

        # Wait until the attribute of the locator changes to the desired value
        max_wait_time = SNOW_BROWSER_TIMEOUT  # maximum time to wait in seconds
        start_time = time.time()
        while True:
            if input_field.get_attribute("aria-expanded") == "true":
                break
            if time.time() - start_time > (max_wait_time / 1000):
                raise TimeoutError("Timeout waiting for autocompletion menu to open")
            time.sleep(0.5)  # wait for a short period before checking again

        # Select the desired value
        time.sleep(0.5)  # wait for the list to be populated
        options = iframe.locator("[id^='ac_option_']")
        for i in range(options.count()):
            opt = options.nth(i)

            # Extract the value from the option element
            if opt.locator(".ac_cell").count() > 0:
                # ... element is multi part (use only the main info)
                opt_value = opt.locator(".ac_cell").first.text_content()
            else:
                # ... element is single part (use the whole text)
                opt_value = opt.text_content()

            if opt_value.lower() == value.lower():
                opt.click()
                break
        else:
            raise ValueError(f"No match for value {value} found in autocomplete menu")

    # All other normal text fields
    else:
        input_field.fill(value)
