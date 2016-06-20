# coding:utf-8
import socket
import sys
import json
import multiprocessing
from multiprocessing import Process
import select
import time
import errno
from db import DB


def pack_dict(d):
    """ 将传入的字典转为json字符串，然后在转为utf-8编码的bytes，并在末尾添加一个b'\r'作结束符"""
    s = json.dumps(d)
    bs = s.encode()
    bs += b'\r' # 末尾添加b'\r'表示结束符

    return bs

def unpack_bytes(bs):
    """ 将传入的bytes对象转为json字符串，然后转为dict对象"""
    bs = bs.rstrip(b'\r')  # 去掉末尾的b'r'
    s = bs.decode()  # 转为字符串，根据协议，这个字符符合json格式
    d = json.loads(s)  # 转为dict对象

    return d


class NonblockingIO():
    """ 用来处理非阻塞socket的连接和IO
    每个socket有四种状态：
        0：未完成connect
        1：刚开始发送数据
        2：还有数据需要发送
        3：接收数据"""

    def __init__(self, epoller, db):
        self.epoller = epoller
        self.sockets = {}  # fd到socket的映射
        self.msgs = {}  # fd到要发送或接收消息的映射
        self.states = {}  # 每个fd的状态，未完成connect或完成connect
        self.times = {}  # fd到时间信息的映射

    def add_fd(self, socket_, state = 0):
        """ 将socket_到要处理的集合中
        state：表示添加时socket_的状态，
            0表示未完成connect
            1表示完成connect
        """
        fd = socket_.fileno()
        # 如果该socket已添加过，就直接返回，避免重复添加
        if fd in self.sockets:
            return

        self.sockets[fd] = socket_
        self.msgs[fd] = ''
        self.states[fd] = state
        # 如果该socket未完成connect
        if state == 0:
            # 注册EPOLLIN EPOLLOUT EPOLLERR，因为nonblocking的未完成connect的socket这三个事件都能收到
            self.epoller.register(fd, select.EPOLLIN | select.EPOLLOUT | select.EPOLLERR)
        # 如果该socket已完成connect
        elif state == 1:
            # 只关心EPOLLOUT，因为我们需要在刚完成connect的socket上发送消息
            self.epoller.register(fd, select.EPOLLOUT)

    def send(self, fd):
        """ 检测该fd对应的socket是否完成connect，如果完成就在fd对应的socket上发送数据"""
        # 如果该fd的状态为未完成conncet
        if self.states[fd] == 0:
            self.__handle_unconnect(fd)
            return
        
        # 如果该fd的状态为刚开始发送数据
        if self.states[fd] == 1:
            self.times['request_'] = round(time.time() * 1000)
            # 将时间信息打包，便于发送
            self.msgs[fd] = pack_dict(self.times[fd])
            # 进入下一状态
            self.states[fd] = 2
        
        # 发送数据
        count = self.sockets[fd].send(self.msgs[fd])
        # 去掉已发送的部分
        self.msgs[fd] = self.msgs[fd][count:]

        # 如果数据已发送完
        if len(self.msgs[fd]) == 0:
            # 清空对应的msg
            self.msgs[fd] = ''
            # 进入下一阶段
            self.states[fd] = 3
            # 重新注册只关心EPOLLIN事件
            self.epoller.modify(fd, select.EPOLLIN)

    
    def recv(self, fd):
        """ 检测fd对应的socket是否完成connect，如果已完成就发送数据"""
        # 如果该fd的状态为未完成conncet
        if self.states[fd] == 0:
            self.__handle_unconnect(fd)
            return
        
        # 如果该fd的状态为接收数据
        if self.states[fd] = 3:
            msg = self.sockets[fd].recv(1024)
            # 如果接收到了数据
            if len(msg) > 0:
                self.msgs[fd] += msg
            # 如果数据已接收完毕
            if len(msg) == 0 or msg[-1] == ord('\r'):
                # 记录时间
                self.times[fd]['request_completed_time'] = round(1000*time.time())
                # 解包收到的数据
                d = unpack_bytes(self.msgs[fd])
                # 关闭连接
                self.sockets[fd].close()
                # 重轮询监听中移出
                self.epoller.unregister(fd)
                # 移除
                self.sockets.pop(fd)
                self.states.pop(fd)
                self.times.pop(fd)
                self.msgs.pop(fd)
                # 将数据保存到数据库中
                db.insert(**d)


    def __handle_unconnect(self, fd):
        """ 处理未完成connect的socket"""
        # 检测connect的状态
        r = self.__if_connected(fd)
        # 如果出错
        if r < 0:
            # 移出该fd对应的信息
            self.sockets[fd].close()
            self.epoller.unregister(fd)
            self.times.pop(fd)
            self.msgs.pop(fd)
            self.states.pop(fd)
        # 如果完成了
        elif r == 1:
            # 进入下个状态
            self.states[fd] = 1
            # 重新注册只关心EPOLLOUT事件
            self.epoller.register(fd, select.EPOLLOUT)


    def __if_connected(self,fd):
        """ 判断fd对应的socket的connect状态
        返回值：-1、0、1
        -1表示出错，0表示未完成，1表示完成"""
        return 0



def epoll_loop(epoller, fd_to_socket, fd_to_times, db):
    """ 在epoller上轮询"""

    while True:
        events = epoller.poll()
        for fd, event in events:
            

def mult_connect_to_server(addr, conn_num, db_table_name):
    """ 对服务器发起异步多连接"""
    # 创建conn_num个socket
    sockets = [socket.socket() for x in range(conn_num)]

    # 将它们都设为非阻塞
    map(lambda sock: sock.setblocking(False), sockets)

    # 发起连接，并记录每个socket发起连接的时间(单位为毫秒)
    times = {}
    for _socket in sockets:
        _socket.connect(addr)
        times[_socket.fileno()] = {'connect_time':round(time.time() * 1000)}

    # 用一个epoll对象来监听它们
    epoller = select.epoll()
    map(lambda  sock: epoller.register(sock, select.EPOLLIN), sockets)

    # 记录文件描述符号到socket对象的映射
    sockets = {sock.fileno:sock for sock in sockets}

    # 创建数据访问对象
    db = DB(table_name=db_table_name)

    # 轮询监听
    epoll_loop(epoller, sockets, times, db=db)

    db.close()


def stress_test(addr, conn_num, db_table_name):
    """ 对服务器进行压力测试"""

    # 创建多个进程，每个进程创建多个到服务器的连接，进程数为当前cpu的核心数
    cpu_count = multiprocessing.cpu_count() # cpu核心数
    conn_num_per_pro = conn_num // cpu_count # 每个进程需要创建的连接数

    # 创建cpu_count个进程
    jobs = [p = Process(target=mult_connect_to_server, args=(addr, conn_num, db_table_name)) for x in range(cpu_count)]

    # 开启所有进程
    map(lambda  job: job.start(), jobs)

    # 等待所有进程结束
    map(lambda job:job.join(), jobs)


if __name__ == '__main__':
    if len(sys.argv < 4):
        print("缺少IP、端口号、连接数参数\n")
        return;
     db_table_name = input("输入本次测试创建的数据库表名:")
     print('本次测试将对(%s, %s)发起%d个连接...\n' % (sys.argv[1], sys.argv[2], int(sys.argv[3])))
     
     # 创建放置测试数据需要的数据表
     db = DB(table_name=db_table_name)
     db.create_table()
     del db

     print('本次测试开始...\n')
     stress_test(addr=(sys.argv[1], sys.argv[2]), conn_num=int(sys.argv[3]), db_table_name=db_table_name)

     print('本次测试结束\n')

