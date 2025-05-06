"""
* TODOS and NOTES

TODO 1 : Improve Error Handling and structure
- This file should not raise errors, but only warn (if not muted) and validate
- errors should be raised at the proper point and with maximal information
- coexistence with test errors can be improved...

TODO 2 : Revise xml schema
- Are all requirements covered? For example max. lenghts, etc.

TODO 3 : Add better documentation & revise code

"""

from cerberus import Validator
from .log import Log
from datetime import datetime
import re
from .helper import r_float

v = Validator()
v.schema = {
    "float": {"type": "float"},
    "net_mass": {"type": "float"},
    "cn_code": {"type": "string", "regex": r"^[0-9]{8}$"},
    "cell_index": {"type": "string", "regex": r"^[A-Z]+[0-9]+$"},
    "version": {"type": "string", "regex": r"^[0-9]+(\.[0-9]+)*$"},
    "eori": {"type": "string", "regex": r"^(DE[0-9]{7}|DE[0-9]{15}|ATEOS[0-9]{8,12}|PL[0-9]{14}Z?|RO[A-Z0-9]{2,15}|FR[0-9]{14})$"}, # "eori": {"type": "string", "regex": r"^(DE[0-9]{7}|DE[0-9]{15}|ATEOS[0-9]{8,12}|PL[0-9]{14}Z?|RO[A-Z0-9]{2,15})$"},
    "string": {"type": "string"},
    "mail_adress": {
        "type": "string",
        "regex": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$",
    },
    "country": {"type": "string"},
    "country_code": {"type": "string", "regex": r"^[A-Z]{2}$"},
    "year": {"type": "string", "regex": r"^[0-9]{4}$"},
    "quarter": {"type": "string", "regex": r"^[1-4]$"},
    "good_quantity_unit": {"type": "string"},
    "production_method": {"type": "string", "regex": r"^P\d{2}( - .*)?$"},
    "boolean": {"type": "string", "regex": r"^[01]$"},
    "inward_processing": {"type": "string", "regex": r"^[01]$"},
    "date_str8": {"type": "string", "regex": r"^[0-9]{8}$"},
    "date_str_xlsx": {
        "type": "string",
        "regex": r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$",
    },
    "customs_procedure_desc": {"type": "string"},
    "customs_procedure_code": {"type": "string", "regex": r"^\d{2}$"},
}


def process_and_validate(val_type: str, input, entry_data=None, condition=None, raise_errors=True, mute=False):
    """
    Cleans the input and validates it against the schema
    """

    val_type, input = pre_process(val_type, input)

    # change, when conditions are implemented
    if not (val_type.endswith("_m")) and (input is None or input == ""):
        return input, True

    val_type = process_suffix(val_type, input, entry_data, condition, raise_errors, mute)

    if not val_type:
        return input, False

    input = process(val_type, input, entry_data)

    if val_type not in v.schema:
        Log.warning(f"[validate] Invalid type '{val_type}' for validation")

    validate = v.validate({val_type: input})

    if not validate:
        Log.warning(f"[validate] Invalid value '{input}' for type '{val_type}'")

    return input, validate


def process_suffix(val_type, input, entry_data, condition, raise_errors, mute):
    if val_type.endswith("_m"):
        # Mandatory field logic
        if input is None or input == "":
            if raise_errors:
                Log.error(f"[progress_suffix] Mandatory field '{val_type}' ['{input}'] is empty.\n Entry data: {entry_data}")
            if not mute:
                Log.warning(f"[progress_suffix] <no_raise_err> Mandatory field '{val_type}' ['{input}'] is empty.\n Entry data: {entry_data}")
            return None

    elif val_type.endswith("_c"):
        # Conditional field logic
        if not condition:
            Log.warning(f"[progress_suffix] Conditional type '{val_type}' provided but no condition specified.")
        else:
            con_type = condition.get("con_type", "AND")
            conditions = condition.get("ls", [])

            condition_met = False
            if con_type == "and":
                condition_met = all(evaluate_condition(entry_data, cond) for cond in conditions)
            elif con_type == "or":
                condition_met = any(evaluate_condition(entry_data, cond) for cond in conditions)
            else:
                Log.warning(f"[progress_suffix] Unknown condition type '{con_type}' for conditional field '{val_type}'.")

            if not condition_met:
                Log.error(f"[progress_suffix] Condition not met for conditional field '{val_type}'.\n Condition: {conditions}\n Entry data: {entry_data})")

        # Check if all condition fields exist in entry_data
        for cond in conditions:
            if cond["field"] not in entry_data:
                Log.error(f"[progress_suffix] Condition field '{cond['field']}' not found in entry data.")

    elif val_type.endswith("_o"):
        # Optional field logic
        pass  # Fügen Sie hier ggf. spezifische Logik für optionale Felder hinzu

    else:
        # No specific suffix, default action
        pass  # Fügen Sie hier ggf. eine Standardaktion hinzu

    return val_type[:-2] if val_type.endswith(("_m", "_c", "_o")) else val_type


def evaluate_condition(entry_data, condition):
    field_name = condition.get("field")
    operator = condition.get("operator")
    expected_value = condition.get("value")

    if field_name not in entry_data:
        Log.warning(f"[evaluate_condition] Field '{field_name}' not found in entry data.")
        return False

    # Get the actual value from the entry_data
    actual_value = entry_data.get(field_name)

    # Evaluate the condition based on the operator
    if operator == "==":
        return actual_value == expected_value
    elif operator == "!=":
        return actual_value != expected_value
    elif operator == "<":
        return actual_value < expected_value
    elif operator == ">":
        return actual_value > expected_value
    elif operator == "<=":
        return actual_value <= expected_value
    elif operator == ">=":
        return actual_value >= expected_value
    else:
        Log.warning(f"Unknown operator '{operator}' in condition.")
        return False


def pre_process(val_type, input_value):
    """
    Processing necessary before suffix processing
    """

    if input is None or input == "":
        return val_type, input

    # this is deactivated for reasons
    # if type(input_value) is not str:
    #    input_value = str(input_value)

    ## * General

    ## * Type-specific processing

    #### string castings

    if val_type[:-2] == "cn_code" or val_type[:-2] == "date_str8" or val_type[:-2] == "quarter" or val_type[:-2] == "string" or val_type[:-2] == "year":
        input_value = str(input_value)

    #### customs procedure

    if val_type[:-2] == "customs_procedure_desc":
        if str(input_value) == "0" or str(input_value) == "-":
            return "customs_procedure_desc" + val_type[-2:], None

        return "customs_procedure_code" + val_type[-2:], input_value[:2]

    #### boolean

    if val_type[:-2] == "boolean":
        if input_value.lower() == "ja" or input_value.lower() == "yes":
            input_value = "1"
        elif input_value.lower() == "nein" or input_value.lower() == "no":
            input_value = "0"
        else:
            input_value = None

    ##### inward processing

    if val_type[:-2] == "inward_processing":
        if input_value.lower() == "ja" or input_value.lower() == "yes":
            input_value = "1"
        elif (
            # for inward procceing, empty string defaults to "no"
            input_value.lower() == "nein" or input_value.lower() == "no"
        ):
            input_value = "0"
        elif input_value == "":
            input_value = "0"
            Log.warning(
                "Empty string for inward_processing defaults to 'no'.",
                title="Empty fields inwards processing",
                print_max=1,
                print_id="empty_inward_processing",
            )
        else:
            input_value = None

    if val_type[:-2] == "eori":
        input_value = input_value.replace(" ", "").replace(" ", "")

    return val_type, input_value


def process(val_type, input_value, entry_data=None):
    def log_change(original, new, description):
        if original != new:
            Log.debug(f"{description}: '{original}' -> '{new}'", key="validator")

    ## * General processing

    if type(input_value) is str:
        # Trim whitespace
        original_value = input_value
        input_value = input_value.strip().replace("\u00a0", "")
        log_change(original_value, input_value, "Trimmed whitespace")

        # something else (probably create xml tree), already does this
        if False:
            # Ersetze alle Zeichen <, > und "
            xml_replacements = {"<": "&lt;", ">": "&gt;", '"': "&quot;"}
            for char, replacement in xml_replacements.items():
                original_value = input_value
                input_value = input_value.replace(char, replacement)
                log_change(
                    original_value,
                    input_value,
                    f"Replaced '{char}' with '{replacement}'",
                )

            # Ersetze nur &-Zeichen, die nicht bereits Teil einer kodierten Entität sind
            original_value = input_value
            input_value = re.sub(r"&(?!amp;|lt;|gt;|quot;)", "&amp;", input_value)
            log_change(original_value, input_value, "Replaced '&' with '&amp;' where necessary")

    ## * Type-specific processing

    if val_type.endswith("_m") or val_type.endswith("_c") or val_type.endswith("_o"):
        val_type = val_type[:-2]

    #### countries

    if val_type == "country":
        from .default_data import DefaultData

        country_db = DefaultData.get("country_data")
        if country_info := country_db.find_country(input_value):
            input_value = country_info["un_code"]
        else:
            Log.error(f"[clean_input_values] Country '{input_value}' not found.")

    #### date strings

    if val_type == "date_str8" and v.validate({"date_str_xlsx": input_value}):
        # Umwandeln des Strings in ein datetime-Objekt
        date_obj = datetime.strptime(input_value, "%Y-%m-%d %H:%M:%S")

        # Umwandeln des datetime-Objekts in das gewünschte Format
        input_value = date_obj.strftime("%Y%m%d")

    # deprecated: float should be floats not strings!
    if val_type == "float" or val_type == "netmass":
        # Remove all spaces

        if type(input_value) is str:
            original_value = input_value
            input_value = input_value.replace(" ", "")
            log_change(original_value, input_value, "Removed all spaces")

            # Replace comma with dot
            original_value = input_value
            input_value = input_value.replace(",", ".")
            log_change(original_value, input_value, "Replaced comma with dot")

        # Validate if the result is a valid float
        try:
            input_value = float(input_value)
        except ValueError:
            Log.warning(f"[clean_input_values] Invalid float format: '{input_value}'")

    #### net_mass

    if val_type == "net_mass":
        if entry_data is None:
            Log.error("[clean_input_values] Could not determine unit for net_mass, no entry_data provided.")
        if "net_mass_unit" not in entry_data:
            Log.error("[clean_input_values] No 'net_mass_unit' in entry_data. Is it loaded before net_mass?")

        unit = entry_data.get("net_mass_unit").lower()

        if unit == "kg":
            input_value = input_value / 1000
        elif unit == "t" or unit == "tonnes" or unit == "tonnen" or unit == "tons":
            input_value = input_value
        else:
            Log.error(f"[clean_input_values] Unknown unit '{unit}' for net_mass in entry_data.")

        input_value = r_float(input_value) # added new 25

    return input_value
