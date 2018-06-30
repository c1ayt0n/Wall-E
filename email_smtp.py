# -*- coding: utf-8 -*-
"""
Created on Sat Nov 25 11:34:25 2017

@author: Administrator
"""


import smtplib  
from email.mime.text import MIMEText



SMTPServer = 'smtp.qq.com'
#sender = '1066528303@qq.com'
passwd = 'xvtvshbjymfkbccc'
sslport = 465




def SendEmail(sender, receiver, subject, text):
    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver
    
    smtp = smtplib.SMTP_SSL(SMTPServer, sslport)
    smtp.login(sender, passwd)
    smtp.sendmail(sender, receiver, msg.as_string())
    smtp.close()

if __name__ == "__main__":
    SendEmail('1066528303@qq.com', 'cxb3713@163.com', 'Python Test', 'Test success!')


print('Send email ok')




