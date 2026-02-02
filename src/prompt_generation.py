import os
import re
import random
import subprocess
import xml.etree.ElementTree as ET
from typing import Generator, Tuple

random.seed(42)


def generate_plantuml_syntax(java_filepath: str):
    """Generates the plantuml syntax for a Java file"""
    # print(java_filepath)
    # if "PMD" in java_filepath:
    #     java_filepath = java_filepath.replace(
    #         "/net/", "/out/production/11 - PMD v1.8/net/"
    #     )

    if not os.path.exists(java_filepath):
        parent_dir = os.path.dirname(java_filepath)
        if os.path.exists(parent_dir + ".java"):
            java_filepath = parent_dir + ".java"
            print(f"Changing filepath to {java_filepath}")
        else:
            raise FileNotFoundError(
                f"Neither {java_filepath} nor its parent directory exists."
            )

    assert os.path.splitext(java_filepath)[1] == ".java", "File extension incorrect"

    # Run plantuml-parser-cli
    plantuml_result = subprocess.run(
        [
            "java",
            "-jar",
            "plantumlparsergit/plantuml-parser/plantuml-parser-cli/build/libs/plantuml-parser-cli-0.0.1-all.jar",
            "-l",
            "JAVA_17",
            "-f",
            java_filepath,
            "-sctr",
            "-spkg",
            "-fpub",
            "-mpub",
            "-fpro",
            "-mpro",
            "-fpri",
            "-mpri",
            "-fdef",
            "-mdef",
        ],
        capture_output=True,
        text=True,
    )

    print(plantuml_result)
    # # Run genuml
    # genuml_result = subprocess.run(
    #     ["genuml", "generate", java_filepath],
    #     capture_output=True,
    #     text=True,
    # )
    return plantuml_result.stdout


def generate_prompt_files(
    root: ET.Element,
    pattern_name: str,
    wrong: bool,
    just_code: bool,
    prompt_type: int = 0,
) -> None:
    """
    Function to generate all the prompt files of the provided pattern (pattern_name).

    INPUT:
        - root -> The root of the Element Tree containing the XML file data
        - pattern_name -> The name of the pattern to generate prompts for
        - wrong -> Whether to create incorrect dataset as well
    """
    if just_code:
        prompt_output_path = "./codes"
    else:
        prompt_output_path = ["./prompts-code", "./prompts-uml", "./prompts-summary"][
            prompt_type
        ]
    base_prompt = None
    with open("prompt.txt", "r") as base_prompt_file:
        base_prompt = base_prompt_file.read()

    # Accessing the Project Names and the filepaths containing the pattern implementation
    for project_name, element_role, rel_filepath, package_name in pattern_finder(
        root, pattern_name, wrong
    ):
        print(project_name, element_role, rel_filepath)
        # Check if pattern_name and element_role subfolders are present
        prompt_file_location = os.path.join(
            prompt_output_path,
            "correct" if not wrong else "incorrect",
            pattern_name,
            element_role,
        )
        if not os.path.exists(prompt_file_location):
            os.makedirs(prompt_file_location)

        # Generating the prompt output file path
        prompt_filepath = os.path.join(
            prompt_file_location,
            f"{project_name} - {os.path.basename(rel_filepath)}.txt",
        )
        try:
            # Reading the code from the source code file
            code = None
            # print(rel_filepath)
            if "beans" in project_name:
                print(3)
                print(rel_filepath)
                if rel_filepath.startswith("org"):
                    rel_filepath += "src" + os.path.sep
                    print(rel_filepath)
            print(rel_filepath)
            if not os.path.exists(rel_filepath + ".java"):
                print(1)
                parent_dir = os.path.dirname(rel_filepath)
                print(parent_dir)
                if os.path.exists(parent_dir + ".java"):
                    print(2)
                    rel_filepath = parent_dir
                    print(f"Changing filepath to {rel_filepath}")
                else:
                    raise FileNotFoundError(
                        f"Neither {rel_filepath} nor its parent directory exists."
                    )
            if prompt_type == 0:
                with open(f"{rel_filepath}.java", "r", errors="ignore") as code_file:
                    code = code_file.read()
            elif prompt_type == 1:
                # rel_filepath = rel_filepath.replace("/src/", "/bin/")
                code = generate_plantuml_syntax(rel_filepath + ".java")
            else:
                code = "WOW"

            uncommented_code = remove_comments(code)

            # Writing formatted prompt to the output file
            with open(prompt_filepath, "w") as prompt_file:
                if just_code:
                    prompt_file.write(code)
                else:
                    prompt_file.write(
                        base_prompt.format(
                            code=uncommented_code,
                            role=element_role,
                            pattern=pattern_name,
                            type="java" if prompt_type == 0 else "uml",
                        )
                    )
        except FileNotFoundError:
            # Writing formatted prompt to the output file
            with open(prompt_filepath, "w") as prompt_file:
                if just_code:
                    prompt_file.write(package_name)
                else:
                    prompt_file.write(
                        base_prompt.format(
                            code=package_name,
                            role=element_role,
                            pattern=pattern_name,
                            type="java" if prompt_type == 0 else "uml",
                        )
                    )


def pattern_finder(
    root: ET.Element, pattern_name: str, wrong: bool
) -> Generator[Tuple[str, str, str, str], None, None]:
    """
    Function to find the pattern instances from the source codes according to the provided file

    INPUT:
        - root -> The root of the Element Tree containing the XML file data
        - pattern_name -> The name of the pattern to search
        - wrong -> Whether to create incorrect dataset as well

    OUTPUT:
        - list of tuples (Project Name, Path to the file)
    """
    pattern_element_map = {
        "singleton": ("singleton",),
        "adapter": ("adapter",),
        "decorator": ("decorator", "concreteDecorator"),
        "facade": ("facade",),
        "flyweight": ("flyweight",),
        "bridge": ("abstraction", "implementor"),
        "composite": ("component", "composite", "leaf"),
        "proxy": ("proxy", "subject"),
    }

    assert type(root) == ET.Element, f"Provide the root of the XML file"
    assert (
        pattern_name in pattern_element_map.keys()
    ), f"{pattern_name} is not supported yet"

    # Extract pattern instances from the XML file by searching for correct stuff
    for program in root:
        project_name = None
        for instance in program:
            if instance.tag == "name":
                project_name = instance.text
            if str(instance.attrib.get("name")).lower() == pattern_name:
                for element in instance.iter():
                    if element.tag in pattern_element_map[pattern_name]:
                        for entity in element.iter():
                            if entity.tag == "entity":
                                # print(
                                #     "{:<30} - {:>10} - {:>10}".format(
                                #         project_name, element.tag, entity.text
                                #     )
                                # )
                                rel_filepath = None
                                package_name = entity.text
                                if wrong and project_name in os.listdir("source-codes"):
                                    while True:
                                        random_pattern = random.choice(
                                            list(pattern_element_map.keys())
                                        )

                                        if random_pattern != pattern_name:
                                            break

                                    # project_names = os.listdir("source-codes")
                                    # project_names.remove(project_name)
                                    while True:
                                        # print(project_name)
                                        rel_filepath = get_random_filepath(
                                            root,
                                            str(project_name),
                                            pattern_name,
                                            pattern_element_map[pattern_name],
                                        )

                                        package_name = ".".join(
                                            rel_filepath.split(os.path.sep)[3:]
                                        )
                                        # Check whether incorrect file got generated
                                        if rel_filepath and check_randomness(
                                            str(rel_filepath), root.iter(pattern_name)
                                        ):
                                            break
                                else:
                                    rel_filepath = get_pattern_filepath(
                                        str(project_name), str(entity.text)
                                    )
                                # print(rel_filepath)
                                if rel_filepath:
                                    yield str(project_name), str(element.tag), str(
                                        rel_filepath
                                    ), str(package_name)


def get_pattern_filepath(project_name: str, filename: str) -> str | None:
    """
    Function that generates the required file paths for the patterns found

    INPUT:
        - project_name -> The root of the Element Tree containing the XML file data
        - pattern_name -> The name of the pattern to search

    OUTPUT:
        - list of tuples (Project Name, Path to the file)
    """
    if project_name in os.listdir("source-codes"):
        filepath_from_src = filename.replace(".", os.path.sep)
        rel_filepath = os.path.join(
            "source-codes",
            project_name,
            "src" if "PMD" not in project_name else "",
            filepath_from_src,
        )
        return str(rel_filepath)
    return None


def remove_comments(string: str) -> str:
    """
    Function to remove comments from a provided string (using regex)

    INPUT :
        - string -> code to be uncommented

    OUTPUT :
        - uncommented code (str)
    """

    pattern = r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)"
    # first group captures quoted strings (double or single)
    # second group captures comments (//single-line or /* multi-line */)
    regex = re.compile(pattern, re.MULTILINE | re.DOTALL)

    def _replacer(match):
        # if the 2nd group (capturing comments) is not None,
        # it means we have captured a non-quoted (real) comment string.
        if match.group(2) is not None:
            return ""  # so we will return empty to remove the comment
        else:  # otherwise, we will return the 1st group
            return match.group(1)  # captured quoted-string

    return regex.sub(_replacer, string)


def get_random_filepath(
    root: ET.Element,
    project_name: str,
    pattern_name: str,
    possible_elements: tuple,
) -> str:
    random_file_choices = []
    source_filepath = os.path.join("source-codes", project_name)
    if "PMD" not in project_name:
        source_filepath = os.path.join(source_filepath, "src")
    else:
        source_filepath = os.path.join(source_filepath, "net")
    for root_path, dirs, files in os.walk(source_filepath):
        if files != []:
            for file in files:
                if "java" in os.path.splitext(file)[1]:
                    random_file_choices.append(
                        os.path.join(root_path, os.path.splitext(file)[0])
                    )

    program_found = False
    random_file_choice = None
    while not program_found:
        random_file_choice = str(random.choice(random_file_choices))
        # print(random_file_choice)

        for program in root:
            for instance in program:
                if instance.tag == "name" and instance.text == project_name:
                    for instance in program:
                        if str(instance.attrib.get("name")).lower() == pattern_name:
                            for element in instance.iter():
                                if element.tag in possible_elements:
                                    for entity in element.iter():
                                        if entity.tag == "entity":
                                            if (
                                                get_pattern_filepath(
                                                    project_name, str(entity.text)
                                                )
                                                != random_file_choice
                                            ):
                                                program_found = True

    return str(random_file_choice)


def check_randomness(
    filepath: str, pattern_instances: Generator[ET.Element, None, None]
) -> bool:
    """
    Function to check if the random filepath generated is not an instance of the provided pattern_instances
    """
    for pattern_instance in pattern_instances:
        # print(pattern_instance)
        for entity in pattern_instance.iter("entity"):
            if entity.text == filepath:
                return False

    return True
