import base64
import datetime
import json
import os
import sys
import io
import tempfile
from decimal import Decimal
import pymysql
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, send_from_directory, jsonify, send_file

import Utils
import parse_excel

app = Flask(__name__)
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
cur_page, cur_page2 = None, None

db = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='root@123',
    db='data',
    autocommit=True
)


@app.route('/api_test/save', methods=['POST'])
def save():
    request_data = request.get_json()
    date = request_data.get('date', '')
    cur_data = request_data.get('data', '')
    uuid = request_data.get('uuid', '')
    if (not date) or (not cur_data) or (not uuid):
        return {}
    company_data, other_data = dict(), dict()
    company_set = [
        'company_basicinfo',
        'company_employee',
        'company_insurance',
        'company_research',
        'company_runningsum'
    ]
    for key in cur_data:
        find = False
        for keyword in company_set:
            if keyword in key.lower():
                find = True
        if find:
            company_data.update({key: cur_data[key]})
        else:
            other_data.update({key: cur_data[key]})
    exist_other_data = load_data_by_table_name(date, uuid)
    exist_other_data.update(other_data)
    save_data_by_table_name(date, json.dumps(exist_other_data, ensure_ascii=False).replace(' ', ''), uuid)

    exist_company_data = load_company_data_by_table_name(uuid)
    exist_company_data.update(company_data)
    save_data_by_table_name('', json.dumps(exist_company_data, ensure_ascii=False).replace(' ', ''), uuid)
    return {
        'status': 'ok'
    }


# test done!
@app.route('/api_test/save_company_data', methods=['POST'])
def save_company_data():
    request_data = request.get_json()
    cur_data = request_data.get('data', '')
    uuid = request_data.get('uuid', '')
    if (not cur_data) or (not uuid):
        return {}
    exist_data = load_company_data_by_table_name(uuid)
    exist_data.update(cur_data)
    save_data_by_table_name('', json.dumps(exist_data, ensure_ascii=False).replace(' ', ''), uuid)
    return {
        'status': 'ok'
    }


@app.route('/api_test/save_from_excel', methods=['POST'])
def save_from_excel():
    request_data = request.get_json()
    date = request_data['date']
    cur_data = request_data['data']
    uuid = request_data.get('uuid', '')
    real_data = dict()
    for item in cur_data:
        real_data[item.get('key')] = item.get('new_value')
    exist_data = load_data_by_table_name(date, uuid)
    exist_data.update(real_data)
    save_data_by_table_name(date, json.dumps(exist_data, ensure_ascii=False).replace(' ', ''), uuid)
    return {
        'status': 'ok'
    }


# test done!
@app.route('/api_test/load_data', methods=['POST'])
def load():
    request_data = request.get_json()
    date = request_data.get('date', '')
    uuid = request_data.get('uuid', '')
    if (not date) or (not uuid):
        return {}
    other_data = load_data_by_table_name(date, uuid)
    company_data = load_company_data_by_table_name(uuid)
    other_data.update(company_data)
    return jsonify(other_data)


# test done!
@app.route('/api_test/load_company_data', methods=['POST'])
def load_company_data():
    request_data = request.get_json()
    uuid = request_data.get('uuid', '')
    return jsonify(load_company_data_by_table_name(uuid))


# test done!
def load_company_data_by_table_name(uuid):
    # 只获取date为空的公司数据
    db.ping(reconnect=True)
    cursor = db.cursor()
    sql = f'''select company_data from company_data_tbl where `date` = '' and company_id = '{uuid}' '''
    cursor.execute(sql)
    cur_data = cursor.fetchall()
    if len(cur_data) == 0:
        return {}
    return json.loads(cur_data[0][0])


# test done!
@app.route('/api_test/load_platform_config', methods=['GET'])
def load_platform_config():
    db.ping(reconnect=True)
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
    return jsonify(result)


# test done!
def get_config_by_table_name(platform_name, table_name):
    db.ping(reconnect=True)
    cursor = db.cursor()
    sql = f'''select * from platform_config_tbl where platform_name='{platform_name}' and table_name='{table_name}' '''
    cursor.execute(sql)
    cur_data = cursor.fetchall()
    if len(cur_data) == 0:
        return []
    return json.loads(cur_data[0][3])


# test done!
@app.route('/api_test/load_config', methods=['GET'])
def real_load_config():
    return jsonify(load_config())


# test done!
def load_config():
    db.ping(reconnect=True)
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


# test done!
def load_data_by_table_name(date, uuid):
    # 仅获取除基本信息外的信息
    if date == '':
        return {}
    db.ping(reconnect=True)
    cursor = db.cursor()
    sql = f'''select company_data from company_data_tbl where `date` = '{date}' and company_id = '{uuid}' '''
    cursor.execute(sql)
    cur_data = cursor.fetchall()
    if len(cur_data) == 0:
        return {}
    return json.loads(cur_data[0][0])


# test done!
def save_data_by_table_name(date, cur_data, uuid):
    # 如果没有数据需要添加
    db.ping(reconnect=True)
    cursor = db.cursor()
    select_sql = f'''select COUNT(*) from company_data_tbl where `date`='{date}' and `company_id`='{uuid}' '''
    cursor.execute(select_sql)
    exist_data = cursor.fetchall()
    has_data = exist_data[0][0] == 1
    if has_data:
        sql = f'''update company_data_tbl set `company_data` = '{cur_data}' where `date` = '{date}' and `company_id`='{uuid}' '''
        cursor.execute(sql)
    else:
        sql = f'''INSERT INTO `company_data_tbl` (`company_id`, `date`, `company_data`) VALUES ('{uuid}', '{date}', '{cur_data}') '''
        cursor.execute(sql)
    cursor.close()
    return


# test done!
@app.route('/get_platform_dropdown')
def get_platform_dropdown():
    page_config = load_config()
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


# test done!
@app.route('/api_test/get_ratio_config')
def get_ratio_config():
    table = request.args.get('table')
    cur_map = {
        'CompanyRunningSumInfo': {
            'company_runningsum_1': 0.001,
            'Tech_EcoInfo_5': 0.001
        }
    }
    return cur_map.get(table, {})


@app.route('/api_test/parse_table', methods=['POST'])
def parse_table():
    request_data = request.get_json()
    parse_data = request_data['parse_data']
    table_type = request_data['type']
    table_name_map = {
        'lr': '利润表',
        'xjll': '现金流量表',
        'zcfz': '资产负债表'
    }
    parse_result = dict()
    dfs(parse_data.get('内容', []), parse_result)
    table_name = table_name_map[table_type]
    config_list = get_config_by_table_name('山东省电子税务局', table_name)
    key_id_map = dict()
    for item in config_list:
        key_id_map[item['key']] = item['id']
    print(key_id_map)
    change_dict = dict()
    for item in parse_result.keys():
        if item in key_id_map.keys():
            change_dict[key_id_map[item]] = {
                'name': item,
                'new_value': parse_result[item],
            }
    exist_data = load_data_by_table_name(datetime.datetime.now().strftime('%Y-%m'))
    for key in change_dict.keys():
        if key in exist_data.keys():
            change_dict[key]['old_value'] = exist_data[key]
        else:
            change_dict[key]['old_value'] = ""
    result = list()
    for key in change_dict.keys():
        result.append({
            'key': key,
            'name': change_dict[key]['name'],
            'new_value': change_dict[key]['new_value'],
            'old_value': change_dict[key]['old_value']
        })
    return jsonify(result)

@app.route('/api/fill_excel', methods=['POST'])
def download_xlsx():
    data = request.get_json()
    table_name = data['table_name']
    excel_path = prepare_excel(table_name)

    if not os.path.exists(excel_path):
        return "文件不存在", 404
    return send_file(excel_path, as_attachment=True, download_name=table_name + "上传数据.xlsx")

def prepare_excel(table):
    # Load data
    table_config = load_config_by_table_name(table)
    data_pool = load_data_by_company_id(datetime.datetime.now().strftime('%Y-%m'), table_config[0])

    data = {}
    for item in data_pool:
        data[item['key']] = item['value']

    return fill_excel_table(table, data)


def fill_excel_table(table, data_pool):
    excel_structure = parse_excel.parse_excel_structure('asset/' + table + '.json')

    # fill excel data | use Excel key get value in data pool
    for key in excel_structure:
        if key in data_pool:
            excel_structure[key]['data'] = data_pool[key]

    # Save excel to temporary path
    temp_dir = tempfile.TemporaryDirectory(delete=False)
    excel_save_path = os.path.join(temp_dir.name, 'temp_' + table + '_excel.xlsx')
    parse_excel.fill_excel_data('asset/' + table + '_template.xlsx', excel_structure, excel_save_path)

    return excel_save_path


def load_config_by_table_name(table):
    db.ping(reconnect=True)
    cursor = db.cursor()
    sql = "select * from platform_config_tbl where table_name = %s"
    cursor.execute(sql, table)
    cur_data = cursor.fetchall()
    result = list()
    for item in cur_data:
        result.append({
            'platform_name': item[1],
            'table_name': item[2],
            'platform_config': json.loads(item[3])
        })
    return result

def load_data_by_company_id(date, table_config):
    input_config = {}
    # for config_item in table_config:
    platform = table_config['platform_name']
    table_name = table_config['table_name']
    platform_config = table_config['platform_config']
    if platform not in input_config.keys():
        input_config[platform] = {}
    input_config[platform].update({table_name: platform_config})

    pool = load_data_by_table_name(date)
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
    return input_config[platform][table_name]

def remove_exponent(num):
    return num.to_integral() if num == num.to_integral() else num.normalize()

def dfs(cur_list, result):
    for item in cur_list:
        item_id = ""
        if item.get('年初数'):
            item_id = item.get('年初数')
        if item.get('本期数'):
            item_id = item.get('本期数')
        result[item.get('项目')] = str(item_id).strip()
        dfs(item.get("children", []), result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088)
