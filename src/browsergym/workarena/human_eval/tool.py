"""
WorkArena Human Evaluation Tool

Known issues:
    * Blocking page interaction: We can't block loading until validation is done because some validation
                                 functions require the page to be loaded. This means the user might act
                                 while validation is ongoing. However, they would need to be very quick to
                                 cause issues.

"""

import argparse
import json
import logging
import os
import random
import tenacity

from time import sleep, time

from browsergym.core.env import BrowserEnv
from browsergym.workarena import ALL_WORKARENA_TASKS, get_all_tasks_humans
from browsergym.workarena.tasks.compositional.base import CompositionalTask


logging.basicConfig(level=logging.INFO)


# All available task classes by name
TASKS = {task.__name__: task for task in ALL_WORKARENA_TASKS}


def get_servicenow_pages(context):
    return [p for p in context.pages if "service-now" in p.url]


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5), reraise=True)
def validation_flag_activated(context):
    return any(
        f.evaluate("typeof window.NEED_VALIDATION !== 'undefined' && window.NEED_VALIDATION")
        for p in get_servicenow_pages(context)
        for f in p.frames
    )


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5), reraise=True)
def reset_validation_flag(context):
    try:
        for page in get_servicenow_pages(context):
            for f in page.frames:
                f.evaluate("window.NEED_VALIDATION = 0;")
    except Exception as e:
        print(e, "Failed to reset validation flag")  # Worst case we'll just keep validating


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5), reraise=True)
def abandon_flag_activated(context):
    return any(
        f.evaluate("typeof window.HUMAN_ABANDON !== 'undefined' && window.HUMAN_ABANDON")
        for p in get_servicenow_pages(context)
        for f in p.frames
    )


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5), reraise=True)
def infeasible_flag_activated(context):
    infeasible = any(
        f.evaluate("typeof window.HUMAN_INFEASIBLE !== 'undefined'")
        for p in get_servicenow_pages(context)
        for f in p.frames
    )

    reason = None
    if infeasible:
        for p in get_servicenow_pages(context):
            try:
                reason = p.evaluate("document.getElementById('reasonTextBox').value")
                break
            except:
                pass

    return infeasible, reason


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5), reraise=True)
def human_console_set_status(msg, context):
    for p in get_servicenow_pages(context):
        p.evaluate(f"document.getElementById('taskStatusDiv').innerText = '{msg}'")


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5), reraise=True)
def human_console_set_progress_status(msg, context):
    for p in get_servicenow_pages(context):
        p.evaluate(f"document.getElementById('progressDiv').innerText = '{msg}'")


def log_result(annotator_info: dict, task_info: dict, metrics: dict, path: str):
    # Read existing log
    if os.path.exists(path):
        log = json.load(open(path, "r"))
    else:
        log = []

    # Append log
    log.append({"annotator_info": annotator_info, "task_info": task_info, "metrics": metrics})
    json.dump(log, open(path, "w"))

    logging.info(f"Logged result: {task_info} -- {metrics}")


def task_already_evaluated(path: str, annotator_info: dict, task_info: dict):
    if not os.path.exists(path):
        return False

    log = json.load(open(path, "r"))
    for entry in log:
        if entry["annotator_info"] == annotator_info and entry["task_info"] == task_info:
            return True

    return False


def setup_environment(task_info: dict):
    task_cls = TASKS[task_info["task_name"]]
    env = BrowserEnv(
        task_entrypoint=task_cls,
        headless=False,
    )
    info, _ = env.reset(seed=task_info["task_seed"])

    # Inject human-eval helper scripts (reload to apply)
    env.task.page.context.add_init_script("window.NEED_VALIDATION = 1;")
    env.task.page.context.add_init_script(
        path=os.path.join(os.path.dirname(__file__), "console.js")
    )
    env.task.page.reload()

    # Patch the chat messages so that the human posts as the bot
    env.chat.page.evaluate(
        """
        (function() {
            let old;

            // Function to wait for addChatMessage to be defined
            function waitForAddChatMessage() {
                if (typeof addChatMessage !== 'undefined') {
                    // Save the original 'addChatMessage' function to 'old'
                    if (typeof old === 'undefined') {
                        old = new Function('return ' + addChatMessage.toString())();
                    }

                    // Redefine 'addChatMessage' to wrap the original function
                    addChatMessage = function(role, timeString, msg) {
                        if (role === 'user') {
                            role = 'assistant'; // Swap role from 'user' to 'assistant'
                        }
                        else if (role === 'assistant') {
                            role = 'user'; // Swap role from 'assistant' to 'user'
                        }
                        old(role, timeString, msg); // Call the original function
                    };
                } else {
                    // Retry after a short delay
                    setTimeout(waitForAddChatMessage, 100);
                }
            }

            // Start waiting for addChatMessage to be defined
            waitForAddChatMessage();
        })();
    """
    )

    # Mark all chat messages as patched so that we don't patch them again
    for m in env.chat.messages:
        m["patched"] = True

    return env


def load_curriculum(path):
    """
    Load curriculum from a file or generate a random one.

    Parameters:
    -----------
    path: str
        Path to the curriculum file. If set to "random", a random curriculum will be generated.

    Returns:
    --------
    curriculum: list

    """
    if path == "random":
        logging.info("Generating random curriculum")
        all_tasks = get_all_tasks_humans(filter="l2") + get_all_tasks_humans(filter="l3")
        random.shuffle(all_tasks)
        curriculum = [{"task_name": x[0].__name__, "task_seed": x[1]} for x in all_tasks]
    else:
        logging.info(f"Loading curriculum from {path}")
        with open(path, "r") as f:
            curriculum = [
                {"task_name": l.split(",")[0].strip(), "task_seed": int(l.split(",")[1].strip())}
                for l in f.readlines()
                if len(l.strip()) > 0
            ]

    return curriculum


@tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5), reraise=True)
def validate_solution(env):
    infos = []
    messages = []
    for p in env.context.pages:
        reward, stop, message, info = env.task.validate(p, env.chat.messages)

        # If a terminal condition is encountered, return it.
        if reward == 1 or (reward == 0 and stop):
            return reward, stop, message, info

        infos.append(info)
        messages.append(message)

    return reward, stop, ", ".join(messages), {"message": ", ".join([i["message"] for i in infos])}


def main():

    # Initialize the argument parser
    parser = argparse.ArgumentParser(
        description="Get annotator info and log path from command line arguments."
    )

    # Define the command line arguments
    parser.add_argument("--email", type=str, required=True, help="Email of the annotator")
    parser.add_argument(
        "--curriculum",
        type=str,
        required=True,
        help='Path to the curriculum file (optional: use "random" for a random one)',
    )
    parser.add_argument(
        "--log",
        type=str,
        required=False,
        default="human_eval_log.json",
        help="Path to the log file",
    )
    parser.add_argument("--reset-log", action="store_true", help="Reset the log file")

    # Parse the arguments
    args = parser.parse_args()

    annotator_info = {"email": args.email}
    logging.info(f"Annotator info: {annotator_info}")

    # Reset the log file if requested
    logging.info(f"Log file: {args.log}")
    if args.reset_log:
        logging.info("Resetting log file")
        json.dump([], open(args.log, "w"))

    # Loop over the curriculum
    curriculum = load_curriculum(args.curriculum)
    logging.info(f"Starting evaluation for {len(curriculum)} tasks")
    for i, task_info in enumerate(curriculum):

        if task_already_evaluated(args.log, annotator_info, task_info):
            logging.info(f"Task {task_info} already evaluated. Skipping.")
            continue

        # Setup the environment
        logging.info(f"Setting up environment for task {task_info}")
        env = setup_environment(task_info)

        # Game loop
        logging.info(f"Starting evaluation for task {task_info}")
        start_time = time()
        end = False
        success = False
        prev_chat_len = len(env.chat.messages)
        while True:
            human_console_set_progress_status(
                f"Task {i + 1} / {len(curriculum)} --- Elapsed: {round(time() - start_time, 2)} sec.",
                env.context,
            )

            # Event: Human marked task as infeasible
            infeasible, infeasible_reason = infeasible_flag_activated(env.context)
            if infeasible and not any([m["role"] == "infeasible" for m in env.chat.messages]):
                logging.info(f"Human marked task as infeasible. Reason: {infeasible_reason}")
                human_console_set_status("Task marked as infeasible.", env.context)
                env.chat.messages.append({"role": "infeasible", "message": infeasible_reason})
                # TODO: There is a small glitch where if the user changes their message after,
                #       the new infeasible message will be saved instead of the initial one that
                #       was added to the chat messages. We can't stop after infeasible has been
                #       declared.

            # Event: Validation is required
            if validation_flag_activated(env.context) or len(env.chat.messages) != prev_chat_len:
                human_console_set_status("Validation in progress...", env.context)

                # Patch all chat messages
                for m in env.chat.messages:
                    if not m.get("patched", False):
                        if m["role"] == "user":
                            m["role"] = "assistant"
                        elif m["role"] == "assistant":
                            m["role"] = "user"
                        m["patched"] = True

                reward, stop, message, info = validate_solution(env)
                logging.info(f"Validation: {info} -- reward: {reward} -- stop: {stop}")

                if reward == 1:
                    human_console_set_status("Success!", env.context)
                    end = True
                    success = True
                else:
                    if not end:  # If we're not already stopping for another reason
                        if stop:
                            human_console_set_status(
                                "Task not completed. Stop required.", env.context
                            )
                            end = True
                            success = False
                        else:
                            human_console_set_status("Task not completed. Keep going.", env.context)

                prev_chat_len = len(env.chat.messages)
                reset_validation_flag(env.context)

            # Event: Human abandoned task
            if abandon_flag_activated(env.context):
                end = True
                success = False
                human_console_set_status("Task abandoned by human.", env.context)

            # Event: Task is finished
            if end:
                log_result(
                    path=args.log,
                    annotator_info=annotator_info,
                    task_info=task_info,
                    metrics={
                        "duration": time() - start_time,
                        "success": success,
                        "infeasible": infeasible_reason if infeasible else None,
                        "abandoned": abandon_flag_activated(env.context),
                        "chat_messages": env.chat.messages,
                    },
                )
                sleep(3)  # Sleep so human has time to read status before it closes
                break

            sleep(0.1)

        human_console_set_status("Cleaning environment. This may take a while...", env.context)
        env.close()
        logging.info(f"Finished evaluation for task {task_info}")


if __name__ == "__main__":
    main()
