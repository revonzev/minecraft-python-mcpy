from rev_modules import rw
from rev_modules import parser
import re

def mcpy():
	# test_code = ["say By Revon Zev", "as at @e[type=!player]:", "\tsay Hello World", "\tsay (c) Revon Zev",
	# 			"\t\tas at @a:", "\t\tsay everyone", "say No one", "// This is a comment"]
	raw_text = rw.read("test.mcpy")

	text_lines = raw_text.split("\n")
	tabbed_lines = tabsReader(text_lines)

	decoded_lines = syntaxMatcher(tabbed_lines)
	rw.write("./test.mcfunction", "\n".join(decoded_lines))


def tabsReader(lines:list):
	new_lines = []
	for line in lines:
		new_line = {"value": "String", "tabs": 0}
		line = line.split("\t")
		for i in line:
			if i == "":
				new_line["tabs"] += 1
			else:
				new_line["value"] = i
				break
		new_lines.append(new_line)
	return new_lines


def syntaxMatcher(lines:list):
	regex = {"pattern": r"^as\sat\s.+:$", "command": "as {value} at @s", "replace": ["as at ", ":"], "execute": True}
	# parent = {"tabs": 0, "value": "", "execute": False}
	parent = {"execute": False, "tabs": 0, "tabs_value": [""]}
	new_lines = []
	command = ""
	current_line = ""
	for line in lines:
		# Non-Execute

		# Execute
		if re.match(regex["pattern"], line["value"]) != None:
			for i in regex["replace"]:
				if i == ":":
					line["value"] = line["value"][:-1:]
					continue
				line["value"] = line["value"].replace(i, "")
			command = regex["command"].replace("{value}", line["value"])
			parent["execute"] = True
			parent["tabs_value"].append(parent["tabs_value"][line["tabs"]] + " " + command)
		elif re.match(r"(//|#) .+", line["value"]) != None:
			continue
		else:
			if line["tabs"] <= parent["tabs"]:
					parent["execute"] = False
					parent["tabs_value"] = [""]

			if parent["execute"] == True:
				command = parent["tabs_value"][line["tabs"]] + " run " + line["value"]
				if re.match(r"execute", command) == None:
					command = "execute " + command
			else:
				command = line["value"]

			new_lines.append(command)

	return new_lines

def converter():
	pass

if __name__ == "__main__":
	mcpy()