# docker-sandbox-API
Host: '115.68.24.126'
Port: 3000

### Request
json
* 'stage':'compile' or 'run'
* 'mime': 'text/x-c++src'
* 'filename': source file name
* 'stdin': string for stdin when you run the program
* 'source': source string

### Response
* 'state': 'tle', 'error', 'compile error', 'success'
