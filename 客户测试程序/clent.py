# encoding:utf-8
import socket
import sys
import josn
import multiprocessing
from multiprocessing import Process
import select
import time

def epoll_loop(epoller, fd_to_socket, fd_to_times):
    """ 在epoller上轮询"""

    # 记录所有socket的状态：1为connneting，2为sending，3为recving
    fd_state = {fd: 1 for fd in fd_to_socket.keys()} # 所有socket的初始状态为1

    # 和fd相关的消息，类型为{fd:bytes}，当socket状态为sending时，msg[fd]为发送消息，当socket的状态为recving时，
    # msg[fd]为接收消息。
    msg = {fd: b'' for fd in fd_to_socket.keys()}

    while True:
        events = epoller.poll()
        for fd, event in events:
            # 如果是连接完成
            if event == select.EPOLLIN and fd_state[fd] == 1:
                # 记录连接完成的时间
                fd_to_times[fd]['connect_completed_time'] = round(time.time() * 1000)
                # todo:把times信息打包发送给服务器

                # 将fd重新注册为关心可写事件
                epoller.modify(fd, select.EPOLLOUT)
                #状态转为sending
                fd_state[fd] = 2

            # 如果是可以发送消息
            elif event == select.EPOLLOUT and fd_state[fd] == 2 :
                
            # 如果是需要接收信息
            elif event == select.EPOLLIN and fd_state[fd] == 3:
                # TODO:接收信息


def mult_connect_to_server(ip, port, conn_num):
    """ 对服务器发起异步多连接"""
    # 创建conn_num个socket
    sockets = [socket.socket() for x in range(conn_num)]

    # 将它们都设为非阻塞
    map(lambda sock: sock.setblocking(False), sockets)

    # 发起连接，并记录每个socket发起连接的时间(单位为毫秒)
    fd_to_times = {}
    for _socket in sockets:
        _socket.connect((ip, port))
        fd_to_times[_socket.fileno()] = {'connect_time':round(time.time() * 1000)}

    # 用一个epoll对象来监听它们
    epoller = select.epoll()
    map(lambda  sock: epoller.register(sock, select.EPOLLIN), sockets)

    # 记录文件描述符号到socket对象的映射
    fd_to_socket = {sock.fileno:sock for sock in sockets}

    # 轮询监听
    epoll_loop(epoller, fd_to_socket, fd_to_times)


def stress_test(server_ip, server_port, conn_num):
    """ 对服务器进行压力测试"""

    # 创建多个进程，每个进程创建多个到服务器的连接，进程数为当前cpu的核心数
    cpu_count = multiprocessing.cpu_count() # cpu核心数
    conn_num_per_pro = conn_num // cpu_count # 每个进程需要创建的连接数

    # 创建cpu_count个进程
    jobs = [p = Process(target=mult_connect_to_server, args=(ip, port, conn_num)) for x in range(cpu_count)]

    # 等待所有进程结束
    map(lambda job:job.join(), jobs)


if __name__ == '__main__':
    if len(sys.argv < 4):
        print("缺少IP、端口号、连接数参数\n")
        return;
     else:
         stress_test(sys.argv[1], sys.argv[2], int(sys.argv[3]))