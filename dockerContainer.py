#-*- coding: utf8 -*-
import subprocess
import time
import os

def execute(command, timeLimit = 5, logger=None):
    try:
        command = 'OUTPUT=$(docker run -d ' + command + '); echo $OUTPUT'

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
            if logger is not None:
                logger.info('TLE')
            return {
                'state': 'tle',
                'exitcode': '9',
                'stdout': '',
                'stderr': 'Time Limit Exceeded'
            }

        containerID = popen.stdout.read().strip()

        popen = subprocess.Popen('docker wait ' + containerID, **kwargs)
        start = time.time()
        while time.time() < start + timeLimit and popen.poll() is None:
            time.sleep(0.1)
        wait = popen.poll()
        if wait is None:
            popen.kill()
            subprocess.call(['docker', 'kill', containerID])
            if logger is not None:
                logger.info('TLE')
            return {
                'state': 'tle',
                'exitcode': '9',
                'stdout': '',
                'stderr': 'Time Limit Exceeded'
            }

        exitCode = int(popen.stdout.read().strip())

        popen = subprocess.Popen('docker logs ' + containerID, **kwargs)
        start = time.time()
        while time.time() < start + timeLimit and popen.poll() is None:
            time.sleep(0.1)
        wait = popen.poll()

        if wait is None:
            popen.kill()
            return {
                'state': 'tle',
                'exitcode': '9',
                'stdout': '',
                'stderr': 'Time Limit Exceeded'
            }

        FNULL = open(os.devnull, 'w')
        subprocess.call(['docker', 'rm', containerID], stdout=FNULL, stderr=FNULL)

        return {
            'state': 'success',
            'exitcode': exitCode,
            'stdout': popen.stdout.read(),
            'stderr': popen.stderr.read()
        }
    except Exception as e:
        if logger is not None:
            logger.critical('Error while docker run. ' + str(e))
        else:
            print 'Error while docker run. ' + str(e)
