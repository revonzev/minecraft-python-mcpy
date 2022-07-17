import json
import os
from queue import Empty
import re
import time


settings_version: int = 2
files_last_modified: list = []
settings: dict = {
    'settings_version': settings_version,
    'watch_delay': 5,
    'dist': './dist/',
    'base': './mcpy/',
    'tab_style': '    ',
    'obfuscate': False,
    'keep_unused_obfuscated_string': False,
    'keep_comment': False,
    'auto_obfuscate': False,
    'file_for_globals': True
}


class Line():
    def __init__(self, text: str) -> None:
        self._indent: int = self._set_indent(text)
        self._type: str = 'text'
        self._text: str = self._remove_indent(text)
        self._code: str = ''
        self._parent: Line = Empty
        self._children: list = []

    def _set_indent(self, text: str) -> int:
        return len(re.findall(settings['tab_style'], text))

    def _remove_indent(self, text: str) -> str:
        return re.sub(settings['tab_style'], '', text)

    def get_indent(self) -> int:
        return self._indent

    def get_text(self) -> str:
        return self._text

    def add_children(self, child: object) -> None:
        self._children.append(child)

    def get_children(self) -> list:
        return self._children

    def set_parent(self, parent: object) -> None:
        self._parent = parent

    def get_parent(self) -> object:
        return self._parent

    def set_code(self, code: str) -> None:
        self._code = code

    def get_code(self) -> str:
        return self._code

    def set_type(self, type: str) -> None:
        self._type = type

    def get_type(self) -> str:
        return self._type


# From https://appdividend.com/2020/01/20/python-list-of-files-in-directory-and-subdirectories/
def get_files(dir_path: str = settings['base']) -> list:
    list_of_file: list = os.listdir(dir_path)
    complete_file_list: list = []

    for file in list_of_file:
        completePath: str = os.path.join(dir_path, file)
        if os.path.isdir(completePath):
            complete_file_list += get_files(completePath)
        elif completePath.endswith('.mcpy'):
            complete_file_list.append(completePath)

    return complete_file_list


def has_files_modified() -> bool:
    global files_last_modified
    files_newly_modified: list = []
    has_modified: bool = False

    if files_last_modified == []:
        for f_path in mcpy_file_paths:
            files_last_modified += [os.stat(f_path).st_mtime]
        has_modified = True
    else:
        for f_path in mcpy_file_paths:
            files_newly_modified += [os.stat(f_path).st_mtime]

        has_modified = files_last_modified != files_newly_modified
        files_last_modified = files_newly_modified

    return has_modified


def newline_to_list(text) -> list:
    return text.split('\n')


def text_to_lines(file_path: str) -> list:
    data: list = []

    with open(file_path) as f:
        lines = newline_to_list(f.read())

    for line in lines:
        data.append(Line(line))

    return data


def compile(file_path: str) -> None:
    lines: list = text_to_lines(file_path)

    # print(f'\n\n\n{file_path}')
    # for line in lines:
    #     print(line.get_text())


if __name__ == '__main__':
    # Load user settings
    try:
        with open('user_settings.json') as f:
            settings = json.load(f)
    except FileNotFoundError:
        with open('user_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)

    if (settings['settings_version'] != settings_version):
        exit()

    # Compiler
    skip = False
    while True:
        # Delay between compilation
        if settings['watch_delay'] == 0:
            input('Press enter to compile mcpy')
        else:
            time.sleep(settings['watch_delay'])

        mcpy_file_paths = get_files()

        # Skip compilation if base folder is empty
        if mcpy_file_paths == []:
            continue

        if has_files_modified():
            for file_path in mcpy_file_paths:
                compile(file_path)
