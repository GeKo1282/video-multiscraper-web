import logging, traceback, re, sys, os
from datetime import datetime

#TODO: Make custom levels of output for logger.log(level, msg)


class Color:
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7
    RESET = "\033[0m"

    FORE_GEN = lambda fore: "\033[" + "3" + str(fore) + "m"
    BACK_GEN = lambda back: "\033[" + "4" + str(back) + "m"
    FORE_RGB = lambda r, g, b: "\033[38;2;" + str(r) + ";" + str(g) + ";" + str(b) + "m"
    DECORATION = lambda dec: "\033[" + str(dec) + "m"


class Fore:
    BLACK = Color.FORE_GEN(Color.BLACK)
    RED = Color.FORE_GEN(Color.RED)
    GREEN = Color.FORE_GEN(Color.GREEN)
    YELLOW = Color.FORE_GEN(Color.YELLOW)
    BLUE = Color.FORE_GEN(Color.BLUE)
    MAGENTA = Color.FORE_GEN(Color.MAGENTA)
    CYAN = Color.FORE_GEN(Color.CYAN)
    WHITE = Color.FORE_RGB(170, 170, 170)

    ORANGE = Color.FORE_RGB(255, 120, 0)
    PINK = Color.FORE_RGB(219, 79, 123)
    MINT = Color.FORE_RGB(42, 189, 110)

    UNDERLINE = Color.DECORATION(4)
    DOUBLE_UNDERLINE = Color.DECORATION(21)


class Back:
    BLACK = Color.BACK_GEN(Color.BLACK)
    RED = Color.BACK_GEN(Color.RED)
    GREEN = Color.BACK_GEN(Color.GREEN)
    YELLOW = Color.BACK_GEN(Color.YELLOW)
    BLUE = Color.BACK_GEN(Color.BLUE)
    MAGENTA = Color.BACK_GEN(Color.MAGENTA)
    CYAN = Color.BACK_GEN(Color.CYAN)
    WHITE = Color.BACK_GEN(Color.WHITE)

class Logger(logging.Logger):
    def __init__(self, *args, datetime_format: str, **kwargs):
        self.datetime_format: str = datetime_format
        self.dummy = bool(kwargs.get('dummy'))
        if 'dummy' in kwargs:
            del kwargs['dummy']
            kwargs['name'] = "DummyLogger"
        self.colors = {"debug": kwargs['colors']['debug'] if 'colors' in kwargs and 'debug' in kwargs['colors'] else Fore.BLUE,
                       "info": kwargs['colors']['info'] if 'colors' in kwargs and 'info' in kwargs['colors'] else Fore.GREEN,
                       "warning": kwargs['colors']['warning'] if 'colors' in kwargs and 'warning' in kwargs['colors'] else Fore.YELLOW,
                       "error": kwargs['colors']['error'] if 'colors' in kwargs and 'error' in kwargs['colors'] else Fore.ORANGE,
                       "critical": kwargs['colors']['critical'] if 'colors' in kwargs and 'critical' in kwargs['colors'] else Fore.RED}
        super().__init__(*args, **kwargs)

    @staticmethod
    def _parse_extra_msg(msg: str, extra: Exception):
        module = f"{str(extra.__module__)}." if hasattr(extra, '__module__') else ""
        class_name = str(extra.__class__.__name__)
        return f"{module}{class_name}: {msg}"

    def _parse_extra(self, extra: Exception):
        module = f"{str(extra.__module__)}." if hasattr(extra, '__module__') else ""
        class_name = str(extra.__class__.__name__)
        trl = traceback.format_exc()
        filepath = sys.exc_info()[2].tb_frame.f_code.co_filename.replace("\\", "/")
        lines = re.findall(r', line [0-9]+,', trl)
        hierarchy = []
        for l in lines:
            hierarchy.append(trl.split("\n")[[l in line for line in trl.split("\n")].index(True) + 1])
        line = re.findall(r'[0-9]+', re.findall(r', line [0-9]+,', trl.split("\n")[len(trl.split("\n")) - 1 - list(
            reversed([filepath in line.replace("\\", "/") for line in
                      trl.split("\n")])).index(
            True)])[0])
        extra_info = f": {module}{class_name}: {str(extra)} [Line {line[0]}]\n"

        extra_info += f"\n{Fore.BLUE}Traceback:"
        for i in range(len(lines)):
            if i < len(lines) - 1:
                path = " ".join(trl.split("\n")[trl.split("\n").index(hierarchy[i]) - 1].split(",")[0].split())
                extra_info += f"\n{Fore.GREEN}{path}\n"
                extra_info += f"{Fore.ORANGE + Fore.UNDERLINE}{re.findall(r'[0-9]+', lines[i])[0]}{Color.RESET + Fore.WHITE} {hierarchy[i]} {Fore.ORANGE}\n"
                extra_info += f'\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/'
            else:
                path = " ".join(trl.split("\n")[trl.split("\n").index(hierarchy[i]) - 1].split(",")[0].split())
                extra_info += f"\n{Fore.GREEN}{path}\n"
                extra_info += f"{Fore.ORANGE + Fore.UNDERLINE}{re.findall(r'[0-9]+', lines[i])[0]}{Color.RESET + Fore.WHITE} {hierarchy[i]}{Fore.WHITE}\n"

        if self.level <= 30:
            extra_info = "\n"
            extra_info += f"{Fore.RED}---------------------------------------------------------------------------\n"
            extra_info += f"{Color.FORE_RGB(50, 168, 109)}{filepath}\n"
            file = open(filepath, "r").readlines()
            file_lines = file[int(line[0]) - 3:int(line[0]) + 2]
            for i, l in enumerate(file_lines):
                if i != 2:
                    extra_info += f"    {Fore.UNDERLINE}{Fore.ORANGE}{int(line[0]) - 2 + i}{Color.RESET}{Fore.YELLOW}{l}"
                else:
                    spaces = 0
                    while l.startswith(" "):
                        spaces += 1
                        l = l[1:]

                    extra_info += f"{Fore.GREEN}--->{Fore.UNDERLINE}{Fore.RED}{int(line[0]) - 2 + i}{Color.RESET}{' ' * spaces}{Fore.RED + Fore.DOUBLE_UNDERLINE}{l}{Color.RESET}"
            extra_info += f"\n{Fore.RED}{module}{class_name}{Fore.WHITE}: {Fore.ORANGE}{str(extra)} [Line {line[0]}]\n"

            if self.level <= 20:
                extra_info += f"{Fore.BLUE}\nTraceback:"
                for i in range(len(lines)):
                    if i < len(lines) - 1:
                        path = " ".join(trl.split("\n")[trl.split("\n").index(hierarchy[i]) - 1].split(",")[0].split())
                        extra_info += f"\n{Fore.GREEN}{path}\n"
                        extra_info += f"{Fore.ORANGE + Fore.UNDERLINE}{re.findall(r'[0-9]+', lines[i])[0]}{Color.RESET + Fore.RED} {hierarchy[i]} {Fore.ORANGE}\n"
                        extra_info += f"\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/"
                    else:
                        path = " ".join(trl.split("\n")[trl.split("\n").index(hierarchy[i]) - 1].split(",")[0].split())
                        extra_info += f"\n{Fore.GREEN}{path}\n"
                        extra_info += f"{Fore.ORANGE + Fore.UNDERLINE}{re.findall(r'[0-9]+', lines[i])[0]}{Color.RESET + Fore.RED} {hierarchy[i]}{Fore.WHITE}"

        return extra_info

    def _print(self, msg, level, *args, **kwargs):
        extra_info = ""
        if 'exc_info' in kwargs:
            extra_info = self._parse_extra(kwargs['exc_info'])
            msg = self._parse_extra_msg(msg, kwargs['exc_info'])
        raised_at = f"{Fore.WHITE}[{Fore.PINK}{datetime.now().strftime(self.datetime_format)}{Fore.WHITE}]"
        output = f"{raised_at}[{self.colors[level]}{level.upper()}{Fore.WHITE}]: {self.colors[level]}{msg}{extra_info}{Fore.WHITE}".replace("\r", self.colors[level])
        if kwargs.get('supress_print') != True:
            print(output)
        return output

    def log_error(self, func, log_finish=False):
        def wrapper(*args, **kwargs):
            try:
                val = func(*args, **kwargs)
            except Exception as e:
                self.error(e, exc_info=e)
            else:
                if not log_finish:
                    return val

                try:
                    return val
                finally:
                    self.info("Finished with no exception!")

        return wrapper

    def debug(self, msg, exc_info = None, *args, **kwargs):
        if self.dummy:
            return
        
        if self.level > 10:
            kwargs['supress_print'] = True
        
        if exc_info:
            self._print(msg, "debug", *args, exc_info=exc_info, **kwargs)
        else:
            self._print(msg, "debug", *args, **kwargs)

    def info(self, msg, exc_info = None, *args, **kwargs):
        if self.dummy:
            return
        
        if self.level > 20:
            kwargs['supress_print'] = True
        
        if exc_info:
            self._print(msg, "info", *args, exc_info=exc_info, **kwargs)
        else:
            self._print(msg, "info", *args, **kwargs)

    def warning(self, msg, exc_info = None, *args, **kwargs):
        if self.dummy:
            return
        
        if self.level > 30:
            kwargs['supress_print'] = True
        
        if exc_info:
            self._print(msg, "warning", *args, exc_info=exc_info, **kwargs)
        else:
            self._print(msg, "warning", *args, **kwargs)

    def error(self, msg, exc_info = None, *args, **kwargs):
        if self.dummy:
            return
        
        if self.level > 40:
            kwargs['supress_print'] = True
        
        if exc_info:
            self._print(msg, "error", *args, exc_info=exc_info, **kwargs)
        else:
            self._print(msg, "error", *args, **kwargs)

    def critical(self, msg, exc_info = None, *args, **kwargs):
        if self.dummy:
            return
        
        if self.level > 50:
            kwargs['supress_print'] = True
        
        if exc_info:
            self._print(msg, "critical", *args, exc_info=exc_info, **kwargs)
        else:
            self._print(msg, "critical", *args, **kwargs)


class FileLogger(Logger):
    def __init__(self, *args, datetime_format: str, log_directory: str = "./", log_file_name_template: str = "%sdt.log", print: bool = True, file_log_level: int = -1, **kwargs):
        self.log_directory: str = log_directory
        os.makedirs(self.log_directory, exist_ok=True)
        self.log_filename: str = None
        self.print: bool = print
        self.file_log_level: int = file_log_level
        super().__init__(*args, datetime_format=datetime_format, **kwargs)
        self.resolve_filename(log_file_name_template)

    def resolve_filename(self, template: str):
        self.log_filename = template.replace("%sdt", datetime.now().strftime(self.datetime_format.replace(":", "-")))

    def append_to_file(self, message: str):
        with open(self.log_directory.removesuffix("//").removesuffix("/") + "/" + self.log_filename, "a") as file:
            file.write(message + "\n")

    def _print(self, msg, level, *args, **kwargs):
        message = super()._print(msg, level, *args, **kwargs, suppress_print=not self.print or kwargs.get('suppress_print') == True)
        if self.file_log_level == -1 or self.file_log_level <= self.level:
            self.append_to_file(message)
        return message
