import socket
import json
import tempfile
import shutil
import subprocess
from docker import Client
import time
import os
import stat

def execute(commmand, timeLimit = 5, extraMessage = ''):
    kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "shell": True
    }
    popen = subprocess.Popen(command, **kwargs)
    start = time.time()
    while time.time() < start + timeLimit and popen.poll() is None:
        time.sleep(0.1)
    wait = popen.poll()

    if wait is None:
        popen.kill()
        return {
            'state': 'tle',
            'stderr': extraMessage + 'Time Limit Exceeded'
        }

    return {
        'state': wait,
        'stdout': popen.stdout.read(),
        'stderr': popen.stderr.read()
    }

HOST = ''
PORT = 3000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))

while True:
    s.listen(5) #maximum number of queued connections

    conn, addr = s.accept()
    print('Connected by', addr)

    data = conn.recv(1024)
    if not data:
        continue

    try:
        D = json.loads(data)
    except Exception as e:
        #JSON load failed
        print ' Error: Cannot load the received data as json.'
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': 'Not an appropriate data.'
        }))
        conn.close()
        continue

    if 'source' not in D:
        #No 'source' key
        print(' Error: No source code.')
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': 'No source code'
        }))
        conn.close()
        continue
    sourceCode = D['source']

    stdin = ''
    if 'stdin' in D:
        stdin = D['stdin']

    fileName = 'a.cpp'
    if 'name' in D:
        fileName = D['name']

    runningTimeLimit = 5
    if 'time_limit' in D:
        runningTimeLimit = int(D['timeLimit'])

    memoryLimit = 128
    if 'memory_limit' in D:
        memoryLimit = int(D['memory_limit'])

    memoryLimitStrict = ''
    if 'memory_limit_strict' in D and bool(D['memory_limit_strict']) == True:
        memoryLimitStrict = '--strict '

    if 'mime' not in D:
        print ' Bad req: no file type.'
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': 'no file type. specify \'mime\''
        }))
        conn.close()
        continue

    filetype = D['mime']
    if filetype != 'text/x-c++src':
        print ' Bad req: not supported.', D['mime']
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': D['mime'] + ' is currently not supported.'
        }))
        conn.close()
        continue

    if 'stage' not in D:
        print ' Bad req: no command.'
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': 'Specify \'stage\''
        }))
        conn.close()
        continue

    stage = D['stage']
    if stage != 'compile' and stage != 'run':
        print ' Bad req: no stage.'
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': 'Invalid value in \'stage\''
        }))
        conn.close()
        continue

    try:
        #make temp directory
        dirpath = tempfile.mkdtemp()
        with open(dirpath + '/' + fileName, 'w') as fp:
            fp.write(sourceCode)
        #make the file to be redirected as stdin
        with open(dirpath + '/stdin.txt', 'w') as fp:
            fp.write(stdin)
    except Exception as e:
        print(' Error: Cannot write source code.', e)
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': 'Server error.'
        }))
        conn.close()
        continue

    #compile
    command = './compile_cpp.sh -v ' + dirpath + ':' + '/data ' + fileName
    result = execute(command, timeLimit = 5, extraMessage = 'Compile')
    if result['state'] == 'tle':
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': 'Compile time limit exceeded.'
        }))
        conn.close()
        continue
    elif result['stderr'] != '':
        print 'Error:', result['stderr']
        conn.sendall(json.dumps({
            'state': 'compile error',
            'stdout': result['stdout'],
            'stderr': result['stderr']
        }))
        conn.close()
        continue

    if stage == 'compile':
        conn.sendall(json.dumps({
            'state': 'success',
            'stdout': result['stdout'],
            'stderr': result['stderr']
        }))
        conn.close()
        continue

    while not os.path.isfile(dirpath + '/a.out') or not bool(os.stat(dirpath + '/a.out').st_mode & stat.S_IXUSR):
        time.sleep(0.1)

    #run
    command = './run_cpp.sh --stdin ' + dirpath + '/stdin.txt ' + '-m ' + str(memoryLimit) + ' ' + memoryLimitStrict + '-v ' + dirpath + ':' + '/data ' + '/data/a.out'
    result = execute(command, timeLimit = runningTimeLimit + 4, extraMessage = 'Running')
    if result['state'] == 'tle':
        conn.sendall(json.dumps({
            'state': 'tle',
            'stderr': 'Time limit exceeded.'
        }))
        conn.close()
        continue
    elif result['stderr'] != '':
        print 'Error:', result['stderr']
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': result['stderr']
        }))
        conn.close()
        continue

    conn.sendall(json.dumps({
        'state': 'success',
        'stdout': result['stdout'],
        'stderr': result['stderr']
    }))
    conn.close()

