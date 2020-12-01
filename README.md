# MCPY
An mcfunction compiler by using Python.

## Execute

### Comment
```
# This is a comment
// This is also a comment
```
*Note: Put a comment in it's own line*

### As At
```
# A
as at @a:
    say Hello World

# B
as @a:
    at @s:
        say Hello World

# execute as @a at @s run say Hello World
```

### As
```
as @a:
    say Hello World

# execute as @a run say Hello World
```

### At
```
at @a:
    say Hello World

# execute at @a run say Hello World
```

### If matches x or x
```
unless score @a home matches [0, 2, 4]:
    say your score is 0 or 2 or 4

# execute unless score @a home matches 0 say your score is 0 or 2 or 4
# execute unless score @a home matches 2 say your score is 0 or 2 or 4
# execute unless score @a home matches 4 say your score is 0 or 2 or 4
```

### Other part of execute
The rest of the execute chain is the same as minecraft, but with a ":" at the end.
```
in nether:
    if block ~ ~ ~ fire:
        say Your burn is in a whole other dimensions

# execute in nether if block ~ ~ ~ fire say Your burn is in a whole other dimensions
```

## Variables

### Defining
```
var my_score dummy "Display"

# scoreboard objectives add score dummy "Display"
# DO NOT DO: var score dummy "Display" = 10
```

### Set
```
my_score @a = 10

# scoreboard players set @a my_score 10
```

### Add
```
my_score @a += 1

# scoreboard players add @a my_score 1
```

### Remove
```
my_score @a -= 1

# scoreboard players remove @a my_score 1
```

### Operation
```
my_score @a *= my_score @p

# scoreboard players operation @a my_score *= @p my_score
# Operations: %=, *=, +=, -=, /=, <, >, =, ><
```

### Store command result
```
my_score @a := say Hello

# execute store result score @a my_score run say Hello
```

## Obfuscation
To generate a new obfuscation, delete `obfuscated_data.json`.
### Variables
In the user_settings.json if `"obfuscate": true` then instead of the variable name it will generate a random 16 character string. You can name the variables as long as you want. This will remove the scoreboards' display name.

If `"obfuscate": false` you are limited in naming your variables to 16 characters (Minecraft's scoreboard objective name limit).

### Tags or strings
To obfuscate a tag or string use 
```
obf tag_name
```

*Note: Any string that matches it will be obfuscated*

## User Settings
### Dist path
The default is `./dist`. It is in the `user_settings.json`.. Dist location is in local. That means it cannot do `C:/Users/user/Documents/project/mcpy/dist` but instead `./dist`.

### Tabbing style
The default is four spaces. It is in the `user_settings.json`. Do use the proper tabbing otherwise the compiler will not compile mcpy to mcfunction correctly.

### Project base path
The default is `./` (Where the mc.exe is). It is in the `user_settings.json`. Any files that's inside a folder inside the project base will be generated in the dist path.

### Individual files
The default is `false`. If you wish to set the files manualy, it is in the `user_settings.json`, set `"individual_file"` to `true`. Then add the files inside `"files"`. If `"individual_file": false` then it will compile all the files inside the project base path.

© 2020 Revon Zev