# docker-sandbox-API
Host: '115.68.24.126'
Port: 3000

### Request
json
* 'stage':'compile' or 'run'
* 'mime': 'text/x-c++src', 'text/x-java', 'text/x-python'
* 'filename': source file name
* 'stdin': stdin 문자열
* 'source': 소스코드 문자열
* 'time_limit': running time limit, 초 단위 (없으면 5초)
* 'memory_limit': memory limit, MByte 단위 (없으면 128MB)
* 'memory_limit_strict': true or false. (없으면 false) true이면 memory_limit만큼만 할당. (memory swap size 제한) false이면 memory_limit의 두 배.(swap size)

### Response
* 'state': 'tle', 'error', 'compile error', 'success'
* 'stdout': stdout
* 'stderr': stderr
