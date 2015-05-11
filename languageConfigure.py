import compileLanguage
import interpreterLanguage
import time
import os
import stat

supportType = ['text/x-c++src', 'text/x-csrc', 'text/x-python', 'text/x-java']
#mime list for the languages that do not need compile:
noCompileType = ['text/x-python']

compileCallingFunction = {
    'text/x-c++src': compileLanguage.compile,
    'text/x-csrc': compileLanguage.compile,
    'text/x-java': compileLanguage.compile
}
compileKwargs = {
    'text/x-c++src': {
        'compilerName': 'g++',
        'option': '-O2 -Wall -lm --static -std=c++11',
        'binaryName': 'a.out',
        'imageName': 'cpp'
    },
    'text/x-csrc':{
        'compilerName': 'gcc',
        'option': '-O2 -Wall -lm --static -std=c99',
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
    'text/x-csrc': compileLanguage.run,
    'text/x-java': interpreterLanguage.run,
    'text/x-python': interpreterLanguage.run
}
runKwargs = {
    'text/x-c++src': {
        'imageName': 'cpp',
    },
    'text/x-csrc': {
        'imageName': 'cpp'
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
    'text/x-csrc': True,
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
