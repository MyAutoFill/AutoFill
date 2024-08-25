import base64
import datetime
import json
import os
import signal
import sys
import io
import webbrowser
import pymysql
from threading import Timer
import xml.etree.ElementTree as ET

import requests
from PIL import Image, ImageDraw, ImageFont

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify

from DrissionPage import ChromiumPage, ChromiumOptions

import Utils

app = Flask(__name__)
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
cur_page, cur_page2 = None, None

db = pymysql.connect(
    host='1.94.26.133',
    port=3306,
    user='root',
    password='root@123',
    db='data',
    autocommit=True
)


@app.route('/button')
def button():
    addr = request.args.get('address')
    select_name = request.args.get('select_name')
    new_addr = base64.urlsafe_b64decode(addr).decode('utf-8')
    new_name = base64.urlsafe_b64decode(select_name).decode('utf-8')
    return render_template('button.html', address=new_addr, select_name=new_name)


@app.route('/new_api', methods=['POST'])
def new_api():
    request_data = request.get_json()
    # button.html会把参数传到这里，用于找到控制的是哪个浏览器页面
    new_addr = str(request_data['url'])
    # 解析出参数列表
    params = new_addr[new_addr.find('?') + 1:].split('&')
    params_dict = dict()
    for item in params:
        params_dict[item[:item.find('=')]] = item[item.find('=') + 1:]
    # address为需控制的浏览器页面，select_name为平台名称，用于确定打开哪个平台
    encode_addr = params_dict.get('address')
    select_name = params_dict.get('select_name')
    select_name = base64.urlsafe_b64decode(select_name).decode('utf-8')
    print(base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    page_config = load_config()
    cur_platform = None
    for item in page_config:
        if item.get('name') == select_name:
            cur_platform = item
            break
    # 获取到当前平台的配置项，包含多个表
    cur_config_list = cur_platform.get('config_list')

    # 获取当前平台用户填写的数据，统一放到池子里
    # 即使一个相同的值，出现在了不同平台中，那也只取对应平台的，只是可以配置相同的id，在设置的时候一样
    data_input_config = raw_load(datetime.datetime.now().strftime('%Y-%m'))
    if select_name not in data_input_config.keys():
        return {
            'status': 'error'
        }
    data_pool = dict()
    for (item, value) in data_input_config[select_name].items():
        for pool in value:
            data_pool[pool.get('key')] = pool.get('value')

    page = ChromiumPage(addr_or_opts=base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    target_page_html = page.latest_tab.html
    cur_map = None
    # 获取到当前表的map映射关系
    if cur_platform.get('title_tag') == "":
        # 如果tag为空，说明是统计局，对该平台所有配置项循环
        for item in cur_config_list:
            # 找到某个表的map
            if item.get('name') in target_page_html:
                cur_map = item.get('map')
                break
    else:
        # 一定要判断当前页面的title中包含关键字
        new_table_head_ele = page.latest_tab.ele('@class=' + cur_platform.get('title_tag'))
        if new_table_head_ele:
            # 说明是税务局情况，需要特殊判断
            table_head = new_table_head_ele.child('tag:h1').inner_html
            for item in cur_config_list:
                if item.get('name') in table_head:
                    cur_map = item.get('map')
                    break
    if cur_map is not None:
        for key, value in cur_map.items():
            find_key = list(value.keys())[0]
            find_value = value[find_key]
            if key in data_pool.keys():
                cur_ele = page.latest_tab.ele(f'@{find_key}={find_value}')
                if cur_ele:
                    cur_ele.clear(by_js=True)
                    cur_ele.input('', clear=True)
                    cur_ele.input(data_pool[key], clear=True)
    frames = page.latest_tab.get_frames()
    print("total" + str(len(frames)))
    for frame in frames:
        for item in cur_config_list:
            print(item.get('name'))
            if item.get('name') in frame.inner_html:
                print("in inner_html")
                cur_map = item.get('map')
                break
            if item.get('name') in frame.html:
                print("in html")
                cur_map = item.get('map')
                break
    able_frame_list = list()
    for frame in frames:
        total = str(frame.inner_html) + str(frame.html)
        flag = False
        for key, value in cur_map.items():
            find_key = list(value.keys())[0]
            find_value = value[find_key]
            if find_value in total:
                flag = True
        if flag:
            able_frame_list.append(frame)
    print("find" + str(len(able_frame_list)))
    for frame in able_frame_list:
        for key, value in cur_map.items():
            find_key = list(value.keys())[0]
            find_value = value[find_key]
            if key not in data_pool.keys():
                continue
            print('key in')
            target_ele = frame.ele(f'@{find_key}={find_value}')
            print(target_ele)
            if target_ele:
                print('find')
                target_ele.clear(by_js=True)
                target_ele.input('', clear=True)
                target_ele.input(data_pool[key], clear=True)
            else:
                continue
    return {
        'status': 'ok'
    }


@app.route('/api/data', methods=['GET'])
def data():
    url = base64.urlsafe_b64decode(request.args.get('url')).decode('utf-8')
    select_name = request.args.get('select_name')
    co = ChromiumOptions().auto_port()
    global cur_page, cur_page2
    if cur_page is not None:
        cur_page.quit()
    if cur_page2 is not None:
        cur_page2.quit()
    cur_page = ChromiumPage(co)
    cur_page.get(url)
    cur_page.set.window.max()
    cur_page2 = ChromiumPage(co)
    cur_page2.set.window.size(100, 400)
    cur_page2.set.window.location(500, 0)
    encode_select_name = base64.urlsafe_b64encode(select_name.encode('utf-8')).decode('utf-8')
    encode_address = base64.urlsafe_b64encode(cur_page.address.encode('utf-8')).decode('utf-8')
    encode_button_address = base64.urlsafe_b64encode(cur_page2.address.encode('utf-8')).decode('utf-8')
    cur_page2.get(
        f'http://127.0.0.1:8088/button?select_name={encode_select_name}&address={encode_address}&button_addr={encode_button_address}')
    return {}

@app.route('/power')
def power():
    return render_template('test_page/power.html')


def raw_load(date):
    total_config = load_platform_config()
    input_config = {}
    for config_item in total_config:
        platform = config_item['platform_name']
        table_name = config_item['table_name']
        platform_config = config_item['platform_config']
        if platform not in input_config.keys():
            input_config[platform] = {}
        input_config[platform].update({table_name: platform_config})
    pool = load_data_by_table_name(date)
    for platform in input_config.keys():
        for table in input_config[platform]:
            for item in input_config[platform][table]:
                if item.get('id') in pool.keys():
                    item.update({'value': pool[item.get('id')]})
                else:
                    item.update({'value': ''})
    return input_config


def load_platform_config():
    cursor = db.cursor()
    sql = '''select * from platform_config_tbl'''
    cursor.execute(sql)
    cur_data = cursor.fetchall()
    result = list()
    for item in cur_data:
        result.append({
            'platform_name': item[1],
            'table_name': item[2],
            'platform_config': json.loads(item[3])
        })
    return result


@app.route('/close_progress', methods=['POST'])
def close_progress():
    request_data = request.get_json()
    new_addr = str(request_data['url'])
    params = new_addr[new_addr.find('?') + 1:].split('&')
    params_dict = dict()
    for item in params:
        params_dict[item[:item.find('=')]] = item[item.find('=') + 1:]
    encode_addr = params_dict.get('address')
    button_addr = params_dict.get('button_addr')
    page = ChromiumPage(addr_or_opts=base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    page.quit()
    page2 = ChromiumPage(addr_or_opts=base64.urlsafe_b64decode(button_addr).decode('utf-8'))
    page2.quit()
    global cur_page, cur_page2
    cur_page = None
    cur_page2 = None
    return {}


def load_config():
    cursor = db.cursor()
    sql = '''select * from platform_info_tbl'''
    cursor.execute(sql)
    cur_data = cursor.fetchall()
    result = list()
    for item in cur_data:
        result.append({
            'name': item[1],
            'title_tag': item[2],
            'url': item[3],
            'img': item[4],
            'config_list': json.loads(item[5]),
        })
    return result


def load_data_by_table_name(date):
    cursor = db.cursor()
    sql = f'''select company_data from company_data_tbl where `date` = '{date}' '''
    cursor.execute(sql)
    cur_data = cursor.fetchall()
    if len(cur_data) == 0:
        return {}
    return json.loads(cur_data[0][0])


if __name__ == '__main__':
    webbrowser.open('http://1.94.26.133')
    app.run(port=8088)
