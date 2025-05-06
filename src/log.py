import re
import os
import inspect
import datetime
import pprint
from .shared import shared_data


class Log:
    n1_prefix = " ┃    · "
    n1_prefix = " ┃      "
    t1_prefix = " ┃    <c>⟨ [S] 〉├┐ </r>"
    t2_prefix = " <c>┃          ││ </r>"
    t3_prefix = " <c>┃          ├┴─────</r><gray>─────────────────────────</r> "
    div_prefix = " ┠───"

    hline_c = "━"

    type_dict = {
        "info": ("green", "➤"),
        "warning": ("orange", "♦︎"),
        "error": ("red", "x"),
        "procedure": ("purple", "→"),
        "question": ("cyan", "?"),
        "debug": ("purple", "♦︎"),
        "wait": ("gray", "⏭"),
        "summary": ("pink", "⏺"),
    }

    muted = False

    printed_title = False

    delay_exit_set = False

    @staticmethod
    def clear():
        os.system("cls" if os.name == "nt" else "clear")
        Log.printed_title = False

    @staticmethod
    def divider():
        terminal_width = Log.terminal_width()
        Log.fs(f"<#6b6b6b>{"─" * (terminal_width * 2 // 3)}</r>", "divider")

    @staticmethod
    def wait_for_input(out_str="<gray>Press Enter to continue...</r>", end="\n"):
        Log.fs(f"\n {out_str}", "wait", end=end)
        # asd
        input()

    @staticmethod
    def title():
        terminal_width = Log.terminal_width()

        print(f"\n {'┏' + Log.hline_c * (terminal_width - 4)}" + "┓", end="")
        out_str = """         ┃                                              ┃
        ┃         <green><b>CBAM XML Converter 2.0 - Dev</r>         ┃
        ┃      <green>▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔</r>      ┃
        ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""

        Log.fs(out_str, end="")

    @staticmethod
    def end():
        terminal_width = Log.terminal_width()
        Log.fs(f"\n {Log.hline_c * terminal_width}", end="")

    @staticmethod
    def info(out_str):
        if not Log.printed_title:
            Log.title()
            Log.printed_title = True
        if not Log.muted:
            Log.fs(out_str, "info")

    warning_id_count = {}
    sev_warning_count = 0

    @staticmethod
    def warning(out_str, title="", source=None, print_max=None, print_id=None, severe=True):
        if print_max is not None and print_id is not None:
            if print_id not in Log.warning_id_count:
                Log.warning_id_count[print_id] = 0
            Log.warning_id_count[print_id] += 1

            if Log.warning_id_count[print_id] > print_max:
                return

        if severe and not Log.muted:
            Log.sev_warning_count += 1

        if source is None:
            source = f"{inspect.stack()[1].function}"

        if not Log.printed_title:
            Log.title()
            Log.printed_title = True

        cb_tag = "<b>" if severe else ""
        cn_tag = f"<yellow>[{Log.sev_warning_count:02d}]</r>  -  " if severe else ""
        out_str = f"{cn_tag}{cb_tag}Warning</r>  |  {cb_tag}<yellow>{title}</r>    ↤  <i>f: <yellow>{source}</r>\n{out_str}"

        if not Log.muted:
            Log.fs(out_str, "warning")

    @staticmethod
    def dialog(question, title="Dialog", options=["yes", "no"]):
        show_str = f"<b><cyan>{title}</r>\n\n"
        show_str += f"{question}\n\n"

        # Optionen anzeigen, falls vorhanden
        if options:
            options_str = "/ ".join(options)
            show_str += f"options: [{options_str}]\n"

        # Eingabeaufforderung erstellen
        show_str += "choice: "
        Log.fs(show_str, "question", end="")

        # Benutzereingabe erfassen
        user_input = input().strip().lower()
        return user_input

    @staticmethod
    def error(out_str, title="Error", source=None, delay_exit=False, raiseErrorDebug=False):
        if source is None:
            source = f"{inspect.stack()[1].function}"

        out_str = f"<b><red>{title}</r>    ↤  <i>f: <red>{source}</r>\n\n{out_str}"

        Log.fs(
            out_str + f"\n\n \033[91m {'- exit delayed -' if delay_exit else 'PROGRAM EXIT'}\033[0m",
            "error",
            end="",
        )

        if not delay_exit:
            Log.end()
            if raiseErrorDebug:
                raise Exception("log error")
            else:
                exit(0)
        else:
            Log.delay_exit_set = True

    @staticmethod
    def exit_if_delayed():
        if Log.delay_exit_set:
            Log.error("delayed exit", delay_exit=False)

    @staticmethod
    def debug(out_str, key="general", title="Debug Log"):
        enabled = {
            "all": False,
            "general": True,
            "load_customer_sheet": False,
            "validator": False,
            "load_default": False,
            "load_files": False,
            "determine_version": False,
            "inherit_version": False,
            "workflow": False,
            "supplier_data": False,
            "xlsx_access": False,
            "installation_data": False,
        }

        out_str = f"<b><purple>{title}</r>   -   [<i><purple>{key}</r>]\n{out_str}"

        if enabled["all"] or enabled[key]:
            Log.fs(out_str, "debug")

    @staticmethod
    def loading_indicater(stop=False):
        if stop:
            print("\r", end="")
        else:
            print(" \033[2K", end="")

    @staticmethod
    def procedure(out_str):
        if not Log.printed_title:
            Log.title()
            Log.printed_title = True
        if not Log.muted:
            Log.fs(out_str, "procedure")

    @staticmethod
    def fs(s, m_type=None, end="\n"):
        interm = Log.add_prefix(s, m_type=m_type, end=end)
        print(Log.parse_colored_string(interm), end="")

    @staticmethod
    def col_from_hex(hex_color):
        """Converts a hex color code to an ANSI escape sequence for the terminal."""
        r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
        return f"\033[38;2;{r};{g};{b}m"

    color_dict = {
        "red": col_from_hex("#ff8756"),
        "green": col_from_hex("#6dcd97"),
        "blue": col_from_hex("#8ee5ff"),
        "orange": col_from_hex("#ffbb51"),
        "yellow": col_from_hex("#ffc107"),
        "purple": col_from_hex("#d1b2ff"),
        "cyan": col_from_hex("#86ffee"),
        "gray": col_from_hex("#555555"),
        "pink": col_from_hex("#ffa6cc"),
    }

    @staticmethod
    def parse_colored_string(s):
        """Parses a string with custom color tags and returns a string with ANSI escape sequences."""

        color_dict = Log.color_dict

        reset = "\033[0m"
        stack = []
        result = ""

        pattern = re.compile(r"<(\/?[#a-zA-Z0-9]+)>|([^<]+)")

        style_dict = {
            "b": "\033[1m",  # Bold
            "i": "\033[3m",  # Italic
            "u": "\033[4m",  # Underline
            "mark": "\033[7m",  # Highlight (Reverse Video)
        }

        for match in pattern.finditer(s):
            tag, text = match.groups()

            if tag:
                if tag.startswith("/"):
                    if tag == "/r":
                        result += reset
                        stack.clear()
                    elif stack:
                        stack.pop()
                        result += stack[-1] if stack else reset
                else:
                    if tag.startswith("#"):  # Wenn der Tag ein Hex-Code ist
                        color = Log.col_from_hex(tag)
                    elif tag in style_dict:  # Wenn es ein Stil-Tag ist
                        color = style_dict[tag]
                    else:  # Wenn der Tag ein benannter Farbname ist
                        color = color_dict.get(tag, "")
                    stack.append(color)
                    result += color
            elif text:
                result += text

        return result + reset

    @staticmethod
    def add_prefix(input_str, m_type=None, end="\n"):
        terminal_size = Log.terminal_width()

        input_str = Log.insert_linebreaks(input_str, terminal_size - 25)
        input_str += end

        if m_type is not None:
            input_str = "\n" + input_str

        num_lines = input_str.count("\n")

        if m_type is None:
            first_line_prefix = Log.n1_prefix
            other_line_prefix = Log.n1_prefix
            last_line_prefix = Log.n1_prefix
        elif m_type == "divider":
            first_line_prefix = last_line_prefix = Log.n1_prefix
            other_line_prefix = Log.div_prefix
        else:
            first_line_prefix = Log.t1_prefix.replace("[S]", Log.type_dict[m_type][1])

            first_line_prefix = first_line_prefix.replace("<c>", Log.color_dict[Log.type_dict[m_type][0]])
            other_line_prefix = Log.t2_prefix
            other_line_prefix = other_line_prefix.replace("<c>", Log.color_dict[Log.type_dict[m_type][0]])
            last_line_prefix = Log.t3_prefix
            last_line_prefix = last_line_prefix.replace("<c>", Log.color_dict[Log.type_dict[m_type][0]])

        lines = input_str.split("\n")

        lines[0] = first_line_prefix + lines[0]

        for i in range(1, len(lines) - 1):
            lines[i] = other_line_prefix + lines[i]

        if len(lines) > 1:
            lines[-1] = last_line_prefix + lines[-1]

        input_str = "\n".join(lines) + "\n"

        return input_str

    @staticmethod
    def terminal_width():
        try:
            return os.get_terminal_size().columns
        except:  # noqa: E722
            return 60

    @staticmethod
    def insert_linebreaks(s, terminal_width):
        result = []
        line_length = 0

        for charac in s:
            if charac == "\n":
                result.append(charac)
                line_length = 0
            else:
                if line_length >= terminal_width:
                    result.append("\n")
                    line_length = 0
                result.append(charac)
                line_length += 1

        return "".join(result)

    def mute():
        Log.muted = True

    def unmute():
        Log.muted = False

    @staticmethod
    def summary(config):
        shared_sum = shared_data["current"].get("summary", None)

        if shared_sum is None:
            Log.fs("No summary available.", "summary")
            return

        log_path = config["log_file"]
        customer_report_num, times_created = Log.create_log_file(log_path)

        num_supporting_docs = sum(shared_data["current"].setdefault("supporting_documents", {}).values())

        time_stamp = datetime.datetime.now().strftime("%d.%m.%Y - %H:%M:%S")

        str_ = f""" <b>SUMMARY</r>  -  <b><pink>Q{shared_sum["quarter"]}</r>-<b><pink>{shared_sum["year"]}</r>  :  '<b><pink>{shared_sum["importer_name"]}</r>'

 <i><gray>{time_stamp}</r>

 <b><gray>META</r>
  warnings:           <b><i><yellow>{Log.sev_warning_count:02}</r>
  times created:      <i><blue>{times_created:02}</r>
  customer reports:   <i><blue>{customer_report_num:02}</r>
  intern report typ   <i><blue>{shared_sum.get("intern_report_type", "no report type")}</r>

 <b><gray>IMPORTER</r>
  name:               <yellow>{shared_sum["importer_name"]}</r>
  eori:               <yellow>{shared_sum["importer_eori"]}</r>

 <b><gray>STRUCTURE</r>
  operators:          <yellow>{shared_sum["num_operators"]:03}</r>
  installations:      <yellow>{shared_sum.get("num_installations", 0):03}</r>

  supporting docs:    <yellow>{num_supporting_docs:03}</r>
  
  imported_goods:     <yellow>{shared_sum["num_imported_goods"]:03}</r>
  goods_emissions:    <yellow>{shared_sum.get("num_goods_emission", 0):03}</r>

 <b><gray>TOTAL</r>
  total quantity:     <yellow>{shared_sum.get("total_net_mass", 0):09.5f}</r> t
  total emissions:    <yellow>{shared_sum.get("total_emissions", 0):09.5f}</r> t CO2

"""

        Log.fs(str_, "summary")

        Log.divider()

        if "intern_report_type" not in shared_sum:
            Log.warning(
                "It seems like an empty report was created!",
                title="EMPTY REPORT WARNING",
            )
            return

    @staticmethod
    def create_log_file(log_path):
        import os
        import csv
        from datetime import datetime

        # Access the summary data
        shared_sum = shared_data["current"].get("summary", None)
        if shared_sum is None:
            Log.warning("No summary available.", title="create_log_file")
            return 0, 0  # Return zeros if no data

        # Prepare the CSV header
        header = [
            "time_stamp",
            "importer_eori",
            "year",
            "quarter",
            "intern_report_type",
            "importer_name",
            "total_quantity",
            "total_emissions",
            "same_report_num",
            "customer_report_num",
        ]

        # Function to remove commas from strings
        def remove_commas(value):
            if isinstance(value, str):
                return value.replace(",", "")
            return value

        # Prepare the data row
        time_stamp = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        importer_eori = remove_commas(shared_sum.get("importer_eori", ""))
        year = remove_commas(str(shared_sum.get("year", "")))
        quarter = remove_commas(str(shared_sum.get("quarter", "")))
        intern_report_type = remove_commas(shared_sum.get("intern_report_type", ""))
        importer_name = remove_commas(shared_sum.get("importer_name", ""))
        total_quantity = shared_sum.get("total_net_mass", 0)
        total_emissions = shared_sum.get("total_emissions", 0)

        # Initialize counts
        same_report_num = 0
        customer_periods = set()

        # Key columns to identify same report
        key_columns = ["importer_eori", "year", "quarter"]

        # Read existing entries from the CSV file
        existing_entries = []
        if os.path.exists(log_path):
            with open(log_path, "r", newline="\n", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    existing_entries.append(row)

        # Count same_report_num and customer_report_num
        for entry in existing_entries:
            entry_importer_eori = remove_commas(entry["importer_eori"])
            entry_year = remove_commas(entry["year"])
            entry_quarter = remove_commas(entry["quarter"])

            if entry_importer_eori == importer_eori:
                period = (entry_year, entry_quarter)
                customer_periods.add(period)
                if entry_year == year and entry_quarter == quarter:
                    same_report_num += 1

        # Increment counts to include the current report
        same_report_num += 1
        current_period = (year, quarter)
        if current_period not in customer_periods:
            customer_periods.add(current_period)
        customer_report_num = len(customer_periods)

        # Prepare the row data with only the columns defined in the header
        row_data = {
            "time_stamp": time_stamp,
            "importer_eori": importer_eori,
            "year": year,
            "quarter": quarter,
            "intern_report_type": intern_report_type,
            "importer_name": importer_name,
            "total_quantity": total_quantity,
            "total_emissions": total_emissions,
            "same_report_num": same_report_num,
            "customer_report_num": customer_report_num,
        }

        # Write the data to the CSV file
        file_exists = os.path.isfile(log_path)
        with open(log_path, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=header)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_data)

        # Return the counts
        return same_report_num, customer_report_num


class MarkerException(Exception):
    """Diese Ausnahme dient als Marker und sollte nicht in natürlichen Kontexten auftreten."""

    pass


import threading
import time
import itertools


class LoadingIndicator:
    def __init__(self):
        self._stop_event = threading.Event()

    def start(self):
        """Starts the loading indicator in a separate thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self):
        """Stops the loading indicator."""
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join()  # Wait for the thread to finish
        print("\r", end="")  # Clear the loading line

    def _animate(self):
        """Animation logic for the indicator."""
        for symbol in itertools.cycle(["  .", "  ..", "  ..."]):  # Infinite cycle of symbols
            if self._stop_event.is_set():
                break
            print(f"  \r{symbol}", end="")
            time.sleep(0.4)  # Adjust the speed of the indicator
