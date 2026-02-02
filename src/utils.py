import os
import sys
import pandas as pd
from time import sleep
from llama_cpp import Llama
from pathlib import Path


def check_path_existence(path: str) -> None:
    """
    Function to generate the correct directories in case they are not already made
    """
    if not os.path.exists(path):
        os.makedirs(path)


def check_collected_prompts(
    model_name: str, correct: bool, prompt_type: int
) -> list[str]:
    """
    Function that does not allow requesting duplicate prompts
    """
    # Access the outputs already collected
    output_file_path = os.path.join(
        ["code-outputs", "uml-outputs", "summary-outputs"][prompt_type],
        model_name.replace(":free", ""),
        "correct" if correct else "incorrect",
    )

    collected_prompts = []

    for root_path, dirs, files in os.walk(output_file_path):
        if dirs == []:
            for file in files:
                collected_prompts.append(
                    os.path.join(
                        os.path.sep.join(root_path.split(os.path.sep)[4:]), file
                    )
                )

    return collected_prompts


def find_file_in_subdir(parent_dir: str, extension: str = ".gguf"):
    """
    Find a file matching pattern in any subdirectory, given a parent directory
    """
    parent = Path(parent_dir)

    # Search Recursively for the file pattern
    files = list(parent.glob(f"*/*{extension}"))

    if not files:
        raise FileNotFoundError(
            f"No files found matching {extension} pattern in {parent_dir}"
        )

    if len(files) > 1:
        print(f"Warning: Found {len(files)} files, using first file")

    return str(files[0])


def evaluate_files(model_id: str, prompt_type: int):
    """
    Function to evaluate the output files
    """
    assert 0 <= prompt_type and prompt_type <= 2, "Prompt type not valid"
    # Initialise Summariser model to help evaluation
    summariser_model_snapshot_path = os.path.join(
        "models",
        "--".join(["models"] + "Qwen/Qwen2.5-3B-Instruct-GGUF".split(os.path.sep)),
        "snapshots",
    )
    summariser_model = Llama(
        model_path=find_file_in_subdir(summariser_model_snapshot_path),
        chat_format="chatml",
        seed=42,
        n_ctx=1024,
        n_threads=os.cpu_count() // 2,
        n_threads_batch=os.cpu_count() // 2,
        use_mlock=True,
        use_mmap=True,
        verbose=False,
    )

    model_output_path = os.path.join(
        ["code-outputs", "uml-outputs", "summary-outputs"][prompt_type],
        model_id,
    )

    if os.path.exists(os.path.join(model_output_path, "responses.xlsx")):
        print("Evaluation completed.... Exiting")
        sys.exit(1)

    total_df_dict: dict[str, dict[str, pd.DataFrame]] = {}

    for dir in os.listdir(model_output_path):
        # Iterate all subdirectories in output path
        subdir_path = os.path.join(model_output_path, dir)
        if not os.path.isdir(subdir_path):
            continue

        # Create four tables, one for each pattern name, and then containing responses; ask for human intervention if y/n not the first letter
        total_df_dict[dir] = {}
        # Iterate over patterns, then individual files
        for pattern in os.listdir(subdir_path):
            pattern_path = os.path.join(subdir_path, pattern)
            response_df = pd.DataFrame(columns=["Filename", "Response"])
            for role in os.listdir(pattern_path):
                role_path = os.path.join(pattern_path, role)
                for model_response in os.listdir(role_path):
                    model_response_path = os.path.join(role_path, model_response)
                    print(model_response_path)
                    if not os.path.isfile(model_response_path):
                        continue
                    response_row = [model_response]

                    with open(model_response_path, "r") as output_file:
                        response = output_file.read().strip()

                        if response.lower().startswith("y"):
                            response_row.append("Y")
                        elif response.lower().startswith("n"):
                            response_row.append("N")
                        else:
                            summariser_response = summariser_model.create_chat_completion(
                                messages=[
                                    {
                                        "role": "system",
                                        "content": "You are an AI helper, who is to help correctly identify whether something is mentioned or implied through the text",
                                    },
                                    {
                                        "role": "user",
                                        "content": f"Read the provided section and reply 'Y' if the section points to the fact that the {pattern} pattern has been implemented in a code, otherwise an 'N'. Also output a percentage for your answer to show how sure you are in brief.\n\nSection: {response}",
                                    },
                                ],
                                max_tokens=200,
                                stream=False,
                            )
                            response_valid = False
                            human_response = str(
                                summariser_response["choices"][0]["message"]["content"]
                            )
                            while not response_valid:
                                print(f"\n{"="*60}\n")
                                # human_response = input(
                                #     f"Read the summariser response and provide the evaluation please...\n\n{"="*60}\n\n{response}\n\n{"="*60}\n\nSummariser Response: {summariser_response['choices'][0]['message']['content']}\n\n{"="*60}\n\nResponse (Default = Summariser): "
                                # ).upper()
                                print(
                                    f"Model Response: {response}\n\n{"="*60}\n\nSummariser Response: {human_response}\n\n{"="*60}\n\nResponse saved: {human_response[0]}"
                                )
                                print(f"\n{"="*60}\n")
                                if human_response[0].upper() in "YN":
                                    response_row.append(human_response[0].upper() + "?")
                                    response_valid = True
                                else:
                                    print("Please provide either Y/n as response...\n")
                                    human_response = input("Response: ")

                            sleep(15)

                    response_df.loc[len(response_df)] = response_row
                total_df_dict[dir][pattern] = response_df

    with pd.ExcelWriter(
        os.path.join(model_output_path, "responses.xlsx"), engine="xlsxwriter"
    ) as writer:
        for dir in total_df_dict:
            start_row = 1
            for pattern in total_df_dict[dir]:
                current_df = total_df_dict[dir][pattern]
                current_df.to_excel(
                    writer, sheet_name=dir, startrow=start_row, startcol=0
                )
                start_row = start_row + len(current_df) + 3


def main():
    model_id = sys.argv[1]
    prompt_type = sys.argv[2]

    assert isinstance(model_id, str) and model_id != "", "Please enter valid model_id"
    try:
        prompt_type = int(prompt_type)
        assert prompt_type <= 2 and prompt_type >= 0, "Please enter valid prompt type"
    except ValueError as e:
        print(f"Error Received: {e}")

    evaluate_files(model_id=model_id, prompt_type=int(prompt_type))


if __name__ == "__main__":
    main()
