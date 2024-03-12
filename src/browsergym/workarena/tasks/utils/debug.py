import playwright.sync_api


# TODO: is this used?
def debug_task(task, random_seed=3):
    with playwright.sync_api.sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir="/tmp/workarena_cromium_user_data",
            headless=False,  # Set headless=True for a non-GUI mode
        )
        (page,) = browser.pages

        try:
            task.setup(seed=random_seed, page=page)
            valid_res = task.validate(page, [])
            assert valid_res is False
            task.cheat()
            assert task.validate(page, []) is True
        finally:
            task.teardown()
            browser.close()
