import base64
import datetime
import webbrowser
import requests
import time
from flask import Flask, render_template, request
from decimal import Decimal
from DrissionPage import ChromiumPage, ChromiumOptions

app = Flask(__name__)
cur_page, cur_page2 = None, None


@app.route('/button')
def button():
    addr = request.args.get('address')
    select_name = request.args.get('select_name')
    uuid = request.args.get('uuid')
    new_addr = base64.urlsafe_b64decode(addr).decode('utf-8')
    new_name = base64.urlsafe_b64decode(select_name).decode('utf-8')
    new_uuid = base64.urlsafe_b64decode(uuid).decode('utf-8')
    return render_template('button.html', address=new_addr, select_name=new_name, uuid=new_uuid)


@app.route('/new_api', methods=['POST'])
def new_api():
    request_data = request.get_json()
    encode_addr, select_name, uuid, cover_flag = parse_page_name(request_data['url'])
    print(encode_addr)
    print(select_name)
    print(uuid)
    print(cover_flag)
    page_config = requests.get('https://xcyb.weihai.cn/api_test/load_config', verify=False).json()
    print(page_config)
    cur_platform = next((item for item in page_config if item.get('name') == select_name), None)
    if not cur_platform:
        return {'status': 'error'}

    # 获取到当前平台的配置项，包含多个表
    cur_config_list = cur_platform.get('config_list')
    # 获取当前平台用户填写的数据，统一放到池子里
    # 即使一个相同的值，出现在了不同平台中，那也只取对应平台的，只是可以配置相同的id，在设置的时候一样
    data_input_config = raw_load(datetime.datetime.now().strftime('%Y-%m'), uuid)

    if select_name not in data_input_config.keys():
        return {'status': 'error'}

    data_pool = {pool.get('key'): pool.get('value') for value in data_input_config[select_name].values() for pool in
                 value}
    page = ChromiumPage(addr_or_opts=base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    target_page_html = page.latest_tab.html

    # 根据不同平台，获取到当前表的map映射关系, 并且填充数据
    get_cur_map(cur_platform, cur_config_list, target_page_html, page, data_pool, cover_flag)

    return {
        'status': 'ok'
    }


def parse_page_name(url):
    # button.html会把参数传到这里，用于找到控制的是哪个浏览器页面
    new_addr = str(url)
    # 解析出参数列表
    params = new_addr[new_addr.find('?') + 1:].split('&')
    params_dict = dict()
    for item in params:
        params_dict[item[:item.find('=')]] = item[item.find('=') + 1:]
    # address为需控制的浏览器页面，select_name为平台名称，用于确定打开哪个平台
    encode_addr = params_dict.get('address')
    select_name = params_dict.get('select_name')
    uuid = params_dict.get('uuid')
    # cover_flag = params_dict.get('cover_flag')
    select_name = base64.urlsafe_b64decode(select_name).decode('utf-8')
    uuid = base64.urlsafe_b64decode(uuid).decode('utf-8')
    # cover_flag = base64.urlsafe_b64decode(cover_flag).decode('utf-8')
    print(base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    return encode_addr, select_name, uuid, "true"


def get_cur_map(cur_platform, cur_config_list, target_page_html, page, data_pool, cover_flag):
    """Get the current map based on the platform configuration."""
    if cur_platform.get('title_tag') == "":
        # 如果tag为空，说明是非使用frame框架的页面，对该平台所有配置项循环
        return fill_general_page(cur_config_list, target_page_html, page, data_pool, cover_flag)

    # 使用frame框架的页面（税务局）
    return fill_bureau_of_taxation_page(cur_platform, cur_config_list, page, data_pool)


def fill_general_page(cur_config_list, target_page_html, page, data_pool, cover_flag):
    start = datetime.datetime.now()
    # 统计局
    schema = None
    for item in cur_config_list:
        if item.get('name') in target_page_html:
            schema = item.get('map')
    if schema is not None and len(schema) > 0:
        fill_general_data_in_page(page, schema, data_pool, cover_flag)
    end = datetime.datetime.now()
    print("Page fill finished in: {}  seconds", (end - start).seconds)


def fill_general_data_in_page(page, schema, data_pool, cover_flag):
    selector_list = [f'@{list(value.keys())[0]}={value[list(value.keys())[0]]}' for value in schema.values()]
    key_list = list(schema.keys())

    find_res = page.latest_tab.find(selector_list, any_one=False)
    print(len(selector_list), len(key_list), len(find_res))

    for key, selector in zip(key_list, selector_list):
        # 如果不覆盖的话，保留用户已经填写的数据
        if cover_flag == 'false':
            if data_pool[key] == '':
                continue
        if key in data_pool:
            cur_ele = find_res[selector]
            if cur_ele:
                if cur_ele.tag in ['input', 'textarea']:
                    cur_ele.clear(by_js=True)
                    cur_ele.input('', clear=True)
                    cur_ele.clear()
                    cur_ele.input(data_pool[key], clear=True)
                elif cur_ele.tag == 'select':
                    try:# TODO太慢了，待优化
                        cur_ele.select.by_text(str(data_pool[key]))
                    except Exception as e:
                        print(e)
            cur_ele = None


def fill_bureau_of_taxation_page(cur_platform, cur_config_list, page, data_pool):
    # 税务局
    start = datetime.datetime.now()
    tax_schema = None
    new_table_head_ele = page.latest_tab.ele('@class=' + cur_platform.get('title_tag'))
    if new_table_head_ele:
        # 说明是税务局情况，需要特殊判断
        table_head = new_table_head_ele.child('tag:h1').inner_html
        for item in cur_config_list:
            if item.get('name') in table_head:
                tax_schema = item.get('map')
    if tax_schema is not None:
        fill_taxation_data_in_page(page, tax_schema, data_pool, cur_config_list)
    end = datetime.datetime.now()
    print("Page fill finished in: {}  seconds", (end - start).seconds)


def fill_taxation_data_in_page(page, cur_map, data_pool, cur_config_list):
    frames = page.latest_tab.get_frames()

    print(f"total {len(frames)}")
    able_frame_list = []
    for frame in frames:
        for item in cur_config_list:
            name, keyword = item.get('name'), item.get('keyword')
            if keyword and (
                    name in frame.inner_html and keyword in frame.inner_html or name in frame.html and keyword in frame.html):
                print(f"in {'inner_html' if name in frame.inner_html else 'html'}")
                cur_map = item.get('map')
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
                if target_ele.tag == 'select':
                    try:
                        target_ele.select(str(data_pool[key]))
                        target_ele.select.by_text(str(data_pool[key]))
                        target_ele.select.by_value(str(data_pool[key]))
                    except Exception as e:
                        print(e)


@app.route('/api/data', methods=['GET'])
def data():
    url = base64.urlsafe_b64decode(request.args.get('url')).decode('utf-8')
    select_name = request.args.get('select_name')
    uuid = request.args.get('uuid')
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
    encode_uuid = base64.urlsafe_b64encode(uuid.encode('utf-8')).decode('utf-8')
    encode_address = base64.urlsafe_b64encode(cur_page.address.encode('utf-8')).decode('utf-8')
    encode_button_address = base64.urlsafe_b64encode(cur_page2.address.encode('utf-8')).decode('utf-8')
    cur_page2.get(
        f'http://127.0.0.1:8088/button?select_name={encode_select_name}&address={encode_address}&button_addr={encode_button_address}&uuid={encode_uuid}')
    return '请关闭当前网页'


def remove_exponent(num):
    return num.to_integral() if num == num.to_integral() else num.normalize()


def raw_load(date, uuid):
    total_config = requests.get('https://xcyb.weihai.cn/api_test/load_platform_config', verify=False).json()
    input_config = {}
    for config_item in total_config:
        platform = config_item['platform_name']
        table_name = config_item['table_name']
        platform_config = config_item['platform_config']
        if platform not in input_config.keys():
            input_config[platform] = {}
        input_config[platform].update({table_name: platform_config})
    pool = requests.post('https://xcyb.weihai.cn/api_test/load_data', json={'date': date, 'uuid': uuid}, verify=False).json()
    for platform in input_config.keys():
        for table in input_config[platform]:
            for item in input_config[platform][table]:
                if item.get('id') in pool.keys():
                    try:
                        float(pool[item.get('id')])
                        left = Decimal(pool[item.get('id')])
                        right = Decimal(item.get('ratio', "1"))
                        item.update({'value': str(remove_exponent(left * right))})
                    except ValueError:
                        item.update({'value': str(pool[item.get('id')])})
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



@app.route('/find_operate_table', methods=['POST'])
def find_operate_table():
    request_data = request.get_json()
    encode_addr, select_name, uuid = parse_page_name(request_data['url'])
    page_config = requests.get('https://xcyb.weihai.cn/api_test/load_config', verify=False).json()
    cur_platform = next((item for item in page_config if item.get('name') == select_name), None)
    if not cur_platform:
        return {'status': 'error'}
    # 获取到当前平台的配置项，包含多个表
    cur_config_list = cur_platform.get('config_list')
    # 获取当前平台用户填写的数据，统一放到池子里
    # 即使一个相同的值，出现在了不同平台中，那也只取对应平台的，只是可以配置相同的id，在设置的时候一样
    data_input_config = raw_load(datetime.datetime.now().strftime('%Y-%m'), uuid)
    if select_name not in data_input_config.keys():
        return {'status': 'error'}
    page = ChromiumPage(addr_or_opts=base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    target_page_html = page.latest_tab.html
    table_name = ''
    for item in cur_config_list:
        if item.get('name') in target_page_html:
            table_name = item.get('name')
    print(table_name)
    return {'name': table_name}


if __name__ == '__main__':
    webbrowser.open('https://xcyb.weihai.cn/auto_fill_test')
    app.run(port=8088)
