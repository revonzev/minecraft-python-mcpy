from copy import deepcopy
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
    'indented_comment': True,
    'keep_empty_lines': False,
    'auto_obfuscate': False,
    'file_for_globals': True
}
mcpy_patterns: dict[str: str] = {
    'FUNCTION_DEFINE': r'^def (?P<name>[^\s]+)\((?P<arguments>.+)?\):$',
    'FUNCTION_CALL': r'^(?P<name>[^\s]+)\((?P<arguments>.+)?\)$',
    'FOR_LIST': r'^for (?P<name>[^\s]+) in \[(?P<list>.+)\]:$',
    'FOR_RANGE': r'^for (?P<name>[^\s]+) in range\((?P<start>\d+),(?:\s*)(?P<end>\d+)\):$',
}
snippet_patterns: dict[str: list[str]] = {
    'SCORE_RESET': [
        r'^score reset (?P<player>[^\s]+(?:\[.+\])?) (?P<objective>[^\s]+)?$',
        r'scoreboard players reset \g<player> \g<objective>',
    ],
    'SCORE_RESET_SELF': [
        r'^score reset (?P<objective>[^\s]+)?$',
        r'scoreboard players reset @s \g<objective>',
    ],
    'SCORE_DEFINE': [
        r'^score (?P<name>[^\s]+) (?P<type>[^\s]+)(?P<display>\s\".+\")?$',
        r'scoreboard objectives add \g<name> \g<type>\g<display>',
    ],
    'SCORE_SET': [
        r'^score (?P<objective>[^\s]+) (?P<player>[^\s]+(?:\[.+\])?) = (?P<value>[0-9]+)$',
        r'scoreboard players set \g<player> \g<objective> \g<value>',
    ],
    'SCORE_SET_SELF': [
        r'^score (?P<objective>[^\s]+) = (?P<value>[0-9]+)$',
        r'scoreboard players set @s \g<objective> \g<value>',
    ],
    'SCORE_ADD': [
        r'^score (?P<objective>[^\s]+) (?P<player>[^\s]+(?:\[.+\])?) \+= (?P<value>[0-9]+)$',
        r'scoreboard players add \g<player> \g<objective> \g<value>',
    ],
    'SCORE_ADD_SELF': [
        r'^score (?P<objective>[^\s]+) \+= (?P<value>[0-9]+)$',
        r'scoreboard players add @s \g<objective> \g<value>',
    ],
    'SCORE_SUBTRACT': [
        r'^score (?P<objective>[^\s]+) (?P<player>[^\s]+(?:\[.+\])?) -= (?P<value>[0-9]+)$',
        r'scoreboard players remove \g<player> \g<objective> \g<value>',
    ],
    'SCORE_SUBTRACT_SELF': [
        r'^score (?P<objective>[^\s]+) -= (?P<value>[0-9]+)$',
        r'scoreboard players remove @s \g<objective> \g<value>',
    ],
    'SCORE_STORE': [
        r'^score (?P<objective>[^\s]+) (?P<player>[^\s]+(?:\[.+\])?) := (?P<command>.+)$',
        r'execute store result score \g<player> \g<objective> run \g<command>',
    ],
    'SCORE_STORE_SELF': [
        r'^score (?P<objective>[^\s]+) := (?P<command>.+)$',
        r'execute store result score @s \g<objective> run \g<command>',
    ],
    'SCORE_OPERATION_TARGET_TARGET': [
        r'^score (?P<objective1>[^\s]+) (?P<player1>[^\s]+(?:\[.+\])?) (?P<operation>[\%\*\+\-\=\<\>]*) (?P<objective2>[^\s]+) (?P<player2>[^\s]+(?:\[.+\])?)$',
        r'scoreboard players operation \g<player1> \g<objective1> \g<operation> \g<player2> \g<objective2>',
    ],
    'SCORE_OPERATION_SELF_TARGET': [
        r'^score (?P<objective1>[^\s]+) (?P<operation>[\%\*\+\-\=\<\>]*) (?P<objective2>[^\s]+) (?P<player2>[^\s]+(?:\[.+\])?)$',
        r'scoreboard players operation @s \g<objective1> \g<operation> \g<player2> \g<objective2>',
    ],
    'SCORE_OPERATION_TARGET_SELF': [
        r'^score (?P<objective1>[^\s]+) (?P<player1>[^\s]+(?:\[.+\])?) (?P<operation>[\%\*\+\-\=\<\>]*) (?P<objective2>[^\s]+)$',
        r'scoreboard players operation \g<player1> \g<objective1> \g<operation> @s \g<objective2>',
    ],
    'SCORE_OPERATION_SELF_SELF': [
        r'^score (?P<objective1>[^\s]+) (?P<operation>[\%\*\+\-\=\<\>]*) (?P<objective2>[^\s]+)$',
        r'scoreboard players operation @s \g<objective1> \g<operation> @s \g<objective2>',
    ],
}


class Line():
    def __init__(self, text: str) -> None:
        self._indent: int = self._set_indent(text)
        # type: COMMAND, COMMENT, SoC (Start of Command), EoC (End of Command),
        #       EMPTY, EoF (End of File), CoC (Continuation of Command), MCPY, CONTINUOUS
        self._type: list[str] = []
        self._text: str = self._remove_indent(text)
        self._mcf: str = ''
        self._parent: Line = Empty
        self._children: list[Line] = []

    def _set_indent(self, text: str) -> int:
        return len(re.findall(settings['tab_style'], text))

    def _remove_indent(self, text: str) -> str:
        return re.sub(settings['tab_style'], '', text)

    def set_indent(self, indent: int) -> None:
        self._indent = indent

    def get_indent(self) -> int:
        return self._indent

    def get_text(self) -> str:
        return self._text

    def set_text(self, text) -> None:
        self._text = text

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

    def set_mcf(self, code: str) -> None:
        self._mcf = code

    def get_mcf(self) -> str:
        return self._mcf

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
    new_lines: list[Line] = []

    with open(file_path) as f:
        text_lines: list[str] = newline_to_list(f.read())

    for line in text_lines:
        line = re.sub('(?:\s*|\t*)$', '', line)

        if (not settings['keep_comment'] and is_mcf_comment(line)) or (not settings['keep_empty_lines'] and is_mcf_empty(line)):
            continue

        new_lines.append(Line(line))

    return new_lines


def lines_to_text(lines: list['Line']) -> str:
    text: str = ''

    for line in lines:
        if 'EoC' in line.get_type():
            text += line.get_mcf()
        elif 'COMMENT' in line.get_type() or 'EMPTY' in line.get_type():
            text += line.get_text()

        if 'EoF' not in line.get_type() and 'CONTINUOUS' not in line.get_type():
            text += '\n'

        if line.get_children() != []:
            text += lines_to_text(line.get_children())

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
    return any(re.search(pattern, text) for pattern in mcpy_patterns.values())


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
            current_path += f'{i}/'
            if not os.path.exists(current_path):
                os.mkdir(current_path)


def set_lines_type(lines: list[Line]) -> list[Line]:
    current_indent: int = 0

    for line in lines:
        if lines[-1] == line:
            line.add_type('EoF')

        if is_mcf_CoC(line.get_text()):
            line.add_type('CONTINUOUS')

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
        print(f"{tabs}- {line.get_mcf()}")

        if line.get_children() != []:
            print_lines_tree(line.get_children(), f"{tabs}  ")


def set_lines_children(lines: list[Line]) -> list[Line]:
    new_lines: list[Line] = []
    prev_line: Line = Empty

    for line in lines:
        if line.get_parent() == Empty:
            current_indent: int = 0
        else:
            current_indent: int = line.get_parent().get_indent() + 1
        if (not settings['indented_comment'] and 'COMMENT' in line.get_type()) or 'EMPTY' in line.get_type():
            if prev_line == Empty:
                line.set_indent(current_indent)
            elif 'CONTINUOUS' in prev_line.get_type():
                line.set_indent(prev_line.get_indent() + 1)
            else:
                line.set_indent(prev_line.get_indent())

        if line.get_indent() == current_indent:
            new_lines.append(line)
        elif line.get_indent() > current_indent:
            line.set_parent(new_lines[-1])
            new_lines[-1].add_children(line)

        prev_line = line

    for line in new_lines:
        if line.get_children() != []:
            line.set_children(set_lines_children(line.get_children()))

    return new_lines


def lines_text_to_mcf(lines: list[Line]) -> list[Line]:
    for line in lines:
        if line.get_parent() == Empty:
            prev_mcf: str = ''
        else:
            prev_mcf: str = line.get_parent().get_mcf()

        if 'SoC' in line.get_type():
            text: str = re.sub(r':(?:\s*|\t*)$', '', line.get_text())
            line.set_mcf(f'execute {text}')
        elif 'CoC' in line.get_type():
            text: str = re.sub(r':(?:\s*|\t*)$', '', line.get_text())
            line.set_mcf(f'{prev_mcf} {text}')

            if not re.search(r'^execute ', line.get_mcf()):
                line.set_mcf(f'execute{line.get_mcf()}')
        elif 'EoC' in line.get_type():
            if not prev_mcf:
                line.set_mcf(line.get_text())
            else:
                line.set_mcf(f'{prev_mcf} run {line.get_text()}')
        else:
            line.set_mcf(prev_mcf)

        if line.get_children() != []:
            line.set_children(lines_text_to_mcf(
                line.get_children()))

    return lines


def which_snippet(text: str) -> bool:
    return next((key for key, pattern in snippet_patterns.items() if re.search(pattern[0], text)), '')


def snippets_to_mcf(lines: list[Line]) -> list[Line]:
    for line in lines:
        snippet_key = which_snippet(line.get_text())
        if snippet_key != '':
            line.set_text(re.sub(
                snippet_patterns[snippet_key][0], snippet_patterns[snippet_key][1], line.get_text()))

        if line.get_children() != []:
            line.set_children(snippets_to_mcf(line.get_children()))

    return lines


def mcpy_for_range(line: Line) -> Line:
    start: int = int(
        re.sub(mcpy_patterns['FOR_RANGE'], '\g<start>', line.get_text()))
    end: int = int(
        re.sub(mcpy_patterns['FOR_RANGE'], '\g<end>', line.get_text()))
    name: str = re.sub(mcpy_patterns['FOR_RANGE'], '\g<name>', line.get_text())

    new_children: list[Line] = []
    for i in range(start, end):
        for child in line.get_children():
            new_children.append(mcpy_for_recursion(deepcopy(child), name, i))
            new_children[-1].set_parent(line)
    line.set_children(new_children)

    return line


def mcpy_for_recursion(line: Line, name: str, i) -> Line:
    line.set_text(line.get_text().replace(name, str(i)))

    if line.get_children() != []:
        for child in line.get_children():
            child.set_parent(line)
            mcpy_for_recursion(child, name, i)

    return line


def process_mcpy(lines: list[Line]) -> list[Line]:
    reprocess = False

    for line in lines:
        if 'MCPY' in line.get_type() and 'PROCESSED' not in line.get_type():
            if 'FOR_RANGE' in line.get_type():
                line = mcpy_for_range(line)
            line.add_type('PROCESSED')
            reprocess = True
            break

        if line.get_children() != []:
            line.set_children(process_mcpy(line.get_children()))

    if reprocess:
        lines = process_mcpy(lines)

    return lines


def compile(file_path: str) -> None:
    lines: list[str] = text_to_lines(file_path)
    lines = set_lines_type(lines)
    lines = set_lines_children(lines)
    lines = snippets_to_mcf(lines)
    lines = process_mcpy(lines)
    lines = lines_text_to_mcf(lines)

    # print(f'\n\n\n{file_path}')
    # print_lines_tree(lines)

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
