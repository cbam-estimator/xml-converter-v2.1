from fastapi import FastAPI, Form
from pydantic import BaseModel
import requests
import os
import uuid
import yaml
from copy import deepcopy
import os
from ..src.workflow_for_api import start

app = FastAPI()

def patch_config(base_config: dict, patch_paths: dict) -> dict:
    config = deepcopy(base_config)
    for key, value in patch_paths.items():
        config[key] = value
    return config

def download_file(url: str, save_path: str):
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to download {url} - Status Code: {response.status_code}")
    with open(save_path, "wb") as f:
        f.write(response.content)

@app.post("/generate_report/")
async def generate_report_api(
    report_type: str = Form(...),
    customer_file_url: str = Form(...),
    supporting_doc_url: str = Form(...)
):
    try:
        # Step 1: Create temp working directory
        session_id = str(uuid.uuid4())
        session_dir = f"/tmp/session_{session_id}"
        input_dir = os.path.join(session_dir, "input")
        os.makedirs(input_dir, exist_ok=True)

        # Step 2: Download files from URLs
        customer_path = os.path.join(input_dir, "customer_file.xlsx")
        supporting_path = os.path.join(input_dir, "supporting_doc.pdf")

        download_file(customer_file_url, customer_path)
        download_file(supporting_doc_url, supporting_path)

        # Step 3: Load config template
        with open("config/config_template.yml", "r") as f:
            base_config = yaml.safe_load(f)

        # Step 4: Patch config with runtime paths
        patch_paths = {
            "input_directory": input_dir,
            "default_data_dir": "/app/resources/default_data",
            "version_layouts_file": "/app/resources/layouts/version_layout.json",
            "output_directory": os.path.join(session_dir, "output")
        }

        config = patch_config(base_config, patch_paths)

        # Step 5: Run report generation workflow
        result = start(config=config, report_type=report_type)

        return result

    except Exception as e:
        return {"status": "error", "message": str(e)}
