import src.workflow_for_api as workflow
import sys
from src.shared import shared_data
import pytest
from src.log import MarkerException
import os
import glob


def test_workflow():
    report_type = "1"
    test_folder = r"E:\Jinyuzzz\Desktop\test"

    xlsx_files = glob.glob(os.path.join(test_folder, "*.xlsx"))
    assert len(xlsx_files) == 1, f"Expected exactly 1 .xlsx file, found {len(xlsx_files)}"
    customer_file_url = xlsx_files[0]

    pdf_files = glob.glob(os.path.join(test_folder, "*.pdf"))
    assert len(pdf_files) == 1, f"Expected exactly 1 .pdf file, found {len(pdf_files)}"
    supporting_doc_url = pdf_files[0]

    workflow.start(
        report_type=report_type,
        customer_file_url=customer_file_url,
        supporting_doc_url=supporting_doc_url
    )
