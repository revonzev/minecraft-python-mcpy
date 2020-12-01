import json
import re
import os
import shutil
import copy
import random
import string

converter = {}
user_settings = {}
obfuscated_str = {}
used_obfuscated_str = {}
files_path = []

def main():
    deleteDist()

    individualFileOrGroup()

    for f_path in files_path:
        raw_text = readFile(f_path)
        text_lines = raw_text.split('\n')

        # Process
        tabbed_lines = tabsReader(text_lines)
        precompiled_lines = precompiler(tabbed_lines)
        compiled_lines = compiler(precompiled_lines)
        postcompiled_lines = postcompiler(compiled_lines)
        
        writeOutputFiles(postcompiled_lines, f_path)


def writeOutputFiles(lines:list, f_path:str):
    # Write .mcfunction
    f_to_w = f_path.replace('.mcpy', '.mcfunction')
    text_to_w = '\n'.join(lines)
    writeFile('./'+f_to_w, text_to_w)
    
    writeFile(f_to_w, text_to_w)

    # Write obfuscation data
    if user_settings['keep_unused_obfuscated_string'] or not user_settings['obfuscate']:
        f_to_w = './obfuscated_data.json'
        text_to_w = json.dumps(obfuscated_str)
    else:
        f_to_w = './unused_obfuscated_data.json'
        text_to_w = json.dumps(used_obfuscated_str)

    writeFile('./'+f_to_w, text_to_w, False)


def individualFileOrGroup():
    global files_path
    
    if user_settings['individual_file']:
        for i in user_settings['files']:
            files_path += [user_settings['base']+i]
    else:
        files_path = getFiles(user_settings['base'])


def postcompiler(lines:list):
    new_lines = []
    if user_settings['obfuscate']:
        lines = obfuscate_lines(lines)

    for i in range(len(lines)):
        if re.match(r'^#.+$', lines[i]) and not user_settings['keep_comment']:
            continue
        # Skip empty lines
        elif lines[i] == '':
            continue
        else:
            new_lines += [lines[i]]

    return new_lines


def obfuscate_lines(lines:list):
    obfuscated_str_keys = list(obfuscated_str.keys())
    new_lines = []
    for i in range(len(lines)):
        # Obfuscate strings
        for ia in range(len(obfuscated_str)):
            lines[i] = lines[i].replace(obfuscated_str_keys[ia], obfuscated_str[obfuscated_str_keys[ia]])

        new_lines += [lines[i]]

    return new_lines


def compiler(lines:list):
    for i in range(len(lines)):
        lines[i] = mcpyVars(lines[i])

    # Execute and compile it
    lines = mcpyExecute(lines)

    return lines


def mcpyExecute(lines:list):
    new_lines = []
    parent = []
    
    for i in range(0, len(lines)):
        lines[i]['execute'] = False

        # Is it part of execute command? change it into mincraft command
        for execute in converter['executes']:
            if re.match(execute['pattern'], lines[i]['value']):
                lines[i]['execute'] = execute['execute']
                for ia in execute['replace']:
                    if ia == ':':
                        lines[i]['value'] = lines[i]['value'][:-1]
                    else:
                        lines[i]['value'] = lines[i]['value'].replace(ia, '')
                # Compile the Mcpy execute line to Minecraft's
                lines[i]['value'] = execute['command'].format(value=lines[i]['value'])
        
        # If there is no execute chain yet, make one
        if lines[i]['execute'] == True and parent == []:
            parent += [{'value':lines[i]['value'], 'tabs':lines[i]['tabs']}]

        # There's already a chain? let's keep it going
        elif parent != [] and lines[i]['tabs'] > parent[0]['tabs']:
            # Is it part of an execute command?
            if lines[i]['execute'] == True:
                for ia in range(0, lines[i]['tabs']):
                    parent += [{'tabs': ia, 'value': ''}]
                parent = parent[:lines[i]['tabs']+1]
                parent[lines[i]['tabs']]['value'] = parent[lines[i]['tabs']-1]['value'] + ' ' + lines[i]['value']
            else:
                new_lines += ['execute ' + parent[lines[i]['tabs']-1]['value'] + ' run ' + lines[i]['value']]
                try:
                    for ia in range(1, len(lines[i:])):
                        # Skip comments
                        if lines[i+ia]['tabs'] == -1:
                            continue
                        # Is the next line not a child? If yes, reset the parent
                        elif lines[i+ia]['tabs'] <= parent[0]['tabs']:
                            parent = []
                            break
                        else: break
                # Reached end of file
                except IndexError:
                    parent = []
        # It's a store command without execute? Put it in
        elif re.match('^store.+$', lines[i]['value']):
            new_lines += ['execute ' + lines[i]['value']]
        # A normal command? Just add it to new lines
        else:
            new_lines += [lines[i]['value']]

    return new_lines

def mcpyVars(line:str):
    for variable in converter['variables']:
        global obfuscated_str
        global used_obfuscated_str
        if re.match(variable['pattern'], line['value']):
            temp = line['value'].split(' ')

            for i in variable['replace']:
                line['value'] = line['value'].replace(i, '')
            
            # Define scoreboard and tags
            if variable['kind'] == 'declare':
                if user_settings['obfuscate'] == True:
                    try:
                        obfuscated_temp = obfuscated_str[temp[1]]
                    except KeyError:
                        obfuscated_temp = ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(16))
                        obfuscated_str[temp[1]] = obfuscated_temp
                    used_obfuscated_str[temp[1]] = obfuscated_str[temp[1]]
                    # Sort from longest to shorest, to avoid string replacement issue
                    obfuscated_str = dict(sorted(obfuscated_str.items(), key=lambda item: (-len(item[0]), item[0])))
                    used_obfuscated_str = dict(sorted(used_obfuscated_str.items(), key=lambda item: (-len(item[0]), item[0])))
                    line['value'] = re.sub(r'(\"|\').+(\"|\')', '""', line['value'])
                line['value'] = variable['command'].format(value=line['value'])
            
            # Set / add / subtract scoreboard
            elif variable['kind'] == 'set-add-remove':
                if temp[2] == '=':
                    temp[2] = 'set'
                elif temp[2] == '+=':
                    temp[2] = 'add'
                elif temp[2] == '-=':
                    temp[2] = 'remove'
                
                line['value'] = variable['command'].format(objective=temp[0], target=temp[1], operation=temp[2], score=temp[3])
            
            # Operation scoreboard
            elif variable['kind'] == 'operation':
                line['value'] = variable['command'].format(objective_1=temp[0], target_1=temp[1], operation=temp[2], objective_2=temp[3], target_2=temp[4])
            
            # Store result of command
            elif variable['kind'] == 'result':
                temp = line['value'].split(' ', 2)
                line['value'] = variable['command'].format(objective=temp[0], target=temp[1], command=temp[2])

    return line
            

def precompiler(lines:list):
    for i in range(0, len(lines)):
        if lines[i]['value'] == 'else:':
            lines[i]['value'] = mcpyElse(lines[:i+1])
        elif re.match(r'^(if|unless).+matches\s\[.+(,\s.+)*,\s.+\]:$', lines[i]['value']):
            multi_ifs = mcpyMultiIfMatches(lines[i:])
            # Remove original child
            for _ in range(0, multi_ifs[0]+1):
                lines.pop(i)
            multi_ifs.pop(0)
            # Insert the ifs
            for an_if in reversed(multi_ifs):
                lines.insert(i, copy.deepcopy(an_if))
            # Continue but with the new lines
            precompiled_lines = precompiler(lines)
            return precompiled_lines

    return lines


def mcpyMultiIfMatches(lines:list):
    data = re.split(r'\[|, |]', lines[0]['value'])[1:-1]
    lines[0]['value'] = lines[0]['value'].replace(',', '')
    lines[0]['value'] = lines[0]['value'].replace('[', '')
    lines[0]['value'] = lines[0]['value'].replace(']', '')
    lines_child = []
    multi_ifs = []

    # Find the child of the multi if matches
    for i in range(0, len(lines)):
        # Skip first line (the 'if ... match ... []')
        if lines[i]['value'] == lines[0]['value']:
            continue

        if lines[i]['tabs'] > lines[0]['tabs']:
            lines_child += [lines[i]]
        # Skip comments
        elif lines[i]['tabs'] == -1:
            continue
        else:
            break
    
    # Generate the multiple if lines
    for i in range(len(data)):
        if_line = copy.deepcopy(lines[0])

        for ia in range(len(data)):
            if data[i] != data[ia]:
                if_line['value'] = if_line['value'].replace(' '+data[ia], '')

        multi_ifs += [if_line]
        multi_ifs += lines_child

    multi_ifs.insert(0, len(lines_child))
    return multi_ifs

def mcpyElse(lines:list):
    else_line = ''

    for i in range(len(lines)-1, 0, -1):
        # Skip 'else:'
        if lines[i]['value'] == 'else':
            continue

        # Is the line in the same indentation
        # And an if or unless?
        elif re.match(r'^(if|unless).+:$', lines[i]['value']) and lines[i]['tabs'] == lines[-1]['tabs']:
            else_line = lines[i]['value'].replace('if', 'khdth')
            else_line = else_line.replace('unless', 'if')
            else_line = else_line.replace('khdth', 'unless')
            break

    return else_line

def tabsReader(lines:list):
    tabbed_lines = []
    
    for line in lines:
        tabbed_line = {'value': '', 'tabs': 0}
        line = line.split(user_settings['tab_style'])
        
        for i in line:
            if i == '':
                tabbed_line['tabs'] += 1
            else:
                tabbed_line['value'] = i
        
        # Is it a comment?
        if re.match(r'^(#|//).+$', tabbed_line['value']):
            tabbed_line['tabs'] = -1
            tabbed_line['value'] = tabbed_line['value'].replace('//', '#')
        
        # Remove empty line
        if tabbed_line['value'] == '':
            continue
        else:
            tabbed_lines += [tabbed_line]

    return tabbed_lines


def readFile(f_path:str):
    with open(f_path, 'r') as file:
        file_inner = file.read()
    return file_inner


def writeFile(f_path:str, data:str, dist=True):
    if dist == True:
        f_path = f_path.replace(user_settings['base'], '')
        f_path = f_path.replace('./', '')
        f_path = ''.join(user_settings['dist']+f_path)
    elif user_settings['base'] != './':
        f_path = f_path.replace(user_settings['base'], './')
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


# From https://appdividend.com/2020/01/20/python-list-of-files-in-directory-and-subdirectories/
def getFiles(dirPath):
    listOfFile = os.listdir(dirPath)
    completeFileList = []
    for file in listOfFile:
        completePath = os.path.join(dirPath, file)
        if os.path.isdir(completePath):
            completeFileList += getFiles(completePath)
        else:
            completeFileList.append(completePath)

    return completeFileList


def deleteDist():
    try:
        shutil.rmtree(user_settings['dist'])
    except FileNotFoundError:
        return


def generateUserSettings():
    global user_settings
    user_settings = {
        "individual_file": False,
        "files": [
            "my_files.mcpy"
        ],
        "dist": "./dist/",
        "base": "./tests/",
        "tab_style": "    ",
        "keep_comment": True,
        "obfuscate": False,
        "keep_unused_obfuscated_string": False
    }

    writeFile('./user_settings.json', json.dumps(user_settings, indent=4), False)


if __name__ == '__main__':
    converter = json.loads(readFile('./converter.json'))

    try:
        user_settings = json.loads(readFile('./user_settings.json'))
    except FileNotFoundError:
        generateUserSettings()

    try:
        obfuscated_str = json.loads(readFile('./obfuscated_data.json'))
    except FileNotFoundError:
        pass
    main()