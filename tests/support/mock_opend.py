"""Local test-only OpenD protobuf peer. No broker, credentials, or real market data.
Fields follow the official SDK .proto definitions; intentionally fragments replies.
"""
import argparse, hashlib, json, pathlib, socketserver, struct, threading, time
from datetime import date

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

def fields(data):
    """Decode the varint/length-delimited request fields used by option queries."""
    offset = 0
    def read_varint():
        nonlocal offset
        value = shift = 0
        while True:
            byte = data[offset]; offset += 1
            value |= (byte & 127) << shift
            if byte < 128: return value
            shift += 7
    while offset < len(data):
        tag = read_varint(); wire = tag & 7
        if wire == 0: value = read_varint()
        elif wire == 2:
            length = read_varint(); value = data[offset:offset+length]; offset += length
        else: raise ValueError(f'Unsupported test request wire type {wire}')
        yield tag >> 3, value

def option(day, kind, owner):
    stock = dict(fields(owner))[2].decode()
    code = stock + day.replace('-', '')[2:] + ('C' if kind == 1 else 'P') + '100000'
    security_info = integer(1,dict(fields(owner))[1])+text(2,code)
    basic = message(1,security_info)+integer(2,12345+kind)+integer(3,100)+integer(4,8)+text(5,'Test option')+text(6,'2026-01-01')
    extra = integer(1,kind)+message(2,owner)+text(3,day)+double(4,100)+integer(5,0)+text(6,'US')+integer(10,1)
    return message(1,basic)+message(3,extra)

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
                self.server.protocols.append(protocol)
                push=b''
                if protocol==1001:
                    payload=integer(1,1011)+integer(2,1)+integer(3,123)+text(4,'0123456789abcdef')+integer(5,10)+integer(7,1)
                    reply=response(payload)
                elif protocol==1002:
                    payload=b''.join(integer(k,0) for k in range(1,6))+integer(6,1)+integer(7,0)+integer(8,1011)+integer(9,7108)+integer(10,int(time.time()))+integer(16,123)
                    reply=response(payload)
                elif protocol==1004: reply=response(integer(1,int(time.time())))
                elif protocol==3224:
                    reply=response(b''.join(message(1,text(1,day)+integer(3,90)) for day in self.server.option_expirations))
                elif protocol==3209:
                    parameters = dict(fields(dict(fields(body))[1]))
                    start, end = parameters[4].decode()[:10], parameters[5].decode()[:10]
                    self.server.option_requests.append((start, end, parameters.get(2,0)))
                    chains = b''
                    for day in self.server.option_expirations:
                        if start <= day <= end:
                            item = b''.join(message(kind,option(day,kind,parameters[1])) for kind in (1,2) if parameters.get(2,0) in (0,kind))
                            chains += message(1,text(1,day)+message(2,item))
                    reply=response(error='mock option entitlement denied') if self.server.reject else response(chains)
                elif protocol==3222:
                    reply=response(message(1,text(1,'My watchlist')+integer(2,1)))
                elif protocol==3213:
                    basic=message(1,security())+integer(2,123)+integer(3,1)+integer(4,3)+text(5,'Apple')+text(6,'1980-12-12')
                    reply=response(message(1,message(1,basic)))
                elif protocol==2001:
                    account=integer(1,1)+integer(2,9007199254740993)+integer(3,2)+integer(4,2)+integer(6,2)
                    reply=response(message(1,account))
                elif protocol==2008: reply=response()
                elif protocol in (2101,2102):
                    header=integer(1,1)+integer(2,9007199254740993)+integer(3,2)
                    if protocol==2101:
                        funds=b''.join(double(k,v) for k,v in [(1,1000),(2,1200),(3,100),(4,1100),(5,0),(6,0),(7,100)])+integer(8,2)
                        reply=response(message(1,header)+message(2,funds))
                    else:
                        position=integer(1,10)+integer(2,0)+text(3,'AAPL')+text(4,'Apple')+b''.join(double(k,v) for k,v in [(5,10),(6,10),(7,110),(8,100),(9,1100),(10,100),(11,10)])+integer(12,2)+integer(30,2)+integer(31,2)
                        reply=response(message(1,header)+message(2,position))
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
        self.protocols=[]
        self.option_requests=[]
        self.option_expirations=[f'{date.today().year+1}-01-15',f'{date.today().year+1}-02-19']
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
