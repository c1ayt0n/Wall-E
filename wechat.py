# -*- coding: utf-8 -*-
"""
Created on Sun Nov 26 10:29:39 2017

@author: Administrator
"""


import os
import sys
import traceback
import webbrowser
import pyqrcode
import requests
import mimetypes
import json
import xml.dom.minidom
import urllib
import time
import re
import random

from traceback import format_exc
from requests.exceptions import ConnectionError, ReadTimeout
import html


UNKONWN = 'unkonwn'
SUCCESS = '200'
SCANED = '201'
TIMEOUT = '408'


class SafeSession(requests.Session):
    def request(self, method, url, params=None, data=None, headers=None, cookies=None, files=None, auth=None,
                timeout=None, allow_redirects=True, proxies=None, hooks=None, stream=None, verify=None, cert=None,
                json=None):
        for i in range(3):
            try:
                return super(SafeSession, self).request(method, url, params, data, headers, cookies, files, auth,
                                                        timeout,
                                                        allow_redirects, proxies, hooks, stream, verify, cert, json)
            except Exception as e:
                #print e.message, traceback.format_exc()
                continue

        #重试3次以后再加一次，抛出异常
        try:
            return super(SafeSession, self).request(method, url, params, data, headers, cookies, files, auth,
                                                    timeout,
                                                    allow_redirects, proxies, hooks, stream, verify, cert, json)
        except Exception as e:
            raise e



class Wechat(object):
    def __init__(self):
        self.DEBUG = False
        self.temp_pwd  =  './'
        self.session = SafeSession()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5'})
        self.qr_file_path = os.path.join(self.temp_pwd, 'wxqr.png')
        self.conf = {'qr':'png'}
        
        self.redirect_uri = ''
        self.base_uri = ''
        self.base_host = ''
        
        self.device_id = 'e' + repr(random.random())[2:17]
        
        self.is_big_contact = False  #通讯录人数过多，无法直接获取
        
        self.my_account = {}  # 当前账户

        # 所有相关账号: 联系人, 公众号, 群组, 特殊账号
        self.member_list = []

        # 所有群组的成员, {'group_id1': [member1, member2, ...], ...}
        self.group_members = {}

        # 所有账户, {'group_member':{'id':{'type':'group_member', 'info':{}}, ...}, 'normal_member':{'id':{}, ...}}
        self.account_info = {'group_member': {}, 'normal_member': {}}

        self.contact_list = []  # 联系人列表
        self.public_list = []  # 公众账号列表
        self.group_list = []  # 群聊列表
        self.special_list = []  # 特殊账号列表
        self.encry_chat_room_id_list = []  # 存储群聊的EncryChatRoomId，获取群内成员头像时需要用到

        self.file_index = 0
    
    
    def run(self):
        self.get_uuid()
        print('uuid=%s' % self.uuid)
        self.gen_qr_code()
        print('gen qrcode ok')
        
        ret = self.wait4login()
        if ret != SUCCESS:
            print('login error, retcode=%s' % (ret))
            return
        if self.login():
            print('login success')
        else:
            print('login error')
            return
        
        if self.init():
            print('init success')
        else:
            print('init error')
            return
            
        self.status_notify()
        self.get_contact()
        self.proc_msg()
            
#    @staticmethod
#    def to_unicode(string, encoding='utf-8'):
#        """
#        将字符串转换为Unicode
#        :param string: 待转换字符串
#        :param encoding: 字符串解码方式
#        :return: 转换后的Unicode字符串
#        """
#        if isinstance(string, str):
#            return string.decode(encoding)
##        elif isinstance(string, unicode):
##            return string
#        else:
#            raise Exception('Unknown Type')
            
        
    def get_uuid(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': 'wx782c26e4c19acffb',
            'fun': 'new',
            'lang': 'zh_CN',
            '_': int(time.time()) * 1000 + random.randint(1, 999),
        }
        r = self.session.get(url, params=params)
        r.encoding = 'utf-8'
        data = r.text
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        if pm:
            code = pm.group(1)
            self.uuid = pm.group(2)
            return code == '200'
        return False
        
    def gen_qr_code(self):
        string = 'https://login.weixin.qq.com/l/' + self.uuid
        qr = pyqrcode.create(string)
        if self.conf['qr'] == 'png':
            qr.png(self.qr_file_path, scale=8)
#            show_image(qr_file_path)
            # img = Image.open(qr_file_path)
            # img.show()
        elif self.conf['qr'] == 'tty':
            qr.png(self.qr_file_path, scale=8)
            print(qr.terminal(quiet_zone=1))
            
    def get_request(self, url):
        r = self.session.get(url)
        r.encoding = 'utf-8'
        data = r.text
        param = re.search(r'window.code=(\d+);', data)
        code = param.group(1)
        return code, data
        
    def wait4login(self):
        LOGIN_TEMPLATE = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s'
        tip = 1
        
        TRY_TIMES = 10
        times = 0
        while times < TRY_TIMES:
            url = LOGIN_TEMPLATE % (tip, self.uuid, int(time.time()))
            print(url)
            code, data = self.get_request(url)
            if code == SCANED:
                print('please scan firstly..')
                tip = 0
            elif code == SUCCESS:
                param = re.search(r'window.redirect_uri="(\S+?)";', data)
                redirect_uri = param.group(1) + '&fun=new'
                self.redirect_uri = redirect_uri
                self.base_uri = redirect_uri[:redirect_uri.rfind('/')]
                temp_host = self.base_uri[8:]
                self.base_host = temp_host[:temp_host.find("/")]
                print(self.redirect_uri, self.base_uri, self.base_host)
                return code
            elif code == TIMEOUT:
                print('timeout')
            else:
                print('unknown')
        return code
    
    
    
    def login(self):
        if len(self.redirect_uri) < 4:
            print('[ERROR] Login failed due to network problem, please try again.')
            return False
        r = self.session.get(self.redirect_uri)
        r.encoding = 'utf-8'
        data = r.text
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement

        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data
        
        print('%s %s %s %s' % (self.skey, self.sid, self.uin, self.pass_ticket))
        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            return False

        self.base_request = {
            'Uin': self.uin,
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.device_id,
        }
        return True
                                                  
        
    def init(self):
        url = self.base_uri + '/webwxinit?r=%i&lang=en_US&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        self.sync_key = dic['SyncKey']
        self.my_account = dic['User']
        self.sync_key_str = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val'])
                                      for keyVal in self.sync_key['List']])
        print('sync_key=%s'     % (self.sync_key))
        print('my_account=%s'   % (self.my_account))
        print('sync_key_str=%s' % (self.sync_key_str))
        return dic['BaseResponse']['Ret'] == 0
        
    
    def status_notify(self):
        url = self.base_uri + '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % self.pass_ticket
        self.base_request['Uin'] = int(self.base_request['Uin'])
        params = {
            'BaseRequest': self.base_request,
            "Code": 3,
            "FromUserName": self.my_account['UserName'],
            "ToUserName": self.my_account['UserName'],
            "ClientMsgId": int(time.time())
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        return dic['BaseResponse']['Ret'] == 0
    
        
    def get_contact(self):
        """获取当前账户的所有相关账号(包括联系人、公众号、群聊、特殊账号)"""
        if self.is_big_contact:
            return False
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' \
                              % (self.pass_ticket, self.skey, int(time.time()))

        #如果通讯录联系人过多，这里会直接获取失败
        try:
            r = self.session.post(url, data='{}')
        except Exception:
            self.is_big_contact = True
            return False
        r.encoding = 'utf-8'
        if self.DEBUG:
            with open(os.path.join(self.temp_pwd,'contacts.json'), 'w') as f:
                f.write(r.text.encode('utf-8'))
        dic = json.loads(r.text)
        self.member_list = dic['MemberList']

        special_users = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail',
                         'fmessage', 'tmessage', 'qmessage', 'qqsync', 'floatbottle',
                         'lbsapp', 'shakeapp', 'medianote', 'qqfriend', 'readerapp',
                         'blogapp', 'facebookapp', 'masssendapp', 'meishiapp',
                         'feedsapp', 'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
                         'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c',
                         'officialaccounts', 'notification_messages', 'wxid_novlwrv3lqwv11',
                         'gh_22b87fa7cb3c', 'wxitil', 'userexperience_alarm', 'notification_messages']

        self.contact_list = []
        self.public_list = []
        self.special_list = []
        self.group_list = []

        for contact in self.member_list:
            if contact['VerifyFlag'] & 8 != 0:  # 公众号
                self.public_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'public', 'info': contact}
            elif contact['UserName'] in special_users:  # 特殊账户
                self.special_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'special', 'info': contact}
            elif contact['UserName'].find('@@') != -1:  # 群聊
                self.group_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'group', 'info': contact}
            elif contact['UserName'] == self.my_account['UserName']:  # 自己
                self.account_info['normal_member'][contact['UserName']] = {'type': 'self', 'info': contact}
            else:
                self.contact_list.append(contact)
                self.account_info['normal_member'][contact['UserName']] = {'type': 'contact', 'info': contact}

        self.batch_get_group_members()

        for group in self.group_members:
            for member in self.group_members[group]:
                if member['UserName'] not in self.account_info:
                    self.account_info['group_member'][member['UserName']] = \
                        {'type': 'group_member', 'info': member, 'group': group}

        if self.DEBUG:
            with open(os.path.join(self.temp_pwd,'contact_list.json'), 'w') as f:
                f.write(json.dumps(self.contact_list))
            with open(os.path.join(self.temp_pwd,'special_list.json'), 'w') as f:
                f.write(json.dumps(self.special_list))
            with open(os.path.join(self.temp_pwd,'group_list.json'), 'w') as f:
                f.write(json.dumps(self.group_list))
            with open(os.path.join(self.temp_pwd,'public_list.json'), 'w') as f:
                f.write(json.dumps(self.public_list))
            with open(os.path.join(self.temp_pwd,'member_list.json'), 'w') as f:
                f.write(json.dumps(self.member_list))
            with open(os.path.join(self.temp_pwd,'group_users.json'), 'w') as f:
                f.write(json.dumps(self.group_members))
            with open(os.path.join(self.temp_pwd,'account_info.json'), 'w') as f:
                f.write(json.dumps(self.account_info))
        return True
    
    
    def test_sync_check(self):
        for host1 in ['webpush.', 'webpush2.']:
            self.sync_host = host1+self.base_host
            try:
                retcode = self.sync_check()[0]
            except:
                retcode = -1
            if retcode == '0':
                return True
        return False
    
    
    def check_msg(self):
        [retcode, selector] = self.sync_check()
        print('[DEBUG] sync_check:%s %s' % (retcode, selector))
        if retcode == '1100':  # 从微信客户端上登出
            return False
        elif retcode == '1101':  # 从其它设备上登了网页微信
            return False
        elif retcode == '0':
            if selector == '2':  # 有新消息
                r = self.sync()
                print(r)
                if r is not None:
                    self.handle_msg(r)                    
            elif selector == '3':  # 未知
                r = self.sync()
                if r is not None:
                    self.handle_msg(r)
            elif selector == '4':  # 通讯录更新
                r = self.sync()
                if r is not None:
                    self.get_contact()
            elif selector == '6':  # 可能是红包
                r = self.sync()
                if r is not None:
                    self.handle_msg(r)
            elif selector == '7':  # 在手机上操作了微信
                r = self.sync()
                if r is not None:
                    self.handle_msg(r)
            elif selector == '0':  # 无事件
                pass
            else:
                r = self.sync()
                if r is not None:
                    self.handle_msg(r)
        else:
            time.sleep(10)
        self.schedule()
        return True
    
    
    def proc_msg(self):
        self.test_sync_check()
        
        while True:
            check_time = time.time()
            try:
                res = self.check_msg()
                if not res:
                    break
            except:
                print('[ERROR] Except in proc_msg')
                print(format_exc())
            check_time = time.time() - check_time
            if check_time < 0.8:
                time.sleep(1 - check_time)
        
    def batch_get_group_members(self):
        """批量获取所有群聊成员信息"""
        url = self.base_uri + '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            "Count": len(self.group_list),
            "List": [{"UserName": group['UserName'], "EncryChatRoomId": ""} for group in self.group_list]
        }
        r = self.session.post(url, data=json.dumps(params))
        r.encoding = 'utf-8'
        dic = json.loads(r.text)
        group_members = {}
        encry_chat_room_id = {}
        for group in dic['ContactList']:
            gid = group['UserName']
            members = group['MemberList']
            group_members[gid] = members
            encry_chat_room_id[gid] = group['EncryChatRoomId']
        self.group_members = group_members
        self.encry_chat_room_id_list = encry_chat_room_id
        
    def sync_check(self):
        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.device_id,
            'synckey': self.sync_key_str,
            '_': int(time.time()),
        }
        url = 'https://' + self.sync_host + '/cgi-bin/mmwebwx-bin/synccheck?' + urllib.parse.urlencode(params)
        try:
            r = self.session.get(url, timeout=60)
            r.encoding = 'utf-8'
            data = r.text
            pm = re.search(r'window.synccheck=\{retcode:"(\d+)",selector:"(\d+)"\}', data)
            retcode = pm.group(1)
            selector = pm.group(2)
            return [retcode, selector]
        except:
            return [-1, -1]
        
    def sync(self):
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&lang=en_US&pass_ticket=%s' \
                              % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            'SyncKey': self.sync_key,
            'rr': ~int(time.time())
        }
        try:
            r = self.session.post(url, data=json.dumps(params), timeout=60)
            r.encoding = 'utf-8'
            dic = json.loads(r.text)
            if dic['BaseResponse']['Ret'] == 0:
                self.sync_key = dic['SyncKey']
                self.sync_key_str = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val'])
                                              for keyVal in self.sync_key['List']])
            return dic
        except:
            return None
        
    
    
    def get_contact_info(self, uid):
        return self.account_info['normal_member'].get(uid)


    def get_group_member_info(self, uid):
        return self.account_info['group_member'].get(uid)

    def get_contact_name(self, uid):
        info = self.get_contact_info(uid)
        if info is None:
            return None
        info = info['info']
        name = {}
        if 'RemarkName' in info and info['RemarkName']:
            name['remark_name'] = info['RemarkName']
        if 'NickName' in info and info['NickName']:
            name['nickname'] = info['NickName']
        if 'DisplayName' in info and info['DisplayName']:
            name['display_name'] = info['DisplayName']
        if len(name) == 0:
            return None
        else:
            return name
    
    def handle_msg_all(self, msg):
        """
        处理所有消息，请子类化后覆盖此函数
        msg:
            msg_id  ->  消息id
            msg_type_id  ->  消息类型id
            user  ->  发送消息的账号id
            content  ->  消息内容
        :param msg: 收到的消息
        """
        pass
    
    @staticmethod
    def get_contact_prefer_name(name):
        if name is None:
            return None
        if 'remark_name' in name:
            return name['remark_name']
        if 'nickname' in name:
            return name['nickname']
        if 'display_name' in name:
            return name['display_name']
        return None
    
    @staticmethod
    def get_group_member_prefer_name(name):
        if name is None:
            return None
        if 'remark_name' in name:
            return name['remark_name']
        if 'display_name' in name:
            return name['display_name']
        if 'nickname' in name:
            return name['nickname']
        return None
    
    def extract_msg_content(self, msg_type_id, msg):
        print('..', sys._getframe().f_code.co_name)
        """
        content_type_id:
            0 -> Text
            1 -> Location
            3 -> Image
            4 -> Voice
            5 -> Recommend
            6 -> Animation
            7 -> Share
            8 -> Video
            9 -> VideoCall
            10 -> Redraw
            11 -> Empty
            99 -> Unknown
        :param msg_type_id: 消息类型id
        :param msg: 消息结构体
        :return: 解析的消息
        """
        mtype = msg['MsgType']
        content = html.unescape(msg['Content'])
        msg_id = msg['MsgId']
        print(mtype, content, msg_id)

        msg_content = {}
        msg_content['is_entergroup'] = 0
        msg_content['is_hongbao'] = 0
        if msg_type_id == 0:
            return {'type': 11, 'data': ''}
        elif msg_type_id == 2:  # File Helper
            return {'type': 0, 'data': content.replace('<br/>', '\n')}
        elif msg_type_id == 3:  # 群聊
            sp = content.find('<br/>')
            uid = content[:sp]
            content = content[sp:]
            content = content.replace('<br/>', '')
            uid = uid[:-1]
            name = self.get_contact_prefer_name(self.get_contact_name(uid))
            if not name:
                name = self.get_group_member_prefer_name(self.get_group_member_name(msg['FromUserName'], uid))
            if not name:
                name = 'unknown'
            msg_content['user'] = {'id': uid, 'name': name}
        else:  # Self, Contact, Special, Public, Unknown
            pass

        msg_prefix = (msg_content['user']['name'] + ':') if 'user' in msg_content else ''
        

        if mtype == 1:
            msg_content['data'] = content
            pass
        elif mtype == 3:
            pass
        elif mtype == 34:
            pass
        elif mtype == 37:
            msg_content['type'] = 37
            msg_content['data'] = msg['RecommendInfo']
            
        elif mtype == 42:
            pass
        elif mtype == 47:
            pass
        elif mtype == 49:
            pass

        elif mtype == 62:
            pass
        elif mtype == 53:
            pass
        elif mtype == 10002:
            pass
        elif mtype == 10000:  # unknown, maybe red packet, or group invite
            pass
        elif mtype == 43:
            pass
        return msg_content
    
    
    def handle_msg(self, r):
        print('..', sys._getframe().f_code.co_name)
        """
        处理原始微信消息的内部函数
        msg_type_id:
            0 -> Init
            1 -> Self
            2 -> FileHelper
            3 -> Group
            4 -> Contact
            5 -> Public
            6 -> Special
            99 -> Unknown
        :param r: 原始微信消息
        """
        for msg in r['AddMsgList']:
            user = {'id': msg['FromUserName'], 'name': 'unknown'}
            if msg['MsgType'] == 51 and msg['StatusNotifyCode'] == 4:  # init message
                msg_type_id = 0
                user['name'] = 'system'
                #会获取所有联系人的username 和 wxid，但是会收到3次这个消息，只取第一次
                if self.is_big_contact and len(self.full_user_name_list) == 0:
                    self.full_user_name_list = msg['StatusNotifyUserName'].split(",")
                    self.wxid_list = re.search(r"username&gt;(.*?)&lt;/username", msg["Content"]).group(1).split(",")
                    with open(os.path.join(self.temp_pwd,'UserName.txt'), 'w') as f:
                        f.write(msg['StatusNotifyUserName'])
                    with open(os.path.join(self.temp_pwd,'wxid.txt'), 'w') as f:
                        f.write(json.dumps(self.wxid_list))
                    print("[INFO] Contact list is too big. Now start to fetch member list .")
                    self.get_big_contact()

            elif msg['MsgType'] == 37:  # friend request
                msg_type_id = 37
                pass
                # content = msg['Content']
                # username = content[content.index('fromusername='): content.index('encryptusername')]
                # username = username[username.index('"') + 1: username.rindex('"')]
                # print u'[Friend Request]'
                # print u'       Nickname：' + msg['RecommendInfo']['NickName']
                # print u'       附加消息：'+msg['RecommendInfo']['Content']
                # # print u'Ticket：'+msg['RecommendInfo']['Ticket'] # Ticket添加好友时要用
                # print u'       微信号：'+username #未设置微信号的 腾讯会自动生成一段微信ID 但是无法通过搜索 搜索到此人
            elif msg['FromUserName'] == self.my_account['UserName']:  # Self
                msg_type_id = 1
                user['name'] = 'self'
            elif msg['ToUserName'] == 'filehelper':  # File Helper
                msg_type_id = 2
                user['name'] = 'file_helper'
            elif msg['FromUserName'][:2] == '@@':  # Group
                msg_type_id = 3
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            elif self.is_contact(msg['FromUserName']):  # Contact
                msg_type_id = 4
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            elif self.is_public(msg['FromUserName']):  # Public
                msg_type_id = 5
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            elif self.is_special(msg['FromUserName']):  # Special
                msg_type_id = 6
                user['name'] = self.get_contact_prefer_name(self.get_contact_name(user['id']))
            else:
                msg_type_id = 99
                user['name'] = 'unknown'
            if not user['name']:
                user['name'] = 'unknown'
            user['name'] = html.unescape(user['name'])
            

            if self.DEBUG and msg_type_id != 0:
                print(u'[MSG] %s:' % user['name'])
            content = self.extract_msg_content(msg_type_id, msg)
            message = {'msg_type_id': msg_type_id,
                       'msg_id': msg['MsgId'],
                       'content': content,
                       'to_user_id': msg['ToUserName'],
                       'user': user}
            self.handle_msg_all(message)
            
    def is_contact(self, uid):
        for account in self.contact_list:
            if uid == account['UserName']:
                return True
        return False
    
    def get_user_id(self, name):
        if name == '':
            return None
#        name = self.to_unicode(name)
        for contact in self.contact_list:
            if 'RemarkName' in contact and contact['RemarkName'] == name:
                return contact['UserName']
            elif 'NickName' in contact and contact['NickName'] == name:
                return contact['UserName']
            elif 'DisplayName' in contact and contact['DisplayName'] == name:
                return contact['UserName']
        for group in self.group_list:
            if 'RemarkName' in group and group['RemarkName'] == name:
                return group['UserName']
            if 'NickName' in group and group['NickName'] == name:
                return group['UserName']
            if 'DisplayName' in group and group['DisplayName'] == name:
                return group['UserName']

        return ''
        
    def apply_useradd_requests(self,RecommendInfo):
        url = self.base_uri + '/webwxverifyuser?r='+str(int(time.time()))+'&lang=zh_CN'
        params = {
            "BaseRequest": self.base_request,
            "Opcode": 3,
            "VerifyUserListSize": 1,
            "VerifyUserList": [
                {
                    "Value": RecommendInfo['UserName'],
                    "VerifyUserTicket": RecommendInfo['Ticket']             }
            ],
            "VerifyContent": "",
            "SceneListCount": 1,
            "SceneList": [
                33
            ],
            "skey": self.skey
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        print(dic)
        return dic['BaseResponse']['Ret'] == 0


            
    def send_msg_by_uid(self, word, dst='filehelper'):
        url = self.base_uri + '/webwxsendmsg?pass_ticket=%s' % self.pass_ticket
        msg_id = str(int(time.time() * 1000)) + str(random.random())[:5].replace('.', '')
#        word = self.to_unicode(word)
        params = {
            'BaseRequest': self.base_request,
            'Msg': {
                "Type": 1,
                "Content": word,
                "FromUserName": self.my_account['UserName'],
                "ToUserName": dst,
                "LocalID": msg_id,
                "ClientMsgId": msg_id
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        data = json.dumps(params, ensure_ascii=False).encode('utf8')
        try:
            r = self.session.post(url, data=data, headers=headers)
        except (ConnectionError, ReadTimeout):
            return False
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0
        
    def schedule(self):
        """
        做任务型事情的函数，如果需要，可以在子类中覆盖此函数
        此函数在处理消息的间隙被调用，请不要长时间阻塞此函数
        """
        print('father')
        self.send_msg_by_uid('hello world')
        time.sleep(2)
        pass

#wx = Wechat()
#wx.run()


