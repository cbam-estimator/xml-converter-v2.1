import sys
import os
from src.load_supplier_tool import load_supplier_tool



supplier_data_dir = r"E:\Jinyuzzz\Desktop"

importer_name = "Federnfabrik August Habighorst GmbH"
installation_name = "Çokyaşar Halat Makina Tel. Galvanizleme Sanayi Ticaret Anonim Şirketi"

importer_name2 = "Alexander Paal GmbH"
installation_name2 = "Neelkamal Enterprises PVT.LTD"

installation_entry = {
    "installation": installation_name2
}
prepared_data = {
    "general_info": {
        "importer_name": importer_name2
    }
}

config = {
    "supplier_workflow": {
        "supplier_data_dir": supplier_data_dir,
        "supplier_tool_pattern": "Supplier_*.xlsx"
    }
}

load_supplier_tool(installation_entry, prepared_data, config)

print("Successfully loaded supplier tool.")
print("General Info:", installation_entry["emission_data"].get("general_info"))
print("Available CN-Codes:", list(installation_entry["emission_data"].keys()))