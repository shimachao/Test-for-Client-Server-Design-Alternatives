# coding:utf-8

import os
import psycopg2 as pg


class DB():
    """ 用于管理对数据库的访问"""

    def __init__(self, table_name):
        """ 连接到dbname数据库"""

        # 从环境变量中获取用户名、密码、数据库名
        user = os.getenv('db_user')
        if not user:
            print('环境变量中没有设置访问数据库需要的用户名\n')
 
        passwd = os.getenv('db_password')
        if not passwd:
            print('环境变量中没有设置数据库密码\n')

        db_name = os.getenv('db_name')
        if not db_name:
            print('环境变量中没有设置要访问的数据库名称\n')

        self.user = user
        self.passwd = passwd
        self.db_name = db_name
        self.table_name = table_name
        self.conn = pg.connect(user=user, password=passwd, database=db_name, host='localhost', port=5432)
        self.cursor = self.conn.cursor()
    

    def create_table(self, table_name=None):
        """ 创建表"""
        if table_name:
            self.table_name = table_name

        sql_str = ("CREATE TABLE %s("
                    "id  SERIAL PRIMARY KEY,"
                    "start_conn_time bigint NOT NULL,"
                    "conn_comp_time bigint NOT NULL,"
                    "request_time bigint NOT NULL,"
                    "request_comp_time bigint NOT NULL"
                    ")" % self.table_name)
                    
        self.cursor.execute(sql_str)
        self.conn.commit()


    def insert(self, start_conn_time, conn_comp_time,request_time, request_comp_time):
        """ 向数据库中插入数据"""
        sql_str = ("INSERT INTO %s(start_conn_time, conn_comp_time, request_time, request_comp_time)"
                " VALUES(%d, %d, %d, %d)") % (self.table_name, start_conn_time, conn_comp_time, \
                                            request_time, request_comp_time)

        self.cursor.execute(sql_str)
        self.conn.commit()


    def close(self):
        """ 关闭对数据库的连接"""
        if not self.conn:
            self.conn.commit()
            if not self.cursor:
                self.cursor.close()
            self.conn.close()
        self.conn = None
        self.cursor = None


    def __del__(self):
        self.close()
        

# 测试
if __name__ == '__main__':
    import time
    table_name = input("输入表名:")
    db = DB(table_name=table_name)
    db.create_table()
    for i in range(3):
        t = round(time.time()*1000)
        db.insert(t, t, t, t)

