from json import loads, dumps
from re import match, split, sub
from os import mkdir, path
from copy import deepcopy
from random import SystemRandom
from string import ascii_letters, digits

converter = {}
user_settings = {}
obfuscated_str = {}
used_obfuscated_str = {}

def mcpy():
	for file in user_settings['files']:
		raw_text = readFile(user_settings['base']+file)
		text_lines = raw_text.split('\n')

		# Process
		tabbed_lines = tabsReader(text_lines)
		precompiled_lines = precompiler(tabbed_lines)
		compiled_lines = compiler(precompiled_lines)
		postcompiled_lines = postcompiler(compiled_lines)
		
		mcfunction_file = file.replace('.mcpy', '.mcfunction')
		writeFile('./{}'.format(mcfunction_file), '\n'.join(postcompiled_lines))
		
		if user_settings['keep_unused_obfuscated_string'] or not user_settings['obfuscate']:
			writeFile('./{}'.format('obfuscated_data.json'), dumps(obfuscated_str), False)
		else:
			writeFile('./{}'.format('obfuscated_data.json'), dumps(used_obfuscated_str), False)


def postcompiler(lines:list):
	new_lines = []
	if user_settings['obfuscate']:
		lines = obfuscate_lines(lines)

	for i in range(0, len(lines)):
		if match(r'^#.+$', lines[i]) and not user_settings['keep_comment']:
			continue
		elif lines[i] == '':
			continue
		else:
			new_lines += [lines[i]]

	return new_lines


def obfuscate_lines(lines:list):
	obfuscated_str_keys = list(obfuscated_str.keys())
	new_lines = []
	for i in range(0, len(lines)):
		# Obfuscate scoreboard name
		for ia in range(0, len(obfuscated_str)):
			lines[i] = lines[i].replace(obfuscated_str_keys[ia], obfuscated_str[obfuscated_str_keys[ia]])
		
		new_lines += [lines[i]]
	
	return new_lines


def compiler(lines:list):
	for i in range(0, len(lines)):
		lines[i] = mcpyVars(lines[i])
	
	# Execute and compile it
	lines = mcpyExecute(lines)
	
	return lines


def mcpyExecute(lines:list):
	new_lines = []
	parent = []
	
	for i in range(0, len(lines)):
		lines[i]['execute'] = False

		# Is it part of execute command?
		for execute in converter['executes']:
			if match(execute['pattern'], lines[i]['value']):
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
				new_lines += ['execute ' + parent[-1]['value'] + ' run ' + lines[i]['value']]
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
				except IndexError:
					parent = []
		# It's a store command without execute? Put it in
		elif match('^store.+$', lines[i]['value']):
			new_lines += ['execute ' + lines[i]['value']]
		# A normal command? Just add it to new lines
		else:
			new_lines += [lines[i]['value']]

	return new_lines

def mcpyVars(line:str):
	for variable in converter['variables']:
		global obfuscated_str
		global used_obfuscated_str
		if match(variable['pattern'], line['value']):
			temp = line['value'].split(' ')

			for i in variable['replace']:
				line['value'] = line['value'].replace(i, '')
			
			# Define scoreboard and tags
			if variable['kind'] == 'declare':
				if user_settings['obfuscate'] == True:
					try:
						obfuscated_temp = obfuscated_str[temp[1]]
					except KeyError:
						obfuscated_temp = ''.join(SystemRandom().choice(ascii_letters + digits) for _ in range(16))
						obfuscated_str[temp[1]] = obfuscated_temp
					used_obfuscated_str[temp[1]] = obfuscated_str[temp[1]]
					# Sort from longest to shorest, to avoid string replacement issue
					obfuscated_str = dict(sorted(obfuscated_str.items(), key=lambda item: (-len(item[0]), item[0])))
					used_obfuscated_str = dict(sorted(used_obfuscated_str.items(), key=lambda item: (-len(item[0]), item[0])))
					line['value'] = sub(r'(\"|\').+(\"|\')', '""', line['value'])
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
		elif match(r'^(if|unless).+matches\s\[\d+(,\s\d+)*,\s\d+\]:$', lines[i]['value']):
			multi_ifs = mcpyMultiIfMatch(lines[i:])
			# Remove original child
			for ia in range(0, multi_ifs[0]+1):
				lines.pop(i)
			multi_ifs.pop(0)
			# Insert the ifs
			for an_if in reversed(multi_ifs):
				# print(an_if['tabs'], an_if['value'])
				lines.insert(i, deepcopy(an_if))
			# for iz in multi_ifs: print(iz['tabs'], iz['value'])
			# Continue but with the new lines
			precompiled_lines = precompiler(lines)
			return precompiled_lines

	return lines


def mcpyMultiIfMatch(lines:list):
	data = split(r'\[|, |]', lines[0]['value'])[1:-1]
	lines[0]['value'] = lines[0]['value'].replace(',', '')
	lines[0]['value'] = lines[0]['value'].replace('[', '')
	lines[0]['value'] = lines[0]['value'].replace(']', '')
	lines_child = []
	multi_ifs = []

	# Find the child of the multi if match
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
		if_line = deepcopy(lines[0])

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
		elif match(r'^(if|unless).+:$', lines[i]['value']) and lines[i]['tabs'] == lines[-1]['tabs']:
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
		if match(r'^(#|//).+$', tabbed_line['value']):
			tabbed_line['tabs'] = -1
			tabbed_line['value'] = tabbed_line['value'].replace('//', '#')
		
		# Remove empty line
		if tabbed_line['value'] == '':
			continue
		else:
			tabbed_lines += [tabbed_line]

	return tabbed_lines


def readFile(path:str):
	file = open(path, 'r')
	file_inner = file.read()
	file.close()
	return file_inner


def writeFile(path:str, data:str, dist=True):
	if dist == True:
		path = path.replace('./', user_settings['dist'])
	elif user_settings['base'] != './':
		path = path.replace(user_settings['base'], './')
	generatePath(path)
	file = open(path, 'w')
	file.write(data)
	file.close()


def generatePath(f_path:str):
	f_path = f_path.replace(path.basename(f_path), '').replace('./', '')
	f_path = f_path.split('/')
	current_path = './'
	for i in f_path:
		if i != '':
			current_path += i + '/'
			if not path.exists(current_path):
				mkdir(current_path)


if __name__ == '__main__':
	converter = loads(readFile('./converter.json'))
	user_settings = loads(readFile('./user_settings.json'))
	try:
		obfuscated_str = loads(readFile('./obfuscated_data.json'))
	except FileNotFoundError:
		pass
	mcpy()