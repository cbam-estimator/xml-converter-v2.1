"""
This file should abstract printing/ logging to a certain degree, so a central point exists to direct output, f.e.
when switching to a GUI, a ms teams bot etc. - also so that printing is beeeautiful and consistent.

Should include:

- welcome message
- customer overview
- progress messages
- info messages
- warning messages
- error logs -> stop program
- bug logs
- info logs (activated with flag)
- soft error with cell
- hard error with cell

TODO:
x - support of styled strings: "Normal and <blue> blue text <orange> and orange and </> blue again"


---

- divider
- y/n question
- colors


"""

import os
from rich.console import Console
from rich.text import Text
import re


class Log:
    console = Console()

    prefix = " ┃    [S] "

    symbol_dict = {
        "info": "\033[94m[i]\033[0m",  # Blau
        "warning": "\033[1;38;5;214m[!]\033[0m",  # Gelb
        "error": "\033[91m[⤬]\033[0m",  # Rot
        "procedure": "\033[92m[→]\033[0m",  # Grün
    }

    muted = False
    called_welcome = False

    @staticmethod
    def welcome():
        terminal_width = Log.terminal_width()

        Log.print_s(f"\n {'┏' + '━' * (terminal_width - 4)}" + "┓", end="")
        out_str = """
        ┃                                              ┃
        ┃         CBAM XML Converter 2.0 - Dev         ┃
        ┃                                              ┃
        ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""
        out_str = Log.prefix_after_newline(out_str)
        Log.print_s(out_str, end="")

    @staticmethod
    def end():
        terminal_width = Log.terminal_width()
        Log.print_s(f"\n {'#' * terminal_width}", end="")

    @staticmethod
    def info(out_str):
        if not Log.called_welcome:
            Log.welcome()
            Log.called_welcome = True
        if not Log.muted:
            print(Log.prefix_after_newline(out_str, "info"), end="")

    @staticmethod
    def warning(out_str):
        if not Log.called_welcome:
            Log.welcome()
            Log.called_welcome = True
        if not Log.muted:
            print(Log.prefix_after_newline(out_str, "warning"), end="")

    @staticmethod
    def error(out_str):
        print(
            Log.prefix_after_newline(
                out_str + "\n\n \033[91mPROGRAM EXIT\033[0m", "error"
            ),
            end="",
        )
        Log.end()

        raise Exception("log error")

    @staticmethod
    def debug(out_str, key="general"):
        enabled = {
            "all": False,
            "general": True,
            "load_customer_sheet": False,
            "validator": False,
            "load_default": False,
        }

        if enabled["all"] or enabled[key]:
            print(Log.prefix_after_newline(out_str, "info"), end="")

    @staticmethod
    def procedure(out_str):
        print(Log.prefix_after_newline(out_str, "procedure"), end="")

    @staticmethod
    def terminal_width():
        try:
            return os.get_terminal_size().columns
        except:  # noqa: E722
            return 50

    @staticmethod
    def prefix_after_newline(ret_str, symbol=None, end="\n"):
        terminal_size = Log.terminal_width()

        ret_str = Log.insert_linebreaks(ret_str, terminal_size - 25)
        ret_str += end

        if symbol is not None:
            ret_str = "\n" + ret_str

        prefix = Log.prefix
        if symbol is None:
            prefix = prefix.replace("[S]", "   ")
        ret_str = ret_str.replace("\n", "\n" + prefix)

        color_s = None

        if symbol is not None:
            ret_str = ret_str.replace("[S]", Log.symbol_dict[symbol] + "  ┏▪", 1)
            color_s = (
                Log.symbol_dict[symbol].split("[")[0]
                + "["
                + Log.symbol_dict[symbol].split("[")[1]
            )

        ret_str = ret_str.replace("[S]", f"{color_s}     ┃ \033[0m")
        ret_str = ret_str[::-1].replace("⎮", " ", 2)[::-1]

        return ret_str

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

    @staticmethod
    def mute():
        Log.muted = True

    @staticmethod
    def unmute():
        Log.muted = False

    @staticmethod
    def print_s(text, end="\n"):
        pattern = re.compile(r"<(.*?)>(.*?)((?=<)|$)")
        position = 0

        while position < len(text):
            match = pattern.search(text, position)
            if not match:
                Log.console.print(text[position:], end=end)
                break

            tag, content = match.group(1), match.group(2)
            position = match.end(2)
            if tag == "r":
                tag = "reset"
            if ";" in tag:
                color, style = tag.split(";", 1)
            else:
                color, style = tag, None

            if color in color_palette:
                color = color_palette[color]

            if style:
                Log.console.print(content, style=f"{style} {color}", end=end)
            else:
                Log.console.print(content, style=color, end=end)


color_palette = {
    "red": "#ff1453",
    "green": "#70c2b4",
    "blue": "#24799e",
    "yellow": "#f3ffbd",
    "purple": "#9933ff",
    "cyan": "#b3dbbf",
    "white": "#f2faef",
    "black": "#1d3658",
}
