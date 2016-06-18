# coding:utf-8
import socket
import sys
import josn
from multiprocessing import Pool, cpu_count,Process
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


def handle_connect(conn_socket):
    """ 处理conn_socket上的连接"""
    # 退出信号的处理函数
    def sigint_handler(sig_num, addtion):
        conn_socket.close()
        sys.exit()
    
    # 注册对退出信号SIGINT的处理
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        # 读取数据
        msg = complete_recv(conn_socket)
        # 发送数据
        complete_send(conn_socket, msg)
    except Closed_error:
        print('读取数据时，对方关闭了连接')
    finally:
        conn_socket.close()


def accept_and_handle(listen_socket):
    """ 监听并处理连接"""
    conn_socket = None
    # 退出信号的处理函数
    def sigint_handler(sig_num, addtion):
        if conn_socket:
            conn_socket.close()
        sys.exit()
    
    # 注册对退出信号SIGINT的处理
    signal.signal(signal.SIGINT, sigint_handler)

    while True:
        # 监听
        nonlocal conn_socket
        conn_socket, addr = listen_socket.accept()
        # 处理连接
        handle_connect(conn_socket)


def server(ip, port):
    """ 预先创建进程池，在（ip, prot）上接收客户的连接"""
    # 创建监听套接字
    listen_socket = socket.socket(family=AF_INET, type=SOCK_STREAM)
    serve_address = (ip, port)
    listen_socket.bind(serve_address)
    listen_socket.listen(1024)

    # 退出信号的处理函数
    def sigint_handler(sig_num, addtion):
        listen_socket.close()
        print('程序被强制退出...')
        sys.exit()
    
    # 注册对退出信号SIGINT的处理
    signal.signal(signal.SIGINT, sigint_handler)
    
    # 预先创建cpu_count个进程
    for i in range(cpu_count()):
        p = Process(target=accept_and_handle, args=(listen_socket,))
        p.start()


if __name__ == '__main__':
    if len(sys.argv < 3):
        print("缺少IP和端口号参数\n")
        return;
     else:
         print('serving at', sys.argv[1], sys.argv[2])
         server(sys.argv[1], sys.argv[2])  # 开始服务