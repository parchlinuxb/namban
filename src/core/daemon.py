import os
import sys
import json
import subprocess

print('Do Not Run this file manually !!!!')

if os.getuid() != 0:
    print('Run this with super user')
    sys.exit(1)


def read_entry():
    entry = ''
    while True:
        _in = input()
        if _in == '&end':
            break
        entry += _in
    return json.loads(entry)

def write_error(err):
    print('$error')
    print(err)
    print('$end')

print('$hello')
sys.stdout.flush()
while input() != '&hi': pass
while True:
    command = input()
    if not command or command[0] != '&':
        continue

    command = command[1:]
    if command == 'copy':
        args = read_entry()
        with subprocess.Popen(
            ['cp', args.get('source'), args.get('dest')],
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL
        ) as process:
            _, err = process.communicate()
            if process.returncode != 0:
                write_error(err)
            else:
                print('$end')
    elif command == 'remove':
        args = read_entry()
        with subprocess.Popen(
            ['rm', args.get('dest')],
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL
        ) as process:
            _, err = process.communicate()
            if process.returncode != 0:
                write_error(err)
            else:
                print('$end')
    elif command == 'write':
        args = read_entry()
        file = args.get('file')
        body = args.get('body')
        try:
            with open(file, 'w+') as f:
                f.write(body)
            print('$end')
        except Exception as e:
            write_error(str(e))
    elif command == 'reload-resolved':
        with subprocess.Popen(
            ['systemctl', 'restart', 'systemd-resolved'],
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL
        ) as process:
            _, err = process.communicate()
            if process.returncode != 0:
                write_error(err)
            else:
                print('$end')
    

