import src.helper as helper
from pprint import pprint

from src.load_customer import process_input_file
from src.default_data import DefaultData
from src.prepare_data import prepare_data
from src.log import Log

from src.workflow import load_input_files
import sys


def test_prepare_data(monkeypatch):
    test_folder_name = "supplierToolTest"

    test_args = [
        "program_name",
        "-f",
        f"/Users/andreas/Lokal/CBAM - Lokal/Workspaces/ce_xml_converter/tests/input_data/{test_folder_name}",
    ]
    monkeypatch.setattr(sys, "argv", test_args)

    Log.clear()
    config = helper.load_config(config_file="config/config.yml")
    input_files = load_input_files(config)

    Log.procedure("Loading default data ...")

    DefaultData.initialize(config)

    raw_data = process_input_file(input_files[0], config["version_layouts_file"])

    prepared_data = prepare_data(raw_data, config)

    # pprint(prepared_data["imported_goods"])
