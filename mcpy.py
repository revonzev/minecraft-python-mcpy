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
    Tokenizer(r'^.+:$', 'EXECUTE'),
    Tokenizer(r'^.+$', 'COMMAND'),
]


def main(text:str):
    lines = listToLines(linesToList(text))
    lines = getParent(lines)
    for i in lines: print(i.parent+i.text)


def listToLines(lines:list):
    new_lines = []
    no = 0
    for line in lines:
        text = re.sub('\s\s\s\s', '', line)
        indent = len(re.findall('\s\s\s\s|\t', line))
        no += 1
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
                elif token.kind == 'COMMAND' and new_lines != []:
                    current_parents = current_parents[:line.indent]
                    if line.indent == 0:
                        current_indent = -1
                        new_lines += [line]
                        break
                    else:
                        current_indent = line.indent
                        new_lines += [Line(line.text, line.indent, line.no, 'execute '+' '.join(current_parents)+' run ')]
                        break
                else:
                    new_lines += [line]
                    break

    return new_lines


if __name__ == '__main__':
    test_str = 'say Hi\nas at @a:\n    at @p:\n        say Hello\n    say Good day\nsay HORA\nas @e:\n    say Hola\nsay Heyo'
    main(test_str)