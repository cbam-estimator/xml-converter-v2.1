from pprint import pprint
from src.create_xml import create_report_structure, create_report
from src.helper import load_config
from src.default_data import DefaultData
from src.load_customer import process_input_file
from src.prepare_data import prepare_data

from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET


def test_report_creation():
    config_file = "config/config.yml"
    config = load_config(config_file=config_file)

    # * Prepare Data

    DefaultData.initialize(config)
    raw_data = process_input_file(config["input_file"], config["version_layouts_file"])
    prepared_data = prepare_data(config, raw_data)

    element_tree = create_report(prepared_data, test_report=True)
    pretty_xml_str = pretty_format_xml(element_tree)

    filename = "tests/output/test_report.xml"
    with open(filename, "w", encoding="utf-8") as file:
        file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        file.write(pretty_xml_str)


def test_report_structure():
    config_file = "config/config.yml"
    config = load_config(config_file=config_file)

    # * Prepare Data

    DefaultData.initialize(config)
    raw_data = process_input_file(config["input_file"], config["version_layouts_file"])
    prepared_data = prepare_data(config, raw_data)

    element_dict = create_report_structure(prepared_data, test_report=True)

    pprint(element_dict)


def pretty_format_xml(element_tree):
    xml_str = ET.tostring(element_tree.getroot(), encoding="unicode")
    parsed = parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent="  ")
    # Entfernen der automatisch hinzugefügten Deklaration
    declaration_removed = "\n".join(pretty_xml.split("\n")[1:])
    return declaration_removed
