import os
import glob
import openpyxl
import pprint

from .log import Log
from .helper import exact_search, non_exact_search
from .xlsx_access import load_table_to_dict


def get_supplier_tool_path(installation_folder_path, installation_entry, prepared_data, config):
    

    
    # * get the supplier tool file

    pattern = config["supplier_workflow"]["supplier_tool_pattern"]
    matches = glob.glob(os.path.join(installation_folder_path, pattern))

    if len(matches) == 0:
        Log.error(
            f"No supplier tool file found for installation '<yellow>{installation_entry['installation']}</r>'",
            title="supplier_workflow | supplier tool file not found",
        )
    elif len(matches) > 1:
        Log.error(
            f"Multiple supplier tool files found for installation '<yellow>{installation_entry['installation']}</r>'",
            title="supplier_workflow | multiple supplier tool files found",
        )
    else:
        supplier_tool_path = matches[0]
        return supplier_tool_path
    



def get_installation_folder_path(installation_entry, prepared_data, config):
    supplier_data_dir = config["supplier_workflow"]["supplier_data_dir"]
    importer = prepared_data["general_info"]["importer_name"]

    # * find the importer folder within the supplier data

    importer_folder = exact_search(importer, os.listdir(supplier_data_dir))
    if importer_folder is None:
        importer_folder = non_exact_search(
            importer,
            os.listdir(supplier_data_dir),
            warn=True,
            warn_title="Supplier Data -> Importer",
        )

    if importer_folder is None:
        Log.error(
            f"No importer folder found for importer '<yellow>{importer}</r>' in supplier data" + f"\nLooking at: <yellow>'{supplier_data_dir}'</r>",
            title="supplier_workflow | importer folder not found",
        )

    importer_folder_path = os.path.join(supplier_data_dir, importer_folder)

    # ↓ < supporting_docs_adjustment 17/04 >

    # if the importer folder contains "customer_supporting_documents" folder and if there is a file in it, get the file path
    if "default_supporting_documents" in config:
        installation_entry["default_supporting_documents"] = config["default_supporting_documents"]

    # ↑ < supporting_docs_adjustment 17/04 >

    # * find the installation folder within the importer folder

    installation_folder = exact_search(installation_entry["installation"], os.listdir(importer_folder_path))

    if installation_folder is None:
        installation_folder = non_exact_search(
            installation_entry["installation"],
            os.listdir(importer_folder_path),
            warn=True,
            warn_title="Importer Folder -> Installation",
        )

    if installation_folder is None:
        Log.error(
            f"No installation folder found for installation '<yellow>{installation_entry['installation']}</r>''",
            title="supplier_workflow | installation folder not found",
        )

    installation_folder_path = os.path.join(importer_folder_path, installation_folder)

    return installation_folder_path


def load_supplier_tool(installation_entry, prepared_data, config):

    installation_folder_path = get_installation_folder_path(installation_entry, prepared_data, config)
    supplier_tool_path = get_supplier_tool_path(installation_folder_path, installation_entry, prepared_data, config)


    # * if present, get supporting docs

    """     supporting_documents_folder_path = os.path.join(installation_folder_path, "supporting_documents")
        if os.path.exists(supporting_documents_folder_path):
            installation_entry["supporting_documents"] = os.listdir(supporting_documents_folder_path)
            Log.info(
                f"Found supporting documents for installation '<yellow>{installation_entry['installation']} despite supplier tool in place!</r>'",
            ) """

    _ = """
        Data fields:

        
        
    """

    wb = openpyxl.load_workbook(supplier_tool_path, data_only=True) # type: ignore
    ws = wb["Output"]

    general_info_rows = [
        "Reporting Period Start",
        "Reporting Period End",
        "Operator name",
        "Operator EORI",
        "Name of the installation (english name)",
        "Name of the installation",
        "Economic activity",
        "Country",
        "City",
        "Street",
        "Street Number",
        "Postcode",
        "P.O. Box",
        "UNLOCODE",
        "Coordinates of the main emission source (latitude)",
        "Coordinates of the main emission source (longitude)",
        "Name of authorized representative",
        "Email",
        "Telephone",
    ]

    info_head_row = "Reporting Period Start"

    columns = {
        "ProPro Name": "production_process_name",
        "ProPro Position": "production_process_position",
        "CN-Code": "cn_code",
        "Direct Emissions: Type of Determination": "direct_emissions_type_of_determination",
        "Direct Emissions: Type of applicable reporting methodology": "direct_emissions_reporting_methodology",
        "Direct Emissions: Additional Information": "direct_emissions_additional_info",
        #    "Direct Emissions: Share of default values": "direct_emissions_share_of_default_values",  # not relevant
        #    "Direct Emissions: Supplier communication": "direct_emissions_supplier_communication",  # not relevant
        "Direct Emissions: Specific Direct Embedded Emissions": "direct_emissions_see",
        "Indirect Emissions: Type of determination": "indirect_emissions_type_of_determination",  # auto-det
        "Indirect Emissions: Source of emission factor": "indirect_emissions_source_of_emission_factor",  # 01, 02
        "Indirect Emissions: Source of electricity": "indirect_emissions_source_of_electricity",  # str
        "Indirect Emissions: Other source indication": "indirect_emissions_other_source_indication",  # opt
        "Indirect Emissions: Electricity consumed [MWh/t]": "indirect_emissions_electricity_consumed",
        "Indirect Emissions: Emission factor": "indirect_emissions_emission_factor",
        "Indirect Emissions: Source of emissions factor value": "indirect_emissions_source_of_emission_factor_value",  # str
        "Production Method: Production Method": "production_method_name",
        "Production Method: Reducing Agent": "production_method_reducing_agent",
        "Production Method: Reducing Agent for Precursor": "production_method_reducing_agent_for_precursor",
        "Production Method: Mn content [%]": "production_method_mn_content",
        "Production Method: Cr content [%]": "production_method_cr_content",
        "Production Method: Ni content [%]": "production_method_ni_content",  # not opt
        "Production Method: Other alloy content [%]": "production_method_other_alloy_content",
        "Production Method: C content [%]": "production_method_c_content",
        "Production Method: Steel scrap usage [t]": "production_method_steel_scrap_usage",
        "Production Method: Steel pre-consumer scrap [%]": "production_method_steel_pre_consumer_scrap",
        "Production Method: Steel product scrap usage [t]": "production_method_steel_product_scrap_usage",
        "Production Method: Non-Iron content": "production_method_non_iron_content",
        "Production Method: Aluminium scrap usage [t]": "production_method_aluminium_scrap_usage",
        "Production Method: Pre-consumer scrap [%]": "production_method_pre_consumer_scrap",
        "Production Method: Non-Aluminium content [%]": "production_method_non_aluminium_content",  # not opt
    }

    head_column = "ProPro Name"

    supplier_tool_data = {}

    supplier_tool_data["general_info"] = load_table_to_dict(ws, info_head_row, general_info_rows, orientation="horizontal")

    # list of dictionaries
    raw_data_ls = load_table_to_dict(ws, head_column, list(columns.keys()))

    # structure the data

    for ls_entry in raw_data_ls:
        # rename the keys
        tmp = {}
        for key, value in ls_entry.items():
            new_key = columns[key]
            tmp[new_key] = value
        ls_entry = tmp

        cn_code = str(ls_entry["cn_code"])
        cn_code_entry = {}

        cn_code_entry["direct_emissions"] = {}
        cn_code_entry["indirect_emissions"] = {}
        cn_code_entry["production_method"] = {}

        for key, value in ls_entry.items():
            if key.startswith("direct_emissions_"):
                new_key = key.replace("direct_emissions_", "")
                cn_code_entry["direct_emissions"][new_key] = value
            elif key.startswith("indirect_emissions_"):
                new_key = key.replace("indirect_emissions_", "")
                cn_code_entry["indirect_emissions"][new_key] = value
            elif key.startswith("production_method_"):
                new_key = key.replace("production_method_", "")
                cn_code_entry["production_method"][new_key] = value
            else:
                cn_code_entry[key] = value

        # calculate the SEE here for simplicity (not rounded to 7 digits yet)

        try:
            emission_factor = cn_code_entry["indirect_emissions"]["emission_factor"]

            electricity_consumed = cn_code_entry["indirect_emissions"]["electricity_consumed"]
            if isinstance(electricity_consumed, str) or isinstance(emission_factor, str):
                Log.error(
                    f"[Supplier <yellow>{installation_entry['installation']}</r>] Invalid value for electricity consumed or emission factor for CN-Code '<yellow>{cn_code}</r>' in supplier tool. Electricity consumed: '<yellow>{electricity_consumed}</r>', Emission factor: '<yellow>{emission_factor}</r>'",
                    title="supplier_tool | invalid value for electricity consumed or emission factor",
                )
            cn_code_entry["indirect_emissions"]["see"] = emission_factor * electricity_consumed

            # correct for the wrong DeterminationType from the Excel - this should be fixed elsewhere!

            dir_tod = cn_code_entry["direct_emissions"]["type_of_determination"]
            indir_tod = cn_code_entry["indirect_emissions"]["type_of_determination"]
            if indir_tod not in ["01", "02", "03"]:
                Log.error(
                    f"Invalid type of determination '<yellow>{indir_tod}</r>' for indirect emissions in supplier tool for CN-Code '<yellow>{cn_code}</r>'",
                    title="supplier_tool | invalid type of determination",
                )
            if dir_tod == "02":
                cn_code_entry["direct_emissions"]["type_of_determination"] = "01"
                Log.warning(
                    f"Read Determation Type 02 (=default value) from supplier tool for direct:type_of_det.('<yellow>{cn_code}</r>')\n→ Overwrite",
                    title="supplier_tool | type of determination 02",
                )

            indir_tod = cn_code_entry["indirect_emissions"]["type_of_determination"]
            if indir_tod not in ["01", "02", "03"]:
                Log.error(
                    f"Invalid type of determination '<yellow>{indir_tod}</r>' for indirect emissions in supplier tool for CN-Code '<yellow>{cn_code}</r>'",
                    title="supplier_tool | invalid type of determination",
                )
            if indir_tod == "02":
                cn_code_entry["indirect_emissions"]["type_of_determination"] = "01"
                Log.warning(
                    f"Read Determation Type 02 (=default value) from supplier tool for indirect:type_of_det.('<yellow>{cn_code}</r>')\n→ Overwrite",
                    title="supplier_tool | type of determination 02",
                )

            # set default value for source of emission factor if not given

            source_of_ef = cn_code_entry["indirect_emissions"]["source_of_emission_factor"]

            if source_of_ef == "01":
                source_of_efv = cn_code_entry["indirect_emissions"]["source_of_emission_factor_value"]
                default_val = "Der Wert wurde anhand der Herstellerangaben berechnet."

                if source_of_efv == "" or source_of_efv is None:
                    cn_code_entry["indirect_emissions"]["source_of_emission_factor_value"] = default_val
                    Log.warning(
                        f"No source of emission factor found for CN-Code '<yellow>{cn_code}</r>'\n→ Set to default value: '<yellow>{default_val}</r>'",
                        title="supplier_tool | source of emission factor",
                    )

            

            if dir_tod == "03" and (cn_code_entry["direct_emissions"]["additional_info"] == "" or cn_code_entry["direct_emissions"]["additional_info"] is None):
                Log.warning(
                    f"No additional information found for CN-Code '<yellow>{cn_code}</r>'\n→ Set to default value: '<yellow>-</r>'",
                    title="supplier_tool | additional info",
                )
                cn_code_entry["direct_emissions"]["additional_info"] = "-"
        
        except Exception as e:
            print("raw_data_ls:")
            pprint.pprint(raw_data_ls)
            Log.warning(
                f"Error while processing CN-Code '<yellow>{cn_code}</r>' in Supplier Tool\nAre the tables in the supplier tool set properly?: '<yellow>{e}</r>'",
                title="supplier_tool | error while processing CN-Code",
            )
            raise e

        supplier_tool_data[cn_code] = cn_code_entry

    # adding at the end, because otherwise I get weird errors

    installation_entry["emission_data"] = supplier_tool_data
