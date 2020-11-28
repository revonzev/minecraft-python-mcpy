# MCPY

An mcfunction compiler by using Python

## Execute

### Comment
```
# This is a comment
// This is also a comment
```

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

### Positioned
```
positioned as @a:
    say Hello World

# execute positioned as @a run say Hello World
```

The rest of the execute chain is the same as minecraft, but with a ":" at the end
```
in overworld:
    if block ~ ~ ~ fire:
        say Your burn is in a whole other dimensions
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

execute store result score @a my_score run say Hello
```