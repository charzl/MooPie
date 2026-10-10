"""Local test-only OpenD protobuf peer. No broker, credentials, or real market data.
Fields follow the vendored official .proto definitions; intentionally fragments replies.
"""
import argparse, hashlib, json, pathlib, socketserver, struct, threading, time

def varint(value):
    data=bytearray()
    while value>127: data.append((value&127)|128); value>>=7
    data.append(value); return bytes(data)
def integer(field,value): return varint(field<<3)+varint(value)
def message(field,data): return varint((field<<3)|2)+varint(len(data))+data
def text(field,value): return message(field,value.encode())
def double(field,value): return varint((field<<3)|1)+struct.pack('<d',value)
def response(payload=b'',error=None):
    return integer(1,0)+message(4,payload) if error is None else integer(1,1)+text(2,error)
def security(): return integer(1,11)+text(2,'AAPL')
def quote(price):
    return (message(1,security())+integer(2,0)+text(3,'1980-12-12')+double(4,.01)+text(5,'2026-01-01 09:30:00')
        +b''.join(double(k,v) for k,v in [(6,115),(7,105),(8,100),(9,price),(10,100),(12,123456),(13,.1),(14,15)])
        +integer(11,123456789)+text(24,'Apple'))
def candle(price=110):
    return text(1,'2026-01-01 00:00:00')+integer(2,0)+b''.join(double(k,v) for k,v in [(3,115),(4,105),(5,100),(6,price),(7,100)])+integer(8,1000)
def packet(protocol,serial,body):
    return struct.pack('<2sIBBII20s8s',b'FT',protocol,0,0,serial,len(body),hashlib.sha1(body).digest(),b'\0'*8)+body

class Peer(socketserver.BaseRequestHandler):
    def handle(self):
        buffer=b''
        while True:
            chunk=self.request.recv(65536)
            if not chunk: return
            buffer+=chunk
            while len(buffer)>=44:
                flag,protocol,fmt,version,serial,length,digest,_=struct.unpack('<2sIBBII20s8s',buffer[:44])
                if len(buffer)<44+length: break
                body=buffer[44:44+length]; buffer=buffer[44+length:]
                if flag!=b'FT' or fmt!=0 or hashlib.sha1(body).digest()!=digest: return
                push=b''
                if protocol==1001:
                    payload=integer(1,1011)+integer(2,1)+integer(3,123)+text(4,'0123456789abcdef')+integer(5,10)+integer(7,1)
                    reply=response(payload)
                elif protocol==1002:
                    payload=b''.join(integer(k,0) for k in range(1,6))+integer(6,1)+integer(7,0)+integer(8,1011)+integer(9,7108)+integer(10,int(time.time()))+integer(16,123)
                    reply=response(payload)
                elif protocol==1004: reply=response(integer(1,int(time.time())))
                elif protocol in (3001,3002):
                    reply=response(error='mock entitlement denied') if self.server.reject else response()
                elif protocol==3004:
                    reply=response(message(1,quote(110)))
                    push=packet(3005,0,response(message(1,quote(111))))
                elif protocol==3006:
                    reply=response(message(1,security())+message(2,candle())+text(3,'Apple'))
                    push=packet(3007,0,response(integer(1,1)+integer(2,2)+message(3,security())+message(4,candle(112))))
                else: reply=response(error=f'Unsupported test protocol {protocol}')
                data=packet(protocol,serial,reply)+push
                self.request.sendall(data[:7]); self.request.sendall(data[7:])
                if protocol==3004 and self.server.disconnect_after_quote: return

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True; daemon_threads=True
    def __init__(self,port=0,reject=False,disconnect_after_quote=False):
        self.reject=reject; self.disconnect_after_quote=disconnect_after_quote
        super().__init__(('127.0.0.1',port),Peer)
    def start(self):
        self.thread=threading.Thread(target=self.serve_forever,daemon=True); self.thread.start(); return self
    def close(self): self.shutdown(); self.server_close(); self.thread.join(timeout=3)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--ready-file',required=True); parser.add_argument('--port',type=int,default=0)
    parser.add_argument('--reject',action='store_true'); parser.add_argument('--disconnect-after-quote',action='store_true'); args=parser.parse_args()
    server=Server(args.port,args.reject,args.disconnect_after_quote)
    pathlib.Path(args.ready_file).write_text(json.dumps({'port':server.server_address[1]}))
    server.serve_forever()
