# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 09:47:30 2017

@author: Administrator
"""

import urllib.request;
from bs4 import BeautifulSoup;

from pandas import Series;
from pandas import DataFrame;
import numpy as np


CITY_CODE = 101280601   # 深圳




class WeatherServer(object):
    def __init__(self, city):
        self.server_url = 'http://www.weather.com.cn/weather/%s.shtml' % city
#        self.soup = ''
#        self.ulsoup = ''
#        print(self.server_url)

    def ConnectServer(self):
        response = urllib.request.urlopen(self.server_url)
        html = response.read()
        self.soup = BeautifulSoup(html)
        
        
    def getOneWeekData(self):
        self.ulSoup = self.soup.find(
            "ul",
            attrs={'class':'t clearfix'}
        )
        
    def getOneWeekTemp(self):
        data = DataFrame(columns=['Day','Temprature'])
        lis = self.ulSoup.find_all('li')
        
        for li in lis:
            h1s = li.find_all('h1')
            ps = li.find_all(
                'p',
                attrs={'class':'tem'}
            )
            if len(h1s)==len(ps):
                day = h1s[0].getText()
                temp = ps[0].getText()
#                print(day,temp)
                data = data.append(
                    Series(
                        [day,temp],
                        index=['Day','Temprature']
                    ),ignore_index=True
                )
        
        tmp = np.array(data)
        data = tmp.tolist()
        return data
    











#response = urllib.request.urlopen(
#    'http://p.3.cn/prices/mgets?skuIds=J_3995643'
#)
#jsonString = response.read();
#
#jsonObject = json.loads(jsonString.decode())
#
#jsonObject[0]['p']














