import base64
import datetime
import json
import os
import signal
import sys
import io
import webbrowser
from threading import Timer
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

from flask import Flask, render_template, request, redirect, url_for, send_from_directory

from DrissionPage import ChromiumPage, ChromiumOptions

import Utils

app = Flask(__name__)
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
cur_page, cur_page2 = None, None


@app.route('/')
def hello_world():
    if judge_login():
        return render_template('index.html')
    else:
        return redirect(url_for('login'))


@app.route('/login')
def login():
    return render_template('login.html')


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
    # if cur_map is not None:
    #     for key, value in cur_map.items():
    #         find_key = list(value.keys())[0]
    #         find_value = value[find_key]
    #         if key in data_pool.keys():
    #             cur_ele = page.latest_tab.ele(f'@{find_key}={find_value}')
    #             if cur_ele:
    #                 cur_ele.clear(by_js=True)
    #                 cur_ele.input('', clear=True)
    #                 cur_ele.input(data_pool[key], clear=True)
    #     return {'status': 'ok'}
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
    cur_page2.get(
        f'http://127.0.0.1:5000/button?select_name={encode_select_name}&address={encode_address}&button_addr={encode_button_address}')
    return {}


@app.route('/data_input')
def data_input():
    if judge_login():
        return render_template('data_input.html')
    else:
        return redirect(url_for('login'))


@app.route('/start_fill')
def start_fill():
    if judge_login():
        return render_template('start_fill.html')
    else:
        return redirect(url_for('login'))


@app.route('/power')
def power():
    return render_template('test_page/power.html')


@app.route('/api/login', methods=['POST'])
def do_login():
    request_data = request.get_json()
    name = request_data['username']
    password = request_data['password']
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        total_data = json.loads(text)
    user_list = total_data.get('user_list', [])
    flag = False
    for user in user_list:
        if user.get('username') == name and user.get('password') == password:
            flag = True
    if flag:
        total_data.update({'current_user': name})
        with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'w', encoding='utf-8') as f:
            f.write(json.dumps(total_data, ensure_ascii=False, indent=4))
        return json.dumps({'status': 1})
    else:
        return json.dumps({'status': 0})


@app.route('/get_db', methods=['GET'])
def get_db():
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        total_data = json.loads(text)
    return json.dumps(total_data, ensure_ascii=False, indent=4)


@app.route('/api/register', methods=['POST'])
def register():
    request_data = request.get_json()
    name = request_data['username']
    password = request_data['password']
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        total_data = json.loads(text)
        user_list = total_data.get('user_list', [])
        user_list.append({'username': name, 'password': password})
        total_data.update({'current_user': name})
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(total_data, ensure_ascii=False, indent=4))
    return json.dumps({'status': 'ok'})


@app.route('/api/logout', methods=['GET'])
def logout():
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        total_data = json.loads(text)
        total_data.update({'current_user': ''})
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(total_data, ensure_ascii=False, indent=4))
    return json.dumps({'status': 'ok'})


def judge_login():
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        total_data = json.loads(text)
    if total_data.get('current_user', ''):
        return True
    else:
        return False


@app.route('/save', methods=['POST'])
def save():
    request_data = request.get_json()
    cur_date = request_data['date']
    save_data = request_data['data']
    save_pool = dict()
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        data_config = json.loads(text)
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
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(data_config, ensure_ascii=False, indent=4))
    return {
        'status': 'ok'
    }


@app.route('/load_data')
def load():
    date = request.args.get('date')
    return json.dumps(raw_load(date))


def raw_load(date):
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        data_config = json.loads(text)
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
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        data_config = json.loads(text)
        return data_config.get(table_name, {})


def load_config(table_name):
    with open(os.path.join(os.path.join(base_path, 'config.json'), 'config.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        data_config = json.loads(text)
        return data_config.get(table_name, {})


def save_user_input(value):
    """
    把前端返回的键值对保存到配置表中
    :param value: 用户输入的键值对 [{"name": "xx", "value": "yy"}, ...]
    :return:
    """
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'r', encoding='utf-8') as f:
        text = f.read()
        total_config = json.loads(text)
    total_config.update({"data_input_config": value})
    with open(os.path.join(os.path.join(base_path, 'data.json'), 'data.json'), 'w', encoding='utf-8') as f:
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


def load_annotations(annotations):
    data_tree = ET.parse(annotations)
    root = data_tree.getroot()
    annotation_table = []
    for text_field in root.find('1'):
        name = text_field.find('name').text
        bndbox = text_field.find('bndbox')
        x = int(bndbox.find('x').text)
        y = int(bndbox.find('y').text)
        w = int(bndbox.find('w').text)
        h = int(bndbox.find('h').text)
        annotation_table.append((name, x, y, w, h))
    return annotation_table


def generate_preview_image(image, annotation_table, preview_data, output_path):
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Times New Roman.ttf', 20)
    except IOError:
        font = ImageFont.load_default()

    # Extract base name without extension for data lookup
    base_name = annotation_table[0][3:-4]

    for obj in annotation_table[1]:
        bbox = obj['bbox']
        draw.rectangle(
            [bbox['xmin'], bbox['ymin'], bbox['xmax'], bbox['ymax']],
            outline='red',
            width=1
        )

        for item in preview_data:
            if item['key'] == obj['name']:
                text = item['value']
                text_width = font.getlength(text)
                x_center = (bbox['xmin'] + bbox['xmax']) / 2
                text_x = x_center - text_width / 2
                draw.text(
                    (text_x, bbox['ymin']),
                    text,
                    fill='blue',
                    font=font
                )
    image.save(output_path)
    return image


@app.route('/preview', methods=['POST'])
def preview():
    user_data = request.get_json()

    # 用户期望生成预览的表名
    preview_table = user_data['name']
    # 暂时使用固定名字，api完成后替换成上面代码
    # preview_table = '统计_工业产销总值及主要产品产量'
    # preview_table = '税务_利润表'

    image_template_path = os.path.join(base_path, os.path.join('images', preview_table + '.png'))
    image_template = Image.open(image_template_path)

    image_label_path = os.path.join(base_path, os.path.join('labels', preview_table + '.xml'))
    image_labels = Utils.parse_labelimg_xml(image_label_path)

    # 暂时使用全部表，api完成后可直接替换成 user_data['value']
    flat_data = user_data['value']
    preview_image_save_path = os.path.join(base_path, os.path.join('images/preview_images', preview_table + '.png'))

    preview_image = generate_preview_image(image_template, image_labels, flat_data, preview_image_save_path)

    image_byte_arr = io.BytesIO()
    preview_image.save(image_byte_arr, format='PNG')
    image_byte_arr.seek(0)
    return {
        'status': 1,
        'path': '/image/' + preview_table + '.png'
    }


@app.route('/image/<path:filename>')
def image(filename):
    return send_from_directory('images/preview_images/', filename)


if __name__ == '__main__':
    webbrowser.open('http://127.0.0.1:5000/login')
    app.run()
