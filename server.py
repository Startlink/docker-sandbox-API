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

def getFromDict(key, D, default='', require=False, connection=None, errorMessage='', loggingMessage=None):
    if key not in D:
        if require:
            if loggingMessage is not None:
                print loggingMessage
            conn.sendall(json.dumps({
                'state': 'error',
                'stderr': errorMessage
            }))
            conn.close()
            return None
        return default
    return D[key]

HOST = ''
PORT = 3030
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))

supportType = ['text/x-c++src', 'text/x-python']

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

    sourceCode = getFromDict(key='source', D=D, require=True, connection=conn, errorMessage='No source code', loggingMessage=' Error: No source code.')
    if sourceCode is None:
        continue

    stdin = getFromDict(key='stdin', D=D, default='')

    fileName = getFromDict(key='name', D=D, default='a.cpp')

    runningTimeLimit = int(getFromDict(key='time_limit', D=D, default=5))

    memoryLimit = int(getFromDict(key='memory_limit', D=D, default=128))

    memoryLimitStrict = ''
    if bool(getFromDict(key='memory_limit_strict', D=D, default=False)):
        memoryLimitStrict = '--strict '

    filetype = getFromDict(key='mime', D=D, require=True, connection=conn,
            errorMessage='The language is currently not supported', loggingMessage=' Bad req: no file type.')
    if filetype is None:
        continue

    if filetype not in supportType:
        print ' Bad req: not supported.', D['mime']
        conn.sendall(json.dumps({
            'state': 'error',
            'stderr': D['mime'] + ' is currently not supported.'
        }))
        conn.close()
        continue

    stage = getFromDict(key='stage', D=D, require=True, connection=conn,
            errorMessage='Specify \'stage\'', loggingMessage=' Bad req: no stage')
    if stage is None:
        continue
    if stage != 'compile' and stage != 'run':
        print ' Bad req: invalid stage.'
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
    if filetype != 'text/x-python':
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
            try:
                shutil.rmtree(dirpath)
            except Exception as e:
                print ' Error: Cannot remove dir.', e
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
    if filetype == 'text/x-python':
        command = './run_py.sh --stdin ' + dirpath + '/stdin.txt ' + '-m ' + str(memoryLimit) + ' ' + memoryLimitStrict + '-v '+ dirpath + ':' + '/data ' + '/data/' + fileName
    else:
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

    try:
        shutil.rmtree(dirpath)
    except Exception as e:
        print ' Error: Cannot remove dir.', e

