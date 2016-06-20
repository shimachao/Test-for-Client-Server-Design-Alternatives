# coding:utf-8
import socket
import sys
import json
import signal

class Closed_error(Exception):
    """ 对方关闭了连接"""
    def __str__(self):
        return repr('连接已关闭')


def complete_recv(conn_socket):
    """ 将conn_socket上的数据读完,
    将接收到的所有数据用一个bytes对象返回"""
    msg = b''
    while True:
        bs = conn_socket.recv(1024)
        if len(bs) == 0:
            # 如果对方关闭了连接
            conn_socket.close()
            # 抛出异常，表示未意料到的关闭
            raise Closed_error()
        msg += bs
        if bs[-1] == ord('\r'):
            # 如果对方发送完数据
           break
    return msg

def complete_send(conn_socket, msg):
    """ 将msg通过conn_socket发送出去"""
    while True:
        count = conn_socket.send(msg)
        msg = msg[count:]  # 去掉已发送的部分
        if len(msg) == 0:
            # 如果数据发送完毕
            break


def server(ip, port):
    """ 迭代处理客户端的连接请求"""
    
    listen_socket = socket.socket()
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    listen_socket.bind((ip, port))
    listen_socket.listen(1024)
    
    conn_socket = None
    # SIGINT信号的处理函数
    def sigint_handler(sig_num, addtion):
        listen_socket.close()
        if conn_socket:
            conn_socket.close()
        print('程序被强制退出...')
        sys.exit()
    
    # 注册对退出信号SIGINT的处理
    signal.signal(signal.SIGINT, sigint_handler)

    while True:
        # 接受一个连接
        conn_socket, addr = listen_socket.accept()
        try:
            # 读取客户端发过来的数据
            msg = complete_recv(conn_socket)
            # 将数据原封不动发送回去
            complete_send(conn_socket, msg)
        except Closed_error:
            print('来自', conn_socket.getpeername(), '的连接提前关闭\n')
        finally:
            conn_socket.close()


    
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("缺少IP和端口号参数\n")
        sys.exit()

    server(sys.argv[1], int(sys.argv[2]))
    