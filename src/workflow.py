from src import helper
import os
import glob
from src.log import Log, MarkerException, LoadingIndicator
import argparse
import datetime
import zipfile
import shutil
from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET
from .default_data import DefaultData
from .load_customer import process_input_file
from .prepare_data import prepare_data
from .create_xml import create_report
import pprint  # noqa
from .shared import shared_data
import openpyxl
from .helper import exact_search, non_exact_search

pause_between_reports = True
pause_after_intro = False

def start(config_file="config/config_JY.yml", no_clear=False):
    print(f"\nChoose a type for the file: ")
    print("1. ZR_DOCS - Zero report with a default supporting documents")
    print("2. ZR_NO_DOCS - Zero report without supporting documents")
    print("3. NO_TAG - Emission report, default value report, Zero report with mixed supporting documents")

    while True:
        user_input = input("Enter your choice (1 / 2 / 3): ").strip()
        if user_input in ("1", "2", "3"):
            break
        print("Invalid input. Please enter 1, 2, or 3.")

    # Step 1: Clear the log display if allowed
    if not no_clear:
        Log.clear()
    
    # Step 2: Load configuration
    config = helper.load_config(config_file=config_file)

    # Step 3: Load input files and any indirect representative files
    input_files, indirect_r_files = load_input_files(config)

    if indirect_r_files:
        input_files.append(indirect_r_files)

    # Step 4: Initialize default reference data
    Log.procedure("Loading default data ...")
    loader = LoadingIndicator()
    loader.start()  # Start the loading indicator
    DefaultData.initialize(config)
    loader.stop()

    ### indirect representative files

    # other files

    # Step 5: Iterate through all input files
    for index, input_data in enumerate(input_files, start=1):
        try:
            # Reset current shared state for each run
            shared_data["current"] = {}
            shared_data["current"]["config"] = config

            # Ensure input_data is a list (for multi-file processing)
            if type(input_data) is not list:
                input_data = [input_data]

            input_file_name = os.path.basename(input_data[0])

           # Step 6: Pause if needed before processing next file
            if index == 1 and pause_after_intro or index > 1 and pause_between_reports:
                Log.wait_for_input(f"<b>Press any button to continue with file {index}:</b> [<orange> {input_file_name.replace("=", " · ")}</orange> ]</b>")

            # Clear screen again if required
            if not no_clear:
                Log.clear()

            # Step 7: Print status of files being processed
            input_dir = config["input_directory"]
            procedure_str = f"<b>Found {len(input_files)} input file{'s' if len(input_files) > 1 else ''}</b> in <gray>{input_dir}</b>\n\n"

            for index_, f in enumerate(input_files, start=1):
                f = f[0]
                filename = os.path.basename(f)
                
                if index_ < index:
                    procedure_str += f" ✓ {filename}\n"
                elif index_ == index:
                    procedure_str += f" ➜ <b>{filename}</b> <green>[in process]</green>\n"
                else:
                    procedure_str += f" - {filename}\n"

            Log.procedure(procedure_str)
            Log.divider()

             # Step 8: Report type tagging if multiple input files
            if len(input_data) > 1:
                shared_data["current"]["report_type"] = "indirect_representative"

            # Step 9: Parse and collect data from all input files
            customer_data = []
            for input_file in input_data:
                config["input_file"] = input_file
                customer_data.append(process_input_file(input_file, config["version_layouts_file"]))

            # Step 10: Extract general customer info
            # Add the output dir to shared data, to access it for pdf creation # todo: move that to load customer
            # that is really ugly and should be changed
            shared_general_info = shared_data.setdefault("general_info", {})
            customer_general_info = customer_data[0]["Allgemeine_Informationen"]["general_information"][0]
            customer_quarter_table = customer_data[0]["Allgemeine_Informationen"]["quarter"][0]

            importer_name = shared_general_info["importer_name"] = customer_general_info["importer_name"]  # should be declarant
            year = shared_general_info["year"] = customer_quarter_table["year"]
            quarter = shared_general_info["quarter"] = customer_quarter_table["quarter"]

            # Step 11: Create output directory
            output_dir = output_path(config, importer_name, year, quarter)

            # creating the dir
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                Log.info(f"Created output directory: {output_dir}")

            # adding the output dir to shared data
            shared_data["current"]["output_dir"] = output_dir

            # tag intepretation

            # Step 12: Handle macOS tags (if applicable)
            if len(input_data) == 1:
                input_file = input_data[0]
                file_name = os.path.basename(input_file)

                if user_input == "3":
                    pass
                elif user_input == "1":
                    Log.info(f"Type <yellow>ZR_DOCS</r> for file {input_file.split('/')[-1]}")
                    config["tagset_determination_approach"] = "zero_report_with_default_docs"

                    # Collect supporting documents from input folder
                    supporting_docs = [f for f in os.listdir(input_dir) if f.startswith("supporting_document_")]

                    if len(supporting_docs) == 0:
                        Log.error("No supporting documents found for zero_report_with_default_docs. Please add supporting documents to the input folder.")
                        return

                    config["default_supporting_documents"] = [os.path.join(input_dir, supporting_doc) for supporting_doc in supporting_docs]
                elif user_input == "2":
                    Log.info(f"Type <yellow>ZR_NO_DOCS</r> for file {input_file.split('/')[-1]}")
                    config["tagset_determination_approach"] = "zero_report_without_docs"


            # Step 13: Load extra customer documents (skip for known quarters)
            if f"Q{quarter}-{year}" not in ["Q4-2023", "Q1-2024", "Q2-2024"]:
                load_customer_supporting_documents(importer_name, config)

            # Step 14: Prepare report data
            prepared_data = prepare_data(customer_data, config)

            # Step 15: Generate XML reports (real and test versions)
            xml_tree = create_report(prepared_data)
            xml_tree_test = create_report(prepared_data, test_report=True)

            # Step 16: Save XML and related output
            save_files(xml_tree, xml_tree_test, config, prepared_data)

            # Step 17: Summary of report
            Log.summary(config)

            # Step 18: User confirmation to finalize report
            user_choice = Log.dialog("Do you want to mark the report as correct and finished?", title="Report Confirmation", options=["yes", "no"])
            if user_choice.lower() == "yes":
                save_completed_report(config)
                copy_to_customer_drive(config)
                report_row_data_to_clipboard()

            Log.info(f"Finished processing file {index} ({input_data[0].split('/')[-1]})")

        # Step 19: Error handling
        except Exception as e:
            if isinstance(e, MarkerException):
                print("marker_exception")
                return

            Log.warning(
                f"An error occurred while processing file {index} ({input_data[0].split('/')[-1]}):\n\n{e}",
                "Workflow",
            )
            raise e


def output_path(config, importer_name, year, quarter):
    output_dir = config["output_directory"]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        Log.info(f"Created output directory: {output_dir}")

    date = datetime.datetime.now().strftime("%Y-%m-%d")

    importer_name = importer_name.replace("&amp;", "&")
    importer_name = importer_name.replace(" ", "_")
    dir_name = f"{date} - {importer_name} - Q{quarter}-{year}"

    return os.path.join(output_dir, dir_name)


def save_files(xml_tree, xml_tree_test, config, prepared_data):
    customer_name, year, quarter = (
        prepared_data["general_info"]["importer_name"],
        prepared_data["general_info"]["year"],
        prepared_data["general_info"]["quarter"],
    )

    output_dir = output_path(config, customer_name, year, quarter)

    file_base_name = f"{customer_name} - Q{quarter}-{year}.xml"

    xml_file = file_base_name
    xml_test_file = f"XML_TEST - {file_base_name}"
    zip_file = "report - " + file_base_name + ".zip"
    zip_test_file = f"ZIP_TEST - {file_base_name}.zip"

    test_folder_name = "1 - test_files"
    report_folder_name = "2 - report_files"
    supporting_docs_folder_name = "3 - supporting_documents"
    input_customer_name = f"4 - input_customer - {file_base_name[:-4]}.xlsx"

    os.makedirs(os.path.join(output_dir, test_folder_name), exist_ok=True)
    os.makedirs(os.path.join(output_dir, report_folder_name), exist_ok=True)

    # delete contents of old supporting docs folder, which is a folder starting with supporting_docs_folder_name
    # however the folder name is not known exactly, so we have to find it
    for folder in os.listdir(output_dir):
        if folder.startswith(supporting_docs_folder_name):
            shutil.rmtree(os.path.join(output_dir, folder))
    os.makedirs(os.path.join(output_dir, supporting_docs_folder_name), exist_ok=True)

    xml_path = os.path.join(output_dir, report_folder_name, xml_file)
    xml_test_path = os.path.join(output_dir, test_folder_name, xml_test_file)
    save_xml(xml_path, xml_tree)
    save_xml(xml_test_path, xml_tree_test)

    shared_data_docs = shared_data["current"].setdefault("supporting_documents", {})

    with zipfile.ZipFile(os.path.join(output_dir, report_folder_name, zip_file), "w", compresslevel=9) as zipf:
        zipf.write(xml_path, xml_file)
        for sup_doc_file_name, amount in shared_data_docs.items():
            for i in range(amount):
                i = i + 1
                basename = os.path.basename(sup_doc_file_name)
                suffix = basename.split(".")[-1]
                basename = basename[: -len(suffix) - 1]
                zipf.write(os.path.join(output_dir, "temp", sup_doc_file_name), basename + f"_{i}" + "." + suffix)

    with zipfile.ZipFile(os.path.join(output_dir, test_folder_name, zip_test_file), "w", compresslevel=9) as zipf:
        zipf.write(xml_test_path, xml_test_file)
        for sup_doc_file_name, amount in shared_data_docs.items():
            for i in range(amount):
                i = i + 1
                basename = os.path.basename(sup_doc_file_name)
                suffix = basename.split(".")[-1]
                basename = basename[: -len(suffix) - 1]
                zipf.write(os.path.join(output_dir, "temp", sup_doc_file_name), basename + f"_{i}" + "." + suffix)

    num_supporting_docs = 0
    for sup_doc_file_name, amount in shared_data_docs.items():
        for i in range(amount):
            num_supporting_docs += 1
            i = i + 1
            basename = os.path.basename(sup_doc_file_name)
            suffix = basename.split(".")[-1]
            basename = basename[: -len(suffix) - 1]
            target_path = os.path.join(output_dir, supporting_docs_folder_name, basename + f"_{i}." + suffix)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy(os.path.join(output_dir, "temp", sup_doc_file_name), target_path)
            print(f"Copied {os.path.join(output_dir, 'temp', sup_doc_file_name)} to {os.path.join(output_dir, supporting_docs_folder_name, basename + f'_{i}' + '.' + suffix)}")

    # rename supporting document folder such that the number len(shared_data_docs) is in brackets at the end
    old_name = os.path.join(output_dir, supporting_docs_folder_name)
    new_name = os.path.join(output_dir, f"{supporting_docs_folder_name} ({num_supporting_docs})")
    os.rename(old_name, new_name)

    input_target = os.path.join(output_dir, os.path.basename(config["input_file"]))
    os.makedirs(os.path.dirname(input_target), exist_ok=True)
    shutil.copy(config["input_file"], input_target)

    # rename the input file
    old_name = os.path.join(output_dir, os.path.basename(config["input_file"]))
    new_name = os.path.join(output_dir, input_customer_name)
    os.makedirs(os.path.dirname(new_name), exist_ok=True)
    os.rename(old_name, new_name)

    if config["move_customer_file"]:
        # deleting the input customer file
        os.remove(config["input_file"])

    # remove temp folder
    if os.path.exists(os.path.join(output_dir, "temp")):
        shutil.rmtree(os.path.join(output_dir, "temp"))


def save_xml(output_path, xml_tree):
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        Log.info(f"Created output directory: {output_dir}")

    pretty_xml_str = pretty_format_xml(xml_tree)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write(pretty_xml_str)


def load_input_files(config):
    parser = argparse.ArgumentParser(description="Add filepath optionally")

    # Definiere das Argument -f/--filepath
    parser.add_argument("-f", "--filepath", type=str, help="Filepath")

    # Parse die Argumente
    args = parser.parse_known_args()[0]

    # Überprüfe, ob das Argument -f/--filepath übergeben wurde
    if args.filepath:
        if not os.path.isdir(args.filepath):
            Log.error("Error: The specified path does not exist.")
            exit()

        config["input_directory"] = args.filepath
        config["output_directory"] = os.path.join(args.filepath, "output")

        Log.info(f" -f argument given. Using specified path: {args.filepath}")

    else:
        Log.info(f"output_dir: {config['output_directory']}\ninput_dir:  {config['input_directory']}")

    files, ind_rep_files = load_files(config)

    # if len(files) != 1:
    #    Log.error("Error: Multiple files in input dict not supported at the moment.")

    # config["input_file"] = files[0]
    return files, ind_rep_files


def load_files(config: dict):
    input_dir = os.path.abspath(config["input_directory"])  # Sicherstellen, dass der Pfad absolut ist

    files_in_directory = os.listdir(input_dir)

    # Ausgabe der Dateien und Verzeichnisse
    Log.debug(
        f"Files in directory '{input_dir}':\n - " + "\n - ".join([file_name for file_name in files_in_directory]),
        "load_files",
    )

    # entferne vorherige benennung falls vorhanden, also prefix \d=:
    for file_name in files_in_directory:
        if file_name[1] == "=":
            old_name = os.path.join(input_dir, file_name)
            new_name = os.path.join(input_dir, file_name[2:])
            os.rename(old_name, new_name)

    patterns = ["customer*.xlsx", "Customer*.xlsx"]
    excel_files_raw = []
    for pattern in patterns:
        excel_files_raw.extend(glob.glob(os.path.join(input_dir, pattern)))

    seen = set()
    excel_files = []

    for path in excel_files_raw:
        norm_path = os.path.normcase(os.path.normpath(path)) 
        if norm_path not in seen:
            seen.add(norm_path)
            excel_files.append(os.path.normpath(path))

    ind_rep_files = []

    ind_rep_folder_name = "2 - indirect_representative"


    if os.path.exists(os.path.join(config["input_directory"], ind_rep_folder_name)):
        ir_pattern1 = "master*.xlsx"
        ir_pattern2 = "importer*.xlsx"

        ind_rep_ls1 = glob.glob(os.path.join(input_dir, ind_rep_folder_name, ir_pattern1))
        ind_rep_ls2 = glob.glob(os.path.join(input_dir, ind_rep_folder_name, ir_pattern2))

        ind_rep_files = ind_rep_ls1 + ind_rep_ls2

        if len(ind_rep_files) == 0:
            pass
        elif len(ind_rep_ls1) > 1 or len(ind_rep_ls1) == 0:
            Log.error("Error: Multiple files or no file starting with 'importer' found in indirect_representative folder.")

        else:
            Log.info(f"Found {len(ind_rep_files)} file{'s' if len(ind_rep_files) > 1 else ''} in indirect_representative folder.")

    if not excel_files and not ind_rep_files:
        Log.error(
            f"Error: No .xlsx files found in input folder for (pattern: '<yellow>{pattern}</r>')\n\nUsing path: <yellow>{input_dir}</r>",
            title=f"'{pattern}' file not found !",
        )
    else:
        file_names = "\n".join([os.path.basename(file) for file in excel_files])
        Log.info(f"Found {len(excel_files)} .xlsx file{'s' if len(excel_files) > 1 else ''}:\n{file_names}")

        files = []
        for i, file_path in enumerate(excel_files, start=1):
            old_name = os.path.basename(file_path)

            new_name = os.path.join(input_dir, f"{i}={old_name}")
            os.rename(file_path, new_name)
            if old_name != new_name:
                Log.debug(
                    f"Renamed\n  {file_path.split('/')[-1]} \n→ {new_name.split('/')[-1]}",
                    "workflow",
                )
                
            files.append(new_name)

        return files, ind_rep_files
    return [], []


def ask_yes_no_question(question):
    while True:
        input_str = Log.add_prefix(f"{question} (y/n): ", "info")
        answer = input(input_str).strip().lower()
        if answer in ["y", "n"]:
            return answer == "y"
        else:
            print(Log.add_prefix("Bitte nur 'y' oder 'n' eingeben."))


def pretty_format_xml(element_tree):
    xml_str = ET.tostring(element_tree.getroot(), encoding="unicode")
    parsed = parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent="  ")
    # Entfernen der automatisch hinzugefügten Deklaration
    declaration_removed = "\n".join(pretty_xml.split("\n")[1:])
    return declaration_removed


import pyperclip


def report_row_data_to_clipboard():
    shared_sum = shared_data["current"].get("summary", {})
    total_quantity = str(shared_sum.get("total_net_mass", 0)) + "t"
    total_emissions = str(shared_sum.get("total_emissions", 0)) + "t CO2"

    clipboard_str = f"{total_quantity}\t{total_emissions}"
    pyperclip.copy(clipboard_str)

    Log.info(" <green>✓</r> Copied Data to Clipboard")


def save_completed_report(config):
    # Get importer_name, quarter_string
    importer_name = shared_data["general_info"]["importer_name"]
    year = shared_data["general_info"]["year"]
    quarter = shared_data["general_info"]["quarter"]
    # Reduce year to last two digits
    year_short = str(year)[-2:]

    # Now, create the folder in 'finished_reports_file_path' and copy the report zip file
    finished_reports_path = config["finished_reports_file_path"]
    # Get date in 'yy-mm-dd' format
    date_str = datetime.datetime.now().strftime("%y-%m-%d")
    folder_name = f"{date_str} [Q{quarter}-{year_short}] {importer_name}"
    destination_dir = os.path.join(finished_reports_path, folder_name)

    # Create the directory
    try:
        os.makedirs(destination_dir, exist_ok=True)
    except Exception as e:
        Log.error(f"Error creating directory '{destination_dir}': {e}", title="Directory Creation Error")
        return

    # Get the report zip file path (not the test zip)
    output_dir = shared_data["current"]["output_dir"]
    report_folder_name = "2 - report_files"
    report_folder_path = os.path.join(output_dir, report_folder_name)
    zip_files = [f for f in os.listdir(report_folder_path) if f.endswith(".zip") and not f.startswith("ZIP_TEST")]
    if not zip_files:
        Log.error("No report zip file found to copy.", title="File Not Found")
        return
    elif len(zip_files) > 1:
        Log.warning("Multiple report zip files found. Copying the first one.")

    report_zip = zip_files[0]
    source_zip_path = os.path.join(report_folder_path, report_zip)
    destination_zip_path = os.path.join(destination_dir, report_zip)

    # Copy the zip file
    try:
        shutil.copy(source_zip_path, destination_zip_path)
    except Exception as e:
        Log.error(f"Error copying file '{source_zip_path}' to '{destination_zip_path}': {e}", title="File Copy Error")
        return

    Log.info(" <green>✓</r> Succesfully copied into Completed Reports folder")


def copy_to_customer_drive(config):
    # Get the 'all_customers_googledrive_filepath' from config
    customer_drive_path = config["all_customers_googledrive_filepath"]
    # Get 'importer_name' from shared_data
    importer_name = shared_data["general_info"]["importer_name"]
    # Construct the path to the importer_name folder
    importer_folder_path = os.path.join(customer_drive_path, importer_name)

    # Check if the importer folder exists
    if not os.path.exists(importer_folder_path):
        # Ask the user if they want to create it
        user_choice = Log.dialog(f"The folder '{importer_name}' does not exist in '{customer_drive_path}'. Do you want to create it?", title="Create Folder", options=["yes", "no"])
        if user_choice.lower() != "yes":
            Log.info("User chose not to create the folder. Skipping copying to customer drive.")
            return
        # Create the folder
        try:
            os.makedirs(importer_folder_path)
            Log.info(f"Created folder '{importer_folder_path}'")
        except Exception as e:
            Log.error(f"Error creating folder '{importer_folder_path}': {e}", title="Folder Creation Error")
            return

    # Now, copy the 'output_dir' into the 'importer_folder_path'
    output_dir = shared_data["current"]["output_dir"]
    output_dir_name = os.path.basename(output_dir)
    destination_path = os.path.join(importer_folder_path, output_dir_name)

    # If the destination folder already exists, replace it
    if os.path.exists(destination_path):
        try:
            shutil.rmtree(destination_path)
            Log.info(f"Removed existing directory '{destination_path.split('/')[-1]}'")
        except Exception as e:
            Log.error(f"Error removing existing directory '{destination_path}': {e}", title="Directory Removal Error")
            return

    # Copy the output directory
    try:
        shutil.copytree(output_dir, destination_path)
        Log.info(" <green>✓</r> Succesfully copied report dir into Google Drive")
    except Exception as e:
        Log.error(f"Error copying '{output_dir}' to '{destination_path}': {e}", title="Copy Error")
        return


def load_customer_supporting_documents(customer_name, config):

    if "tagset_determination_approach" in config:
        return

    supplier_data_dir = config["supplier_workflow"]["supplier_data_dir"]
    importer = customer_name

    # * find the importer folder within the supplier data

    Log.debug(
        f"[Importer Search] Searching for folder matching importer '<yellow>{importer}</r>' "
        f"in path: <yellow>{supplier_data_dir}</r>\n"
        f"Available folders:\n - " + "\n - ".join(os.listdir(supplier_data_dir))
    )

    
    importer_folder = exact_search(importer, os.listdir(supplier_data_dir))
    if importer_folder is None:
        importer_folder = non_exact_search(
            importer,
            os.listdir(supplier_data_dir),
            warn=True,
            warn_title="Customer Supporting Docs | Supplier Data",
        )

    if importer_folder is None:
        Log.error(
            f"No importer folder found for importer '<yellow>{importer}</r>' in supplier data" + f"\nLooking at: <yellow>'{supplier_data_dir}'</r>",
            title="supplier_workflow | importer folder not found",
        )

    importer_folder_path = os.path.join(supplier_data_dir, importer_folder)

    # ↓ < supporting_docs_adjustment 17/04 >

    # if the importer folder contains "customer_supporting_documents" folder and if there is a file in it, get the file path
    if not "default_supporting_documents" in config:
        matching_folders = [
            f for f in os.listdir(importer_folder_path)
            if "supporting_document" in f.lower() and os.path.isdir(os.path.join(importer_folder_path, f))
        ]

        if matching_folders:
            supporting_docs_folder = os.path.join(importer_folder_path, matching_folders[0])
            files = [f for f in os.listdir(supporting_docs_folder) if not f.startswith('.')]
            if len(files) > 0:
                supporting_docs_file = os.path.join(supporting_docs_folder, files[0])
                config["default_supporting_documents"] = [supporting_docs_file]
                Log.info(
                    f"Found default supporting document in folder '<yellow>{supporting_docs_folder}</r>': '<yellow>{supporting_docs_file}</r>'",
                )

    # ↑ < supporting_docs_adjustment 17/04 >