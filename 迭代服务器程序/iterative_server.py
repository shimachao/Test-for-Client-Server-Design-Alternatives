# encoding:utf-8
import socket
import sys
import josn

def main(ip, port):
    """ 迭代处理客户端的连接请求"""
    
    listen_socket = socket.socket(family=AF_INET, type=SOCK_STREAM)
    serve_address = (ip, port)
    listen_socket.bind(serve_address)
    listen_socket.listen(10)
    
    while True:
        conn_socket, addr = listen_socket.accept()
    
if __name__ == '__main__':
    if len(sys.argv < 3):
        print("缺少IP和端口号参数\n")
        return;
     else:
         main(sys.argv[1], sys.argv[2])
    