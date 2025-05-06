from src.default_data import DefaultData
from pprint import pprint
from src.helper import load_config


def test_load_default():
    config_file = "config/config.yml"
    config = load_config(config_file=config_file)

    DefaultData.initialize(config)
    default_data = DefaultData.data_dict

    pprint(default_data)

    pprint(DefaultData.get("report_default_values"))
