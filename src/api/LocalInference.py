import os
import sys
import logging
from .. import utils
from datetime import datetime
from llama_cpp import (
    Llama,
    LLAMA_ROPE_SCALING_TYPE_LINEAR,
    LLAMA_ROPE_SCALING_TYPE_YARN,
)
from time import sleep
import argparse
from pathlib import Path


def process_in_chunks(
    llm: Llama, long_text: str, chunk_size: int = 1500, max_tokens: int = 1024
):
    """Process long text into chunks"""
    chunks = [
        str(long_text[i : i + chunk_size]) for i in range(0, len(long_text), chunk_size)
    ]

    results = []
    context = ""

    for i, chunk in enumerate(chunks):
        chunked_prompt = f"""Context from previous: {context}

            Current chunk:
            {chunk}
            
            Continue processing:
        """


def run_model(
    model_id: str, pattern: str, prompt_type: int, correct: bool, half_power: bool
) -> None:
    """
    Function to inference LLM in local machine and store results in appropriate files.

    INPUTS: model_name = string (which model to inference)
            pattern = string (which pattern to identify)
            correct = bool (whether to decipher for correct files or not)

    OUTPUTS: None
    """

    print(model_id, pattern, prompt_type, correct, half_power)

    # Define logging parameters
    logging.basicConfig(
        filename="local_error.log",
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    local_model_logpath = "llama_cpp_verbose.log"

    # Calculate model path
    model_snapshot_path = os.path.join(
        "models",
        "--".join(["models"] + model_id.split(os.path.sep)),
        "snapshots",
    )

    # Load models
    n_threads = os.cpu_count()
    assert n_threads is not None, "Error Received... Can't find threads"
    n_threads_half = n_threads // 2
    if half_power:
        print(f"\n{"="*60}\n")
        print("Running Half Efficiency")
        print(f"\n{"="*60}\n")
        n_threads = n_threads // 2
    else:
        n_threads = n_threads - 2
    model = Llama(
        model_path=utils.find_file_in_subdir(model_snapshot_path),
        chat_format="chatml",
        # Parameters tuning
        n_ctx=17000,
        n_threads=n_threads - 2 if not half_power else n_threads_half,
        n_threads_batch=n_threads,
        n_batch=512,
        n_ubatch=2048,
        # rope_scaling_type=LLAMA_ROPE_SCALING_TYPE_LINEAR,
        # rope_freq_base=10000,
        use_mlock=True,
        use_mmap=True,
        verbose=True,
    )

    # Declarations
    common_prompt_path = ["prompts-code", "prompts-uml", "prompts-summary"][prompt_type]
    pattern_prompt_path = os.path.join(
        common_prompt_path, "correct" if correct else "incorrect", pattern
    )
    collected_prompts = utils.check_collected_prompts(model_id, correct, prompt_type)
    print(collected_prompts)

    # Iterate over all prompt files
    for i, role in enumerate(os.listdir(pattern_prompt_path)):
        print(i, role)
        role_path = os.path.join(pattern_prompt_path, role)
        for j, prompt in enumerate(
            sorted(os.listdir(role_path), key=lambda x: int(x[:2].strip()))
        ):
            # Make prompt ready
            current_prompt_file_path = os.path.join(role_path, prompt)
            print(os.path.sep.join(current_prompt_file_path.split(os.path.sep)[2:]))
            if (
                os.path.sep.join(current_prompt_file_path.split(os.path.sep)[2:])
            ) in collected_prompts:
                print(f"Prompt {prompt} already used..... Skipping")
                continue
            with open(current_prompt_file_path, "r") as current_prompt_file:
                current_prompt = current_prompt_file.read()

            print(f"Loaded prompt {os.path.basename(current_prompt_file_path)}....")

            print(f"Model inferenced...")

            with open(local_model_logpath, "a") as log_file:
                # Redirect stderr to the log_file
                original_stderr = sys.stderr
                sys.stderr = log_file

                # Inference the local model and log output results
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                log_file.write(f"\n{'='*60}\n")
                log_file.write(f"[{timestamp}] Filename: {prompt}")
                log_file.write(f"\n{'='*60}\n")
                # log_file.flush()

                output = model.create_chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a senior software engineer experienced in object-oriented design patterns.",
                        },
                        {"role": "user", "content": current_prompt},
                    ],
                    temperature=0.6,
                    max_tokens=1200,
                    top_p=0.95,
                    stream=False,
                )

                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                log_file.write(f"\n{'='*60}\n")
                log_file.write(f"[{timestamp}] Output Received")
                log_file.write(f"\n{'='*60}\n")

                # Restore stderror
                sys.stderr = original_stderr

            assert isinstance(output, dict)
            res = output["choices"][0]["message"]["content"]

            output_file_path = os.path.join(
                ["code-outputs", "uml-outputs", "summary-outputs"][prompt_type],
                model_id.replace(":free", ""),
                "correct" if correct else "incorrect",
                pattern,
                role,
                f"{os.path.basename(current_prompt_file_path)}",
            )

            # Check directory presence
            utils.check_path_existence(os.path.dirname(output_file_path))

            print(f"Response received.... Writing to {output_file_path}")

            try:
                with open(output_file_path, "w") as output_file:
                    output_file.write(str(res))
                    print("Output sorted....")

            except FileExistsError as e:
                logger.error(f"Error occurred: {e}")
                print("Error message received and logged... Aborting")
                sys.exit(1)

            except FileNotFoundError as e:
                logger.error(f"Error occurred: {e}")
                print("Error message received and logged... Aborting")
                sys.exit(2)

            # Add some delay to let the machine cool down
            sleep(30)


def main():
    # Create Parser
    parser = argparse.ArgumentParser(description="Inference a model via model_id")

    # Arguments
    parser.add_argument("--model", type=str, help="Path to model's GGUF file")
    parser.add_argument("--pattern", type=str, help="Pattern name to inference")
    parser.add_argument("--prompt", type=int, help="What prompts to use")
    parser.add_argument(
        "--correct",
        action=argparse.BooleanOptionalAction,
        help="Test for correct or incorrect appearance",
    )
    parser.add_argument(
        "--half",
        action=argparse.BooleanOptionalAction,
        help="Whether to use full or half threads",
    )

    args = parser.parse_args()

    assert args.model, "Model name cannot be empty..."
    assert args.pattern, "Pattern name cannot be empty..."
    assert (
        isinstance(args.prompt, int) and 0 <= args.prompt and args.prompt <= 2
    ), "Prompt type not valid..."
    assert isinstance(args.correct, bool), "Correct must be a boolean"
    assert isinstance(args.half, bool), "Half must be a boolean"

    # Run the inferencing script
    run_model(
        model_id=args.model,
        pattern=args.pattern,
        prompt_type=args.prompt,
        correct=args.correct,
        half_power=args.half,
    )


if __name__ == "__main__":
    main()
