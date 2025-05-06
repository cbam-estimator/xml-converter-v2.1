import pprint
import datetime
import os

from .helper import is_null_value, r_float
from .log import Log
from .default_data import DefaultData
from .validator import Validator
from .supplier_data import get_supplier_data
from .installation_data import get_installation_data
from .shared import shared_data


def prepare_data(customer_dict_ls, config):
    """
    This functions groups and aggregates the data in the proper way and calculates emissions values.

    """

    prepared_data_dict = {}

    # for indirect representative general info is created on the first file, operators and installations are aggregated

    create_general_info_dict(customer_dict_ls[0], prepared_data_dict)

    for customer_dict in customer_dict_ls:
        create_operator_dict(customer_dict, prepared_data_dict)

        installation_data = get_installation_data(config, prepared_data_dict, customer_dict)

        create_installations_dict(customer_dict, prepared_data_dict)

    create_imported_goods(customer_dict_ls, prepared_data_dict)

    ## > imported goods/procedures

    create_procedures(customer_dict, prepared_data_dict)

    ## > imported goods/GoodsEmissions

    create_goods_emissions(customer_dict, prepared_data_dict, installation_data, config)

    return prepared_data_dict


def create_general_info_dict(customer_dict, prepared_data_dict):
    sheet_general_info = customer_dict["Allgemeine_Informationen"]

    table_general_info = sheet_general_info["general_information"]
    table_quarter = sheet_general_info["quarter"]

    general_info_dict = {**table_general_info[0], **table_quarter[0]}
    del general_info_dict["pk_index"]

    shared_summary = shared_data["current"].setdefault("summary", {})

    shared_summary["year"] = general_info_dict["year"]
    shared_summary["quarter"] = general_info_dict["quarter"]
    shared_summary["importer_eori"] = general_info_dict["importer_eori"]
    shared_summary["importer_name"] = general_info_dict["importer_name"]

    prepared_data_dict["general_info"] = general_info_dict


def create_goods_emissions(customer_dict, prepared_data_dict, installation_data, config):
    imported_goods = prepared_data_dict["imported_goods"]

    report_year = prepared_data_dict["general_info"]["year"]
    report_quarter = prepared_data_dict["general_info"]["quarter"]

    for ig_key, imported_good in imported_goods.items():
        cn_code = ig_key.split(";")[0]
        country = ig_key.split(";")[1]

        raw_entries = imported_good["raw_entries"]

        goods_emission = {}

        for entry in raw_entries:
            installation = entry["det_installation"]
            operator = entry["det_operator"]

            if installation is not None:
                io_key = installation["installation_name"]
            else:
                io_key = operator["operator_name"]

            if " - " not in entry["production_method"]:
                production_method = entry["production_method"]
                production_method_name = "-"
            else:
                production_method, production_method_name = entry["production_method"].split(" - ")

            if io_key not in goods_emission:
                # iterates over all installations/ operator entries

                installation_name = io_key

                fix_determination_type = installation_data.get("fix_type_of_determination", None)  # todo : rename and restructure

                cn_code_emission_data = None

                if fix_determination_type == "02":  # default value report
                    inst_determination_type = "02"

                    cn_code_emission_data = default_emission_data(cn_code)

                elif fix_determination_type == "03":  # full zero report, without documentation
                    installation_data_entry = installation_data["default"]
                    cn_code_emission_data = installation_data_entry["emission_data"]["default"]

                    if "default_supporting_documents" in installation_data:
                        installation_data_entry["supporting_documents"] = installation_data["default_supporting_documents"]

                else:
                    # find the supplier/ default data set for the given installation
                    ## todo: this must support non exact matches as well
                    installation_data_entry = installation_data[installation_name]
                    inst_determination_type = installation_data_entry["type_of_determination"]

                    emission_data = installation_data_entry["emission_data"]

                    # select cn code specific data if det_type is 01
                    if inst_determination_type == "03":  # zero report
                        cn_code_emission_data = emission_data["default"]
                    elif inst_determination_type == "01":  # real data
                        if cn_code not in emission_data:
                            pprint.pprint(emission_data)
                            print(f"CN code: {cn_code}, cn code data type: {type(cn_code)}, emission data snd key: {list(emission_data.keys())[1]}, emission data first key type: {type(list(emission_data.keys())[0])}, emission data first key: {list(emission_data.keys())[0]}, emission data snd key type: {type(list(emission_data.keys())[1])}")
                            Log.error(
                                f"CN code <yellow>{cn_code}</r> from customer data not found in supplier data (using det_type {inst_determination_type})\n. Installation: {installation_name}",
                                title="Missing CN Code in Supplier Data",
                            )
                        cn_code_emission_data = emission_data[cn_code]

                ## direct

                direct_emissions_data = cn_code_emission_data["direct_emissions"]
                indirect_emissions_data = cn_code_emission_data["indirect_emissions"]
                applicable_reporting_type_methodology = direct_emissions_data["reporting_methodology"]
                see_direct = direct_emissions_data["see"]
                see_indirect = indirect_emissions_data["see"]

                net_mass = entry["net_mass"]

                direct_tod = direct_emissions_data["type_of_determination"]
                indirect_tod = indirect_emissions_data["type_of_determination"]

                # Todo : Take a look on production method; should be compared with supplier data

                # general

                goods_emission[io_key] = {
                    "operator": operator,
                    "installation": installation,
                    "net_mass": net_mass,
                    "production_method": {production_method: None},
                    "production_method_name": production_method_name,
                    "applicable_reporting_type_methodology": applicable_reporting_type_methodology,
                    "country_of_production": entry["country_of_production"],
                }

                # direct emissions

                goods_emission[io_key]["direct_emissions"] = {
                    "DeterminationType": direct_emissions_data["type_of_determination"],
                    "ApplicableReportingTypeMethodology": direct_emissions_data["reporting_methodology"],
                    "ApplicableReportingMethodology": direct_emissions_data["additional_info"],
                    "SpecificEmbeddedEmissions": see_direct,
                }

                # indirect emissions

                goods_emission[io_key]["indirect_emissions"] = {
                    "DeterminationType": indirect_emissions_data["type_of_determination"],
                    "SpecificEmbeddedEmissions": see_indirect,  # not necessary here, is calculated later on
                    "ElectricitySource": indirect_emissions_data["source_of_electricity"],
                    "OtherSourceIndication": indirect_emissions_data["other_source_indication"],
                    "EmissionFactorSource": indirect_emissions_data["source_of_emission_factor"],
                    "ElectricityConsumed": indirect_emissions_data["electricity_consumed"],
                    "EmissionFactor": indirect_emissions_data["emission_factor"],
                    "EmissionFactorSourceValue": indirect_emissions_data["source_of_emission_factor_value"],
                }

                # production_method

                # todo : implement this

                ## SupportingDocuments

                if fix_determination_type != "02" and (indirect_tod == "03" or direct_tod == "03"):
                    goods_emission[io_key]["supporting_documents"] = create_supporting_documents(
                        installation_data_entry, cn_code, installation, operator, prepared_data_dict["general_info"], config
                    )

                    # dirty quick fix, does not work with multiple documents
                    additional_info = goods_emission[io_key]["direct_emissions"]["ApplicableReportingMethodology"]
                    if additional_info is not None and "<template>" in additional_info:
                        doc_name = goods_emission[io_key]["supporting_documents"][0]["Attachment"]["Filename"]
                        additional_info = additional_info.replace("<template>", doc_name)
                        goods_emission[io_key]["direct_emissions"]["ApplicableReportingMethodology"] = additional_info

                    Log.info(
                        f"Supporting documents for {io_key}:\n{goods_emission[io_key]['supporting_documents']}",
                    )
                else:
                    Log.info(
                        f"determination type {inst_determination_type} for {io_key} does not require supporting documents"
                    )

            else:
                # aggregate masses
                goods_emission[io_key]["net_mass"] += entry["net_mass"]
                # add production method
                goods_emission[io_key]["production_method"][production_method] = None

        num_goods_emission = len(goods_emission)
        shared_summary = shared_data["current"].setdefault("summary", {})
        shared_summary_num_goods_emission = shared_summary.setdefault("num_goods_emission", 0)
        shared_summary["num_goods_emission"] = shared_summary_num_goods_emission + num_goods_emission

        imported_good["goods_emissions"] = goods_emission


def create_supporting_documents(installation_data_entry, cn_code, installation, operator, general_info, config):
    "Must return a dict for supporting documents, structured like the report xml"

    def create_attachment(doc):
        basename = doc.split("/")[-1]

        shared_sup_docs = shared_data["current"].setdefault("supporting_documents", {})
        document_index = shared_sup_docs.setdefault(basename, 0)
        document_index += 1
        shared_sup_docs[basename] = document_index

        data_type = basename.split(".")[-1]
        filename = f"{basename[:-len(data_type) - 1]}_{document_index}.{data_type}"
        # Dictionary mit MIME-Typen
        mime_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

        # Hole den MIME-Typ aus dem Dictionary oder setze einen Standardwert
        mime_type = mime_types.get(data_type.lower(), None)

        if mime_type is None:
            Log.error(f"Unsupported MIME type for document {doc}", title="Unsupported MIME type", raiseErrorDebug=False)

        # Baue den URI (Pfad zur Datei)
        # Hier solltest du den tatsächlichen Pfad zu deinen Dokumenten angeben

        attachment = {
            "Filename": filename,
            # "URI": uri,
            "MIME": mime_type,
            "Binary": f"binary_{doc}",
        }

        return attachment

    # empty list if no supporting documents are available
    supporting_doc_ls = installation_data_entry.get("supporting_documents", [])
    

    return_ls = []

    for index, doc in enumerate(supporting_doc_ls):
        # determine the global index of the document

        if doc == "<template>":
            doc = create_doc_pdf(installation_data_entry, cn_code, installation, operator, general_info, config)

        entry = {
            "SequenceNumber": str(index + 1),
            "Type": "TED05",
            "ReferenceNumber": str(index),
            "Attachment": create_attachment(doc),
        }
        return_ls.append(entry)

    return return_ls


def create_doc_pdf(installation_data_entry, cn_code, installation, operator, general_info, config):
    import datetime
    import os
    import io
    from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName, PdfObject, PageMerge
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    import textwrap

    template_file_path = config["supplier_workflow"]["doc_template_file"]
    template_signature_name = config["supplier_workflow"]["doc_signature_name"]

    # Get the current date in the format dd.mm.yyyy
    date = datetime.datetime.now().strftime("%d.%m.%Y")

    # Collect supplier (hersteller) information
    supplier_name = operator["operator_name"] if operator is not None else installation["installation_name"]
    supplier_country = operator["operator_country"] if operator is not None else installation["installation_country"]
    supplier_contact_person = operator["operator_contact_person"] if operator is not None else installation["installation_contact_person"]
    supplier_email = operator["operator_email"] if operator is not None else installation["installation_email"]

    # Collect declarant (deklarant) information
    declarant_name = general_info["importer_name"]
    declarant_eori = general_info["importer_eori"]
    declarant_contact_person = general_info["importer_contact_person"]
    declarant_email = "-"  # this is missing in the general info

    # Create the file path
    output_dir = shared_data["current"]["output_dir"]
    output_dir = os.path.join(output_dir, "temp")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    sanitized_supplier_name = supplier_name.replace(" ", "_").replace("/", "_")
    file_path = os.path.join(output_dir, f"doc_{cn_code}_{sanitized_supplier_name}_{date}.pdf")

    # Prepare the form data dictionary
    form_data = {
        "deklarant_name": declarant_name,
        "deklarant_EORI": declarant_eori,
        "deklarant_kontaktperson": declarant_contact_person,
        "deklarant_kontaktperson_mail": supplier_email,  # quick fix, fields are swapped
        "hersteller_name": supplier_name,
        "hersteller_land": supplier_country,
        "hersteller_kontaktperson": supplier_contact_person,
        "hersteller_kontaktperson_mail": declarant_email,  # quick fix, fields are swapped
        "cn_codes": cn_code,
        "signature_name": template_signature_name,
        "signature_date": date,
    }

    num_comm_attempts = 8

    # Handle the fields that have multiple entries (DatumX, Grund des ScheiternsX, AnmerkungenX)
    for i in range(1, num_comm_attempts + 1):
        # Construct the keys for the installation_data_entry dictionary
        date_key = f"date of attempt {i}"
        remarks_dropdown_key = f"remarks dropdown {i}"  # Corresponds to "Grund des ScheiternsX"
        remarks_key = f"remarks {i}"  # Corresponds to "AnmerkungenX"

        # Get the date of the attempt if it exists
        if date_key in installation_data_entry and installation_data_entry[date_key]:
            # Format the date if it's a datetime object
            attempt_date = (
                installation_data_entry[date_key].strftime("%d.%m.%Y")
                if isinstance(installation_data_entry[date_key], datetime.datetime)
                else str(installation_data_entry[date_key])
            )
            form_data[f"Datum{i}"] = attempt_date
        else:
            form_data[f"Datum{i}"] = ""

        # Get the "Grund des Scheiterns" (reason for failure) if it exists
        if remarks_dropdown_key in installation_data_entry and installation_data_entry[remarks_dropdown_key]:
            form_data[f"Grund des Scheiterns{i}"] = installation_data_entry[remarks_dropdown_key]
        else:
            form_data[f"Grund des Scheiterns{i}"] = ""

        # Get the "Anmerkungen" (remarks) if it exists
        if remarks_key in installation_data_entry and installation_data_entry[remarks_key]:
            form_data[f"Anmerkungen{i}"] = installation_data_entry[remarks_key]
        else:
            form_data[f"Anmerkungen{i}"] = ""

    # Function to fill the PDF form
    def fill_pdf(input_pdf_path, output_pdf_path, data_dict):
        import io
        from pdfrw import PdfReader, PdfWriter, PdfDict, PageMerge
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        import textwrap

        # === Text Properties (Adjust as Needed) ===
        text_alignment = "top-left"  # Alignment: 'top-left' (currently only this option)
        font_size = 7  # Smaller font size
        wrap_at_chars = 38  # Wrap text after 50 characters
        truncate_after_chars = 38 * 4  # Truncate text after 200 characters

        # Load the PDF template
        template_pdf = PdfReader(input_pdf_path)

        # Create a list to hold pages with updated content
        updated_pages = []

        for page_num, page in enumerate(template_pdf.pages):
            annotations = page.Annots
            if annotations:
                # Create a canvas to draw the text
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=(float(page.MediaBox[2]), float(page.MediaBox[3])))

                for annotation in annotations:
                    if annotation.Subtype == "/Widget" and annotation.T:
                        # Extract the field name
                        field_name = annotation.T[1:-1]  # Remove parentheses
                        if field_name in data_dict:
                            value = data_dict[field_name]
                            # Apply truncation
                            if len(value) > truncate_after_chars:
                                value = value[:truncate_after_chars]
                            # Apply line wrapping
                            lines = textwrap.wrap(value, width=wrap_at_chars)
                            # Get the field rectangle
                            rect = [float(x) for x in annotation.Rect]
                            x1, y1, x2, y2 = rect
                            # Calculate field width and height
                            field_width = x2 - x1
                            field_height = y2 - y1
                            # Set the text position
                            text_x = x1
                            text_y = y2 - font_size  # Align to top-left
                            # Draw the text onto the canvas
                            can.setFont("Helvetica", font_size)
                            line_height = font_size * 1.2  # Line spacing
                            for line in lines:
                                can.drawString(text_x, text_y, line)
                                text_y -= line_height
                                if text_y < y1:
                                    break  # Stop if we reach the bottom of the field
                # Finalize the canvas
                can.save()
                packet.seek(0)
                # Merge the canvas onto the page
                new_pdf = PdfReader(packet)
                overlay = PageMerge(new_pdf.pages[0]).render()
                PageMerge(page).add(overlay).render()
                # Remove form fields
                page.Annots = []
            # Add the updated page to the list
            updated_pages.append(page)

        # Write the updated pages to the output PDF
        writer = PdfWriter()
        writer.addpages(updated_pages)
        writer.write(output_pdf_path)

    # Call the fill_pdf function with the template and output file paths
    fill_pdf(template_file_path, file_path, form_data)

    return file_path


def default_emission_data(cn_code):
    # use of default values

    cn_code_def_vals = DefaultData.get("cn_code_default_values")
    default_data = cn_code_def_vals[cn_code]

    cn_code_emission_data = {
        "direct_emissions": {
            "type_of_determination": "02",
            "reporting_methodology": "TOM03",
            "additional_info": None,
            "see": default_data["see_direct"],
        },
        "indirect_emissions": {
            "type_of_determination": "02",
            "see": default_data["see_indirect"],
            "source_of_electricity": "SOE03",
            "other_source_indication": "'Received from the grid' wurde ausgewählt weil Feld verpflichtend ist. Eigentlich ist die Information nicht verfügbar weil Defaultwerte genutzt werden.",
            "electricity_consumed": None,
            "emission_factor": None,
            "source_of_emission_factor": None,
            "source_of_emission_factor_value": None,
        },
    }

    return cn_code_emission_data


def determine_supplier_data(
    determination_type,
    general_info,
    cn_code,
    operator=None,
    installation=None,
    config=None,
):
    # determination type 01: Actual Data
    # determination type 02: Estimated values including default values made available and published by the Commission

    if determination_type == "01":
        if operator is None or config is None:
            Log.error(
                f"Operator or config is missing for determination type 01.",
                title="Error",
            )

        supplier_data = get_supplier_data(cn_code, general_info, operator, installation, config)
        return supplier_data

    elif determination_type == "02":
        # use of default values

        cn_code_def_vals = DefaultData.get("cn_code_default_values")

        default_supplier_data = cn_code_def_vals[cn_code]

        return default_supplier_data
    else:
        raise ValueError(f"Unkown determination type {determination_type} for emission values.")


def create_operator_dict(customer_dict, prepared_data_dict):
    sheet_operator = customer_dict["Ihre_Hersteller_Liste"]
    table_operator = sheet_operator["operator_list"]

    operator_dict = {}

    for operator_entry in table_operator:
        operator_name = operator_entry["operator_name"]
        if operator_name in operator_dict:
            Log.error(f"[prepare data] Duplicate operator name {operator_name} in {operator_entry}")
        else:
            operator_dict[operator_name] = operator_entry

    shared_summary = shared_data["current"].setdefault("summary", {})
    shared_summary["num_operators"] = len(operator_dict)

    # this dict key is named faulty, should be operator_dict
    # keep the values already present in the dict for indirect representative
    prepared_data_dict["importer_dict"] = {**prepared_data_dict.get("importer_dict", {}), **operator_dict}


def create_installations_dict(customer_dict, prepared_data_dict):
    sheet_installations = customer_dict.get("Produktions_Standorte_Liste", {})
    table_installations = sheet_installations.get("installations", {})
    importer_dict = prepared_data_dict["importer_dict"]

    installations_dict = {}

    for installation_entry in table_installations:
        installation_name = installation_entry["installation_name"]
        if installation_name in installations_dict:
            Log.error(f"[prepare data] Duplicate installation name {installation_name} in {installation_entry}")
        elif installation_name in importer_dict:
            Log.error(f"[prepare data] Installation name {installation_name} is already used as importer name in {installation_entry}")
        else:
            installations_dict[installation_name] = installation_entry

    shared_summary = shared_data["current"].setdefault("summary", {})
    shared_summary["num_installations"] = len(installations_dict)

    # keep the values already existing for indirect representative
    prepared_data_dict["installations_dict"] = {**prepared_data_dict.get("installations_dict", {}), **installations_dict}


def create_imported_goods(customer_dict_ls, prepared_data_dict):
    imported_goods = {}
    importer_dict = prepared_data_dict["importer_dict"]
    installations_dict = prepared_data_dict.get("installations_dict", {})

    indirect_representative_report = len(customer_dict_ls) > 1

    for customer_dict in customer_dict_ls:
        sheet_cn_codes = customer_dict["Angaben_zu_Warenmengen"]
        table_cn_codes = sheet_cn_codes["table_imported_goods"]
        importer_entry = customer_dict["Allgemeine_Informationen"]["general_information"][0]
        importer_name = importer_entry["importer_name"]
        importer_eori = importer_entry["importer_eori"]
        importer_country = importer_entry["importer_country"]
        importer_city = importer_entry["importer_city"]

        for entry in table_cn_codes:
            # determine importer in order to determine country code

            operator_or_installation = entry["operator_or_installation"]

            operator = None
            installation = None

            if operator_or_installation in installations_dict:
                installation = installations_dict[operator_or_installation]
                operator = importer_dict[installation["installation_operator_name"]]
            elif operator_or_installation in importer_dict:
                installation = None
                operator = importer_dict[operator_or_installation]
            else:
                try:
                    installation_name = operator_or_installation.split("(")[0][:-1]
                    installation = installations_dict[installation_name]
                    operator = importer_dict[installation["installation_operator_name"]]
                except Exception:
                    Log.error(
                        f"[prepare data] Could not determine importer/ installation for 'Warenmengen' entry with \nOperator/ Installation: '<yellow>{operator_or_installation}</r>'\n\n entry: {pprint.pformat(entry)}\n\n importer_dict: {pprint.pformat(importer_dict)}",
                        title="operator/ installation mismatch in customer data",
                    )

            if "country_of_origin" not in entry or entry["country_of_origin"] is None or entry["country_of_origin"] == "":
                entry["country_of_origin"] = operator["operator_country"]
            print(f"country_of_origin: {entry['country_of_origin']}")

            country_code = entry["country_of_origin"] # country code?
            imported_good_key = entry["cn_code"] + ";" + country_code + ";" + importer_name

            entry["det_operator"] = operator
            entry["det_installation"] = installation

            if installation is not None:
                entry["country_of_production"] = installation["installation_country"]
            else:
                entry["country_of_production"] = operator["operator_country"]

            # creating a list of entries with same key, that will be processed by create_procedures
            # (merging the entries here already would disregard different procedures)
            if imported_good_key not in imported_goods:
                imported_goods[imported_good_key] = {
                    "raw_entries": [entry],
                    "procedures": [],
                    "importer": {
                        "name": importer_name,
                        "eori": importer_eori,
                        "country": importer_country,
                        "city": importer_city,
                    },
                    "country_of_origin": entry["country_of_origin"],
                }
            else:
                imported_goods[imported_good_key]["raw_entries"].append(entry)

    shared_summary = shared_data["current"].setdefault("summary", {})
    num_imported_goods = len(imported_goods)
    shared_summary["num_imported_goods"] = num_imported_goods

    prepared_data_dict["imported_goods"] = imported_goods


def create_procedures(customer_dict, prepared_data_dict):
    imported_goods = prepared_data_dict["imported_goods"]

    # using the chance to create a total netmass entry here

    for _, imported_good in imported_goods.items():
        imported_good_total_netmass = 0

        """
        Every ImportedGoods entry contains a list of up to 9 procedures, together with their corresponding net mass.
        Every procedure entry can have up to 9 entries with inward processing information 
        """

        procedures = {}

        raw_entry_ls = imported_good["raw_entries"]

        for entry in raw_entry_ls:
            """
            Group and aggregate procedures by requested procedure and previous procedure
            """

            imported_good_total_netmass += r_float(entry["net_mass"], round_to=9)

            requested_procedure = entry["requested_procedure"]

            previous_procedure = entry.get("previous_procedure", None)

            current_entry_procedure = {
                "net_mass": entry["net_mass"],
                "requested_procedure": requested_procedure,
                "previous_procedure": previous_procedure,
                "inward_processing": entry["inward_processing"],
                "inward_processing_information": None,
            }

            cond_a = current_entry_procedure["inward_processing"] == "1"
            cond_b = previous_procedure == "51" or previous_procedure == "54"

            if cond_a ^ cond_b:
                Log.error(f"[prepare data] Contradicting entries w.r. to inward processing in {entry} : {cond_a} ^ {cond_b}")

            inward_processing_active = cond_a and cond_b

            if inward_processing_active:
                inward_processing_values = [
                    "already_processed",
                    "not_processed",
                    "member_state_of_authorization",
                    "bill_of_discharge_waiver",
                    "authorization",
                    "start_date",
                    "end_date",
                    "deadline",
                ]

                inward_processing_info = {ent: entry[ent] for ent in inward_processing_values}

                current_entry_procedure["inward_processing_information"] = inward_processing_info

            procedure_key = f"{requested_procedure};" + f"{previous_procedure}"

            if procedure_key not in procedures:
                # creating entry for procedure key
                procedures[procedure_key] = current_entry_procedure
            else:
                # if the procedure key already exists, aggregate the masses
                procedures[procedure_key]["net_mass"] += r_float(current_entry_procedure["net_mass"], round_to=9) # will be used for calculation so round to 9 digits instead of 6

            # * inward processing

            inward_processing_info = current_entry_procedure["inward_processing_information"]

            if inward_processing_info is not None:
                # if inward processing information is not existing, create it
                if procedures[procedure_key]["inward_processing_information"] is None:
                    procedures[procedure_key]["inward_processing_information"] = {}

                # exclude processed masses before building key
                already_processed = inward_processing_info.pop("already_processed")
                not_processed = inward_processing_info.pop("not_processed")

                if inward_processing_info["bill_of_discharge_waiver"] is None:
                    inward_processing_info["bill_of_discharge_waiver"] = "0"

                # build key to aggregate equal entries of inward processing information
                ip_key = "".join([inw_proc_val for inw_proc_val in inward_processing_info.values()])

                inward_processing_entries = procedures[procedure_key]["inward_processing_information"]

                if ip_key in inward_processing_entries:
                    # equal entries are existing -> merge
                    inward_processing_entries[ip_key]["already_processed"] += already_processed
                    inward_processing_entries[ip_key]["not_processed"] += not_processed

                else:
                    # readd excluded masses:
                    inward_processing_info["already_processed"] = already_processed
                    inward_processing_info["not_processed"] = not_processed
                    inward_processing_entries[ip_key] = inward_processing_info

            if len(procedures[procedure_key]) > 9:
                Log.error(f"Too many custom procedures for key {procedure_key} (max: 9, actual: {len(procedures[procedure_key])})")

        imported_good["procedures"] = procedures
        imported_good["total_net_mass"] = imported_good_total_netmass
