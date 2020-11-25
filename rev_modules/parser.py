def parse(lines:dict, returnable = False):
    new_lines = []
    execute_base = ""
    for i in range(0, len(lines)):
        has_excluded = hasExcludedCommand(lines[i]["line"])
        if has_excluded == True:
            new_lines.append(intoCommands(lines[i]["line"]))
            if hasChild(i, lines):
                parse(lines[i+1], returnable = True)
        else:
            new_lines.append(lines[i]["line"])
    print(new_lines)

def hasExcludedCommand(line:str):
    excluded_commands = ["as", "at"]
    words = line.split(" ")
    if words[0] == "execute":
        return False
    for word in words:
        for excluded_word in excluded_commands:
            if word == excluded_word:
                return True
    return False

def hasChild(index, lines):
    if lines[index]["indents"] < lines[index+1]["indents"]:
        return True

def intoCommands(line:str):
    words = line.split(" ")
    new_line = "execute"
    for i in range(0, len(words)):
        if words[i] == "as":
            new_line += " {} {}".format(words[i], words[i+1])
    return new_line