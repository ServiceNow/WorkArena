from browsergym.core.env import BrowserEnv
from browsergym.workarena import get_all_tasks_agents

AGENT_L2_SAMPLED_SET = get_all_tasks_agents(filter="l2")

AGENT_L2_SAMPLED_TASKS, AGENT_L2_SEEDS = [sampled_set[0] for sampled_set in AGENT_L2_SAMPLED_SET], [
    sampled_set[1] for sampled_set in AGENT_L2_SAMPLED_SET
]
from time import sleep

for task, seed in zip(AGENT_L2_SAMPLED_TASKS, AGENT_L2_SEEDS):
    print("Task:", task)

    # Instantiate a new environment
    env = BrowserEnv(task_entrypoint=task, headless=False, slow_mo=1000)
    env.reset()

    # Cheat functions use Playwright to automatically solve the task
    env.chat.add_message(role="assistant", msg="On it. Please wait...")

    for i in range(len(env.task)):
        sleep(1)
        env.task.cheat(page=env.page, chat_messages=env.chat.messages, subtask_idx=i)
        sleep(1)
        reward, done, message, info = env.task.validate(
            page=env.page, chat_messages=env.chat.messages
        )

    if reward == 1:
        env.chat.add_message(role="user", msg="Yes, that works. Thanks!")
    else:
        env.chat.add_message(
            role="user", msg=f"No, that doesn't work. {message.get('message', '')}"
        )

    sleep(3)
    env.close()
