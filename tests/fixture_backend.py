"""Loopback-only HTTP/WebSocket backend used by native configuration tests."""
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from socketserver import ThreadingMixIn
import struct

def receive(stream,count):
    data=b''
    while len(data)<count:
        block=stream.read(count-len(data)) if hasattr(stream,'read') else stream.recv(count-len(data))
        if not block: raise EOFError('Unexpected fixture EOF')
        data+=block
    return data

class FixtureServer(ThreadingMixIn,HTTPServer):
    daemon_threads=True

class RouteBackend(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def reply(self):
        size=int(self.headers.get('Content-Length','0'))
        body=self.rfile.read(size) if size else b''
        value=dict(role=self.server.role,path=self.path,method=self.command,body_bytes=len(body),
                   headers={k.lower():v for k,v in self.headers.items()})
        if self.headers.get('Upgrade','').lower()=='websocket':
            self.connection.settimeout(6)
            accept=base64.b64encode(hashlib.sha1((self.headers['Sec-WebSocket-Key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            self.send_response(101);self.send_header('Upgrade','websocket');self.send_header('Connection','Upgrade')
            self.send_header('Sec-WebSocket-Accept',accept);self.end_headers();self.wfile.flush()
            try:
                head=receive(self.rfile,2)
                if head[0]!=0x81 or not head[1]&128: raise ValueError('Expected masked text frame')
                length=head[1]&127
                if length==126: length=struct.unpack('!H',receive(self.rfile,2))[0]
                if length>4096: raise ValueError('Oversize fixture frame')
                mask=receive(self.rfile,4);encoded=receive(self.rfile,length)
                value['message']=bytes(b^mask[i%4] for i,b in enumerate(encoded)).decode()
                data=json.dumps(value).encode()
                self.wfile.write(b'\x81'+(bytes([len(data)]) if len(data)<126 else b'\x7e'+struct.pack('!H',len(data)))+data)
                self.wfile.flush()
            except (EOFError,OSError): pass
            self.close_connection=True
            return
        failed=self.path.split('?',1)[0].endswith('/fail')
        data=b'SENSITIVE BACKEND ERROR' if failed else json.dumps(value).encode()
        self.send_response(500 if failed else 200)
        for key,value in [('Content-Type','application/json'),('Content-Length',str(len(data))),
                          ('Connection','close'),('Cache-Control','public, max-age=86400'),
                          ('Expires','Thu, 01 Jan 2037 00:00:00 GMT'),('Content-Security-Policy','default-src *'),
                          ('X-Frame-Options','DENY'),('Access-Control-Allow-Origin','*'),
                          ('Access-Control-Allow-Credentials','true'),('X-Powered-By','SecretRuntime/1'),
                          ('Set-Cookie','JSESSIONID=fixture; Path=/'),('Set-Cookie','SESSION=fixture; Path=/'),
                          ('Set-Cookie','XSRF-TOKEN=fixture; Path=/')]: self.send_header(key,value)
        self.end_headers()
        if self.command!='HEAD': self.wfile.write(data)
        self.close_connection=True
    do_GET=do_HEAD=do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=reply
    def log_message(self,*args): pass
