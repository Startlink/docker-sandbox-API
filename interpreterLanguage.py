#-*- coding: utf8 -*-
import dockerContainer

def getVolumnPath(S):
    L = S.split(':')
    containerVolumn = L[1]
    if containerVolumn[len(containerVolumn)-1] != '/':
        containerVolumn = containerVolumn + '/'

    hostVolumn = L[0]
    if hostVolumn[len(hostVolumn)-1] != '/':
        hostVolumn = hostVolumn + '/'
    return (hostVolumn, containerVolumn)

def run(runName, volumn, option='', intpName='python', imageName='baekjoon/onlinejudge-gcc:4.8', memoryLimit=128, memorySwapLimit=256, stdinName='stdin.txt', timeLimit=5, logger=None):
    (hostVolumn, containerVolumn) = getVolumnPath(volumn)

    #Run
    command = "-v %s --net none --memory %sm --memory-swap %sm %s sh -c '%s %s %s < %s'" % (volumn, str(memoryLimit), str(memorySwapLimit), imageName, intpName, option, runName, containerVolumn+stdinName)
    logger.debug(command)
    D = dockerContainer.execute(command, timeLimit, logger)

    exitCode = D['exitcode']
    if logger is not None:
        logger.info('Run done. (exit code: %s)' % str(exitCode))

    res = {}
    if exitCode == 0:
        res['state'] = 'success'
        res['stdout'] = D['stdout']
        res['stderr'] = D['stderr']
    elif D['state'] == 'tle':
        res['state'] = 'tle'
        res['stdout'] = ''
        res['stderr'] = 'Running time limit exceeded.'
    elif exitCode == 137:
        res['state'] = 'error'
        res['stdout'] = ''
        res['stderr'] = 'Memory limit exceeded.'
    elif 'docker' not in D['stderr']:
        res['state'] = 'error'
        res['stdout'] = D['stdout']
        res['stderr'] = D['stderr']
        if logger is not None:
            logger.info('Exception while running(may due to user): ' + res['stderr'])
    else:
        res['state'] = 'error'
        res['stdout'] = ''
        res['stderr'] = 'Server error.'
        if logger is not None:
            logger.critical('Error while running: ' + res['stderr'])
        else:
            print 'Error while running: ' + res['stderr']

    return res
