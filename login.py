# coding=utf-8
import pandas as pd
import urllib
import codecs
import requests
from PIL import Image
from sklearn.externals import joblib
from bs4 import BeautifulSoup
import copy
import time
import numpy as np
import re
import os
import base64
from urllib import parse
import urllib.request
from predict_func import verify



class Spider:
	def __init__(self, url):
		self.__uid = ''
		self.__real_base_url = ''
		self.__base_url = url
		self.__name = ''
		self.__base_data = {
			'btn_zcj':'%C0%FA%C4%EA%B3%C9%BC%A8',
			'__EVENTTARGET': '',
			'__EVENTARGUMENT': '',
			'__VIEWSTATE': '',
			'ddl_kcxz': '',
			'ddl_ywyl': '',
			'ddl_kcgs': '',
			'ddl_xqbs': '',
			'ddl_sksj': '',
			'TextBox1': '',
			'dpkcmcGrid:txtChoosePage': '1',
			'dpkcmcGrid:txtPageSize': '200',
		}
		self.__headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.62 Safari/537.36',
		}
		self.session = requests.Session()
		self.__now_lessons_number = 0

	def verify(self, url, model, save=False):
		"""
		:param url: 验证码地址
		:param model: 处理该验证码的模型
		:param save: 是否保存临时文件到cache
		:return:
		"""
		if save:
			pic_file = 'cache/captcha.png'
			urllib.request.urlretrieve(url, pic_file)
			image = Image.open(pic_file).convert("L")
		else:
			r = self.session.get(url)
			with open('cache/captcha.png', 'wb') as f:
				f.write(r.content)
			image = Image.open('cache/captcha.png')
		x_size, y_size = image.size
		y_size -= 5
		piece = (x_size-24) / 8
		centers = [4+piece*(2*i+1) for i in range(4)]
		data = np.empty((4, 21 * 16), dtype="float32")
		for i, center in enumerate(centers):
			single_pic = image.crop((center-(piece+2), 1, center+(piece+2), y_size))
			data[i, :] = np.asarray(single_pic, dtype="float32").flatten() / 255.0
			if save:
				single_pic.save('cache/captcha-%s.png' % i)
		clf = joblib.load(model)
		answers = clf.predict(data)
		answers = map(chr, map(lambda x: x + 48 if x <= 9 else x + 87 if x <= 23 else x + 88, map(int, answers)))
		return answers

	def __set_real_url(self):
		request = self.session.get(self.__base_url, headers=self.__headers)
		real_url = request.url
		if real_url != 'http://218.75.197.123:83/' and real_url != 'http://218.75.197.123:83/index.apsx':   # 湖南工业大学
			self.__real_base_url = real_url[:len(real_url) - len('default2.aspx')]
		else:
			if real_url.find('index') > 0:
				self.__real_base_url = real_url[:len(real_url) - len('index.aspx')]
			else:
				self.__real_base_url = real_url
		return request

	def __get_code(self):

		model = 'model/SVC_Model_zf.pkl'
		if self.__real_base_url != 'http://218.75.197.123:83/':
			request = self.session.get(self.__real_base_url + 'CheckCode.aspx', headers=self.__headers)
		else:
			request = self.session.get(self.__real_base_url + 'CheckCode.aspx?', headers=self.__headers)
		with open('code.jpg', 'wb')as f:
			f.write(request.content)
		image = Image.open('code.jpg')
		x_size, y_size = image.size
		y_size -= 5
		piece = (x_size-24) / 8
		centers = [4+piece*(2*i+1) for i in range(4)]
		data = np.empty((4, 21 * 16), dtype="float32")
		for i, center in enumerate(centers):
			single_pic = image.crop((center-(piece+2), 1, center+(piece+2), y_size))
			data[i, :] = np.asarray(single_pic, dtype="float32").flatten() / 255.0
			# if save:
			single_pic.save('cache/captcha-%s.png' % i)
		clf = joblib.load(model)
		answers = clf.predict(data)
		answers = map(chr, map(lambda x: x + 48 if x <= 9 else x + 87 if x <= 23 else x + 88, map(int, answers)))
		captcha_list = list(answers)
		captcha_code = ''.join(captcha_list)
		print(captcha_code)

		# im.show()
		# print('Please input the code:')
		# code = input()
		return captcha_code

	def __get_login_data(self, uid, password):
		self.__uid = uid
		request = self.__set_real_url()
		soup = BeautifulSoup(request.text, 'lxml')
		form_tag = soup.find('input')
		__VIEWSTATE = form_tag['value']
		code = self.__get_code()
		data = {
			'__VIEWSTATE': __VIEWSTATE,
			'txtUserName': self.__uid,
			'TextBox2': password,
			'txtSecretCode': code,
			'RadioButtonList1': '学生'.encode('gb2312'),
			'Button1': '',
			'lbLanguage': '',
			'hidPdrs': '',
			'hidsc': '',
		}
		return data

	def login(self, uid, password):
		while True:
			data = self.__get_login_data(uid, password)
			if self.__real_base_url != 'http://218.75.197.123:83/':
				request = self.session.post(self.__real_base_url + 'default2.aspx', headers=self.__headers, data=data)
			else:
				request = self.session.post(self.__real_base_url + 'index.aspx', headers=self.__headers, data=data)
			soup = BeautifulSoup(request.text, 'lxml')
			if request.status_code != requests.codes.ok:
				print('4XX or 5XX Error,try to login again')
				time.sleep(0.5)
				continue
			if request.text.find('验证码不正确') > -1:
				print('Code error,please input again')
				continue
			if request.text.find('密码错误') > -1:
				print('Password may be error')
				return False
			if request.text.find('用户名不存在') > -1:
				print('Uid may be error')
				return False
			try:
				name_tag = soup.find(id='xhxm')
				self.__name = name_tag.string[:len(name_tag.string) - 2]
				print('欢迎' + self.__name)
				return self.__name
			except Exception as e:
				print(e)
				print('Unknown Error,try to login again.')
				time.sleep(0.5)
				continue

	def __set__VIEWSTATE(self, soup):
		__VIEWSTATE_tag = soup.find('input', attrs={'name': '__VIEWSTATE'})
		return __VIEWSTATE_tag['value']
		self.__base_data['__VIEWSTATE'] = __VIEWSTATE_tag['value']


	def get_page(self,name):
		while True:
			data = {
			'xh': self.__uid,
			'xm': parse.quote(name.encode('gb2312')),
			'gnmkdm': 'N121605',
			}
			self.__headers['Referer'] = self.__real_base_url + 'xscjcx.aspx?xh=' + self.__uid +'&xm=' + parse.quote(name.encode('gb2312')) + '&gnmkdm=N121605'
			try:
				request = self.session.post(self.__real_base_url + 'xscjcx.aspx?xh=' + self.__uid +'&xm=' + parse.quote(name.encode('gb2312')) + '&gnmkdm=N121605', params=data, headers=self.__headers)
				get_source = self.session.get(self.__real_base_url + 'xscjcx.aspx?xh=' + self.__uid +'&xm=' + parse.quote(name.encode('gb2312')) + '&gnmkdm=N121605',headers=self.__headers)
			except Exception as e:
				print(e)
				print('Unknown Error,try to login again.')
				time.sleep(0.5)
				continue
			get_source =  get_source.content.decode('gb2312')
			soup=BeautifulSoup(get_source,'lxml')
			info = {
					'__EVENTTARGET': '',
					'__EVENTARGUMENT': '',
					'__VIEWSTATE':self.__set__VIEWSTATE(soup),
					'hidLanguage':'',
					'ddlXN':'',
					'ddlXQ':'',
					'ddl_kcxz':'',
					'btn_zcj': '历年成绩'.encode('gb2312')
			}
			try:
				get_score = self.session.post(self.__real_base_url + 'xscjcx.aspx?xh=' + self.__uid +'&xm=' + parse.quote(name.encode('gb2312')) + '&gnmkdm=N121605', headers=self.__headers,data = info)
			except Exception as e:
				print(e)
				print('Unknown Error,try to login again.')
				time.sleep(0.5)
				continue
			get_score =  get_score.content.decode('gb2312')
			soup2 = BeautifulSoup(get_score,'lxml')
			base64 = self.__set__VIEWSTATE(soup2)
		return base64

class Parse:
	def __init__(self,data):
		self.data = data

	def output_html(self,data):
		fout = codecs.open('output.html', 'w', encoding='utf-8')
		fout.write("<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" />")
		fout.write("<html>")
		fout.write("<body>")

		fout.write("<table border='1' align='center' cellpadding='16' cellspacing='1' bgcolor='#BBFFFF'>")
		i = 1
		for ele in data:
			fout.write("<tr>")
			if i==1:
				fout.write("<td font-family=\"Microsoft YaHei\" align='center'>课程</td>")
				fout.write("<td font-family=\"Microsoft YaHei\" align='center'>平时成绩</td>")
				fout.write("<td font-family=\"Microsoft YaHei\" align='center'>考试成绩</td>")
				fout.write("<td font-family=\"Microsoft YaHei\" align='center'>最终成绩</td>")
				fout.write("<tr>")
			fout.write("<td align='center' font-family=\"Microsoft YaHei\" >%s</td>" % (ele['课程']))
			fout.write("<td align='center' font-family=\"Microsoft YaHei\" >%s</td>" % (ele['平时成绩']))
			fout.write("<td align='center' font-family=\"Microsoft YaHei\" >%s</td>" % (ele['考试成绩']))
			fout.write("<td align='center' font-family=\"Microsoft YaHei\" >%s</td>" % (ele['最终成绩']))
			i = i + 1
		fout.write("</table>")
		fout.write("</body>")
		fout.write("</html>")
		fout.close()

	def get_grades(self):
		p1 = re.compile(r';l<(.*?);>>;>;;>;', re.S)
		data1 = re.findall(p1, self.data)
		data2 = [i for i in data1 if ((len(i)<=30)&(len(i)>=2))]  #删除过长元素
		pattern1 = re.compile(r'[o<](.*?)[>]')
		pattern2 = re.compile(r'&(.*?)\\')
		pattern3 = re.compile(r'\\(.*?)e')
		data3 =[unit for unit in data2 if ((pattern1.match(unit) == None) and (pattern2.match(unit) == None) and (pattern3.match(unit) == None))]
		data4 = data3[8:-2]
		while "理论课" in data4:
			data4.remove("理论课")

		for i in range(len(data4)):

			if ((data4[i]=="体育军事教学部") or (data4[i]=="教务处") or(data4[i] == "大学外语教学部")):
				data4[i] = data4[i-1]

			data4[i] = data4[i].lstrip()
			if (i+2<=len(data4)):
				if ((data4[i]=="素质教育选修课") & (data4[i+1]=="素质教育选修课")):
					data4.remove(data4[i])
			# print(data4[i] + '\t\t',end='')

			if i+1==len(data4):
				break
			# if data4[i+1][0]>='A' and data4[i+1][0] <= 'Z' and data4[i+1][2].isdigit():
				# print("\n")
		pattern4 = re.compile(r'\d[.]\d')
		data5 = []
		for i in range(len(data4)):
			if i+4==len(data4):
				break
			if data4[i][0]>='A' and data4[i][0] <= 'Z' and data4[i][2].isdigit():
				data5.append(data4[i+1])
			if ((pattern4.match(data4[i]) != None) & (pattern4.match(data4[i+1]) != None )):
				data5.append(data4[i+2])
				data5.append(data4[i+3])
				data5.append(data4[i+4])
				# print(data4[i+2],data4[i+3],data4[i+4],"\n")
		data = []
		form = {}
		for i in range(1,int(len(data5)/4)+1):
			data.append({'课程':data5[(i-1)*4],'平时成绩':data5[(i-1)*4+1],'考试成绩':data5[(i-1)*4+2],'最终成绩':data5[(i-1)*4+3]})

		self.output_html(data)



if __name__ == '__main__':
	url = 'http://' + 'jw3.ahu.cn/default2.aspx'
	spider = Spider(url)
	uid = ''  #学号
	password = '' #密码
	name = spider.login(uid, password)
	encrypted = spider.get_page(name)
	encodestr = base64.b64decode(str.encode(encrypted))
	decoded = encodestr.decode('utf-8','ignore')
	parse = Parse(decoded)
	parse.get_grades()

	#os.system("pause")