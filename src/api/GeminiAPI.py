from time import sleep
import os
import base64
from google import genai
from google.genai import types


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def run_model(model_name="gemini-2.0-flash", full=False, ignore=[], images=False):
    # Any changes should only be made in the following lines
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    content_path = (
        "scenarios/Punctuality/variant-3asdf.txt" if not full else "scenarios/"
    )
    prompt_path = "text-prompt.txt" if not images else "image-prompt.txt"
    # model_name = "gemini-2.0-flash"
    output_path = "./final-outputs/" if not images else "./image-outputs-seedream-gend/"

    if os.path.isdir(content_path):
        for scenario in os.listdir(content_path):
            # print(scenario)
            if len(ignore) != 0:
                if scenario in ignore:
                    continue
            scenario_path = os.path.join(content_path, scenario)
            if not images:
                variants = [
                    var
                    for var in os.listdir(scenario_path)
                    if os.path.isfile(os.path.join(scenario_path, var))
                ]
                for variant in variants:
                    formatted_content_path = os.path.join(scenario_path, variant)
                    get_response(
                        client,
                        formatted_content_path,
                        output_path,
                        model_name,
                        prompt_path,
                        images,
                    )
                    print(f"Generated response for {scenario}-{variant}...")
                    sleep(60)

            else:
                images_path = os.path.join(scenario_path, "images")
                variants = [
                    var
                    for var in os.listdir(images_path)
                    if os.path.isfile(os.path.join(images_path, var)) and "-tr" in var
                ]
                for variant in variants:
                    formatted_images_path = os.path.join(images_path, variant)
                    print(f"waiting for response to output for {formatted_images_path}")
                    get_response(
                        client,
                        formatted_images_path,
                        output_path,
                        model_name,
                        prompt_path,
                        images,
                    )
                    print(f"Generated response for {scenario}-{variant}...")
                    sleep(60)

    else:
        get_response(client, content_path, output_path, model_name, prompt_path, images)


def get_response(client, content_path, output_path, model_name, prompt_path, images):
    formatted_output_path = os.path.join(
        output_path,
        model_name,
        (
            os.path.basename(os.path.dirname(content_path))
            if not images
            else os.path.basename(os.path.dirname(os.path.dirname(content_path)))
        ),
        os.path.splitext(os.path.basename(content_path))[0],
    )

    content_type = os.path.splitext(os.path.basename(content_path))[1]

    if not os.path.exists(os.path.dirname(formatted_output_path)):
        os.makedirs(os.path.dirname(formatted_output_path))

    with open(prompt_path, "r") as fp:
        prompt = fp.read()

    with open("questions.txt", "r") as fq:
        questions = fq.read()

    if not images:
        with open(content_path, "r") as fs:
            content = fs.read()
        formatted_prompt = prompt.format(content=content, questions=questions)
        request_content = formatted_prompt
    else:
        with open(content_path, "rb") as fi:
            content = fi.read()
        formatted_prompt = prompt.format(questions=questions)
        request_content = [
            types.Part.from_bytes(
                data=content,
                mime_type=f"image/{content_type[1:]}",
            ),
            formatted_prompt,
        ]

    response = client.models.generate_content(
        model=model_name, contents=request_content
    )

    with open(formatted_output_path + ".txt", "w") as fo:
        fo.write(str(response.text))
