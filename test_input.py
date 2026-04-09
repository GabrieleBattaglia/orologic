import msvcrt, sys, time, queue, threading

def bg_thread(q):
    time.sleep(3)
    q.put('e4')

q = queue.Queue()
threading.Thread(target=bg_thread, args=(q,), daemon=True).start()

def async_input(prompt, q):
    sys.stdout.write(prompt)
    sys.stdout.flush()
    buf = []
    while True:
        try:
            msg = q.get_nowait()
            # Clear line
            sys.stdout.write('\r' + ' ' * (len(prompt) + len(buf)) + '\r')
            sys.stdout.write(f'New move: {msg}\n')
            sys.stdout.write(prompt + ''.join(buf))
            sys.stdout.flush()
        except queue.Empty:
            pass

        if msvcrt.kbhit():
            c = msvcrt.getwche()
            if c == '\r' or c == '\n':
                sys.stdout.write('\n')
                return ''.join(buf)
            elif c == '\b':
                if buf:
                    buf.pop()
                    sys.stdout.write(' \b')
            else:
                buf.append(c)
        time.sleep(0.01)

print('Result:', async_input('Prompt> ', q))

