import base64
import json
import os
import signal
import sys
import webbrowser

from flask import Flask, render_template, request

from DrissionPage import ChromiumPage, ChromiumOptions

app = Flask(__name__)
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))


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
    new_addr = str(request_data['url'])
    params = new_addr[new_addr.find('?') + 1:].split('&')
    params_dict = dict()
    for item in params:
        params_dict[item[:item.find('=')]] = item[item.find('=') + 1:]
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
    cur_config_list = cur_platform.get('config_list')

    data_input_config = load_config('data_input_config')
    data_pool = dict()
    for (item, value) in data_input_config.items():
        for pool in value:
            data_pool[pool.get('key')] = pool.get('value')

    page = ChromiumPage(addr_or_opts=base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    target_page_html = page.latest_tab.html
    cur_map = None
    if cur_platform.get('title_tag') == "":
        for item in cur_config_list:
            if item.get('name') in target_page_html:
                cur_map = item.get('map')
                break
    else:
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
    page = ChromiumPage(co)
    page.get(url)
    page.set.window.max()
    page2 = ChromiumPage(co)
    page2.set.window.size(100, 200)
    page2.set.window.location(500, 0)
    encode_select_name = base64.urlsafe_b64encode(select_name.encode('utf-8')).decode('utf-8')
    encode_address = base64.urlsafe_b64encode(page.address.encode('utf-8')).decode('utf-8')
    encode_button_address = base64.urlsafe_b64encode(page2.address.encode('utf-8')).decode('utf-8')
    page2.get(f'http://127.0.0.1:5000/button?select_name={encode_select_name}&address={encode_address}&button_addr={encode_button_address}')
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
    save_user_input(request_data)
    return {
        'status': 'ok'
    }


@app.route('/load')
def load():
    table = request.args.get('table')
    return json.dumps(load_config(table))


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
    os.kill(os.getpid(), signal.SIGINT)
    sys.exit()


def load_config(table_name):
    with open(os.path.join(base_path, 'data.json'), 'r', encoding='utf-8') as f:
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


if __name__ == '__main__':
    webbrowser.open_new('http://127.0.0.1:5000')
    app.run()
