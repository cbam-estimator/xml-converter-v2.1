from .log import Log
from .load_customer import process_input_file
from . import helper
from .default_data import DefaultData
from .prepare_data import prepare_data
from .create_xml import create_report
import src.workflow as workflow
import argparse

# * Proceedings


# load config file

Log.title()

config_file = "config.yml"
config = helper.load_config(config_file=config_file)
Log.info(f"Loaded settings from {config_file}")

input_file = workflow.input_files(config)

# * Default Data

DefaultData.initialize(config)

# * Customer File

customer_data = process_input_file(input_file, config["version_layouts_file"])

# * Pre Processing

prepared_data = prepare_data(customer_data)


# * Create Report Structure

xml_tree = create_report(prepared_data)
xml_tree_test = create_report(prepared_data, test_report=True)

workflow.save_files(xml_tree, xml_tree_test, config, prepared_data)


if False:
    Log.info(f"Loaded customer file {config['input_file']}")
    # TODO Log.customer_info(report_dict)

    # calculate emissions, enrich with missing data

    # TODO : calculate_emissions(report_dict)
    # TODO : add_standard_data(report_dict)

    # * Create xml reports

    # * Save files at the right places

    # *  Create logs

    Log.procedure("Reading input file...")
    Log.info("Input file read successfully.")
    Log.warning("Warning: This is a warning message.")
    Log.error(
        "Error: This is an error message. This is an error message.This is an error message. This is an error message. This is an error message.This is an error message.This is an error message. This is an error message.This is an error message.This is an error message. This is an error message.This is an error message.This is an error message. This is an error message.This is an error message.This is an error message. This is an error message.This is an error message."
    )
    Log.end()
