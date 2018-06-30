# -*- coding: utf-8 -*-
"""
Created on Sat Dec  2 10:17:00 2017

@author: Administrator
"""


import json
import requests


TULING_URL = 'http://www.tuling123.com/openapi/api'
API_KEY = '2addf14a803e4721835e2bad77461950'
USERID = 'cxb3713'



def getTulingResp(info, key=API_KEY, userid=USERID):
    dict = {'key':'', 'info':'', 'userid':''}
    dict['key'] = key
    dict['info'] = info
    dict['userid'] = userid
    r = requests.post(TULING_URL, data=json.dumps(dict))
    
    return r.text



#res = getTulingResp('今天星期几')
#print(res)



