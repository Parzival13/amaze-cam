import io
import logging
from http import server
import cv2
import socketserver
from threading import Condition

PAGE = """\
<html>
<head>
    <title>USB Camera Web Stream</title>
</head>
<body>
    <h1>USB Camera Stream</h1>
    <div>
        <img src="stream.mjpg" width="640" height="480" style="margin:0 0 20px 0"/>
    </div>
</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, frame):
        with self.condition:
            self.frame = frame
            self.condition.notify_all()

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()

class StreamingServer(server.HTTPServer):
    allow_reuse_address = True

camera = cv2.VideoCapture(0)  # Use the appropriate camera index
output = StreamingOutput()

try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    print("Streaming.")
    
    while True:
        ret, frame = camera.read()
        if not ret:
            break
        
        frame = cv2.resize(frame, (640, 480))
        _, jpeg_frame = cv2.imencode('.jpg', frame)
        output.write(jpeg_frame.tobytes())

        server.handle_request()  # Handle a single request, non-blocking

finally:
    print("Stream ended.")
    camera.release()
    