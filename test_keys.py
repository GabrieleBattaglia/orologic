import msvcrt, sys
print('Type something, ESC to exit.')
while True:
    if msvcrt.kbhit():
        c = msvcrt.getwch()
        if c == '\x1b': break
        print(repr(c))

