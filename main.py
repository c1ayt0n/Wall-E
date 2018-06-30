# -*- coding: utf-8 -*-
"""
Created on Wed Nov 29 22:48:13 2017

@author: Administrator
"""


import sys
from wechat import Wechat
from weather import WeatherServer
import datetime
from tuling import getTulingResp
import json


class WXBot(Wechat):
    def __init__(self):
        Wechat.__init__(self)
        self.start_sched = datetime.datetime(2017, 11, 30, 23, 3, 00)
        self.sched_cnt = []
        self.sched_content = []
        self.sched_list = []
    
    def timer_run(self):
        now = datetime.datetime.now()
        if now > self.start_sched + datetime.timedelta(seconds=3) and len(self.sched_list):
            for i in range(len(self.sched_list)):
                if self.sched_cnt[i] > 0:
                    function = self.sched_list[i]
                    function(self.sched_content[i])
                    self.sched_cnt[i] -= 1
            self.start_sched = now
            
    
    def timer_function_register(self, fun, content, cnt):
        self.sched_list.append(fun)
        self.sched_content.append(content)
        self.sched_cnt.append(cnt)
        
    
    def schedule(self):
        self.timer_run()
        
    def handle_msg_all(self, msg):
        print('..', sys._getframe().f_code.co_name)
        print('msg=', msg)
        username = msg['user']['name']
        print(username)
        info = msg['content']['data']
        if msg['msg_type_id'] == 4:    # 普通信息
            res_json = getTulingResp(info)
            print(type(res_json))
            res = json.loads(res_json)
            print(res)
            text = res['text']
            print(text)
            uid = Wechat.get_user_id(self, username)
            Wechat.send_msg_by_uid(self, text, uid)
        elif msg['msg_type_id'] == 37:   # 添加好友请求
            print(info)
            Wechat.apply_useradd_requests(self, info)




if __name__ == "__main__":         
    bot = WXBot()
    '''
    weather = WeatherServer(101280601)   # shenzhen
    weather.ConnectServer()
    weather.getOneWeekData()
    temp = weather.getOneWeekTemp()
    msg = str(temp)
    print(msg)
    bot.timer_function_register(bot.send_msg_by_uid, msg, 3)
    '''
    
    bot.run()
    
    












