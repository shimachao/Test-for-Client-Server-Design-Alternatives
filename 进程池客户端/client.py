import sys
import json
import time
import socket
from db import DB
from multiprocessing import Pool, cpu_count


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


def complete_send(conn_socket, msg):
    """ 将msg通过conn_socket发送出去"""
    while True:
        count = conn_socket.send(msg)
        msg = msg[count:]  # 去掉已发送的部分
        if len(msg) == 0:
            # 如果数据发送完毕
            break


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
            raise socket.error()
        msg += bs
        if bs[-1] == ord('\r'):
            # 如果对方发送完数据
           break
    return msg


def task(addr, db_table_name):
    """ 向addr发送数据，然后接收数据"""
    # 创建socket
    sock = socket.socket()
    try:
        # 发起连接，记录连接发起的时间
        start_conn_time = round(time.time(*1000))
        sock.connect(addr)

        # 记录连接成功的时间
        conn_comp_time = round(time.time(*1000))

        # 准备要发送json数据
        d = {'start_conn_time': start_conn_time,
            'conn_comp_time': conn_comp_time,}
        msg = pack_dict(d)

        # 记录发起请求的时间
        request_time = round(time.time(*1000))
        # 发送数据
        complete_send(sock, msg)
        
        # 开始接收数据
        bmsg = complete_recv(sock)
        # 关闭socket
        sock.close()
        # 记录接收完成的时间
        request_comp_time = round(time.time(*1000))
        # 解包数据
        d = unpack_bytes(bmsg)
        # 将发起请求和请求返回时间插入字典
        d['request_time'] = request_time
        d['request_comp_time'] = request_comp_time
        # 将数据保存到数据库
        db = DB(db_table_name)
        db.insert(**d)
        db.close()
    except socket.error as e:
        print(sock.getsockname,'上连接发生错误，', e)




def stress_test(addr, conn_num, db_table_name):
    """ 创建一个进程池，对服务器进行压力测试"""
    start_time = time.time()
    p = Pool(cpu_count())
    for i in range(conn_num):
        p.apply_async(func=task,args=(addr, db_table_name))

    print('等待任务结束...')
    p.close()
    p.join()
    end_time = time.time()
    print('任务完成...')
    print('本次测试共向服务端发送%', conn_num, '个连接')
    print('耗时', end_time - start_time, 's')
    print('详细数据已记录到test_data数据库的', db_table_name, '表中')



if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('少了ip和端口号参数，请重新运行程序并添加参数')
        sys.exit()
    conn_num = input('本次测试发起的连接数：')
    db_table_name = input('输入本次测试创建的数据库表名:')

    # 创建放置测试数据需要的数据表
    db = DB(table_name=db_table_name)
    db.create_table()  # 创建表
    db.close()
    del db

    print('本次测试开始...\n')
    stress_test(addr=(sys.argv[1], int(sys.argv[2])),conn_num=conn_num, db_table_name=db_table_name)

    print('本次测试结束\n')