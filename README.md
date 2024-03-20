# WorkArena: How Capable are Web Agents at Solving Common Knowledge Work Tasks?

[[Paper]](https://arxiv.org/abs/2403.07718) ♦ [[Benchmark Contents]](#benchmark-contents) ♦ [[Getting Started]](#getting-started) ♦ [[Live Demo]](#live-demo) ♦ [[BrowserGym]](https://github.com/ServiceNow/BrowserGym) ♦ [[Citing This Work]](#citing-this-work)

`WorkArena` is a suite of browser-based tasks tailored to gauge web agents' effectiveness in supporting routine tasks for knowledge workers. 
By harnessing the ubiquitous [ServiceNow](https://www.servicenow.com/what-is-servicenow.html) platform, this benchmark will be instrumental in assessing the widespread state of such automations in modern knowledge work environments.

WorkArena is included in [BrowserGym](https://github.com/ServiceNow/BrowserGym), a conversational gym environment for the evaluation of web agents.


https://github.com/ServiceNow/WorkArena/assets/2374980/68640f09-7d6f-4eb1-b556-c294a6afef70


## Benchmark Contents

At the moment, WorkArena includes `23,150` task instances drawn from `29` tasks that cover the main components of the ServiceNow user interface. The following videos show an agent built on `GPT-4-vision` interacting with every such component. As emphasized by our results, this benchmark is not solved and thus, the performance of the agent is not always on point.

### Knowledge Bases

**Goal:** The agent must search for specific information in the company knowledge base.

_The agent interacts with the user via BrowserGym's conversational interface._

https://github.com/ServiceNow/WorkArena/assets/1726818/352341ba-b501-46ac-bfa6-a6c9be1ac2b7

### Forms

**Goal:** The agent must fill a complex form with specific values for each field.

https://github.com/ServiceNow/WorkArena/assets/1726818/e2c2b5cb-3386-4f3c-b073-c8c619e0e81b

### Service Catalogs

**Goal:** The agent must order items with specific configurations from the company's service catalog.

https://github.com/ServiceNow/WorkArena/assets/1726818/ac64db3b-9abf-4b5f-84a7-e2d9c9cee863

### Lists

**Goal:** The agent must filter a list according to some specifications.

_In this example, the agent struggles to manipulate the UI and fails to create the filter._

https://github.com/ServiceNow/WorkArena/assets/1726818/7538b3ef-d39b-4978-b9ea-8b9e106df28e

### Menus

**Goal:** The agent must navigate to a specific application using the main menu.

https://github.com/ServiceNow/WorkArena/assets/1726818/ca26dfaf-2358-4418-855f-80e482435e6e

## Getting Started

To setup WorkArena, you will need to get your own ServiceNow instance, install our Python package, and upload some data to your instance. Follow the steps below to achieve this.

### a) Create a ServiceNow Developer Instance

1. Go to https://developer.servicenow.com/ and create an account.
2. Click on `Request an instance` and select the `Utah` release (initializing the instance will take a few minutes)
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

```python
import random

from browsergym.core.env import BrowserEnv
from browsergym.workarena import ALL_WORKARENA_TASKS
from time import sleep


random.shuffle(ALL_WORKARENA_TASKS)
for task in ALL_WORKARENA_TASKS:
    print("Task:", task)

    # Instantiate a new environment
    env = BrowserEnv(task_entrypoint=task,
                    headless=False, 
                    slow_mo=1000)
    env.reset()

    # Cheat functions use Playwright to automatically solve the task
    env.chat.add_message(role="assistant", msg="On it. Please wait...")
    env.task.cheat(env.page, env.chat.messages)

    # Post solution to chat
    if "KnowledgeBaseSearchTask" in str(task):
        answer = env.chat.messages[-1]["message"]
        env.chat.add_message(role="assistant", msg=f"The answer is:")
        env.chat.add_message(role="assistant", msg=answer)
    else:
        env.chat.add_message(role="assistant", msg="I'm done!")

    # Validate the solution
    reward, stop, info, message = env.task.validate(env.page, env.chat.messages)
    if reward == 1:
        env.chat.add_message(role="user", msg="Yes, that works. Thanks!")
    else:
        env.chat.add_message(role="user", msg=f"No, that doesn't work. {message.get('message', '')}")

    sleep(3)
    env.close()
```


## Citing This Work

Please use the following BibTeX to cite our work:
```
@misc{workarena2024,
      title={WorkArena: How Capable Are Web Agents at Solving Common Knowledge Work Tasks?}, 
      author={Alexandre Drouin and Maxime Gasse and Massimo Caccia and Issam H. Laradji and Manuel Del Verme and Tom Marty and Léo Boisvert and Megh Thakkar and Quentin Cappart and David Vazquez and Nicolas Chapados and Alexandre Lacoste},
      year={2024},
      eprint={2403.07718},
      archivePrefix={arXiv},
      primaryClass={cs.LG}
}
```
