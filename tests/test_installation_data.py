# * TODO : reparieren, nützlichkeit prüfen
from pprint import pprint  # noqa
import sys

import src.helper as helper
from src.load_customer import process_input_file
from src.default_data import DefaultData
from src.prepare_data import prepare_data, create_general_info_dict  # noqa
from src.log import Log
from src.workflow import load_input_files
from src.installation_data import get_installation_data


def test_installation_data(monkeypatch):
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

    customer_dict = process_input_file(input_files[0], config["version_layouts_file"])

    ## prepare data

    prepared_data_dict = {}

    create_general_info_dict(customer_dict, prepared_data_dict)

    # create_importer_dict(customer_dict, prepared_data_dict)

    # pprint(customer_dict)

    # pprint(prepared_data_dict)

    installation_data = get_installation_data(config, prepared_data_dict, customer_dict)  # noqa

    # pprint(installation_data)
    # print(f":::{installation_data}")
