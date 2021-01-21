# MCPY
An mcfunction compiler by using Python.

## Execute

### Comment
```
# This is a comment
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

# Compile into
execute as @a at @s run say Hello World
```

### As
```
as @a:
    say Hello World

# Compile into
execute as @a run say Hello World
```

### At
```
at @a:
    say Hello World

# Compile into
execute at @a run say Hello World
```

### If matches x or x
```
unless score @a home matches [0, 2, 4]:
    say your score is 0 or 2 or 4

# Compile into
execute unless score @a home matches 0 say your score is 0 or 2 or 4
execute unless score @a home matches 2 say your score is 0 or 2 or 4
execute unless score @a home matches 4 say your score is 0 or 2 or 4
```

### Other part of execute
The rest of the execute chain is the same as minecraft, but with a ":" at the end.
```
in nether:
    if block ~ ~ ~ fire:
        say Your burn is in a whole other dimensions

# Compile into
execute in nether if block ~ ~ ~ fire say Your burn is in a whole other dimensions
```

## Scoreboards

### Defining
```
score name dummy "Display"

# Compile into
scoreboard objectives add score dummy "Display"
```

### Set
```
home @a = 10
home = 10

# Compile into
scoreboard players set @a home 10
scoreboard players set @s home 10
```

### Add
```
home @a += 1
home += 1

# Compile into
scoreboard players add @a home 1
scoreboard players add @s home 1
```

### Remove
```
home @a -= 1
home -= 1

# Compile into
scoreboard players remove @a home 1
scoreboard players remove @s home 1
```

### Operation
```
home @a *= home @p
home @a *= home
home *= home @p
home *= home

# Compile into
scoreboard players operation @a home *= @p home
scoreboard players operation @a home *= @s home
scoreboard players operation @s home *= @p home
scoreboard players operation @s home *= @s home

# Operations: %=, *=, +=, -=, /=, <, >, =, ><
```

### Store command result
```
home @a := say Hello
home := say Hello

# execute store result score @a home run say Hello
# execute store result score @s home run say Hello
```

## Obfuscation
To generate a new obfuscation, delete `obfuscated_data.json`.
### Scoreboards
In the user_settings.json if `"obfuscate": true` then instead of the variable name it will generate a random 16 character string. You can name the variables as long as you want. This will remove the scoreboards' display name.

If `"obfuscate": false` you are limited in naming your variables to 16 characters (Minecraft's scoreboard objective name limit).

### Tags or strings
To obfuscate a tag or string use 
```
obf tag_name
```

*Note: Any string that matches it, will be obfuscated*

## User Settings
The file is `user_settings.json`

### Watch delay
The default is every 5 seconds. How much delay before it checks if a file has been updated and compile. If set to 0, then it is on manual.

### Dist path
The default is `./dist`. Dist location is in local. That means it cannot do `C:/Users/user/Documents/project/mcpy/dist` but instead `./dist`.

### Tabbing style
The default is four spaces. Do use the proper tabbing otherwise the compiler will not compile mcpy to mcfunction correctly.

### Project base path
The default is `./` (Where the mc.exe is). Any files that're inside the project base path will be generated in the dist path.

### Individual files
The default is `false`. If you wish to set the files manualy, set `"individual_file"` to `true`. Then add the files inside `"files"` list. If `"individual_file": false` then it will compile all the files inside the project base path.

© 2020 Revon Zev