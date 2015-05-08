import socket
import json
import tempfile
import shutil
import subprocess
import time
import os
import stat
import logging
import datetime
import cpp as cppContainer
import python as pythonContainer

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
            'stdout': '',
            'stderr': extraMessage + 'Time Limit Exceeded'
        }

    return {
        'state': wait,
        'stdout': popen.stdout.read(),
        'stderr': popen.stderr.read()
    }

def sendResponse(conn, state, stdout, stderr, logger):
    res = json.dumps({ 'state': state, 'stdout': stdout, 'stderr': stderr })
    try:
        conn.sendall(res)
    except Exception as e:
        logger.error('Failed to send the response. ' + str(e))
    finally:
        logger.debug(res)

def getFromDict(key, D, default='', errorMessage=None, logger=None):
    if key not in D:
        if errorMessage is not None:
            if logger is None:
                print errorMessage
            else:
                logger.error(errorMessage)
            sendResponse(conn, state='error', stdout='', stderr=errorMessage, logger=logger)
            return None
        return default
    return D[key]

HOST = ''
PORT = 3000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((HOST, PORT))

supportType = ['text/x-c++src', 'text/x-python', 'text/x-java']
compilerName = {
    'text/x-c++src': 'g++',
    'text/x-java': 'javac'
}
compileOption = {
    'text/x-c++src': '-std=c++0x -Wall',
    'text/x-java': ''
}
compileBinaryName = {
    'text/x-c++src': 'a.out',
    'text/x-java': None
}
dockerImageName = {
    'text/x-c++src': 'cpp',
    'text/x-java': 'java'
}
#mime list for the languages that do not need compile:
noCompileType = ['text/x-python']

#Configure logger
logger = logging.getLogger('sever')
logger.setLevel(logging.DEBUG)

fileHandler = logging.FileHandler('server_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '.log')
fileHandler.setLevel(logging.WARNING)

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fileHandler.setFormatter(formatter)
consoleHandler.setFormatter(formatter)

logger.addHandler(fileHandler)
logger.addHandler(consoleHandler)


while True:
    s.listen(5) #maximum number of queued connections

    conn, addr = s.accept()

    logger.info('Connected by ' + str(addr))

    #Block ip except for our web server
    if addr[0] != '115.68.182.172':
        logger.warning('Unauthorized connection by ' + str(addr))

        sendResponse(conn, state='error', stdout='', stderr='Connection refused', logger=logger)
        conn.close()
        continue

    data = conn.recv(1024)
    if not data:
        continue
    logger.debug(str(data))

    #JSON string to python dictionary
    try:
        D = json.loads(data)
    except Exception as e:
        #JSON load failed
        logger.error('Cannot load the received data as json. ', str(e))
        sendResponse(conn, state='error', stdout='', stderr='Not an appropriate data.', logger=logger)
        conn.close()
        continue

    try:
        #Get source code
        sourceCode = getFromDict(key='source', D=D, errorMessage='No source code', logger=logger)
        if sourceCode is None:
            conn.close()
            continue

        with open('temp.cpp', 'w') as tempfp:
            tempfp.write(sourceCode)

        #Get stdin string
        stdin = getFromDict(key='stdin', D=D, default='')

        #Get file name
        fileName = getFromDict(key='name', D=D, default='a.cpp')

        #Get running time limit
        try:
            runningTimeLimit = int(getFromDict(key='time_limit', D=D, default=5))
        except ValueError as verr:
            logger.error('running time limit value error. ' + str(e))
            sendResponse(conn, state='error', stdout='', stderr='Running time limit value is not an acceptable form. It should be only a integer.', logger=logger)
        except Exception as e:
            logger.critical(str(e))
            sendResponse(conn, state='error', stdout='', stderr='Server error.', logger=logger)

        #Get memory limit
        try:
            memoryLimit = int(getFromDict(key='memory_limit', D=D, default=128))
        except ValueError as verr:
            logger.error('memory limit value error. ' + str(e))
            sendResponse(conn, state='error', stdout='', stderr='Memory limit value is not an acceptable form.', logger=logger)
        except Exception as e:
            logger.critical(str(e))
            sendResponse(conn, state='error', stdout='', stderr='Server error.', logger=logger)

        #Get if memory_strict option is on
        try:
            isStrict = bool(getFromDict(key='memory_limit_strict', D=D, default=False))
        except ValueError as verr:
            logger.error('memory limit value error. ' + str(e))
            sendResponse(conn, state='error', stdout='', stderr='Memory_limit_strict is not an acceptable form.', logger=logger)
        except Exception as e:
            logger.critical(str(e))
            sendResponse(conn, state='error', stdout='', stderr='Server error.', logger=logger)

        #Set memory limit and memory swap limit
        memorySwapLimit = memoryLimit * 2
        if isStrict:
            memoryLimitStrict = memoryLimit

        #Get mime (file type)
        filetype = getFromDict(key='mime', D=D, errorMessage='The language should be specified.', logger=logger)
        if filetype is None:
            conn.close()
            continue

        #See if the type is supported
        if filetype not in supportType:
            logger.warning('Bad request: ' + str(D['mime']) + ' not supported.')
            sendResponse(conn, state='error', stdout='', stderr=D['mime'] + ' is currently not supported.', logger=logger)
            conn.close()
            continue

        #Get which stage should be done
        stage = getFromDict(key='stage', D=D, errorMessage='Specify \'stage\'', logger=logger)
        if stage is None:
            conn.close()
            continue

        #See if the stage is invalid
        if stage != 'compile' and stage != 'run':
            logger.warning('Bad request: invalid stage')
            sendResponse(conn, state='error', stdout='', stderr='Invalid value in \'stage\'', logger=logger)
            conn.close()
            continue

        #make temp directory
        try:
            dirpath = tempfile.mkdtemp()
        except Exception as e:
            logger.critical('Cannot write source code. ' + str(e))
            sendResponse(conn, state='error', stdout='', stderr='Server error.', logger=logger)
            conn.close()
            continue

        try:
            with open(dirpath + '/' + fileName, 'w') as fp:
                fp.write(sourceCode)
            #make the file to be redirected as stdin
            with open(dirpath + '/stdin.txt', 'w') as fp:
                fp.write(stdin)
        except Exception as e:
            logger.critical('Cannot write source code or stdin file. ' + str(e))
            sendResponse(conn, state='error', stdout='', stderr='Server error.', logger=logger)
            conn.close()
            continue

        #compile
        if filetype not in noCompileType:
            result = cppContainer.compile(sourceFile=[fileName], volumn = dirpath + ':' + '/data',
                    compilerName = compilerName[filetype], option=compileOption[filetype],
                    binaryName = compileBinaryName[filetype],
                    imageName = dockerImageName[filetype], timeLimit = 5, logger = logger)

            if result['state'] != 'success':
                sendResponse(conn, state=result['state'], stdout=result['stdout'], stderr=result['stderr'], logger=logger)
                conn.close()
                continue

            if stage == 'compile':
                try:
                    shutil.rmtree(dirpath)
                except Exception as e:
                    logger.error('Cannot remove dir. (' + dirpath + ') ' + str(e))
                    logger.info('Compile success')
                    sendResponse(conn, state='success', stdout=result['stdout'], stderr=result['stderr'], logger=logger)
                    conn.close()
                    continue
                sendResponse(conn, state='success', stdout=result['stdout'], stderr=result['stderr'], logger = logger)
                conn.close()
                continue

            #Block until file writing done
            compileSuccess = True
            start = time.time()
            while not os.path.isfile(dirpath + '/a.out') or not bool(os.stat(dirpath + '/a.out').st_mode & stat.S_IXUSR):
                #no more than 5 secs
                if time.time() > start + 5:
                    compileSuccess = False
                    break
                time.sleep(0.1)
            if not compileSuccess:
                logger.critical('Cannot write binary file.')
                sendResponse(conn, state='error', stdout='', stderr='Server error.', logger=logger)
                conn.close()
                continue

        #run
        if filetype == 'text/x-python':
            result = pythonContainer.run(sourceFileName=fileName, volumn=dirpath+':/data',
                memoryLimit = memoryLimit, memorySwapLimit = memorySwapLimit,
                timeLimit = runningTimeLimit+2, logger= logger)
        else:
            binaryName = compileBinaryName[filetype]
            if filetype == 'text/x-java':
                binaryName = fileName[:fileName.rfind('.')]
            result = cppContainer.run(volumn = dirpath + ':/data',
                binaryName=binaryName, imageName='cpp', stdinName = 'stdin.txt',
                memoryLimit = memoryLimit, memorySwapLimit = memorySwapLimit,
                timeLimit = runningTimeLimit+2, logger= logger)

        if result['state'] != 'success':
            logger.info('Run failed: ' + result['stderr'])
            sendResponse(conn, state=result['state'], stdout=result['stdout'], stderr=result['stderr'], logger=logger)
            conn.close()
            continue

        logger.info('Run success')
        sendResponse(conn, state='success', stdout=result['stdout'], stderr=result['stderr'], logger=logger)
        conn.close()

    except Exception as e:
        logger.critical('Unknown exception.s ' + str(e))

    try:
        shutil.rmtree(dirpath)
    except Exception as e:
        logger.error('Cannot remove dir. (' + dirpath + ') ' + str(e))
        if conn:
            sendResponse(conn, state='success', stdout=result['stdout'], stderr=result['stderr'], logger=logger)
            conn.close()
