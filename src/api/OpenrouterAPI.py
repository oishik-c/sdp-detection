# from openai import OpenAI
import os
import sys
import json
import requests
import logging
from .. import utils
from time import sleep


def run_model(model_name: str, pattern: str, prompt_type: int, correct: bool) -> None:
    """
    Function to inference LLM using Openrouter API methods and store results in appropriate files.

    INPUTS: model_name = string (which model to inference)
            pattern = string (which pattern to identify)
            correct = bool (whether to decipher for correct files or not)

    OUTPUTS: None
    """
    # Define Logging Parameters
    logging.basicConfig(
        filename="error_logs.log",
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    # Declarations
    common_prompt_path = ["prompts-code", "prompts-uml", "prompts-summary"][prompt_type]

    pattern_prompt_path = os.path.join(
        common_prompt_path, "correct" if correct else "incorrect", pattern
    )
    collected_prompts = utils.check_collected_prompts(model_name, correct, prompt_type)

    # Iterate over all prompt files
    for i, role in enumerate(os.listdir(pattern_prompt_path)):
        role_path = os.path.join(pattern_prompt_path, role)
        for j, prompt in enumerate(
            sorted(os.listdir(role_path), key=lambda x: int(x[:2].strip()))
        ):
            # Make request payload ready for one project file
            current_prompt_file_path = os.path.join(role_path, prompt)
            if (
                os.path.sep.join(current_prompt_file_path.split(os.path.sep)[2:])
                in collected_prompts
            ):
                print(f"Prompt {prompt} already used.... Skipping")
                continue
            with open(current_prompt_file_path, "r") as current_prompt_file:
                current_prompt = current_prompt_file.read()

            print(f"Loaded prompt {os.path.basename(current_prompt_file_path)}....")

            data_payload = json.dumps(
                {
                    "model": model_name,
                    "messages": [{"role": "user", "content": current_prompt}],
                }
            )
            url_payload = "https://openrouter.ai/api/v1/chat/completions"
            header_payload = {
                "Authorization": f"Bearer {os.getenv("OPENROUTER_API_KEY")}",
                "Content-Type": "application/json",
            }

            print(f"Request sent to {model_name}....")
            # Send request to Openrouter API to provide the response
            response = requests.post(
                url=url_payload,
                headers=header_payload,
                data=data_payload,
            )

            # Store the response to appropriate file
            output_file_path = os.path.join(
                ["code-outputs", "uml-outputs", "summary-outputs"][prompt_type],
                model_name.replace(":free", ""),
                "correct" if correct else "incorrect",
                pattern,
                role,
                f"{os.path.basename(current_prompt_file_path)}",
            )

            # Check the presence of directories
            utils.check_path_existence(os.path.dirname(output_file_path))

            print(f"Response Received.... Writing to {output_file_path}")

            try:
                with open(output_file_path, "w") as output_file:
                    output_file.write(
                        response.json()["choices"][0]["message"]["content"] + "\n"
                    )

                print("Output Stored...")

            except KeyError as e:
                logger.error(
                    f"An error occurred: {e}\nResponse Received:\n{response.json()}\n\n",
                    exc_info=True,
                )
                print("Error Message Received and Logged... Aborting")
                sys.exit(1)

            sleep(60 * 2)
