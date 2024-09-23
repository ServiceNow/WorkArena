# WorkArena++: Towards Compositional Planning and Reasoning-based Common Knowledge Work Tasks

## Getting Started

To setup WorkArena, you will need to get your own ServiceNow instance, install our Python package, and upload some data to your instance. Follow the steps below to achieve this.

### a) Create a ServiceNow Developer Instance

1. Go to https://developer.servicenow.com/ and create an account.
2. Click on `Request an instance` and select the `Washington` release (initializing the instance will take a few minutes)
3. Once the instance is ready, you should see your instance URL and credentials. If not, click _Return to the Developer Portal_, then navigate to _Manage instance password_ and click _Reset instance password_.
4. You should now see your URL and credentials. Based on this information, set the following environment variables:
    * `SNOW_INSTANCE_URL`: The URL of your ServiceNow developer instance
    * `SNOW_INSTANCE_UNAME`: The username, should be "admin"
    * `SNOW_INSTANCE_PWD`: The password, make sure you place the value in quotes "" and be mindful of [escaping special shell characters](https://onlinelinuxtools.com/escape-shell-characters). Running `echo $SNOW_INSTANCE_PWD` should print the correct password.
6. Log into your instance via a browser using the admin credentials. Close any popup that appears on the main screen (e.g., agreeing to analytics).

**Warning:** Feel free to look around the platform, but please make sure you revert any changes (e.g., changes to list views, pinning some menus, etc.) as these changes will be persistent and affect the benchmarking process.

### b) Install WorkArena and Initialize your Instance

Run the following command to install WorkArena in the [BrowswerGym](https://github.com/servicenow/browsergym) environment:
```
pip install browsergym-workarena
```

Then, run this command in a terminal to upload the benchmark data to your ServiceNow instance:
```
workarena-install
```

Finally, install [Playwright](https://github.com/microsoft/playwright):
```
playwright install
```

Your installation is now complete! 🎉


## Live Demo

Run this code to see WorkArena in action.

Note: the following example executes WorkArena's oracle (cheat) function to solve each task. To evaluate an agent, calls to `env.step()` must be used instead.

```python
import random

from browsergym.core.env import BrowserEnv
from browsergym.workarena import get_all_tasks_agents
 
AGENT_L2_SAMPLED_SET = get_all_tasks_agents(filter="l2")
 
AGENT_L2_SAMPLED_TASKS, AGENT_L2_SEEDS = [sampled_set[0] for sampled_set in AGENT_L2_SAMPLED_SET], [
    sampled_set[1] for sampled_set in AGENT_L2_SAMPLED_SET
]
from time import sleep

for (task, seed) in zip(AGENT_L2_SAMPLED_TASKS, AGENT_L2_SEEDS):
    print("Task:", task)

    # Instantiate a new environment
    env = BrowserEnv(task_entrypoint=task,
                    headless=False)
    env.reset()

    # Cheat functions use Playwright to automatically solve the task
    env.chat.add_message(role="assistant", msg="On it. Please wait...")
    
    for i in range(len(env.task)):
        sleep(1)
        env.task.cheat(page=env.page, chat_messages=env.chat.messages, subtask_idx=i)
        sleep(1)
        reward, done, message, info = env.task.validate(page=env.page, chat_messages=env.chat.messages)
   
    if reward == 1:
        env.chat.add_message(role="user", msg="Yes, that works. Thanks!")
    else:
        env.chat.add_message(role="user", msg=f"No, that doesn't work. {info.get('message', '')}")

    sleep(3)
    env.close()
```
