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

## Variables

### Defining
```
var score dummy "Display"

# scoreboard objectives add score dummy "Display"
```

### Set
```
score @a = 10

# scoreboard players set @a score 10
```

### Add
```
score @a += 1

# scoreboard players add @a score 1
```

### Remove
```
score @a -= 1

# scoreboard players remove @a score 1
```