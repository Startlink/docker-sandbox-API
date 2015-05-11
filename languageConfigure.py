import compileLanguage
import interpreterLanguage
import time
import os
import stat

compileCallingFunction = {
    'text/x-c++src': compileLanguage.compile,
    'text/x-java': compileLanguage.compile
}
compileKwargs = {
    'text/x-c++src': {
        'compilerName': 'g++',
        'option': '-std=c++0x -Wall',
        'binaryName': 'a.out',
        'imageName': 'cpp'
    },
    'text/x-java': {
        'compilerName': 'javac',
        'option': '-d /data',
        'binaryName': None,
        'imageName': 'java'
    }
}

runCallingFunction = {
    'text/x-c++src': compileLanguage.run,
    'text/x-java': interpreterLanguage.run,
    'text/x-python': interpreterLanguage.run
}
runKwargs = {
    'text/x-c++src': {
        'imageName': 'cpp',
    },
    'text/x-python': { },
    'text/x-java': {
        'option': '-classpath /data',
        'intpName': 'java',
        'imageName': 'java'
    }
}
ifTheBinaryFileNeedsXMode = {
    'text/x-c++src': True,
    'text/x-java': False
}

def isFileWritingDone(fileName, checkXMode = False, blockTimeLimit = 2):
    #Block until file writing done
    start = time.time()
    while not(os.path.isfile(fileName) and (checkXMode == False or bool(os.stat(fileName).st_mode & stat.S_IXUSR))):
        #no more than 2 secs
        if time.time() > start + blockTimeLimit:
            return False
        time.sleep(0.1)
    return True
