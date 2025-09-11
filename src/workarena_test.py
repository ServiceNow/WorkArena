import os


os.environ["SNOW_INSTANCE_URL"] = "https://myarena18demo.service-now.com/"
os.environ["SNOW_INSTANCE_UNAME"] = "admin"
os.environ["SNOW_INSTANCE_PWD"] = r"Snow@456"

from time import sleep
from browsergym.core.env import BrowserEnv
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

# Run just the Developer Laptop tasks by default (add others here if you want)
TASK_CLASSES = [
    OrderDeveloperLaptopTask,      # L1 atomic
    OrderDevelopmentLaptopPCTask,  # L2 multi-step
    # Example: to include others, uncomment:
    # OrderIpadMiniTask,
    # OrderIpadProTask,
    # OrderSalesLaptopTask,
    # OrderStandardLaptopTask,
    # OrderAppleWatchTask,
    # OrderAppleMacBookPro15Task,
    # OrderLoanerLaptopTask,
]

for TaskCls in TASK_CLASSES:
    # Build the entrypoint from the imported class (lets BrowserEnv instantiate it)
    entrypoint = f"{TaskCls.__module__}.{TaskCls.__name__}"
    print("Task:", entrypoint)

    env = BrowserEnv(task_entrypoint=entrypoint, headless=False, slow_mo=1000)
    env.reset()

    # Optional: say something in chat
    env.chat.add_message(role="assistant", msg="On it. Please wait...")

    try:
        # Multi-step (L2/…): iterate subtasks; single-step (L1): one pass
        n_subtasks = len(env.task) if hasattr(env.task, "__len__") else 1

        if n_subtasks > 1:
            for i in range(n_subtasks):
                sleep(1)
                env.task.cheat(page=env.page, chat_messages=env.chat.messages, subtask_idx=i)
                sleep(1)
                reward, done, message, info = env.task.validate(
                    page=env.page, chat_messages=env.chat.messages
                )
        else:
            cheat_messages = []
            env.task.cheat(env.page, cheat_messages)
            for m in cheat_messages:
                env.chat.add_message(role=m["role"], msg=m["message"])
            reward, done, message, info = env.task.validate(env.page, cheat_messages)

        # Simple feedback
        if reward == 1:
            env.chat.add_message(role="user", msg="Yes, that works. Thanks!")
        else:
            env.chat.add_message(
                role="user", msg=f"No, that doesn't work. {info.get('message', '')}"
            )

        sleep(2)
    finally:
        env.close()
