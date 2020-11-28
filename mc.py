from rev_modules import rw
from copy import deepcopy
import json
import re

converter_settings = json.loads(rw.read("./converter.json"))
user_settings = json.loads(rw.read("./user_settings.json"))

def mcpy():
	for mcpy_file in user_settings["files"]:
		raw_text = rw.read(mcpy_file)
		text_lines = raw_text.split("\n")
		tabbed_lines = tabsReader(text_lines)
		predecoded_lines = predecode(tabbed_lines)
		decoded_lines = syntaxMatcher(predecoded_lines)

		mcfunction_file = mcpy_file.replace(".mcpy", ".mcfunction")
		rw.write("./{}".format(mcfunction_file), "\n".join(decoded_lines))


def tabsReader(lines:list):
	new_lines = []
	for line in lines:
		new_line = {"value": "", "tabs": 0}
		line = line.split(user_settings["tab_style"])
		empty_check = ""
		for i in line:
			if i == "":
				empty_check += i
				new_line["tabs"] += 1
			else:
				empty_check = i
				new_line["value"] = i
				break
		if empty_check == "":
			continue
		
		new_lines.append(new_line)
	return new_lines


def syntaxMatcher(lines:list):
	parent = {"execute": False, "tabs": 0, "tabs_value": [""], "continue": False}
	new_lines = []
	new_line = ""
	is_execute = [False]
	for line in lines:
		# Variables
		for variable in converter_settings["variables"]:
			regex = r"{}".format(variable["pattern"])
			if re.match(regex, line["value"]):
				kind = variable["kind"]
				for i in variable["replace"]:
					line["value"] = line["value"].replace(i, "")

				if kind == "declare":
					line["value"] = variable["command"].replace("{value}", line["value"])
				elif kind == "set-add-remove":
					temp = line["value"].split(" ")
					if temp[2] == "=":
						temp[2] = "set"
					elif temp[2] == "+=":
						temp[2] = "add"
					elif temp[2] == "-=":
						temp[2] = "remove"
					line["value"] = variable["command"].replace("{operation}", temp[2])
					line["value"] = line["value"].replace("{target}", temp[1])
					line["value"] = line["value"].replace("{objective}", temp[0])
					line["value"] = line["value"].replace("{score}", temp[3])
				elif kind == "operation":
					temp = line["value"].split(" ")
					line["value"] = variable["command"].replace("{target_1}", temp[1])
					line["value"] = line["value"].replace("{objective_1}", temp[0])
					line["value"] = line["value"].replace("{operation}", temp[2])
					line["value"] = line["value"].replace("{target_2}", temp[4])
					line["value"] = line["value"].replace("{objective_2}", temp[3])
				elif kind == "result":
					temp = line["value"].split(" ", 2)
					line["value"] = variable["command"].replace("{target}", temp[1])
					line["value"] = line["value"].replace("{objective}", temp[0])
					line["value"] = line["value"].replace("{command}", temp[2])
					parent["execute"] = True
					parent["continue"] = True

		# Execute
		for execute in converter_settings["execute"]:
			regex = r"{}".format(execute["pattern"])
			if re.match(regex, line["value"]) != None:
				is_execute = [True, execute]
				break
			else:
				is_execute = [False, execute]
		
		if (len(parent["tabs_value"])-1) > line["tabs"]:
			parent["execute"] = False
			parent["tabs_value"] = parent["tabs_value"][:line["tabs"]+1]
		
		# Is part of execute command
		if is_execute[0]:
			for i in is_execute[1]["replace"]:
				# Remove end ":"
				if i == ":":
					line["value"] = line["value"][:-1:]
					continue
				# Replace mcpy to mcfunction
				line["value"] = line["value"].replace(i, "")
			# Replace converter "{value}" with mcpy value
			new_line = is_execute[1]["command"].replace("{value}", line["value"])
			# Set parent
			parent["execute"] = True
			parent["tabs_value"].append(parent["tabs_value"][line["tabs"]] + " " + new_line)

		# Comment
		elif re.match(r"((//|#) .+)|^$", line["value"]) != None and not user_settings["keep_comment_and_empty_line"]:
			continue
		elif re.match(r"((//|#) .+)|^$", line["value"]) != None and user_settings["keep_comment_and_empty_line"]:
			new_lines.append(line["value"])
			continue

		else:
			if parent["execute"] == True:
				if parent["continue"]:
					new_line = parent["tabs_value"][line["tabs"]] + " " + line["value"]
					parent["continue"] = False
				else:
					new_line = parent["tabs_value"][line["tabs"]] + " run " + line["value"]
				if re.match(r"execute", new_line) == None:
					new_line = "execute" + new_line
			else:
				new_line = line["value"]

			new_lines.append(new_line)

	return new_lines


def predecode(lines):
	# Group line based on parent and indent
	indent_check = 0
	new_lines = []
	group = []
	lines_group = [{}]
	for i in range(0, len(lines)):
		indent_check -= lines[i]["tabs"]
		if indent_check < 0:
			group += [lines[i]]
		elif indent_check > 0:
			group = []
			group += [lines[i]]
		else:
			if re.match(r"^.+:$", lines[i]["value"]):
				group = []
				group += [lines[i]]
			else:
				group += [lines[i]]
		indent_check = lines[i]["tabs"]

		if lines_group[-1] != group:
			lines_group += [group]
	lines_group.pop(0)

	new_lines_group = []
	for line_group in lines_group:
		values_only = []
		tabs_only = 0
		if len(line_group) > 1:
			tabs_only = line_group[1]["tabs"]
		else:
			tabs_only = line_group[0]["tabs"]
		for line in line_group:
			values_only += [line["value"]]
		new_lines_group += [{"tabs": tabs_only,"values": values_only}]
	lines_group = new_lines_group
	
	# Predecoder
	for i in range(0, len(lines_group)):
		# Mcpy else
		if lines_group[i]["values"][0] == "else:":
			line_num = i-1
			while line_num > 0:
				if re.match(r"^(if|unless)\s.+:$", lines_group[line_num]["values"][0]) != None:
					if lines_group[line_num]["tabs"] == lines_group[i]["tabs"]:
						lines_group[i]["values"][0] = else_special(lines_group[line_num]["values"][0])
						break
				line_num -= 1
		# Mcpy multiple match
		if re.match(r"^if.+\[\d+(, \d)*, \d\]:$", lines_group[i]["values"][0]) != None:
			# Split
			data_full = re.split(r"\[|, |]", lines_group[i]["values"][0])
			data = deepcopy(data_full)[1:-1]
			new_line = ""
			new_lines_group = deepcopy(lines_group)
			new_lines_group.pop(i)
			for ia in range(0, len(data)):
				new_line = "".join(data_full)
				new_line = new_line.replace("".join(data), "{value}")
				new_line = new_line.replace("{value}", data[ia])
				new_lines_group.insert(i, deepcopy(lines_group[i]))
				new_lines_group[i]["values"][0] = new_line
			lines_group = new_lines_group

	# Ungrouper
	new_lines = []
	for group in lines_group:
		for value in group["values"]:
			if re.match(r"^.+:$", value) != None:
				new_lines += [{"tabs": group["tabs"]-1, "value": value}]
			else:
				new_lines += [{"tabs": group["tabs"], "value": value}]

	return new_lines


def else_special(s):
	s = s.replace("if", "lyayk")
	s = s.replace("unless", "if")
	s = s.replace("lyayk", "if")
	return s


if __name__ == "__main__":
	mcpy()