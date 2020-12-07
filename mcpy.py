import re


class Tokenizer:
    def __init__(self:object, pattern:str, kind:str, command='', replace=[]) -> None:
        super().__init__()
        self.pattern = pattern
        self.command = command
        self.replace = replace
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
    for i in lines: print(i.parent+i.text)


def scoreToCommands(lines):
    new_lines = []
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


if __name__ == '__main__':
    main(readFile('./tests/test.mcpy'))