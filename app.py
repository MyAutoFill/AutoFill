import base64
import datetime
import json
import os
import signal
import sys
import webbrowser
from threading import Timer

from flask import Flask, render_template, request

from DrissionPage import ChromiumPage, ChromiumOptions

app = Flask(__name__)
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
cur_page, cur_page2 = None, None


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/input')
def input_data():
    return render_template('test_page/input.html')


@app.route('/dashboard')
def dashboard():
    return render_template('test_page/dashboard.html')


@app.route('/tax')
def tax():
    return render_template('test_page/tax_benefit.html')


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
    page_config = load_config('page_config')
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


@app.route('/data', methods=['POST'])
def data():
    request_data = request.get_json()
    print(request_data)
    url = str(request_data['url'])
    select_name = str(request_data['select_name'])
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
    cur_page2.get(f'http://127.0.0.1:5000/button?select_name={encode_select_name}&address={encode_address}&button_addr={encode_button_address}')
    return {}


@app.route('/data_input')
def data_input():
    return render_template('data_input.html')


@app.route('/start_fill')
def start_fill():
    return render_template('start_fill.html')


@app.route('/power')
def power():
    return render_template('test_page/power.html')


@app.route('/save', methods=['POST'])
def save():
    request_data = request.get_json()
    cur_date = request_data['date']
    save_data = request_data['data']
    save_pool = dict()
    with open(os.path.join(base_path, 'data.json'), 'r', encoding='utf-8') as f:
        data_config = json.load(f)
    value_pool = data_config.get('value_pool')
    for platform in save_data.keys():
        for table in save_data[platform]:
            for item in save_data[platform][table]:
                if not item.get('value'):
                    continue
                save_pool[item.get('id')] = item.get('value')
    exist = set()
    for item in value_pool:
        if item.get('date') != cur_date:
            continue
        if item.get('id') in save_pool.keys():
            item.update({'value': save_pool[item.get('id')]})
            exist.add(item.get('id'))
    for item in save_pool.keys():
        if item not in exist:
            value_pool.append({
                "id": item,
                "date": cur_date,
                "value": save_pool[item]
            })
    data_config.update({'value_pool': value_pool})
    with open(os.path.join(base_path, 'data.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(data_config, ensure_ascii=False, indent=4))
    return {
        'status': 'ok'
    }


@app.route('/load_data')
def load():
    date = request.args.get('date')
    return json.dumps(raw_load(date))


def raw_load(date):
    with open(os.path.join(base_path, 'data.json'), 'r', encoding='utf-8') as f:
        data_config = json.load(f)
    input_config = data_config.get('data_input_config')
    value_pool = data_config.get('value_pool')
    pool = dict()
    for item in value_pool:
        if item.get('date') != date:
            continue
        pool[item.get('id')] = item.get('value')
    for platform in input_config.keys():
        for table in input_config[platform]:
            for item in input_config[platform][table]:
                if item.get('id') in pool.keys():
                    item.update({'value': pool[item.get('id')]})
                else:
                    item.update({'value': ''})
    return input_config


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


def load_data(table_name):
    with open(os.path.join(base_path, 'data.json'), 'r', encoding='utf-8') as f:
        return json.load(f).get(table_name, {})


def load_config(table_name):
    with open(os.path.join(base_path, 'config.json'), 'r', encoding='utf-8') as f:
        return json.load(f).get(table_name, {})


def save_user_input(value):
    """
    把前端返回的键值对保存到配置表中
    :param value: 用户输入的键值对 [{"name": "xx", "value": "yy"}, ...]
    :return:
    """
    with open(os.path.join(base_path, 'data.json'), 'r', encoding='utf-8') as f:
        total_config = json.load(f)
    total_config.update({"data_input_config": value})
    with open(os.path.join(base_path, 'data.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(total_config, ensure_ascii=False, indent=4))


@app.route('/get_platform_dropdown')
def get_platform_dropdown():
    page_config = load_config('page_config')
    result = list()
    for item in page_config:
        result.append({
            'name': item.get('name'),
            'url': item.get('url'),
            'img': item.get('img')
        })
    return result


def open_browser():
    co = ChromiumOptions().auto_port()
    page = ChromiumPage(co)
    page.get('http://127.0.0.1:5000')


if __name__ == '__main__':
    webbrowser.open_new('http://127.0.0.1:5000')
    app.run()
