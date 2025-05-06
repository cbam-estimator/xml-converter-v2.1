"""TODOS and NOTES

* TODOS

- Something

* NOTES

- Something

"""

import pprint
import xml.etree.ElementTree as ET
import os
import xml.etree.ElementTree as ET
import base64
import re


from datetime import datetime
from .default_data import DefaultData
from .log import Log
from xml.dom.minidom import parseString
from .shared import shared_data
from .helper import r_float


def create_report(prepared_data, test_report=False):
    shared_data["current"]["summary"]["test_report"] = test_report

    root_dict = create_report_structure(prepared_data, test_report)
    xml_tree = create_xml(root_dict)
    # xml_tree.write("report.xml", encoding="utf-8", xml_declaration=True)

    return xml_tree


def post_process(xml_tree):
    "beautify, convert to string, round floats to 7 digits after comma, convert <group>None</group> to <group/>"

    # convert to string, beautify

    xml_str = ET.tostring(xml_tree.getroot(), encoding="unicode")
    parsed = parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent="  ")
    # Entfernen der automatisch hinzugefügten Deklaration
    declaration_removed = "\n".join(pretty_xml.split("\n")[1:])
    return declaration_removed

    return xml_tree


def create_xml(root_dict):
    ET.register_namespace("", "http://xmlns.ec.eu/BusinessObjects/CBAM/Types/V1")
    root = ET.Element("{http://xmlns.ec.eu/BusinessObjects/CBAM/Types/V1}QReport")
    add_elements(root, root_dict)
    return ET.ElementTree(root)


def add_elements(parent, input_dict):
    for key, val in input_dict.items():
        if isinstance(val, dict):
            # Erstelle ein neues Element für das verschachtelte Dictionary
            child = ET.SubElement(parent, key)
            add_elements(child, val)  # Rekursiver Aufruf für das verschachtelte Dictionary
        elif isinstance(val, list):
            # Erstelle ein neues Element für jedes Element in der Liste
            key = "".join(key.split("_")[1:])
            for element in val:
                child = ET.SubElement(parent, key)
                add_elements(child, element)
        elif isinstance(val, str) and val.startswith("binary_"):
            # Lade die Datei am Pfad x, wobei val "binary_x" ist
            filename = val[len("binary_") :]  # Extrahiere den Pfad x aus "binary_x"
            filename = os.path.join(shared_data["current"]["output_dir"], "temp", filename)
            try:
                with open(filename, "rb") as f:
                    binary_data = f.read()
                # Kodieren der Binärdaten in Base64
                encoded_data = base64.b64encode(binary_data).decode("utf-8")
                # Erstelle ein neues Element und setze den kodierten Inhalt
                child = ET.SubElement(parent, key)
                child.text = encoded_data
            except Exception as e:
                # Fehlerbehandlung, falls die Datei nicht gelesen werden kann
                # child = ET.SubElement(parent, key)
                # child.text = ""
                Log.error(f"Error reading binary file '{filename}': {e}")
        else:
            # Erstelle ein neues Element für den aktuellen Key-Value-Paar
            child = ET.SubElement(parent, key)
            if val is None:
                val = ""
            child.text = str(val)


def create_report_structure(prepared_data, test_report):
    root_dict = {}

    report_intro(root_dict, prepared_data, test_report)

    root_dict["ls_ImportedGood"] = []

    for index, (key, imported_good) in enumerate(prepared_data["imported_goods"].items()):
        imported_good["cn_code"] = key.split(";")[0]
        imported_good["country"] = key.split(";")[1]

        imported_good_dict = {}
        entry_imported_good(imported_good_dict, index, imported_good)
        root_dict["ls_ImportedGood"].append(imported_good_dict)

    return root_dict


def entry_imported_good(root, idx, imported_good):
    root["ItemNumber"] = str(idx + 1)

    cn_code = imported_good["cn_code"]
    cn_default_data = DefaultData.get("cn_code_default_values")[cn_code]
    good_description = cn_default_data["description_of_goods"]

    shared_current = shared_data["current"]
    if shared_current.get("report_type", None) == "indirect_representative":
        importer = imported_good["importer"]

        root["Importer"] = {
            "Name": importer["name"],
            "IdentificationNumber": importer["eori"],
            "ImporterAddress": {"Country": importer["country"], "City": importer["city"]},
        }

    root["CommodityCode"] = {
        "HsCode": cn_code[:-2],
        "CnCode": cn_code,
        "CommodityDetails": {"Description": good_description},
    }
    root["OriginCountry"] = {"Country": imported_good["country_of_origin"]}

    root["ls_ImportedQuantity"] = []

    # * ImportedQuantity / procedure

    overall_net_mass = 0
    overall_emissions = 0

    for idx_, (_, imported_quantity) in enumerate(imported_good["procedures"].items()):
        inward_processing_info = imported_quantity["inward_processing_information"]
        inward_processing = inward_processing_info is not None

        xd_imported_quantity = {}
        root["ls_ImportedQuantity"].append(xd_imported_quantity)

        xd_imported_quantity["SequenceNumber"] = str(idx_ + 1)
        xd_imported_quantity["Procedure"] = {
            "RequestedProc": imported_quantity["requested_procedure"],
            "PreviousProc": imported_quantity["previous_procedure"],
        }

        if inward_processing:
            discharge_bill_waiver = inward_processing_info["bill_of_discharge_waiver"]

            # standard value discharge waiver is 0
            if discharge_bill_waiver is None or discharge_bill_waiver == "":
                discharge_bill_waiver = "0"

            xd_imported_quantity["Procedure"]["InwardProcessingInfo"] = {
                "MemberStateAuth": inward_processing_info["member_state_of_authorization"],
                "DischargeBillWaiver": discharge_bill_waiver,
                "Authorisation": inward_processing_info["authorization"],
                "StartTime": inward_processing_info["start_date"],
                "EndTime": inward_processing_info["end_date"],
                "Deadline": inward_processing_info["deadline"],
            }

        xd_imported_quantity["ImportArea"] = {"ImportArea": "EU"}

        # * 1 or 2 entries of MeasureProcedureImported (processed vs. not processed)

        xd_imported_quantity["ls_MeasureProcedureImported"] = []

        if inward_processing_info is None:
            net_mass_not_processed = imported_quantity["net_mass"]
            net_mass_processed = 0

        else:
            net_mass_not_processed = r_float(inward_processing_info["not_processed"])
            net_mass_processed = r_float(inward_processing_info["already_processed"])

            total_net_mass = r_float(imported_quantity["net_mass"])

            tolerance = 1e-8    # necessary because of float precision
            if abs(net_mass_not_processed + net_mass_processed - total_net_mass) > tolerance:
                Log.error(f"[entry_reported_good] Net masses not matching: {net_mass_not_processed} + {net_mass_processed} != {imported_quantity['net_mass']}")

        # TODO : Check if this is on correct level!

        if net_mass_not_processed != 0:
            mpi = {}
            mpi["Indicator"] = "0"
            mpi["NetMass"] = r_float(net_mass_not_processed, return_string=True)
            mpi["MeasurementUnit"] = "01"
            xd_imported_quantity["ls_MeasureProcedureImported"].append(mpi)

        if net_mass_processed != 0:
            mpi = {}
            mpi["Indicator"] = "1"
            mpi["NetMass"] = r_float(net_mass_processed, return_string=True)
            mpi["MeasurementUnit"] = "01"
            xd_imported_quantity["ls_MeasureProcedureImported"].append(mpi)

        xd_imported_quantity["SpecialReferences"] = {
            "AdditionalInformation": "-",
        }

    # ende : ImportedQuantity

    root["MeasureImported"] = {
        "NetMass": r_float(imported_good["total_net_mass"], return_string=True),
        "MeasurementUnit": "01",
    }

    shared_summary = shared_data["current"].setdefault("summary", {})
    if not shared_summary["test_report"]:
        shared_summary["total_net_mass"] = shared_summary.get("total_net_mass", 0) + imported_good["total_net_mass"]

    cn_code_default_data = DefaultData.get("cn_code_default_values")[cn_code]
    # see_direct = cn_code_default_data["see_direct"]
    # see_indirect = cn_code_default_data["see_indirect"]
    # emissions_per_unit = see_direct + see_indirect

    # Add keys here for right order
    root["TotalEmissions"] = {
        "EmissionsPerUnit": None,
        "OverallEmissions": None,
        "TotalDirect": None,
        "TotalIndirect": None,
        "MeasurementUnit": "EMU1",
    }

    root["Remarks"] = {
        "AdditionalInformation": "No Remarks",
    }

    # * GoodsEmissions / Installations

    root["ls_GoodsEmissions"] = []

    overall_emissions = 0
    total_direct = 0
    total_indirect = 0

    for idx_, (key, goods_emission) in enumerate(imported_good["goods_emissions"].items()):
        xd_goods_emissions = {}
        root["ls_GoodsEmissions"].append(xd_goods_emissions)

        xd_goods_emissions["SequenceNumber"] = str(idx_ + 1)
        
        xd_goods_emissions["ProductionCountry"] = goods_emission["country_of_production"]

        operator = goods_emission["operator"]
        installation = goods_emission["installation"]

        def strip_index_suffix(name):
            # Entfernt "_i_<Zahl>" am Ende des Strings
            return re.sub(r'_i_\d+$', '', name)

        parts = operator['operator_name'].split("_")
        if len(parts) >= 3 and parts[1] == "i":
            try:
                int(parts[2])
                # remove _i_x
                operator['operator_name'] = strip_index_suffix(operator['operator_name'])
            except ValueError:
                pass

        if installation is not None:
            parts = installation['installation_name'].split("_")
            if len(parts) >= 3 and parts[1] == "i":
                try:
                    int(parts[2])
                    # remove _i_x
                    installation['installation_name'] = strip_index_suffix(installation['installation_name'])
                except ValueError:
                    pass
        

        if operator is not None and len(operator) > 70:
                raise ValueError(f"Operator name too long (>70): {operator['operator_name']}")
        
        if installation is not None and len(installation) > 70:
                raise ValueError(f"Installation name too long (>70): {operator['operator_name']}")

        # if installation is not None and operator["operator_name"].startswith("dummy"):     ### Question about Zwischenhändler
        if operator["operator_name"].startswith("dummy"):
            Log.warning(f"[entry_imported_good] Operator name starts with 'dummy' → Not setting operator data")
        else:
            xd_goods_emissions["InstallationOperator"] = {
                "OperatorId": "-",
                "OperatorName": operator["operator_name"],
                "OperatorAddress": {
                    "Country": operator["operator_country"],
                    "SubDivision": None,
                    "City": operator["operator_city"],
                    "Street": operator["operator_street"],
                    "StreetAdditionalLine": operator["operator_street_additional_line"],
                    "Number": operator["operator_street_number"],
                    "Postcode": operator["operator_postcode"],
                    "POBox": None,
                },
                "ContactDetails": {
                    "Name": operator["operator_contact_person"],
                    "Phone": operator["operator_phone"],
                    "Email": operator["operator_email"],
                },
            }
            

            if installation is None:
                # if no installation is provided, use operator data
                installation = {}
                for key in operator.keys():
                    insta_key = key.replace("operator", "installation")
                    installation[insta_key] = operator[key]

            xd_goods_emissions["Installation"] = {
                "InstallationId": "-",
                "InstallationName": installation["installation_name"],
                "Address": {
                    "EstablishmentCountry": installation["installation_country"],
                    "SubDivision": None,
                    "City": installation["installation_city"],
                    "Street": installation["installation_street"],
                    "StreetAdditionalLine": installation["installation_street_additional_line"],
                    "Number": installation["installation_street_number"],
                    "Postcode": installation["installation_postcode"],
                    "POBox": None,
                    "PlotParcelNumber": None,
                    "Latitude": None,
                    "Longitude": None,
                    "CoordinatesType": None,
                },
            }

        direct_emissions = goods_emission["direct_emissions"]
        indirect_emissions = goods_emission["indirect_emissions"]

        inst_netmass = r_float(goods_emission["net_mass"])

        see_direct = r_float(direct_emissions["SpecificEmbeddedEmissions"])

        emission_factor = r_float(indirect_emissions["EmissionFactor"], round_to=5)
        electricity_consumed = r_float(indirect_emissions["ElectricityConsumed"], round_to=2)

        if emission_factor is not None:  # not with default values
            see_indirect = r_float(emission_factor * electricity_consumed)
        else:
            see_indirect = r_float(indirect_emissions["SpecificEmbeddedEmissions"])


        ## PLAUSUILITY CHECK -> Move to somewhere else!

        if see_direct > 35.0:
            Log.error(f"[entry_imported_good] see_direct > 35: {see_direct}")

        if see_indirect > 35.0:
            Log.error(f"[entry_imported_good] see_direct > 35: {see_indirect}")

        ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## ## 

        emissions_per_unit = r_float(see_direct) + r_float(see_indirect)

        inst_overall_emissions = r_float(inst_netmass * emissions_per_unit)
        inst_total_direct = r_float(inst_netmass * see_direct)
        inst_total_indirect = r_float(inst_netmass * see_indirect)

        overall_emissions += r_float(inst_overall_emissions)
        total_direct += r_float(inst_total_direct)
        total_indirect += r_float(inst_total_indirect)

        xd_goods_emissions["ProducedMeasure"] = {
            "NetMass": r_float(inst_netmass, return_string=True),
            "MeasurementUnit": "01",
        }

        xd_goods_emissions["InstallationEmissions"] = {
            "OverallEmissions": r_float(inst_overall_emissions, return_string=True),
            "TotalDirect": r_float(inst_total_direct, return_string=True),
            "TotalIndirect": r_float(inst_total_indirect, return_string=True),
            "MeasurementUnit": "EMU1",
        }

        xd_goods_emissions["DirectEmissions"] = {
            "DeterminationType": direct_emissions["DeterminationType"],
            "ApplicableReportingTypeMethodology": direct_emissions["ApplicableReportingTypeMethodology"],  # Comission Rules / Other Methods / Default
            "ApplicableReportingMethodology": direct_emissions["ApplicableReportingMethodology"],
            "SpecificEmbeddedEmissions": see_direct,
            "MeasurementUnit": "EMU1",  # default value always EMU1 = tonnes
        }

        xd_goods_emissions["IndirectEmissions"] = {
            "DeterminationType": indirect_emissions["DeterminationType"],
            "SpecificEmbeddedEmissions": see_indirect,
            "MeasurementUnit": "EMU1",  # default value always EMU1 = tonnes
            "ElectricitySource": indirect_emissions["ElectricitySource"],
            "OtherSourceIndication": indirect_emissions["OtherSourceIndication"],
            "EmissionFactorSource": indirect_emissions["EmissionFactorSource"],
            "ElectricityConsumed": r_float(electricity_consumed, round_to=2, return_string=True),
            "EmissionFactor": r_float(emission_factor, round_to=5, return_string=True),
            "EmissionFactorSourceValue": indirect_emissions["EmissionFactorSourceValue"],
        }

        # TODO: this has to be a list! Dict must be restructured ...

        method_id = list(goods_emission["production_method"].keys())[0]

        if method_id is not None and len(method_id) > 0:

            

            xd_goods_emissions["ProdMethodQualifyingParams"] = {
                "SequenceNumber": "1",
                "MethodId": method_id,
                "MethodName": goods_emission["production_method_name"],
            }
        else:
            Log.warning(f"[entry_imported_good] NO PRODUCTION METHOD PROVIDED for goods emission {idx_ + 1} of imported good {idx + 1}")

        # * Supporting Documents

        if goods_emission.get("supporting_documents", None) is not None:
            xd_goods_emissions["ls_SupportingDocuments"] = goods_emission["supporting_documents"]

    #     """ structure dump
    #     0..99	 ------Supporting Documents (for emissions definition)	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments
    # 1..1	Sequence number	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\SequenceNumber	n..5
    # 1..1	Type of emissions document	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Type	an..5
    # 0..1	Country of document issuance	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Country	a2
    # 1..1	Reference number	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\ReferenceNumber	an..70
    # 0..1	Document line item number	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\LineItemNumber	n..5
    # 0..1	Issuing authority name	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\IssuingAuthName	an..70
    # 0..1	Validity start date	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\ValidityStartDate	an10
    # 0..1	Validity end date	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\ValidityEndDate	an10
    # 0..1	Description	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Description	an..256
    # 0..1	 --------Attachments	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Attachment
    # 1..1	Filename	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Attachment\Filename	an..256
    # 0..1	URI	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Attachment\URI	an..2048
    # 1..1	MIME	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Attachment\MIME	an..70
    # 1..1	Included binary object	Qreport\ImportedGood\GoodsEmissions\SupportingDocuments\Attachment\Binary	binary
    #     """

    netmass = imported_good["total_net_mass"]
    emissions_per_unit = overall_emissions / netmass
    root["TotalEmissions"]["EmissionsPerUnit"] = r_float(emissions_per_unit, return_string=True)
    root["TotalEmissions"]["OverallEmissions"] = r_float(overall_emissions, return_string=True)
    root["TotalEmissions"]["TotalDirect"] = r_float(total_direct, return_string=True)
    root["TotalEmissions"]["TotalIndirect"] = r_float(total_indirect, return_string=True)

    if not shared_summary["test_report"]:
        shared_summary["total_emissions"] = shared_summary.get("total_emissions", 0) + overall_emissions


def report_intro(root, prepared_data, test_report):
    options = DefaultData.get("options")

    date_and_time = datetime.now().strftime("%Y-%m-%dT00:00:00Z")

    creation_time_opt = options.get("report_creation_time")
    if creation_time_opt != "default":
        try:
            date_and_time = datetime.strptime(creation_time_opt, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%dT00:00:00Z")
        except Exception as e:
            Log.warning(f"[prologue] Invalid creation date specified in config: {creation_time_opt} != 'default'\n → Using default\nError: {e}")

    general_info = prepared_data["general_info"]

    root["SubmissionDate"] = date_and_time
    root["ReportId"] = None
    root["ReportingPeriod"] = "Q" + general_info["quarter"]
    root["Year"] = general_info["year"]

    importer_adress = {
        "Country": general_info["importer_country"],
        "SubDivision": None,
        "City": general_info["importer_city"],
        "Street": general_info["importer_street"],
        "StreetAdditionalLine": general_info["importer_address_addition"],
        "Number": general_info["importer_street_number"],
        "Postcode": general_info["importer_postcode"],
        "POBox": None,
    }

    def declarant():
        root = {}
        if test_report:
            root["Name"] = f"TEST:{prepared_data["general_info"]["importer_name"]}"

            cest_eori = DefaultData.get("report_default_values")["Declarant.IdentificationNumber"]
            root["IdentificationNumber"] = cest_eori

        else:
            root["Name"] = prepared_data["general_info"]["importer_name"]

            root["IdentificationNumber"] = prepared_data["general_info"]["importer_eori"]

        # 01 = Importer for All Goods /
        # 02 = Indirect Customs Representative for All Goods /
        # 03 = Importer for Some Goods / Indirect Customs Representative for Some Goods
        if shared_data["current"].get("report_type", None) == "indirect_representative":
            root["Role"] = "02"
        else:
            root["Role"] = "01"
        # todo: for ind. repr. obtain if state is 01 or 02 depending on wether the master file is empty and set in shared

        root["ActorAddress"] = importer_adress
        return root

    def importer_representative(entry_type="importer"):
        if entry_type == "importer":
            desc = "Importer"
        elif entry_type == "representative":
            desc = "Representative"
        else:
            Log.error(f"[importer_representative] Invalid type: {entry_type}")

        root = {}
        general_info = prepared_data["general_info"]

        root["Name"] = general_info["importer_name"]

        config = shared_data["current"]["config"]
        if test_report and not config["options"]["set_customer_eori_as_importer_eori"]:
            cest_eori = DefaultData.get("report_default_values")["Declarant.IdentificationNumber"]
            root["IdentificationNumber"] = cest_eori

        else:
            root["IdentificationNumber"] = general_info["importer_eori"]

        root[f"{desc}Address"] = importer_adress
        return root

    def national_competent_auth():
        root = {}
        if test_report:
            root["ReferenceNumber"] = "DE000004"
        elif general_info["importer_country"] == "DE":
            root["ReferenceNumber"] = "DE000004"
        elif general_info["importer_country"] == "AT":
            root["ReferenceNumber"] = "DE000004"
        elif general_info["importer_country"] == "FR":
            root["ReferenceNumber"] = "FR000001"
        else:
            Log.error(f"[national_competent_auth] NathCompAuths other then FR, DE and AT not supporter yet. Customer country: '{general_info['importer_country']}")
        return root

    def signatures():
        date_str8 = date_and_time[:10].replace("-", "")

        root = {}
        root["ReportConfirmation"] = {
            "GlobalDataConfirmation": 1,
            "UseOfDataConfirmation": 1,
            # "SignatureDate": date_str8,
            "SignaturePlace": general_info["importer_city"],
            "Signature": general_info["importer_contact_person"],
            "PositionOfPersonSending": general_info["importer_contact_person_position"],
        }

        # todo : conditional: only real data period
        root["ApplicableMethodologyConfirmation"] = {"OtherApplicableReportingMethodology": 1}
        return root

    root["Declarant"] = declarant()

    if shared_data["current"].get("report_type", None) == "indirect_representative":
        root["Representative"] = importer_representative("representative")
    else:
        root["Importer"] = importer_representative()

    root["NationalCompetentAuth"] = national_competent_auth()
    root["Signatures"] = signatures()
