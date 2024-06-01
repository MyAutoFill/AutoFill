import base64
import json

from flask import Flask, render_template, request

from DrissionPage import ChromiumPage, ChromiumOptions

app = Flask(__name__)


@app.route('/')
def hello_world():
    return render_template('index.html')


@app.route('/input')
def input_data():
    return render_template('input.html')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


config = [
    {
        "row": "工业总产值(当年价格)",
        "col": "本月",
        "value": "1314",
        "name": "c1_1_3"
    },
    {
        "row": "工业总产值(当年价格)",
        "col": "1-本月",
        "value": "1234",
        "name": "c1_1_4"
    },
    {
        "row": "工业销售产值(当年价格)",
        "col": "本月",
        "value": "000",
        "name": "c1_2_3"
    },
    {
        "row": "工业销售产值(当年价格)",
        "col": "1-本月",
        "value": "001",
        "name": "c1_2_4"
    },
    {
        "row": "其中:出口交货值",
        "col": "本月",
        "value": "004",
        "name": "c1_3_3"
    },
    {
        "row": "其中:出口交货值",
        "col": "1-本月",
        "value": "500",
        "name": "c1_3_4"
    },
]


@app.route('/button')
def button():
    addr = request.args.get('address')
    new_addr = base64.urlsafe_b64decode(addr).decode('utf-8')
    print(new_addr)
    return render_template('button.html', address=new_addr)


@app.route('/new_api', methods=['POST'])
def new_api():
    request_data = request.get_json()
    new_addr = str(request_data['url'])
    encode_addr = new_addr[new_addr.find('address=') + len('address='):]
    page = ChromiumPage(addr_or_opts=base64.urlsafe_b64decode(encode_addr).decode('utf-8'))
    for item in config:
        page.latest_tab.ele('@name='+item.get('name')).input(item.get('value'))
    return {}


@app.route('/data')
def data():
    co = ChromiumOptions().auto_port()
    page = ChromiumPage(co)
    page.get('http://127.0.0.1:5000/dashboard')
    print(page.latest_tab.tab_id)
    page2 = ChromiumPage(co)
    page2.set.window.size(100, 100)
    page2.get('http://127.0.0.1:5000/button?address=' + base64.urlsafe_b64encode(page.address.encode('utf-8')).decode('utf-8'))
    return {}


@app.route('/save')
def save():
    print(request.args.get('name'))
    print(request.args.get('value'))
    name = request.args.get('name')
    value = request.args.get('value')
    save_user_input('page_config', "1", [{"name": name, "value": value}])
    return {}


@app.route('/load')
def load():
    return json.dumps(load_config('page_config'))


def load_config(table_name):
    with open('data.json', 'r') as f:
        return json.load(f).get(table_name, {})


def save_user_input(table_name, system_id, value):
    """
    把前端返回的键值对保存到配置表中
    :param table_name: 表名，一般为page_config
    :param system_id: 对接系统的id，page_config的id字段
    :param value: 用户输入的键值对 [{"name": "xx", "value": "yy"}, ...]
    :return:
    """
    value_map = dict()
    for item in value:
        value_map[item.get('name')] = item.get('value')
    with open('data.json', 'r') as f:
        total_config = json.load(f)
    print(total_config)
    config_list = total_config.get(table_name, [])
    for item in config_list:
        if item.get('id') != system_id:
            continue
        cur_config = item.get('config')
        for config_item in cur_config:
            if config_item['name'] not in value_map:
                continue
            config_item['value'] = value_map[config_item['name']]
        item.update({'config': cur_config})
    print(config_list)
    print(json.dumps(total_config))
    with open('data.json', 'w') as f:
        f.write(json.dumps(total_config))





if __name__ == '__main__':
    app.run()
