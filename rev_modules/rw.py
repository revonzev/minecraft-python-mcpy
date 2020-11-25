from os import mkdir
from os import path

def read(file_loc:str):
    file = open(file_loc, "r")
    file_inner = file.read()
    file.close()
    return file_inner

def write(file_loc:str, data:str):
    file_loc = file_loc.replace("./", "./dist/")
    generatePath(file_loc)
    file = open(file_loc, "w")
    file.write(data)
    file.close()

def generatePath(file_loc:str):
    path_loc = file_loc.replace(path.basename(file_loc), "").replace("./", "")
    path_loc = path_loc.split("/")
    current_path = "./"
    for i in path_loc:
        if i != '':
            current_path += i + "/"
            if not path.exists(current_path):
                mkdir(current_path)