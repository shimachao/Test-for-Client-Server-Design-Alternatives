# coding:utf-8
import os
import sys
import josn
import socket
import select
import signal
from select import epoll
from multiprocessing import Pool, cpu_count,Process

class SocketIO():
    """ 此类专门用于在套接字上读取信息"""

    def __init__(self, epoller):
        self.epoller = epoller
        self.sockets = {}  # fd到socket的映射
        self.msgs = {}  # fd到消息的映射


    def add_fd(self, socket_):
        """ 将socket_添加到要处理的集合中"""
        # 如果该socket不存在才添加
        if scoket_.fileno() not in self.sockets:
            self.sockets[socket_.fileno()] = socket_
            self.msgs[socket_.fileno()] = ''  # 设置初始消息为空
            self.epoller.register(socket_.fileno(), select.EPOLLIN)


    def recv(self, fd):
        """ 在fd对应的socket读"""
        # 如果该fd不在要处理的集合中，则不处理
        if fd not in self.sockets:
            return

        # 接收消息，并判读对方是否关闭了连接
        msg = self.sockets[fd].recv(1024)
        # 如果对方关闭了连接
        if len(msg) = 0:
            print(self.socket.ggetpeername ,'提前关闭了连接')
            # 关闭连接
            self.sockets[fd].close()
            # 移出监听
            self.epoller.unregister(fd)
            # 从要处理的集合中删除
            self.sockets.pop(fd)
            self.states.pop(fd)
            self.msgs.pop(fd)
            return
        else:
            self.msgs[fd] += msg
        
        # 判读对方是否发送完数据
        if msg[-1] == ord('\r'):
            # 如果对方已经发送完消息，则进入下一状态
            self.states[fd] = 2
            # 重新关注该fd上的可写事件
            self.epoller.modify(fd, select.EPOLLOUT)


    def send(self, fd):
        """ 在fd对应的socket上发送消息"""
        # 如果该fd不在要处理的集合中，则不处理
        if fd not in self.sockets:
            return
        
        # 发送消息
        count = self.sockets[fd].send(self.msgs[fd])
        # 将发送成功的部分去除
        self.msgs[fd] = self.msgs[fd][count:]

        # 如果数据发送完毕，就关闭连接，并不再关注该fd对应的socket
        if len(self.msgs[fd] == 0):
            self.sockets[fd].close()
            self.epoller.unregister(fd)
            self.sockets.pop(fd)
            self.msgs.pop(fd)



def epoll_loop(epoller, listen_socket_fd):
    """ 监听listen_socket 如果收到新的连接就把新的连接也加入监控"""

    SocketIO io_hander(epoller)  # 专门处理io的对象
    while  True:
        events = epoller.poll()
        for fd, flag in events:
            # 如果是listen socket上的读事件
            if fd == listen_socket_fd and flag == select.EPOLLIN:
                # 接受新连接
                conn_socket,addr = sockets[listen_socket_fd].accept()
                # 将新连接加入监听计划
                io_hander.add(conn_socket)

            # 如果是普通连接上的可读事件
            elif flag == select.EPOLLIN:
                io_hander.recv(fd)

            # 如果是普通连接上的可写事件
            elif flag == select.EPOLLOUT:
                io_hander.send(fd)



def server(ip, port):
    """ 利用IO复用在监听并处理客户连接"""
    # 创建监听套接字
    listen_socket = socket.socket()
    serve_address = (ip, port)
    # 设置地址重用和端口重用
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    listen_socket.bind(serve_address)
    listen_socket.listen(1024)

    # 创建epoller对象
    epoller = epoll()

    # 将listen_socket加入到epoller的监听中
    epoller.register(listen_socket, select.EPOLLIN)

    # SIGINT信号的处理函数
    def sigint_handler(sig_num, addtion):
        listen_socket.close()
        epoller.close()
        print('程序被强制退出...')
        sys.exit()
    
    # 注册对退出信号SIGINT的处理
    signal.signal(signal.SIGINT, sigint_handler)

    print('进程', os.getpid(), '已启动')

    # 开始epoll轮询
    epoll_loop(epoller, listen_socket.fileno(), sockets)


def multi_server(ip, port, process_num):
    """ 利用进程池+io复用处理客户请求"""

    print('主进程', os.getpid(), '已启动')

    # 创建并启动子进程
    for i in range(1, process_num):
        p = Process(target=server, args=(ip, port))
        p.start()
    
    # 主进程也做同样的服务
    server(ip, port)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("缺少IP和端口号参数\n")
        return;
    
    count = int(input('输入你希望创建的进程数(提示:本机有%d个cpu核):' % cpu_count()))
    print('serving at', sys.argv[1], sys.argv[2])
    multi_server(sys.argv[1], int(sys.argv[2]), count)  # 开始服务