import re
import time
from base64 import b64encode

import pyDes
import binascii
import requests
from Crypto.Cipher import AES
from lxml import etree
from bs4 import BeautifulSoup
from pymysql.converters import escape_string
import pymysql

pysql = "127.0.0.1"
mysql_port = 3306
mysql_user = ''
mysql_password = ""
mysql_database = ""


def clear_string(source_list, string):
    """
        清除列表中存在的特定字符串
        :param source_list: 要处理的列表
        :param string :要清除的字符串
    """
    dist_list = []
    for item in source_list:
        if string in item:
            # print()
            dist_list.append(re.sub(string, '', item))
        else:
            dist_list.append(item)
    return dist_list


def join_my_answer(type, my_answer):
    '''
    由于判断题的答案在列表中是分开的，所以要将列表中判断题的答案连接在一起
    :param type: 题目类型
    :param my_answer: 答案
    :return: 拼接好的答案
    '''
    try:
        index = type.index('判断题')
        answer = my_answer[0:index]
        for i in range(index, len(my_answer), 2):
            a = ''.join(my_answer[i:i + 2])
            answer.append(a)
        return answer
    except ValueError:
        # 没有的判断题
        print('没有判断题')
        return my_answer


def deal_answer(answer):
    '''
    对答案进行处理，将其替换成'√', '×'
    :param answer:
    :return:
    '''
    dist_answer = []
    for judge in answer:
        if judge == 'fr dui':
            dist_answer.append('√')
        else:
            dist_answer.append('×')
    return dist_answer


def comb_question(type, question, items, select_items, my_answer, judge_answer):
    """
    将问题的所有项进行组合，
    :param type: 题目类型
    :param question: 题目
    :param items: 选项（选择题）
    :param select_items: 选择内容
    :param my_answer: 我的答案
    :param judge_answer: 对我的答案的判断
    :return: 组合好的问题
    """
    # 先将 题目类型、题目、我的答案、答案判断 组合成一个元组，放在列表里面
    comb_ok_question = list(zip(type, question, my_answer, judge_answer))
    # 然后把选择题的选项组合好
    i = 0
    # 由于这里的选择题只有四个选项
    for index in range(0, len(items), 4):
        options = tuple(zip(items[index:index + 4], select_items[index:index + 4]))
        # options = tuple(zip(select_items[index:index + 4]))
        comb_ok_question[i] += tuple(options)
        i += 1
    return comb_ok_question


def pkcs7padding(text):
    """
    明文使用PKCS7填充
    """
    bs = 16
    length = len(text)
    bytes_length = len(text.encode('utf-8'))
    padding_size = length if (bytes_length == length) else bytes_length
    padding = bs - padding_size % bs
    padding_text = chr(padding) * padding
    coding = chr(padding)
    return text + padding_text


def encryptByAES(message):
    keyword = "u2oh6Vu^HWe4_AES"
    key = keyword.encode('utf-8')
    iv = keyword.encode('utf-8')

    cipher = AES.new(key, AES.MODE_CBC, iv)
    # 处理明文
    content_padding = pkcs7padding(message)
    # 加密
    encrypt_bytes = cipher.encrypt(content_padding.encode('utf-8'))
    # 重新编码
    result = str(b64encode(encrypt_bytes), encoding='utf-8')
    return result


def encrypt_des(msg, key):
    des_obj = pyDes.des(key, key, pad=None, padmode=pyDes.PAD_PKCS5)
    secret_bytes = des_obj.encrypt(msg, padmode=pyDes.PAD_PKCS5)
    return binascii.b2a_hex(secret_bytes)


def sign_in(username: str, password: str):
    url = "https://passport2.chaoxing.com/fanyalogin"
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Content-Length': '95',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': '',
        'Host': 'passport2.chaoxing.com',
        'Origin': 'https://passport2.chaoxing.com',
        'Referer': 'https://passport2.chaoxing.com/login?fid=&newversion=true&refer=http%3A%2F%2Fi.chaoxing.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/86.0.4240.193 Safari/537.36 Edg/86.0.622.68',
        'X-Requested-With': 'XMLHttpRequest'
    }
    data = "fid=-1&uname={0}&password={1}&refer=http%253A%252F%252Fi.chaoxing.com&t=true&forbidotherlogin=0&validate=&doubleFactorLogin=0&independentId=0".format(
        encryptByAES(str(username)),encryptByAES(str(password)))
    print(data)
    rsp = requests.post(url=url, headers=headers, data=data)
    if rsp.json()['status'] is False:
        print(rsp.json()['msg2'], rsp.status_code)
        exit(0)
    else:
        cookieStr = ''
        for item in rsp.cookies:
            cookieStr = cookieStr + item.name + '=' + item.value + ';'
        # print(cookieStr)  # cookie
        return cookieStr


def get_course(cookie: str):
    course_headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36 Edg/85.0.564.51'
    }
    course_rsp = requests.get(url="http://mooc1-2.chaoxing.com/visit/courses", headers=course_headers)
    if course_rsp.status_code == 200:
        from lxml import etree
        class_HTML = etree.HTML(course_rsp.text)
        print("处理成功，您当前已开启的课程如下：\n")
        i = 0
        global course_dict
        course_dict = {}
        for class_item in class_HTML.xpath("/html/body/div/div[2]/div[3]/ul/li[@class='courseItem curFile']"):
            # courseid=class_item.xpath("./input[@name='courseId']/@value")[0]
            # classid=class_item.xpath("./input[@name='classId']/@value")[0]
            try:
                class_item_name = class_item.xpath("./div[2]/h3/a/@title")[0]
                # 等待开课的课程由于尚未对应链接，所有缺少a标签。
                i += 1
                print(class_item_name)
                course_dict[i] = [class_item_name,
                                  "https://mooc1-2.chaoxing.com{}".format(class_item.xpath("./div[1]/a[1]/@href")[0])]
            except:
                pass
        return course_dict
        # print("———————————————————————————————————")
    else:
        print("error:课程处理失败")


def get_dic(dic_name: str):
    for key, value in course_dict.items():
        if value[0] == dic_name:
            # print(key) # 第几个课程
            link = course_dict[key][1]
            # print(link) # 301 未跳转前url
            return link


def deal_course(url: str):
    global params_vc
    course_302_url = url
    # 跳转前页  https://mooc1-2.chaoxing.com/mycourse/studentcourse?courseId=237188697&clazzid=82975979&cpi=128909989&enc=168b0343361309593dbf4949438c0e33&fromMiddle=1&vc=1
    try:
        params_vc = re.findall(r".*&vc=(.*)&cpi=.*", course_302_url, re.S)[0]
    except:
        params_vc = "undefined"
    user_agent_list = [
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
    ]
    import random
    course_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Cookie': cookie,
        'Host': 'mooc1-2.chaoxing.com',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': random.choice(user_agent_list)
    }
    # 302跳转，requests库默认追踪headers里的location进行跳转，使用allow_redirects=False
    try:
        course_302_rsp = requests.get(url=course_302_url, headers=course_headers, allow_redirects=False)
        new_url = course_302_rsp.headers['Location']
        print(new_url)
        return new_url
    except:
        return 0


def add_misson(url: str):
    global utenc
    course_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'keep-alive',
        'Cookie': cookie,
        'Host': 'mooc1-2.chaoxing.com',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/85.0.4183.102  Safari/537.36 Edg/85.0.564.51'
    }
    course_rsp = requests.get(url=url, headers=course_headers)
    print(course_rsp.status_code)

    try:
        utenc = re.findall(r'.*utEnc="(.*)"', course_rsp.text, re.S)[0]
    except:
        utenc = "undefined"
    print(utenc)
    course_HTML = etree.HTML(course_rsp.text)
    # 为防止账号没有课程或没有班级，需要后期在xpath获取加入try，以防报错
    chapter_mission = []
    print("开始获取课程")
    for course_unit in course_HTML.xpath("/html/body/div[5]/div[1]/div[2]/div[3]/div"):
        print(course_unit.xpath("./h2/span/a/@title")[0])
        for chapter_item in course_unit.xpath("./div"):
            chapter_status = chapter_item.xpath("//h3/a/span[@class='icon']/em/@class")[0]
            if chapter_status == "openlock":  # orange 未完成  openlock 已完成 blank非任务点
                print("已完成----", chapter_item.xpath("./h3/a/span/span[@class='articlename']/@title")[0],
                      "      ",
                      chapter_item.xpath("./h3/a/span[@class='icon']/em/@class")[0])
                chapter_mission.append("https://mooc1-2.chaoxing.com{}".format(
                    chapter_item.xpath(".//h3[@class='clearfix']/a/@href")[0]))  # 直接全部加进去，一个一个看
            elif chapter_status == "orange":
                url = chapter_item.xpath(".//h3[@class='clearfix']/a/@href")[0]
                if url == "javascript:;":
                    print("锁定----", chapter_item.xpath("./h3/a/span/span[@class='articlename']/@title")[0],
                          "      ", )
                else:
                    # chapter_mission.append("https://mooc1-2.chaoxing.com{}".format(url))  # 直接全部加进去，一个一个看
                    print("未完成----", chapter_item.xpath("./h3/a/span/span[@class='articlename']/@title")[0],
                          "      ",
                          chapter_item.xpath(".//h3[@class='clearfix']/a/@href")[0])
            else:
                print("锁定----", chapter_item.xpath("./h3/a/span/span[@class='articlename']/@title")[0],
                      "      ", )

    print("课程读取完成，共有%d个章节已完成" % len(chapter_mission))
    return chapter_mission


def get_tm(tm_get_url):
    global courseId
    course_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Connection': 'close',
        'Cookie': cookie,
        'Host': 'mooc1-2.chaoxing.com',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/85.0.4183.102 Safari/537.36 Edg/85.0.564.51',

    }
    # 302跳转，requests库默认追踪headers里的location进行跳转，使用allow_redirects=False
    time.sleep(1)
    print(tm_get_url)
    tm_url_rsp = requests.get(url=tm_get_url, headers=course_headers, allow_redirects=False)
    tm_url_rsp.close()
    # print(tm_get_url)
    tm_from = re.compile(
        '&cpi=(?P<to_url>.*?)";',
        re.S)
    result = tm_from.findall(tm_url_rsp.text)[0]
    # print(result)
    chapterId = re.findall(r'.*chapterId=(.*)&.*courseId', tm_get_url)[0]
    data_from = re.compile(
        r"\{courseId:'(?P<courseID>.*?)',chapterId:'(?P<chapterId>.*?)',clazzid:'(?P<clazzid>.*?)',cpi:'(?P<cpi>.*?)'},",
        re.S)
    data_result = data_from.findall(tm_url_rsp.text)[0]
    courseId = data_result[0]
    # chapterId = data_result[1]
    clazzid = data_result[2]
    cpi = data_result[3]
    # print(courseId, chapterId, clazzid,cpi)
    for list_num in range(0, 6):
        list_to_url = "https://mooc1-2.chaoxing.com/mooc-ans/knowledge/cards?clazzid=" + clazzid + "&courseid=" + courseId + "&knowledgeid=" + chapterId + "&num=" + str(
            list_num) + "&" + result
        print(list_to_url)
        while True:
            try:
                cards_respose = requests.get(list_to_url, headers=course_headers, allow_redirects=False).text
                break
                # print(cards_respose)  # 答题301前的页面
            except:
                time.sleep(1)

        # try:  # 没有题目的章节在这里会报错
        title = re.findall(r'<title>(.*)</title>', cards_respose, re.S)[0]
        if title == "章节测验":
            print("测试", list_to_url)
            datas = re.findall(r'.*"attachments":\[(.*);.*}catch\(e\)', cards_respose, re.S)[0]
            ktoken = re.findall(r'"ktoken".*?"(.*?)",', datas, re.S)[0]
            try:
                enc = re.findall(r'"enc":"(.*?)","type":"workid"', datas)[0]
            except:
                enc = re.findall(r'"enc":"(.*?)","job":true,"type":"workid"', datas)[0]
            try:
                workId = re.findall(r',"workid":"(.*?)","_jobid"', datas)[0]
            except:
                schoollid = re.findall(r'"schoolid":"(.*?)","module"', datas)[0]
                workId = re.findall(r'"workid":(.*?),"_jobid"', datas)[0]
                workId = schoollid + "-" + workId
            # 有题目
            print(list_to_url + '有题目')

            data = {
                'api': params_vc,
                'workId': workId,
                'jobid': 'work-{}'.format(workId),
                'needRedirect': 'true',
                'knowledgeid': chapterId,
                'ut': 's',
                'clazzId': clazzid,
                'type': '',
                'enc': enc,
                'utenc': utenc,
                'courseid': courseId
            }

            param = 'https://mooc1-2.chaoxing.com/mooc-ans/api/work?api={}&workId={}&jobid={}&needRedirect={}&skipHeader=true&knowledgeid={}&ktoken={}&cpi={}&ut={}&clazzId={}&type={}&enc={}&utenc={}&courseid={}' \
                .format(data['api'], data['workId'], data['jobid'], data['needRedirect'], data['knowledgeid'],
                        ktoken,
                        cpi,
                        data['ut'], data['clazzId'], data['type']
                        , data['enc'], data['utenc'], data['courseid'])
            print(param)
            for_url = deal_course(deal_course(param))
            print(for_url)
            if for_url == 0:
                print(list_to_url + '\r异常返回跳过')
            else:
                print("准备对单个题目处理")
                get_list_tm(for_url)  # 内容
                time.sleep(1)
                # print(param)


def get_list_tm(url):
    global result, true_result
    course_headers = {
        'Cookie': cookie,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/85.0.4183.102 Safari/537.36 Edg/85.0.564.51'
    }
    # 302跳转，requests库默认追踪headers里的location进行跳转，使用allow_redirects=False
    try:
        tm_resp = requests.get(url=url, headers=course_headers).text
    except:
        print("详细请求失败")
        tm_resp = requests.get(url=url, headers=course_headers).text
    page = BeautifulSoup(tm_resp, "html.parser")
    table = page.find_all("div", attrs={"class": "TiMu", "style": "position:relative"})
    if not table:
        table = page.find_all("div", attrs={"class": "TiMu"})
    for div in table:
        # print(div)
        page = BeautifulSoup(str(div), "html.parser")
        div_list = page.find("div", class_="clearfix").get_text()
        p = re.compile(r'【(.*?)】', re.S)
        list_work = re.findall(p, div_list)[0]  # 题目类型
        soup = BeautifulSoup(str(div), 'html.parser')

        # 提取每个选项及其对应的文本内容和图片链接
        da = [
            (
                item.find('i').get_text(strip=True),
                item.find('a').get_text(strip=True)
                if item.find('a').get_text(strip=True)
                else "<img src=\"" + item.find('img')['src'] + '\">'
                if item.find('img')
                else ''
            )
            for item in soup.find_all('li', class_='clearfix')
        ]
        new_da_list = str([item[1] for item in da])

        if list_work == "单选题" or list_work == "多选题":
            # 我的答案
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(str(div), 'html.parser')
            # 找到类名为 "Py_answer" 的 div 元素
            py_answer_div = soup.find('div', class_='Py_answer clearfix')
            # 提取 "我的答案" 文本内容
            true_result = 0
            result = 0
            try:
                my_answer_span = py_answer_div.find('span', string=lambda x: '我的答案' in x)
                my_answer = my_answer_span.get_text(strip=True).split('：')[-1]
            except:
                try:
                    my_answer_span = py_answer_div.find('span', string=lambda x: '正确答案' in x)
                    my_answer = my_answer_span.get_text(strip=True).split('：')[-1]
                except:
                    print("题目未完成")
                    break
            # 匹配 "我的答案" 与选项数组，并输出正确答案
            my_answer = re.findall(r'[A-Z]', my_answer)
            # 根据匹配到的选项在数组中查找对应的答案
            my_answer = '#'.join([answer for option, answer in da if option[:-1] in my_answer])

            tm = re.sub(r'(\t|\n|\s)?', '', div_list)
            tm = re.split('【[\u4e00-\u9fa5]{3}】', tm)[1:][0]  # [1:]表示从第几行开始 [0]表示直接拿
            # 找到类名为 "Py_answer" 的 div 元素，提取我的答案
            try:
                answer_div = soup.find('div', class_='Py_answer')
                is_correct = 'dui' in answer_div.find('i', class_='fr').get('class', [])
                # 判断是否正确，并返回结果
                result = '正确' if is_correct else '错误'
                get_mysql(list_work, tm, my_answer, result, true_result, new_da_list)
            except:
                print("无正确答案")
                print(list_work, tm, da, result, true_result, new_da_list)
                print("=" * 50)
                # get_answer(list_work, tm)

        elif list_work == "判断题":
            new_da_list = str("['正确','错误']")
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(str(div), 'html.parser')

            # 找到类名为 "Zy_TItle" 的 div 元素，提取题目
            tm = re.sub(r'(\t|\n|\s)?', '', div_list)
            tm = re.split('【[\u4e00-\u9fa5]{3}】', tm)[1:][0]  # [1:]表示从第几行开始 [0]表示直接拿

            # 找到类名为 "Py_answer" 的 div 元素，提取我的答案
            try:
                answer_div = soup.find('div', class_='Py_answer')
                my_answer = answer_div.find('i', class_='font14').text.strip()
                is_correct = 'dui' in answer_div.find('i', class_='fr').get('class', [])
                # 判断是否正确，并返回结果
                result = '正确' if is_correct else '错误'
                get_mysql(list_work, tm, my_answer, result, true_result, new_da_list)
            except:
                print("无正确答案")
                print(list_work, tm, da, result, true_result, new_da_list)
                print("=" * 50)
        else:
            print("未知题型", list_work)
            exit(0)


def get_mysql(data_type, tm, da, result, true_result, optionTexts):
    """单选题 从哪一年开始,我国HIV感染者和艾滋病患者数出现了突飞猛进的增长,并逐年上升?()  答案选项  2004 正确 0  题目选项"""
    print(data_type, tm, da, result, true_result, optionTexts)
    # 数据库
    conn = pymysql.connect(host=pysql,
                           port=mysql_port,
                           user=mysql_user,
                           password=mysql_password,
                           database=mysql_database)
    # 使用 cursor() 方法创建一个游标对象 cursor
    cursor = conn.cursor()
    if result == "正确" or true_result == "正确":
        # 打开数据库连接
        # 打开数据库连接
        query = "SELECT * FROM tk where tm= '%s' AND type='%s' AND courseId='%s'AND optionTexts is NULL" % (
            escape_string(tm), data_type, courseId)
        # 执行sql语句
        cursor.execute(query)
        if cursor.rowcount > 0:  # 存在才才更新
            # 数据库
            sql = f"update tk SET da='%s'where tm='%s' and type= '%s' and courseId ='%s' AND optionTexts='%s'" % (
                escape_string(da), escape_string(tm), data_type, courseId, escape_string(optionTexts))
            # print(sql)
            cursor.execute(sql)
            # 判断是否更新成功
            if cursor.rowcount == 0:
                print(
                    f"{'-' * 25}\n数据已存在\n课程ID:{courseId} \n题目类型:{data_type} \n题目:{tm} \n答案:{da}\n{'-' * 25}")
            else:
                print(
                    f"{'-' * 25}\n数据更新成功{'-' * 25}\n课程ID:{courseId} \n题目类型:{data_type} \n题目:{tm} \n答案:{da}\n{'-' * 25}")
            # 提交到数据库
            conn.commit()
        else:
            sql = "SELECT * FROM tk where tm= '%s' AND type='%s' AND courseId='%s' and optionTexts='%s'" % (
                escape_string(tm), data_type, courseId, escape_string(optionTexts))
            # 执行sql语句
            cursor.execute(sql)
            if cursor.rowcount > 0:  # 存在才才更新
                # 数据库
                sql = f"update tk SET da='%s' where tm='%s' and type= '%s' and courseId ='%s' and optionTexts='%s'" % (
                    escape_string(da), escape_string(tm), data_type, courseId, escape_string(optionTexts))
                # print(sql)
                cursor.execute(sql)
                # 判断是否更新成功
                if cursor.rowcount == 0:
                    print(
                        f"{'-' * 25}\n数据已存在\n课程ID:{courseId} \n题目类型:{data_type} \n题目:{tm} \n答案:{da}\n{'-' * 25}")
                else:
                    print(
                        f"{'-' * 25}\n数据更新成功\n{'-' * 25}\n课程ID:{courseId} \n题目类型:{data_type} \n题目:{tm} \n答案:{da}\n{'-' * 25}")
                # 提交到数据库
                conn.commit()
            else:
                sql = "insert into tk(type,tm,da,courseId,optionTexts) values('%s','%s','%s','%s','%s')" % (
                    data_type, escape_string(tm), escape_string(da), courseId, escape_string(optionTexts))
                cursor.execute(sql)
                print(
                    f"{'-' * 25}\n插入数据\n课程ID:{courseId} \n题目类型:{data_type} \n题目:{tm} \n答案:{da}\n{'-' * 25}")
        # 关闭游标和连接
        conn.commit()
        conn.close()
    else:
        print("答案错误")
    print("本页完毕")


def get_answer(list_work, tm):
    headers = {
        'Content-type': 'application/json',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, "
                      "like Gecko) Chrome/105.0.0.0 Safari/537.36",
    }
    while True:
        try:
            resp = requests.get(
                f'https://q.icodef.com/api/v1/q/{tm}?token=', # 这里填token
                headers=headers)
        except requests.exceptions.ConnectTimeout:
            print("请求失败重试")
            time.sleep(3)
            break
        resp.close()
        # print("休息1秒")
        # time.sleep(1)
        print(tm + "\r", resp.json())
        resp.encoding = 'utf-8'
        code = resp.json()['code']
        if code == 0:
            das = resp.json()['data']['correct']
            da = '#'.join(answer['content'] for answer in das)
            # 使用 cursor() 方法创建一个游标对象 cursor
            get_mysql(list_work, tm, da, "正确", "正确", 0)
            break
        elif code == -1:
            print(resp.json())
            print("-" * 50)
            msg = resp.json()['msg']
            print(msg)
            break


if __name__ == '__main__':
    cookie = sign_in("", "")  # 获取cookie 账号 密码
    # get_list_tm(
    #     "https://mooc1-2.chaoxing.com/mooc-ans/work/selectWorkQuestionYiPiYue?courseId=233538292&workId=30477284&workAnswerId=52647217&api=1&knowledgeid=705049090&classId=86455501&oldWorkId=1385-5811&jobid=work-1385-5811&type=&isphone=false&submit=false&enc=c7ba23a551b48ae6dee0e002e9d17663&cpi=265484310&mooc2=0&skipHeader=true")
    # print(course_dict)
    # 获取字典中键的数量
    course_dict = get_course(cookie)  # 字典
    num_keys = len(course_dict)
    # 循环输出1，2，3，...，num_keys
    # list_url = deal_course(get_dic(input("请输入要查询的课程:  ")))
    # tm_url = add_misson(list_url)  # 301 之后页面 获取章节内容
    # if tm_url:
    #     for list_tm_url in tm_url:
    #         # print(i, course_dict[i][0])
    #         get_tm(list_tm_url)  # 解析最终答题url
    # else:
    #     print("课程已结课")
    # list_url = deal_course(get_dic("大学生防艾健康教育"))  # 单独课程
    # tm_url = add_misson(list_url)  # 301 之后页面 获取章节内容

    for i in range(1, num_keys + 1):
        list_url = deal_course(course_dict[i][1])
        # deal_course 302页面
        print(i, course_dict[i][0], list_url)

        # 301页面 详细课程主页 https://mooc1-2.chaoxing.com/mycourse/studentcourse?courseId=237188697&clazzid=82975979&cpi=128909989&enc=168b0343361309593dbf4949438c0e33&fromMiddle=1&vc=1
        tm_url = add_misson(list_url)  # 301 之后页面 获取章节内容
        if tm_url:
            for list_tm_url in tm_url:
                # print(i, course_dict[i][0])
                get_tm(list_tm_url)  # 解析最终答题url
        else:
            print("课程已结课")
