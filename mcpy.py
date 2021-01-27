import random
import re
import os
import json
import shutil
import string
import time
from loguru import logger


class UserSettings:
    def __init__(self, watch_delay = 5, dist = './dist/', base = './mcpy/',
    tab_style = "    ", obfuscate = False, keep_unused_obfuscated_string = False,
    keep_comment = False) -> None:
        super().__init__()
        self.watch_delay = watch_delay
        self.dist = dist
        self.base = base
        self.tab_style = tab_style
        self.obfuscate = obfuscate
        self.keep_unused_obfuscated_string = keep_unused_obfuscated_string
        self.settings_version = settings_version
        self.keep_comment = keep_comment
    

    def load(self):
        f = json.loads(readFile('./user_settings.json'))
        self.watch_delay = f['watch_delay']
        self.dist = f['dist']
        self.base = f['base']
        self.tab_style = f['tab_style']
        self.obfuscate = f['obfuscate']
        self.keep_unused_obfuscated_string = f['keep_unused_obfuscated_string']
        self.settings_version = f['settings_version']
        self.keep_comment = f['keep_comment']
    

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
    def __init__(self:object, text:str, indent:int, no:int, parent='', childs = []) -> None:
        super().__init__()
        self.text = text
        self.indent = indent
        self.no = no
        self.parent = parent
        self.childs = childs


tokens = [
    Tokenizer(r'^#.+', 'COMMENT'),
    Tokenizer(r'^def\s.+\((.+|)\):$', 'DEFINE-FUNCTION'),
    Tokenizer(r'^.+\((.+|)\)$', 'CALL-FUNCTION'),
    Tokenizer(r'^as\sat\s.+:$', 'ASAT'),
    Tokenizer(r'^else:$', 'ELSE'),
    Tokenizer(r'^(if|unless).+matches\s\[.+(,\s.+)*,\s.+\]:$', 'MULTI-MATCH'),
    Tokenizer(r'^.+:$', 'EXECUTE'),
    Tokenizer(r'^score\s.+\s(.+|.+\s\".+\")$', 'SCORE-DEFINE', 'scoreboard objectives add {} {} {}'),
    Tokenizer(r'^.+\s.+\s=\s\d+$', 'SCORE-SET', 'scoreboard players set {} {} {}'),
    Tokenizer(r'^.+\s=\s\d+$', 'SCORE-SET-SELF', 'scoreboard players set {} {} {}'),
    Tokenizer(r'^.+\s.+\s\+=\s\d+$', 'SCORE-ADD', 'scoreboard players add {} {} {}'),
    Tokenizer(r'^.+\s\+=\s\d+$', 'SCORE-ADD-SELF', 'scoreboard players add {} {} {}'),
    Tokenizer(r'^.+\s.+\s\-=\s\d+$', 'SCORE-SUBTRACT', 'scoreboard players remove {} {} {}'),
    Tokenizer(r'^.+\s-=\s\d+$', 'SCORE-SUBTRACT-SELF', 'scoreboard players remove {} {} {}'),
    Tokenizer(r'^.+\s.+\s\:=\s.+$', 'SCORE-STORE', 'store result score {} {} run {}'),
    Tokenizer(r'^.+\s:=\s.+$', 'SCORE-STORE-SELF', 'store result score {} {} run {}'),
    Tokenizer(r'^.+\s(%|\*|\+|\-|\\|)(=|<|>|(><))\s.+$', 'SCORE-OPERATION', 'scoreboard players operation {} {} {} {} {}'),
    Tokenizer(r'^obf\s.+$', 'OBFUSCATE'),
    Tokenizer(r'^.+$', 'COMMAND'),
]


@logger.catch
def main(f_path:str):
    logger.info(f'Reading {f_path}')
    text = readFile(f_path)
    logger.success(f'Read {f_path}')

    logger.info('Converting text to list')
    lines = listToLines(linesToList(text))
    logger.success('Converted text to list')
    
    logger.info('Precompiling')
    lines = precompile(lines)
    logger.success('Precompiling finished')

    logger.info('Compiling Mcpy execute to Mcfunction execute')
    lines = getParent(lines)
    logger.success('Compiled Mcpy execute to Mcfunction execute')

    logger.info('Compiling Mcpy score ot Mcfunction scoreboard')
    lines = scoreToCommands(lines)
    logger.success('Compiled Mcpy score ot Mcfunction scoreboard')

    lines_str = ''

    logger.info('Converting list to text')
    for line in lines:
        lines_str += f'{line.parent}{line.text}\n'
    lines_str = lines_str.replace('\n\n', '\n')
    logger.success('Converted list to text')

    if settings.obfuscate:
        logger.info('Obfuscating...')
        lines_str = obfuscate(lines_str)
        logger.success('Obfuscated')

    writeOutputFiles(lines_str, f_path)


def precompile(lines:list):
    global user_functions
    skip_count = 0
    new_lines = []
    for idx, line in enumerate(lines):
        if skip_count == 0:
            for token in tokens:
                if re.match(token.pattern, line.text):
                    if token.kind == 'MULTI-MATCH':
                        line.childs = getChild(idx, lines)
                        skip_count = len(line.childs) + 1 # Skip the real child

                        base = re.sub(r'\[.+\]:$', '', line.text)
                        values = re.sub(r'^(if|unless).+matches\s\[', '', line.text)
                        values = re.sub(r'\]:$', '', values)
                        values = re.split(r',\s|,', values)

                        # For nested multi match
                        line.childs = precompile(line.childs)
                        
                        for value in values:
                            new_lines += [Line(base+value+':', line.indent, line.no, line.parent, line.childs)]
                            for child in line.childs:
                                new_lines += [child]

                    elif token.kind == 'DEFINE-FUNCTION':
                        line.childs = getChild(idx, lines)
                        skip_count = len(line.childs) + 1 # Skip the real child
                        
                        for child in line.childs:
                            child.indent = child.indent - 1
                        
                        line.childs = precompile(line.childs)

                        # Get function name and arguments
                        arg = re.sub(r'^def\s.+\(', '', line.text)
                        arg = re.sub(r'\):$', '', arg)
                        args = re.split(r',\s|,', arg)
                        line.text = re.sub('^def ', '', line.text)
                        line.text = re.sub(r'\((.+|)\):$', '', line.text)
                        user_functions[line.text] = {'args': args, 'childs': line.childs}
                    
                    elif token.kind == 'CALL-FUNCTION':
                        for function in user_functions.keys():
                            skip_count = 1 # Skip the current line
                            args_str = re.sub(r'^.+\(', '', line.text)
                            args_str = re.sub(r'\)$', '', args_str)
                            args_found = re.findall(r'(?:"|\')(.*?)(?:"|\')', args_str)
                            args_str = re.sub(r'(?:"|\')(.*?)(?:"|\')', 'SKIP', args_str)
                            args_splited = re.split(r',\s|,', args_str)
                            current_arg_skip_idx = 0
                            args = []

                            for arg in args_splited:
                                if arg == 'SKIP':
                                    args += [args_found[current_arg_skip_idx]]
                                    current_arg_skip_idx += 1
                                else:
                                    args += [arg]

                            if re.match(function+r'\(', line.text):
                                new_child = []
                                for child in user_functions[function]['childs']:
                                    new_child = Line(child.text, child.indent+line.indent, child.no, child.parent, child.childs)
                                    for i in range(len(args)):
                                        if args[i] == '':
                                            args[i] = user_functions[function]['args'][i]
                                        new_child.text = new_child.text.replace(user_functions[function]['args'][i], args[i])
                                    new_lines += [new_child]

        if skip_count == 0: # Not the or the child of a multi match? just add it
            new_lines += [line]
        else:
            skip_count -= 1

    return new_lines


def getChild(index:int, lines:list):
    parent = lines[index]
    childs = []
    for idx, line in enumerate(lines):
        if idx > index and line.indent > parent.indent:
            childs += [line]
        elif idx > index and line.indent <= parent.indent:
            return childs
    return childs

def obfuscate(lines_str:str):
    global obfuscated_data
    global used_obfuscated_data
    
    # Sort from longest to shorest, to avoid string replacement issue
    obfuscated_data = dict(sorted(obfuscated_data.items(), key=lambda item: (-len(item[0]), item[0])))
    used_obfuscated_data = dict(sorted(used_obfuscated_data.items(), key=lambda item: (-len(item[0]), item[0])))

    for data in obfuscated_data:
        lines_str = lines_str.replace(data, obfuscated_data[data])

    if settings.keep_unused_obfuscated_string:
        writeFile('./obfuscated_data.json', json.dumps(obfuscated_data, indent=4), False)
    else:
        writeFile('./obfuscated_data.json', json.dumps(used_obfuscated_data, indent=4), False)

    return lines_str


def scoreToCommands(lines):
    for line in lines:
        for token in tokens:
            if re.match(token.pattern, line.text):
                if token.kind == 'SCORE-DEFINE':
                    temp = re.sub('^score ', '', line.text)
                    temp = temp.split(maxsplit=2)

                    if len(temp) == 3:
                        line.text = token.command.format(temp[0], temp[1], temp[2])
                    elif len(temp) == 2:
                        line.text = token.command.format(temp[0], temp[1], '')
                    
                    # Obfuscate
                    if settings.obfuscate:
                        if obfuscated_data.get(temp[0]) == None:
                            obfuscated_data[temp[0]] = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(16))
                        used_obfuscated_data[temp[0]] = obfuscated_data[temp[0]]

                    break
                elif token.kind == 'OBFUSCATE':
                    temp = re.sub(r'^obf\s', '', line.text)
                    temp = re.sub(r'\"|\'|', '', temp)
                    # Obfuscate
                    if settings.obfuscate:
                        if obfuscated_data.get(temp) == None:
                            obfuscated_data[temp] = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(16))
                        used_obfuscated_data[temp] = obfuscated_data[temp]
                    line.text = ''
                    line.parent = ''
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
                    if re.match(r'.+\s.+\s(%|\*|\+|\-|\\|)(=|<|>|(><))\s.+\s.+', line.text):
                        line.text = token.command.format(temp[1], temp[0], temp[2], temp[4], temp[3])
                        break
                    elif re.match(r'.+\s(%|\*|\+|\-|\\|)(=|<|>|(><))\s.+\s.+', line.text):
                        line.text = token.command.format('@s', temp[0], temp[1], temp[3], temp[2])
                        break
                    elif re.match(r'.+\s.+\s(%|\*|\+|\-|\\|)(=|<|>|(><))\s.+', line.text):
                        line.text = token.command.format(temp[1], temp[0], temp[2], '@s', temp[3])
                        break
                    elif re.match(r'.+\s(%|\*|\+|\-|\\|)(=|<|>|(><))\s.+', line.text):
                        line.text = token.command.format('@s', temp[0], temp[1], '@s', temp[2])
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
        new_lines += [Line(text, indent, no)]
    return new_lines


def linesToList(text:str):
    return text.split('\n')


def getParent(lines:list): # TODO Rename this to some thing more suitable
    current_parents = []
    current_indent = -1
    new_lines = []
    for line in lines:
        for token in tokens:
            if re.match(token.pattern, line.text):
                if token.kind == 'COMMENT':
                    if settings.keep_comment and not settings.obfuscate:
                        new_lines += [line]
                    break
                elif token.kind == 'ASAT':
                    temp = line.text.replace('at ', '')
                    temp = temp[:-1]
                    line.text = f'{temp} at @s:'
                elif token.kind == 'MULTI-MATCH':
                    break
                elif token.kind == 'EXECUTE' and current_indent < line.indent:
                    current_parents += [line.text[:-1]]
                    current_indent = line.indent
                    break
                elif token.kind == 'EXECUTE' and current_indent >= line.indent:
                    current_parents = current_parents[:line.indent+1]
                    try:
                        current_parents[line.indent] = line.text[:-1]
                    except IndexError:
                        current_parents += [line.text[:-1]]
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

    logger.info(f'Writing output file {f_path}')
    with open(f_path, 'w') as file:
        file.write(data)


def generatePath(f_path:str):
    f_path = f_path.replace(os.path.basename(f_path), '').replace('./', '')
    f_path = re.split(r'/|\\', f_path)
    current_path = './'
    for i in f_path:
        if i != '':
            current_path += i + '/'
            if not os.path.exists(current_path):
                os.mkdir(current_path)


# From https://appdividend.com/2020/01/20/python-list-of-files-in-directory-and-subdirectories/
def getFiles(dirPath):
    listOfFile = os.listdir(dirPath)
    completeFileList = []
    for file in listOfFile:
        completePath = os.path.join(dirPath, file)
        if os.path.isdir(completePath):
            completeFileList += getFiles(completePath)
        elif completePath.endswith('.mcpy'):
            completeFileList.append(completePath)

    return completeFileList


def writeOutputFiles(lines_str:str, f_path:str):
    # Write .mcfunction
    f_path = f_path.replace('.mcpy', '.mcfunction')
    writeFile(f_path, lines_str)


def deleteDist():
    try:
        shutil.rmtree(settings.dist)
        logger.success('Deleted dist folder')
    except FileNotFoundError:
        logger.info('Dist folder not found')
        return


def isModified():
    global files_last_modified
    files_newly_modified = []
    hasModified = False

    if files_last_modified == []:
        for f_path in files_path:
            files_last_modified  += [os.stat(f_path).st_mtime]
        hasModified = True
    else:
        for f_path in files_path:
            files_newly_modified += [os.stat(f_path).st_mtime]
        
        hasModified = files_last_modified != files_newly_modified
        files_last_modified = files_newly_modified

    return hasModified


if __name__ == '__main__':
    logger.add('mcpy.log', mode='w')
    logger.info('Made by Revon Zev')

    files_last_modified = []
    settings_version = 0

    # user_settings.json
    settings = UserSettings()
    try:
        logger.success('user_settings.json loaded')
        settings.load()
    except FileNotFoundError:
        logger.info('user_settings.json not found. Generating new user_settings.json')
        settings.generate()
    except KeyError:
        logger.info('user_settings.json KeyError. Generating new user_settings.json')
        settings.generate(True)
    
    if settings.settings_version != settings_version:
        logger.warning(f'user_settings.json version is old. current: {settings.settings_version}, latest: {settings_version}. Generating new user_settings.json')
        logger.info('Old settings can be found at user_settings_old.json')
        settings.generate(True)

    while True:
        try:
            files_path = getFiles(settings.base)
        except FileNotFoundError:
            os.mkdir(settings.base)
            files_path = getFiles(settings.base)

        skip_compile = False
        if files_path == []:
            logger.info('Project is empty. Compiling skipped')
            skip_compile = True

        if isModified() and not skip_compile:
            logger.info('Compiling...')
            user_functions = {}

            # obfuscated_data.json
            used_obfuscated_data = {}
            try:
                obfuscated_data = json.loads(readFile('./obfuscated_data.json'))
                logger.success('obfuscated_data.json loaded')
            except FileNotFoundError:
                logger.info('obfuscated_data.json not found. Skipping')
                obfuscated_data = {}

            logger.info('Deleting dist path')
            deleteDist()

            for file in files_path:
                logger.info(f'Generating {file}')
                main(file)
                logger.info(f'Generated {file}')
            
            logger.success('Compiled')
            
        if settings.watch_delay != 0:
            time.sleep(settings.watch_delay)
        else:
            input('Enter to compile')