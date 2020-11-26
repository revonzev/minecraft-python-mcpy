from rev_modules import rw
import json
import re

converter_settings = json.loads(rw.read("./converter.json"))
user_settings = json.loads(rw.read("./user_settings.json"))

def mcpy():
	for mcpy_file in user_settings["files"]:
		raw_text = rw.read(mcpy_file)
		text_lines = raw_text.split("\n")
		tabbed_lines = tabsReader(text_lines)
		decoded_lines = syntaxMatcher(tabbed_lines)

		mcfunction_file = mcpy_file.replace(".mcpy", ".mcfunction")
		rw.write("./{}".format(mcfunction_file), "\n".join(decoded_lines))


def tabsReader(lines:list):
	new_lines = []
	for line in lines:
		new_line = {"value": "", "tabs": 0}
		line = line.split(user_settings["tab_style"])
		for i in line:
			if i == "":
				new_line["tabs"] += 1
			else:
				new_line["value"] = i
				break
		new_lines.append(new_line)
	return new_lines


def syntaxMatcher(lines:list):
	parent = {"execute": False, "tabs": 0, "tabs_value": [""]}
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

		# Execute
		for execute in converter_settings["execute"]:
			regex = r"{}".format(execute["pattern"])
			if re.match(regex, line["value"]) != None:
				is_execute = [True, execute]
				break
			else:
				is_execute = [False, execute]
		
		# Is not execute children
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
		elif re.match(r"((//|#) .+)|^$", line["value"]) != None:
			continue

		else:
			if parent["execute"] == True:
				new_line = parent["tabs_value"][line["tabs"]] + " run " + line["value"]
				if re.match(r"execute", new_line) == None:
					new_line = "execute" + new_line
			else:
				new_line = line["value"]

			new_lines.append(new_line)

	return new_lines

if __name__ == "__main__":
	mcpy()