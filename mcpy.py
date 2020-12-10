import re
import os
import json

settings_version = 1


class UserSettings:
    def __init__(self, watch_delay = 5, individual_file = False, files = [], dist = './dist/', base = './',
    tab_style = "    ", obfuscate = False, keep_unused_obfuscated_string = False) -> None:
        super().__init__()
        self.watch_delay = watch_delay
        self.individual_file = individual_file
        self.files = files
        self.dist = dist
        self.base = base
        self.tab_style = tab_style
        self.obfuscate = obfuscate
        self.keep_unused_obfuscated_string = keep_unused_obfuscated_string
        self.settings_version = settings_version
    

    def load(self):
        f = json.loads(readFile('./user_settings.json'))
        self.watch_delay = f['watch_delay']
        self.individual_file = f['individual_file']
        self.files = f['files']
        self.dist = f['dist']
        self.base = f['base']
        self.tab_style = f['tab_style']
        self.obfuscate = f['obfuscate']
        self.keep_unused_obfuscated_string = f['keep_unused_obfuscated_string']
        self.settings_version = f['settings_version']
    

    def generate(self, keep_old_settings = False):
        if keep_old_settings:
            f = json.loads(readFile('./user_settings.json'))
            writeFile('./user_settings_old.json', json.dumps(f, indent=4), False)
        self.settings_version = settings_version
        writeFile('./user_settings.json', json.dumps(self.__dict__, indent=4), False)


class Tokenizer:
    def __init__(self:object, pattern:str, kind:str, command='') -> None:
        super().__init__()
        self.pattern = pattern
        self.command = command
        self.kind = kind


class Line:
    def __init__(self:object, text:str, indent:int, no:int, parent='') -> None:
        super().__init__()
        self.text = text
        self.indent = indent
        self.no = no
        self.parent = parent


tokens = [
    Tokenizer(r'^as\sat\s.+:$', 'ASAT'),
    Tokenizer(r'^else:$', 'ELSE'),
    Tokenizer(r'^.+:$', 'EXECUTE'),
    Tokenizer(r'^score\s.+\s(.+|.+\s\".+\")$', 'SCORE-DEFINE', 'scoreboard objectives add {} {} {}'),
    Tokenizer(r'^score\s.+\s=\s.+$', 'SCORE-SET', 'scoreboard players set {} {} {}'),
    Tokenizer(r'^.+\s.+\s(%|\*|\+|\-|\\|)(=|<|>|(><))\s.+\s.+$', 'SCORE-OPERATION', 'scoreboard players operation {} {} {} {} {}'),
    Tokenizer(r'^.+\s=\s.+$', 'SCORE-SET-SELF', 'scoreboard players set {} {} {}'),
    Tokenizer(r'^.+\s.+\s\+=\s.+$', 'SCORE-ADD', 'scoreboard players add {} {} {}'),
    Tokenizer(r'^.+\s\+=\s.+$', 'SCORE-ADD-SELF', 'scoreboard players add {} {} {}'),
    Tokenizer(r'^.+\s.+\s\-=\s.+$', 'SCORE-SUBTRACT', 'scoreboard players remove {} {} {}'),
    Tokenizer(r'^.+\s-=\s.+$', 'SCORE-SUBTRACT-SELF', 'scoreboard players remove {} {} {}'),
    Tokenizer(r'^.+\s.+\s\:=\s.+$', 'SCORE-STORE', 'store result score {} {} run {}'),
    Tokenizer(r'^.+\s:=\s.+$', 'SCORE-STORE-SELF', 'store result score {} {} run {}'),
    Tokenizer(r'^.+$', 'COMMAND'),
]


def main(text:str):
    lines = listToLines(linesToList(text))
    lines = getParent(lines)
    lines = scoreToCommands(lines)
    lines_str = ''
    for line in lines:
        lines_str += f'{line.parent}{line.text}\n'
    writeFile('./test.mcfunction', lines_str)


def scoreToCommands(lines):
    for line in lines:
        for token in tokens:
            if re.match(token.pattern, line.text):
                if token.kind == 'SCORE-DEFINE':
                    temp = re.sub('^score ', '', line.text)
                    temp = temp.split()
                    if len(temp) == 3:
                        line.text = token.command.format(temp[0], temp[1], temp[2])
                    elif len(temp) == 2:
                        line.text = token.command.format(temp[0], temp[1], '')
                    break
                elif token.kind == 'SCORE-SET':
                    temp = line.text.replace('= ', '', 1)
                    temp = temp.split()
                    line.text = token.command.format(temp[1], temp[0], temp[2])
                    break
                elif token.kind == 'SCORE-SET-SELF':
                    temp = line.text.replace('= ', '', 1)
                    temp = temp.split()
                    line.text = token.command.format('@s', temp[0], temp[1])
                    break
                elif token.kind == 'SCORE-ADD':
                    temp = line.text.replace('+= ', '', 1)
                    temp = temp.split()
                    line.text = token.command.format(temp[1], temp[0], temp[2])
                    break
                elif token.kind == 'SCORE-ADD-SELF':
                    temp = line.text.replace('+= ', '', 1)
                    temp = temp.split()
                    line.text = token.command.format('@s', temp[0], temp[1])
                    break
                elif token.kind == 'SCORE-SUBTRACT':
                    temp = line.text.replace('-= ', '', 1)
                    temp = temp.split()
                    line.text = token.command.format(temp[1], temp[0], temp[2])
                    break
                elif token.kind == 'SCORE-SUBTRACT-SELF':
                    temp = line.text.replace('-= ', '', 1)
                    temp = temp.split()
                    line.text = token.command.format('@s', temp[0], temp[1])
                    break
                elif token.kind == 'SCORE-OPERATION':
                    temp = line.text.split()
                    line.text = token.command.format(temp[1], temp[0], temp[2], temp[4], temp[3])
                    break
                elif token.kind == 'SCORE-STORE':
                    temp = line.text.replace(':= ', '', 1)
                    temp = temp.split(maxsplit=2)
                    line.text = token.command.format(temp[1], temp[0], temp[2])
                    if line.parent == '':
                        line.parent = 'execute '
                    break
                elif token.kind == 'SCORE-STORE-SELF':
                    temp = line.text.replace(':= ', '', 1)
                    temp = temp.split(maxsplit=1)
                    line.text = token.command.format('@s', temp[0], temp[1])
                    if line.parent == '':
                        line.parent = 'execute '
                    break
    return lines


def listToLines(lines:list):
    new_lines = []
    no = 0
    for line in lines:
        text = re.sub('\s\s\s\s|\t', '', line)
        indent = len(re.findall('\s\s\s\s|\t', line))
        no += 1
        if re.match(r'^#|//.+$', text):
            continue
        new_lines += [Line(text, indent, no)]
    return new_lines


def linesToList(text:str):
    return text.split('\n')


def getParent(lines:list):
    current_parents = []
    current_indent = -1
    new_lines = []
    for line in lines:
        for token in tokens:
            if re.match(token.pattern, line.text):
                if token.kind == 'ASAT':
                    temp = line.text.replace('at ', '')
                    temp = temp[:-1]
                    line.text = f'{temp} at @s:'
                elif token.kind == 'EXECUTE' and current_indent < line.indent:
                    current_parents += [line.text[:-1]]
                    current_indent = line.indent
                    break
                elif token.kind == 'EXECUTE' and current_indent >= line.indent:
                    current_parents = current_parents[:line.indent+1]
                    current_parents[line.indent] = line.text[:-1]
                    current_indent = line.indent
                    break
                elif token.kind == 'ELSE':
                    temp = re.sub(r'^if', 'kecvd', current_parents[line.indent])
                    temp = re.sub(r'^unless', 'if', temp)
                    current_parents[line.indent] = re.sub(r'^kecvd', 'unless', temp)
                    break
                else:
                    current_parents = current_parents[:line.indent]
                    if line.indent == 0:
                        current_indent = -1
                        new_lines += [line]
                        break
                    else:
                        current_indent = line.indent
                        new_lines += [Line(line.text, line.indent, line.no, 'execute '+' '.join(current_parents)+' run ')]
                        break

    return new_lines


def readFile(f_path:str):
    with open(f_path, 'r') as file:
        file_inner = file.read()
    return file_inner


def writeFile(f_path:str, data:str, dist=True):
    if dist == True:
        f_path = f_path.replace(settings.base, '')
        f_path = f_path.replace('./', '')
        f_path = ''.join(settings.dist+f_path)
    elif settings.base != './':
        f_path = f_path.replace(settings.base, './')

    generatePath(f_path)

    with open(f_path, 'w') as file:
        file.write(data)


def generatePath(f_path:str):
    f_path = f_path.replace(os.path.basename(f_path), '').replace('./', '')
    f_path = f_path.split('/')
    current_path = './'
    for i in f_path:
        if i != '':
            current_path += i + '/'
            if not os.path.exists(current_path):
                os.mkdir(current_path)


if __name__ == '__main__':
    settings = UserSettings()

    try:
        settings.load()
    except FileNotFoundError:
        settings.generate()
    except KeyError:
        settings.generate(True)
    
    if settings.settings_version != settings_version:
        settings.generate(True)

    main(readFile('./tests/test.mcpy'))