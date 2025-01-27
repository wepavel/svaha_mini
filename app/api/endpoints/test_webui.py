
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.exceptions import EXC, ErrorCode
from fastapi import APIRouter, Cookie

router = APIRouter()

def html(user_id):

    p0 = """<!DOCTYPE html>
<html>
    <head>
        <title>SSE Listener</title>
    </head>
    <style>
    html * {
      font-size: 12px !important;
      color: #0f0 !important;
      font-family: Andale Mono !important;
      background-color: #000;
    }

    </style>
            """
    p2 = f"""
    <body>
        <h1>EventSource Of User {user_id}</h1>
        <script>
            let eventSource;
            // EventSource;
            // WebSocket
            eventSource = new EventSource('http://{settings.HOST}:{settings.PORT}/api/v1/streaming/sse-status/{user_id}');"""
    p3 = """
              eventSource.onopen = function(e) {
                log("Event: open");
              };

              eventSource.onerror = function(e) {
                log("Event: error");
                if (this.readyState == EventSource.CONNECTING) {
                  log(`Reconnecting (readyState=${this.readyState})...`);
                } else {
                  log("Error.");
                }
              };


              eventSource.addEventListener('test', function(e) {
                log("Event: test, data: " + e.data);
              });

              eventSource.onmessage = function(e) {
                log("Event: message, data: " + e.data);
              };


            //}

            function stop() {
              eventSource.close();
              log("Disconnected");
            }

            function log(msg) {
              let time = new Date()
              let timeval = time.getHours() + ':' + time.getMinutes() + ':' + time.getSeconds() + '  ';
              logElem.innerHTML = timeval + msg + "<br>" + logElem.innerHTML;
              //document.documentElement.scrollTop = 99999999;
            }
            </script>

            <!-- <button onclick="start()">start</button> -->
            <button onclick="log('stop')">stop</button>
            <div id="logElem" style="margin: 6px 0"></div>

            <!-- <button onclick="stop()">Stop</button> -->

    </body>
</html>
"""
    return p0 + p2 + p3

@router.get('/get-user-sse/{session_id}')
async def get_sse(session_id: str) -> HTMLResponse:

    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(html(session_id))


@router.get('/get-user-sse-test')
async def get_sse_test(session_id: str | None = Cookie(None)) -> HTMLResponse:

    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)

    return HTMLResponse(html(session_id))

def html_ws(user_id):
    p0 = """<!DOCTYPE html>
<html>
    <head>
        <title>Test</title>
    </head>
    <style>
    html * {
      font-size: 12px !important;
      color: #0f0 !important;
      font-family: Andale Mono !important;
      background-color: #000;
    }
    </style>
    """
    p2 = f"""
    <body>
        <h1>WebSocket Of User {user_id}</h1>
        <script>
            let socket;

            function connect() {{
                socket = new WebSocket('wss://api.machine-prod.ru/ws/v1/files/ws-status{user_id}');
    """
    p3 = """
                socket.onopen = function(e) {
                    log("Connection established");
                };

                socket.onmessage = function(event) {
                    log("Received data: " + event.data);
                };

                socket.onerror = function(error) {
                    log("WebSocket Error: " + error.message);
                };

                socket.onclose = function(event) {
                    if (event.wasClean) {
                        log(`Connection closed cleanly, code=${event.code} reason=${event.reason}`);
                    } else {
                        log('Connection died');
                    }
                };
            }

            function stop() {
                if (socket) {
                    socket.close();
                    log("Disconnected");
                }
            }

            function log(msg) {
                let time = new Date()
                let timeval = time.getHours() + ':' + time.getMinutes() + ':' + time.getSeconds() + '  ';
                logElem.innerHTML = timeval + msg + "<br>" + logElem.innerHTML;
            }

            // Автоматически подключаемся при загрузке страницы
            connect();
        </script>

        <button onclick="stop()">Stop</button>
        <button onclick="connect()">Reconnect</button>
        <div id="logElem" style="margin: 6px 0"></div>

    </body>
</html>
"""
    return p0 + p2 + p3



@router.get('/get-user-ws/{session_id}')
async def get_ws(session_id: str) -> HTMLResponse:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(html_ws(session_id))


@router.get('/get-user-ws-test')
async def get_ws(session_id: str | None = Cookie(None)) -> HTMLResponse:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(html_ws(session_id))



def file_upload_html(session_id: str, track_id: str, type: str):
    p0 = """
<!DOCTYPE html>
<head>
    <meta charset="UTF-8">
    <style>
        * {
            font-size: 12px !important;
            color: #0f0 ;
            font-family: Andale Mono !important;
            background-color: #000;
        }

        .progress-wrapper {
            width:100%;
        }

        .progress-wrapper .progress {
            background-color: #0f0;
            width:0%;
            padding:5px 0px 5px 0px;
            color: black;
        }

        .file-upload-button {
            padding: 5px 10px;
            border: 1px solid #0f0;
            cursor: pointer;
            display: inline-block;
            margin-top: 30px;
        }

        .file-upload input[type="file"] {
            display: none;
        }

         input {
             font-size: 12px !important;
             color: #0f0 ;
             font-family: Andale Mono !important;
             background-color: #000;
                }

    </style>
    """
    p1 = """
    <script>
        function postFile() {
            var formdata = new FormData();

            formdata.append('file1', document.getElementById('file1').files[0]);

            var request = new XMLHttpRequest();

            request.upload.addEventListener('progress', function (e) {
                var file1Size = document.getElementById('file1').files[0].size;
                console.log(file1Size);

                if (e.loaded <= file1Size) {
                    var percent = Math.round(e.loaded / file1Size * 100);
                    document.getElementById('progress-bar-file1').style.width = percent + '%';
                    document.getElementById('progress-bar-file1').innerHTML = percent + '%';
                }

                if(e.loaded == e.total){
                    document.getElementById('progress-bar-file1').style.width = '100%';
                    document.getElementById('progress-bar-file1').innerHTML = '100%';
                }
            });

"""
    p2 = f"""
            request.open('post', 'http://127.0.0.1:8001/api/v1/files/true-upload/{session_id}/mock/mock');
            // request.timeout = 45000;
            request.send(formdata);
            """
    p3 = """
        }
    </script>
</head>
<form id="form1">

    <div class="file-upload">
        <label for="file1" class="file-upload-button">Choose file</label>
        <input id="file1" type="file" />

    </div>
    <div class="progress-wrapper">
        <div id="progress-bar-file1" class="progress"></div>
    </div>
    <button type="button" onclick="postFile()">Upload File</button>
</form>
</html>
    """
    return p0 + p1 + p2 + p3

@router.get('/upload-ui/{session_id}/{track_id}/{type}')
async def upload_ui(session_id: str, track_id: str, type: str) -> HTMLResponse:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(file_upload_html(session_id, track_id, type))


@router.get('/upload-ui-test/{track_id}/{type}')
async def upload_ui(track_id: str, type: str, session_id: str | None = Cookie(None)) -> HTMLResponse:
    if not session_id:
        raise EXC(ErrorCode.SessionNotFound)
    return HTMLResponse(file_upload_html(session_id, track_id, type))