# !/user/bin/env python
# -*- coding:utf-8 -*- 
# time: 2018/10/21--16:21
__author__ = 'Henry'

'''
项目:最简易标准滑块验证码
网址:http://gkcf.jxedu.gov.cn/
'''

import requests, time, re, json, base64, random, execjs
from PIL import Image


def process_captcha():
    '''处理滑动验证码'''
    url = 'http://171.34.169.85/api/getcode?callback=jQuery1110066666666666666666_{}&spec=200*100&type=0&_={}'.format(
        str(timestamp), str(timestamp_1))
    headers = {
        'Referer': 'http://gkcf.jxedu.gov.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    }
    html = requests.get(url, headers=headers)
    content = json.loads(re.search(r'\((.*?)\)', html.text, re.S).group(1))
    id = content.get('Id')  # 验证码id
    top = content.get('y')  # 缺口顶端到图片顶端的距离
    array = content.get('array')  # 打乱顺序
    # print(id, array, top, sep='\n')
    normal = content.get('normal').rsplit(',', 1)[1]  # 打乱的图片的base64
    img_normal = base64.b64decode(normal)
    with open('img_normal.jpg', 'wb') as f:
        f.write(img_normal)

    # 还原验证码
    # 验证码切成上下,各10个,一共分成了20片
    # eg: array = '8,13,18,16,7,4,10,0,15,2,1,19,5,12,11,9,17,14,3,6' ; top = '15'
    image = Image.open('img_normal.jpg')
    print('验证码图片信息:' + image.format, image.size, image.mode)
    im = Image.new(image.mode, image.size)  # 新建一个空白图片,按顺序贴上去
    array = [int(i) for i in array.split(',')]
    for i in range(20):
        arr = array.index(i)  # 把第arr+1个位置的图片粘贴到第i+1个位置处
        if i < 10:
            if arr < 10:
                # 上上 i=0,arr=3
                img = image.crop((20 * arr, 0, 20 * (arr + 1), 50))
                im.paste(img, (20 * i, 0, 20 * (i + 1), 50))
            else:
                # 下上 i=9,arr=16
                img = image.crop((20 * (arr - 10), 50, 20 * (arr - 9), 100))
                im.paste(img, (20 * i, 0, 20 * (i + 1), 50))
        else:
            if arr < 10:
                # 上下 i=19,arr=1
                img = image.crop((20 * arr, 0, 20 * (arr + 1), 50))
                im.paste(img, (20 * (i - 10), 50, 20 * (i - 9), 100))
            else:
                # 下下 i=10,arr=11
                img = image.crop((20 * (arr - 10), 50, 20 * (arr - 9), 100))
                im.paste(img, (20 * (i - 10), 50, 20 * (i - 9), 100))
    # im.show()
    im.save('img_1.jpg')  # 保存还原后的图片

    # 计算滑块需要移动的距离
    # 缺口:40x40 ; 包括左边和上边的两条白线(占1像素)
    # 思路:根据返回的y值(缺口顶端到图片顶端的距离eg:x),就从y=x+1开始,计算往下的40个像素RGB的和,其中和值最大的(因为白色RGB(255,255,255))那一竖条白线就是缺口的最左边
    sum, distance = 0, 0
    for x in range(0, im.size[0]):  # 宽度
        pixel_sum = 0
        for y in range(int(top) + 1, int(top) + 41):
            pixel = im.getpixel((x, y))
            pixel_sum += pixel[0] + pixel[1] + pixel[2]  # 计算RGB总和
        # print(pixel_sum)
        if pixel_sum > sum:
            sum = pixel_sum  # 缺口左边白线往下的40个像素RGB的和
            distance = x

    print('*' * 50)
    print('滑块需要移动的距离为:' + str(distance))  # 滑块需要移动的距离
    return id, distance


def process_data(params):
    '''模拟滑动轨迹,生成data参数'''
    '''
    t1 = new Date(), //开始滑动时间
    t2 = new Date(); //结束滑动时间
    var arrayDate = new Array();//鼠标/手指移动轨迹 eg: [[1,1540199592355],[2,1540199592379],[3,1540199592388]...]==>改成["1,1540199592355","2,1540199592379"]方便拼接
    arrayDate.push([_x, new Date().getTime()]);  //_x:滑块移动的距离
    var data = LZString.compressToEncodedURIComponent(JSON.stringify({  //加密函数:字典转成json,再类似base64
                    Id: Id,  //验证码id
                    point: _x, //滑块移动的总距离
                    timespan: t2 - t1, //滑动总时间 eg:1160
                    datelist: (arrayDate.join("|")) //将arrayDate用'|'连接成字符串 eg:"1,1540199592355|2,1540199592379|3,1540199592388|..."
                }));
    宽是200,减去滑块宽40,等于160,相当于也就160条轨迹!
    因为data参数也就和_x移动距离有关了
    
    拿到移动轨迹，模仿人的滑动行为，先匀加速后匀减速
    匀变速运动基本公式：
    ①v=v0+at
    ②s=v0t+(1/2)at²
    ③v²-v0²=2as

    :param distance: 需要移动的距离
    :return: 轨迹(tracks_list)+时间戳(timestamp_list)+总date_list
    '''
    distance = params[1]
    # 初速度
    v = 0
    # 位移/轨迹列表，列表内的一个元素代表0.02s的位移
    tracks_list = []
    # 当前的位移
    current = 0
    while current < distance - 13:
        # 加速度越小，单位时间的位移越小,模拟的轨迹就越多越详细
        a = random.randint(10000, 12000)  # 加速运动
        # 初速度
        v0 = v
        t = random.randint(9, 18)
        s = v0 * t / 1000 + 0.5 * a * ((t / 1000) ** 2)
        # 当前的位置
        current += s
        # 速度已经达到v,该速度作为下次的初速度
        v = v0 + a * t / 1000
        # 添加到轨迹列表
        if current < distance:
            tracks_list.append(round(current))
    # 减速慢慢滑
    if round(current) < distance:
        for i in range(round(current) + 1, distance + 1):
            tracks_list.append(i)
    else:
        for i in range(tracks_list[-1] + 1, distance + 1):
            tracks_list.append(i)

    # 生成时间戳列表
    timestamp_list = []
    timestamp = int(time.time() * 1000)
    for i in range(len(tracks_list)):
        t = random.randint(11, 18)
        timestamp += t
        timestamp_list.append(timestamp)
        i += 1
    # 生成总datelist
    totaltime = timestamp_list[-1] - timestamp_list[0]
    datelist = [str(i) + ',' + str(j) for i, j in zip(tracks_list, timestamp_list)]
    datelist = '|'.join(datelist)
    return datelist, totaltime


def encrypt_data(params, track):
    '''生成加密参数data'''
    data = {
        'Id': params[0],  # 验证码id
        'point': params[1],  # 滑块移动的总距离
        'timespan': track[1],  # 滑动总时间 eg: 1160
        'datelist': track[0]
    }
    with open('encrypt_data.js', encoding='utf-8') as f:
        jsdata = f.read()
    encrypt_data = execjs.compile(jsdata).call('encrypt_data', data)
    return encrypt_data


def check_captcha(data):
    '''验证'''
    url = 'http://171.34.169.85/api/checkcode?callback=jQuery1110066666666666666666_{}&data={}&type=0&_={}'.format(
        str(timestamp), data, str(timestamp_2))
    # print(url)
    headers = {
        'Referer': 'http://gkcf.jxedu.gov.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    }
    html = requests.get(url, headers=headers)
    content = re.search(r'\((.*?)\)', html.text, re.S).group(1)
    print('*'*50)
    print('返回验证数据' + content)
    print('*' * 50)
    if json.loads(content).get('msg') == '正确':
        print('恭喜您,滑动验证成功~!')
        print('*' * 50)

if __name__ == '__main__':
    timestamp = int(time.time() * 1000)
    timestamp_1 = timestamp + 1
    timestamp_2 = timestamp + 2
    params = process_captcha()
    tracks = process_data(params)
    print('生成滑块轨迹:' + tracks[0], tracks[1])
    data = encrypt_data(params, tracks)
    print(data)
    check_captcha(data)
