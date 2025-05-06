from src.load_customer import process_input_file
import src.helper as helper
from src.default_data import DefaultData
from src.workflow import load_input_files
import pprint


def test_load_customer():
    config_file = "config/config.yml"
    config = helper.load_config(config_file=config_file)

    DefaultData.initialize(config)

    input_files = load_input_files(config)

    # * Customer File

    config["input_file"] = input_files[0]

    raw_data = process_input_file(config["input_file"], config["version_layouts_file"])

    pprint.pprint(raw_data)
