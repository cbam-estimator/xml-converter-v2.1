import src.workflow as workflow
import sys
from src.shared import shared_data
import pytest
from src.log import MarkerException


def test_workflow():
    test_folder_name = "supplierToolTest"

    test_args = [
        "program_name",
        "-f",
        f"/Users/andreas/Lokal/CBAM - Lokal/Workspaces/ce_xml_converter/tests/input_data/{test_folder_name}",
    ]
    # monkeypatch.setattr(sys, "argv", test_args)

    workflow.start(no_clear=True)
