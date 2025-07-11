import yaml
from yaml.loader import SafeLoader
from rich.text import Text
from .log import Log
import unicodedata
# import xattr
import plistlib
from string import Template
from pathlib import Path
import difflib
from pathlib import Path


# def get_macos_tags(file_path):
#     try:
#         # Versuchen, das erweiterte Attribut für Finder-Tags zu lesen
#         tags = xattr.getxattr(file_path, "com.apple.metadata:_kMDItemUserTags")
#         # Umwandeln der Binärdaten im plist-Format in eine Python-Struktur
#         tags = plistlib.loads(tags)
#         return tags
#     except (KeyError, OSError, plistlib.InvalidFileException) as e:
#         # Wenn keine Tags vorhanden sind oder ein Fehler auftritt, wird eine Nachricht zurückgegeben
#         return None


def load_config(config_file):
    with open(config_file, "r") as f:
        raw_config = yaml.safe_load(f)

    paths = raw_config.get("paths", {})

    def resolve_path(path_str):
        resolved = Template(path_str).safe_substitute(paths)
        return str(Path(resolved))

    def resolve_all_paths(obj):
        if isinstance(obj, dict):
            return {k: resolve_all_paths(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [resolve_all_paths(i) for i in obj]
        elif isinstance(obj, str):
            return resolve_path(obj)
        return obj

    config = resolve_all_paths(raw_config)

    return config


def convert_dict_to_lowercase(data, protect_keys=[]):
    if isinstance(data, dict):
        # Rekursiver Aufruf für jedes Element im Dictionary
        return {key: (convert_dict_to_lowercase(value, protect_keys) if key not in protect_keys else value) for key, value in data.items()}
    elif isinstance(data, list):
        # Rekursiver Aufruf für jedes Element in der Liste
        return [convert_dict_to_lowercase(element, protect_keys) for element in data]
    elif isinstance(data, str):
        # Umwandeln von Strings in Kleinbuchstaben
        return data.lower()
    else:
        # Andere Datentypen bleiben unverändert
        return data


def is_null_value(value):
    return value is not None and value != "" and value != "-" and value != "0"


def non_exact_search(target, search_list, warn=False, warn_title=None):
    # Searches for a non-exact match of a target string in a list of strings
    for search_str in search_list:
        target = normalize_str(target)
        search_str = normalize_str(search_str)
        if clean_supplier_str(target.lower()) == clean_supplier_str(search_str.lower()):
            if warn:
                Log.warning(
                    f"Non-exact match for target '<yellow>{target}</r>' in {warn_title}. Matched:\n'<yellow>{target}</r>'\n'<yellow>{search_str}</r>'",
                    title="non-exact match | {warn_title}",
                )
            return search_str

    return None


def r_float(value, round_to=6, return_string=False):
    if value is None:
        return None
    rounded_value = round(float(value), round_to)
    
    if return_string:
        # Format string to exclude scientific notation
        return f"{rounded_value:.{round_to}f}"
    
    return rounded_value


def exact_search(target, search_list):
    # Searches for an exact match of a target string in a list of strings
    for search_str in search_list:
        target = normalize_str(target)
        search_str = normalize_str(search_str)
        if target.strip().lower() == search_str.strip().lower():
            return search_str

    return None


def normalize_str(s):
    return unicodedata.normalize("NFC", s)


def clean_supplier_str(supplier_str):
    # Cleans installation or operator string for comparison within supplier tool

    if supplier_str is None:
        return None

    ignore_ls = (
        " ",
        " ",
        "-",
        "_",
        "(",
        ")",
        ".",
        ",",
        ";",
        ":",
        "/",
        "\\",
        "co",
        "ltd",
        "gmbh",
    )

    for word in ignore_ls:
        supplier_str = supplier_str.replace(word, "")

    return supplier_str
