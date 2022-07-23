import json
import os
from queue import Empty
import re
import shutil
import time


settings_version: int = 2
files_last_modified: list[str] = []
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
mcpy_patterns: dict[str: str] = {
    'FUNCTION_DEFINE': r'^def (?P<name>[^\s]+)\((?P<arguments>.+)?\):(?:\s*|\t*)$',
    'FUNCTION_CALL': r'^(?P<name>[^\s]+)\((?P<arguments>.+)?\)(?:\s*|\t*)$',
    'FOR_LIST': r'^for (?P<name>[^\s]+) in \[(?P<list>.+)\]:(?:\s*|\t*)$',
    'FOR_RANGE': r'^for (?P<name>[^\s]+) in range\((?P<start>.+),(?:\s*)(?P<end>.+)\):(?:\s*|\t*)$',
}
mcf_patterns: dict[str: list[str]] = {
    'SCORE_DEFINE': [
        r'^score (?P<name>[^\s]+) (?P<type>[^\s]+)(?P<display>\s\".+\")?(?:\s*|\t*)$',
        r'scoreboard objectives add \g<name> \g<type>\g<display>',
    ],
    'SCORE_RESET': [
        r'^score reset (?P<player>[^\s]+) (?P<objective>[^\s]+)?(?:\s*|\t*)$',
        r'scoreboard players reset \g<player> \g<objective>',
    ],
    'SCORE_SET': [
        r'^score (?P<objective>[^\s]+) (?P<player>.+ )?= (?P<value>[0-9]+)(?:\s*|\t*)$',
        r'scoreboard players set \g<player>\g<objective> \g<value>',
        r'scoreboard players set @s \g<objective> \g<value>',
    ],
    'SCORE_ADD': [
        r'^score (?P<objective>[^\s]+) (?P<player>.+ )?+= (?P<value>[0-9]+)(?:\s*|\t*)$',
        r'scoreboard players add \g<player>\g<objective> \g<value>',
        r'scoreboard players add @s \g<objective> \g<value>',
    ],
    'SCORE_SUBTRACT': [
        r'^score (?P<objective>[^\s]+) (?P<player>.+ )?-= (?P<value>[0-9]+)(?:\s*|\t*)$',
        r'scoreboard players remove \g<player>\g<objective> \g<value>',
        r'scoreboard players remove @s \g<objective> \g<value>',
    ],
    'SCORE_OPERATION': [
        r'^score (?P<objective1>[^\s]+) (?P<player1>.+ )?(?P<operation>[%*+-=<>]*) (?P<objective2>[^\s]+)(?P<player2> .+)?(?:\s*|\t*)$',
        r'scoreboard players operation \g<player1>\g<objective1> \g<operation>\g<player2> \g<objective2>',
        r'scoreboard players operation @s \g<objective1> \g<operation>\g<player2> \g<objective2>',
        r'scoreboard players operation \g<player1>\g<objective1> \g<operation> @s \g<objective2>',
        r'scoreboard players operation @s\g<objective1> \g<operation> @s \g<objective2>',
    ],
    'SCORE_STORE': [
        r'^score (?P<objective>[^\s]+) (?P<player>.+ )?:= (?P<command>.+)$',
        r'execute store result score \g<player>\g<objective> run \g<command>',
    ]
}


class Line():
    def __init__(self, text: str) -> None:
        self._indent: int = self._set_indent(text)
        # type: COMMAND, COMMENT, SoC (Start of Command), EoC (End of Command),
        #       EMPTY, EoF (End of File), CoC (Continuation of Command), MCPY
        self._type: list[str] = []
        self._text: str = self._remove_indent(text)
        self._code: str = ''
        self._parent: Line = Empty
        self._children: list[Line] = []

    def _set_indent(self, text: str) -> int:
        return len(re.findall(settings['tab_style'], text))

    def _remove_indent(self, text: str) -> str:
        return re.sub(settings['tab_style'], '', text)

    def get_indent(self) -> int:
        return self._indent

    def get_text(self) -> str:
        return self._text

    def set_children(self, children: list[object]) -> None:
        self._children = children

    def add_children(self, child: object) -> None:
        self._children.append(child)

    def get_children(self) -> list[object]:
        return self._children

    def set_parent(self, parent: object) -> None:
        self._parent = parent

    def get_parent(self) -> object:
        return self._parent

    def set_code(self, code: str) -> None:
        self._code = code

    def get_code(self) -> str:
        return self._code

    def set_type(self, type: list[str]) -> None:
        self._type = type

    def add_type(self, type: str) -> None:
        self._type.append(type)

    def get_type(self) -> list[str]:
        return self._type


# From https://appdividend.com/2020/01/20/python-list-of-files-in-directory-and-subdirectories/
def get_files(dir_path: str = settings['base']) -> list[str]:
    list_of_file: list[str] = os.listdir(dir_path)
    complete_file_list: list[str] = []

    for file in list_of_file:
        completePath: str = os.path.join(dir_path, file)
        if os.path.isdir(completePath):
            complete_file_list += get_files(completePath)
        elif completePath.endswith('.mcpy'):
            complete_file_list.append(completePath)

    return complete_file_list


def has_files_modified() -> bool:
    global files_last_modified
    files_newly_modified: list[str] = []
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


def newline_to_list(text: str) -> list[str]:
    return text.splitlines()


def text_to_lines(file_path: str) -> list[Line]:
    data: list[Line] = []

    with open(file_path) as f:
        lines: list[str] = newline_to_list(f.read())

    for line in lines:
        data.append(Line(line))

    return data


def lines_to_text(lines: list['Line']) -> str:
    text: str = ''
    for line in lines:
        if line.get_children() != []:
            lines_to_text(line.get_children())
        else:
            text += line.get_code() + '\n'

    return text


def delete_dist() -> None:
    try:
        shutil.rmtree(settings['dist'])
    except FileNotFoundError:
        return


def is_mcf_comment(text: str) -> bool:
    return re.search(r'^(?:\s*|\t*)#.+', text)


def is_mcf_empty(text: str) -> bool:
    return re.search(r'^(\s*|\t*)$', text)


def is_mcf_EoC(text: str) -> bool:
    return not is_mcf_CoC(text)


def is_mcf_SoC(text: str, indent: int, current_indent: int = 0) -> bool:
    return indent == current_indent and is_mcf_CoC(text)


def is_mcf_CoC(text: str) -> bool:
    return re.search(r':(?:\s*|\t*)$', text)


def is_mcpy(text: str) -> bool:
    for pattern in mcpy_patterns.values():
        if re.search(pattern, text):
            return True

    return False


def which_mcpy(text: str) -> str:
    for key, pattern in mcpy_patterns.items():
        if re.search(pattern, text):
            return key


def write_output_files(text: str, file_path: str):
    file_path = file_path.replace('.mcpy', '.mcfunction')

    file_path = file_path.replace(settings['base'], '')
    file_path = file_path.replace('./', '')
    file_path = ''.join(settings['dist']+file_path)

    create_folder_path(file_path)

    with open(file_path, 'w') as file:
        file.write(text)


def create_folder_path(f_path: str):
    f_path = f_path.replace(os.path.basename(f_path), '').replace('./', '')
    f_path = re.split(r'/|\\', f_path)
    current_path = './'
    for i in f_path:
        if i != '':
            current_path += i + '/'
            if not os.path.exists(current_path):
                os.mkdir(current_path)


def set_lines_type(lines: list[Line]) -> list[Line]:
    current_indent: int = 0

    for line in lines:
        if lines[-1] == line:
            line.add_type('EoF')

        if is_mcf_comment(line.get_text()):
            line.add_type('COMMENT')
            continue
        elif is_mcf_empty(line.get_text()):
            line.add_type('EMPTY')
            continue
        elif is_mcpy(line.get_text()):
            line.add_type('MCPY')
            line.add_type(which_mcpy(line.get_text()))
            continue
        else:
            line.add_type('COMMAND')

        if is_mcf_SoC(line.get_text(), line.get_indent(), current_indent):
            line.add_type('SoC')
        elif is_mcf_CoC(line.get_text()):
            line.add_type('CoC')
        elif is_mcf_EoC(line.get_text()):
            line.add_type('EoC')

    return lines


def print_lines_tree(lines: list[Line], tabs: str = ""):
    for line in lines:
        print(tabs + "- " + str(line.get_type()) + "---" + line.get_text())

        if line.get_children() != []:
            print_lines_tree(line.get_children(), tabs + "  ")


def set_lines_children(lines: list[Line]) -> list[Line]:
    new_lines: list[Line] = []

    for line in lines:
        if line.get_parent() == Empty:
            current_indent: int = 0
        else:
            current_indent: int = line.get_parent().get_indent() + 1

        if line.get_indent() == current_indent:
            new_lines.append(line)
        elif line.get_indent() > current_indent:
            line.set_parent(new_lines[-1])
            new_lines[-1].add_children(line)

    for line in new_lines:
        if line.get_children() != []:
            line.set_children(set_lines_children(line.get_children()))

    return new_lines


def compile(file_path: str) -> None:
    lines: list[str] = text_to_lines(file_path)
    lines = set_lines_type(lines)
    lines = set_lines_children(lines)

    print(f'\n\n\n{file_path}')
    print_lines_tree(lines)

    text: str = lines_to_text(lines)  # TODO

    write_output_files(text, file_path)


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
            input('Press enter to compile mcpy files')
        else:
            time.sleep(settings['watch_delay'])

        mcpy_file_paths = get_files()

        # Skip compilation if base folder is empty
        if mcpy_file_paths == []:
            continue

        if has_files_modified():
            delete_dist()

            for file_path in mcpy_file_paths:
                compile(file_path)
