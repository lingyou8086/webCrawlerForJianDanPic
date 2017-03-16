#!/usr/bin/env python
# _*_ coding: utf-8 _*_
from bs4 import BeautifulSoup
import os
import urllib.request
import urllib.error
import time
import imghdr
import threading
import queue
import random
# import sys
# reload(sys)
# sys.setdefaultencoding('utf-8')
import http.client

http.client.HTTPConnection._http_vsn = 10
http.client.HTTPConnection._http_vsn_str = 'HTTP/1.0'


__author__ = 'lingyou'

'''
版本：2.0
更新内容：图片下载改成多线程方式，提高下载速度
          改变图片命名规则，变为
          下载进度介绍 （总共图片数目 当前下载了图片数目 ）
          将记录历史下载错误的数组errorUrl 改为 set 格式



思路：
1.读取本地文件  pageUrl.txt  imgUrl.txt errorUrl.txt  到数组  pageUrl[]  imgurl_old[] errorUrl[] 记录此时 imgurl[] 长度
2.进入爬取流程  
    爬取页面URL  判断是否在pageUrl[] 中已存在  如果不存在就加入数组
    爬取图片URL  判断是否在 imgurl[] 中已存在  如果不存在就加入数组
3.进入下载流程
    读取imgurl[] 下载图片
    如果下载失败则将URL存入 errorUrl[]
4.进入重试流程
    读取 errorUrl[] 重新下载失败的URL
        如果下载成功 则将URL从中去除
        最后判断该数组是否为空
            如果不为空 则将内容追加到 errorUrl.txt

文件：pageUrl.txt  imgUrl.txt errorUrl.txt
数组：pageUrl_old[]  imgurl_old[] errorUrl[]

'''


class CrawlerForJDan(object):
    def __init__(self, root_url, proNum):
        self.que = queue.Queue()
        self.proNum = proNum
        self.headers = {
                'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
        # 页面url
        self.pageUrl = []
        # 图片URL
        self.imgUrl = []
        # 下载错误页面
        self.errorUrl = set()
        # 历史图片数量
        self.imgNum = 0
        # 初始化数组 载入历史下载数据
        self.initArray()
        # 爬取开关
        self.switch = True
        self.numTo2OffSwitch = 0
        self.root_url = root_url
        path = os.path.abspath(".")
        self.picpath = os.path.join(path, "Lpic")
        if not os.path.exists(self.picpath):
            os.mkdir(self.picpath)

        # 初始化数组 载入历史下载数据
    def initArray(self):
    
        path = os.path.abspath(".")
        path_pageUrl = os.path.join(path, "pageUrl.txt")
        path_imgUrl = os.path.join(path, "imgUrl.txt")
        path_errorUrl = os.path.join(path, "errorUrl.txt")
        
        # 判断文件是否存在 不存在则创建文件
        self.checkFileAndCreat(path_pageUrl)
        self.checkFileAndCreat(path_imgUrl)
        self.checkFileAndCreat(path_errorUrl)
        
        print("初始化数组 载入历史下载数据......")
        print("载入历史页面URL......\n")
        with open(path_pageUrl, 'r') as f:
            for line in f.readlines():
                self.pageUrl.append(line.strip())
        print("载入历史页面URL成功")
        print("已爬取页面URL数量：",len(self. pageUrl))
        print("\n载入历史图片URL......")
        with open(path_imgUrl, 'r') as f:
            for line in f.readlines():
                self.imgUrl.append(line.strip())
        self.imgNum = len(self.imgUrl)
        print("载入历史图片URL成功")
        print("已爬取图片URL数目：", self.imgNum)
        print("\n载入历史下载失败URL......")
        with open(path_errorUrl, 'r') as f:
            for line in f.readlines():
                self.errorUrl.add(line.strip())
        print("载入历史下载失败URL成功")
        print("历史下载失败URL数量：", len(self.errorUrl))
    # 检查文件是否存在，如果不存在就创建  用于检查历史URL文件检查
    def checkFileAndCreat(self, path):
        if not os.path.exists(path):
            with open(path, 'a') as f:
                pass

    # 获取页面URL、图片URL
    def getUrls(self, pageUrl):
        print("\n\n开始爬取图片URL\n\n")
        if pageUrl is None:
            print("URL为空")
            return None
        response = urllib.request.urlopen(pageUrl)
        if response.getcode() != 200:
            print("获取页面出错，错误代码：", response.getcode())
            return None
        content = response.read()
        self.parserPage(content, pageUrl)

    def parserPage(self, content, pageUrl):
        links = []
        next_page = ""
        soup = BeautifulSoup(content, 'html.parser', from_encoding='utf-8')
        # 下一页url
        page = soup.find('a', class_='previous-comment-page')
        if page:
            next_page = page['href']
            print("\n\n本页地址：", pageUrl)
            # 图片的URL
            img_links = soup.find_all('a', class_="view_img_link")
            print("\n\n本页图片数量：", len(img_links))
            print()
            for link in img_links:
                new_link = link['href']
                # 截取URL
                new_link = new_link[2:]
                # 拼接URL
                new_link = "http://" + new_link
                links.append(new_link)
                # 增加新的URL信息
            if next_page not in self.pageUrl:
                self.pageUrl.append(next_page)
            else:
                # 如果页面URL在历史页面URL中出现过，则进行计数累加
                self.numTo2OffSwitch += 1
            if self.numTo2OffSwitch == 2:
                # 如果计数累加到2 则关闭爬取循环
                self.switch = False
                return None
            for link in links:
                if link not in self.imgUrl:
                    self.imgUrl.append(link)
            self.root_url = next_page
        else:
            # 当到达最后一页时 停止循环
            # 本页图片的URL
            img_links = soup.find_all('a', class_="view_img_link")
            print("\n\n本页图片数量：", len(img_links))
            print()
            for link in img_links:
                new_link = link['href']
                # 截取URL
                new_link = new_link[2:]
                # 拼接URL
                new_link = "http://" + new_link
                links.append(new_link)
                # 增加新的URL信息
            for link in links:
                if link not in self.imgUrl:
                    self.imgUrl.append(link)
            self.switch = False
            print("\n\n到达最后一页，图片URL爬取完毕\n\n")
            return None

    def saveurl2file(self):
        print("开始存储爬取到的URL......\n")
        path = os.path.abspath(".")
        path_pageUrl = os.path.join(path, "pageUrl.txt")
        path_imgUrl = os.path.join(path, "imgUrl.txt")
        # path_errorUrl = os.path.join(path, "errorUrl.txt")
        self.save(path_pageUrl,self.pageUrl)
        self.save(path_imgUrl, self.imgUrl)
        # self.save(path_errorUrl, self.errorUrl)
        print("存储完成......")
    def save(self, path, urls):
        with open(path, 'w') as f:
            for url in urls:
                f.write(url)
                f.write('\n')
    # 下载图片
    def downLoadImage(self):
        print("\n\n开始下载图片......\n\n")
        list_url = self.imgUrl[self.imgNum:]
        if len(list_url) > 0:
            for url in list_url:
                self.que.put(url)
            for i in range(self.proNum):
                # print(self.proNum)
                t = threading.Thread(target=CrawlerForJDan.worker, args=(self,))
                t.daemon = True
                t.start()
            self.que.join()
    def worker(self):
        while True:
            item = self.que.get()
            self.taskInfo(item)
            self.que.task_done()
    def taskInfo(self, url):
        if url:
            content = ''
            try:
                req = urllib.request.Request(url=url, headers=self.headers)
                content = urllib.request.urlopen(req).read()
            except urllib.error.HTTPError as e:
                print(e.code)
                try:
                    content = urllib.request.urlopen(url).read()
                except urllib.error.HTTPError as e:
                    # print e.code
                    # print url
                    print(url+"下载失败，存入下载错误记录")
                    self.errorUrl.add(url)
            if not content == '':
                time.sleep(0.1)
                imgtype = imghdr.what('', h=content)
                if not imgtype:
                    imgtype = 'jpg'
                time_now = int(time.time())
                time_local = time.localtime(time_now)
                dt = time.strftime("%Y%m%d%H%M%S", time_local)
                current_pro = threading.current_thread().getName()
                random_num = random.random() * 10
                pre_name = dt+current_pro+str(random_num)
                name = "%s.%s" % (pre_name, imgtype)
                imgPath = os.path.join(self.picpath, name)
                with open(imgPath, 'wb') as f:
                    f.write(content)
                    print(name)
                    print(url, u"---下载成功\n")
                    print("队列中还有  %d  张待下载" % self.que.qsize())
    # 下载历史下载错误列表中的图片
    def downLoadImageFromErrorUrl(self):
        if len(self.errorUrl) > 0:
            print("\n\n开始下载历史下载错误的图片......\n\n")
            if self.que.qsize() > 0:
                self.que = None
                self.que = queue.Queue()
            for i in self.errorUrl:
                self.que.put(i)
            for i in range(self.proNum):
                t = threading.Thread(target=CrawlerForJDan.errorWorker, args=(self,))
                t.daemon = True
                t.start()
            self.que.join()
            print("下载结束")
            # 存储下载失败的URL到文件
            path = os.path.abspath(".")
            path_errorUrl = os.path.join(path, "errorUrl.txt")
            self.save(path_errorUrl, self.errorUrl)
        else:
            print("\n\n历史下载失败列表为空\n\n")
    def errorWorker(self):
        while True:
            item = self.que.get()
            self.errorTask(item)
            self.que.task_done()
    def errorTask(self, url):
        if url:
            content = ''
            try:
                req = urllib.request.Request(url=url, headers=self.headers)
                content = urllib.request.urlopen(req).read()
            except urllib.error.HTTPError as e:
                print(e.code)
                print(url+"再次下载失败")
            if not content == '':
                time.sleep(0.1)
                imgtype = imghdr.what('', h=content)
                if not imgtype:
                    imgtype = 'jpg'
                time_now = int(time.time())
                time_local = time.localtime(time_now)
                dt = time.strftime("%Y%m%d%H%M%S", time_local)
                current_pro = threading.current_thread().getName()
                random_num = random.random() * 10
                pre_name = dt + current_pro + str(random_num)
                name = "%s.%s" % (pre_name, imgtype)
                imgPath = os.path.join(self.picpath, name)
                with open(imgPath, 'wb') as f:
                    f.write(content)
                    print(url, u"---下载成功\n")
                    # 将下载成功的URL从失败列表中移除
                    self.errorUrl.discard(url)
                    print("历史下载错误队列中还有  %d  张待下载" % self.que.qsize())
    def main(self):
        while self.switch:
            self.getUrls(self.root_url)
        self.saveurl2file()
        self.downLoadImage()
        self.downLoadImageFromErrorUrl()

if __name__ == "__main__":

    root_url = ""
    root_url1 = "http://jandan.net/ooxx"
    root_url2 = "http://jandan.net/ooxx/page-20#comments"
    sel = input("全量下载按 1  ------- 试用一下按 2 \n")
    if sel == "1":
        root_url = root_url1
    else:
        root_url = root_url2
    print()
    proNum = 0
    while True:
        try:
            proNum = int(input("下载图片的进程数："))
        except ValueError as e:
            print("请输入一个合适的数字\n")
        if proNum > 0:
            break
    crawl = CrawlerForJDan(root_url, proNum)
    crawl.main()
