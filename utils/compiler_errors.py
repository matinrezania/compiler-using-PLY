import config
from utils.color_prints import Colorprints

class CompilerErrors(object):

    def __init__(self):
        self.errors = 0
        self.error_messages = []


    def print_error_messages(self):
        self.error_messages.sort(key=self.sort_by_lineno)
        for er_msg in self.error_messages:
            Colorprints.print_in_black(f"{config.code_file_path}:", end="")
            Colorprints.print_in_cyan(f"{er_msg['lineno']}: ", end="")
            if "is_hint" in er_msg:
                Colorprints.print_in_yellow(f"{er_msg['message']}")
            else:
                Colorprints.print_in_red(f"{er_msg['message']}")


    def add_error(self, error, increment_number=True):
        if not error in self.error_messages:
            self.error_messages.append(error)
            if increment_number:
                self.errors += 1 


    def sort_by_lineno(self, er_msg):
        return er_msg["lineno"]
