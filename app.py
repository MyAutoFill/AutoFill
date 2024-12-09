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

import requests
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, send_from_directory, jsonify, send_file

import Utils
import parse_excel

app = Flask(__name__)
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
cur_page, cur_page2 = None, None

db = pymysql.connect(
    host='119.3.122.142',
    port=3306,
    user='root',
    password='root@123',
    db='data',
    autocommit=True
)

remote_db = pymysql.connect(
    host='192.168.242.206',
    port=3306,
    user='dy_6c0E1r3',
    password='Dy_c1e4Aa3',
    db='wh_rsj',
    autocommit=True
)


@app.route('/api/save', methods=['POST'])
def save():
    request_data = request.get_json()
    date = request_data.get('date', '')
    cur_data = request_data.get('data', '')
    uuid = request_data.get('uuid', '')
    if (not date) or (not cur_data) or (not uuid):
        return {}
    save_full_data_by_uuid(date, cur_data, uuid)
    return {
        'status': 'ok'
    }


def save_full_data_by_uuid(date, data, uuid):
    company_data, other_data = dict(), dict()
    company_set = [
        'company_basicinfo',
        'company_employee',
        'company_insurance',
        'company_research',
        'company_runningsum'
    ]
    for key in data:
        find = False
        for keyword in company_set:
            if keyword in key.lower():
                find = True
        if find:
            company_data.update({key: data[key]})
        else:
            other_data.update({key: data[key]})
    exist_other_data = load_data_by_table_name(date, uuid)
    exist_other_data.update(other_data)
    save_data_by_table_name(date, json.dumps(exist_other_data, ensure_ascii=False).replace(' ', ''), uuid)

    exist_company_data = load_company_data_by_table_name(uuid)
    exist_company_data.update(company_data)
    save_data_by_table_name('', json.dumps(exist_company_data, ensure_ascii=False).replace(' ', ''), uuid)


# test done!
@app.route('/api/save_company_data', methods=['POST'])
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


@app.route('/api/sync_data', methods=['POST'])
def sync_data():
    request_data = request.get_json()
    date = request_data.get('date', '')
    # 确认用户对当前页面数据是否进行修改，直接从数据库拿会导致用户新修改数据丢失
    cur_data = request_data.get('data', '')
    # TODO uuid to company name?
    uuid = request_data.get('uuid', '')
    if (not date) or (not cur_data) or (not uuid):
        return {'status': 'error'}

    # TODO 等第三方实现接口后才能确定token
    third_party_result = http_get(uuid, '')

    # 处理返回数据
    if third_party_result['status'] == 'error':
        return {'status': 'error'}
    third_party_data = third_party_result['data']

    # 使用excel mapping 将第三方数据转换成标准数据
    config = parse_excel.parse_json_config('asset/sync_data_api_config.json')
    mapping_data = dict()
    for key in config:
        if len(key['map']) > 0:
            for item in key['map']:
                mapping_data[item] = key['map'][item]

    for key in third_party_data:
        if key in mapping_data:
            if mapping_data[key] is not None:
                third_party_data[mapping_data[key]] = third_party_data.pop(key)

    # 更新已有数据
    for key in cur_data:
        if key in third_party_data:
            cur_data[key] = third_party_data[key]

    # 更新数据库
    save_full_data_by_uuid(date, cur_data, uuid)

    # 从数据库重新获取数据返回
    other_data = load_data_by_table_name(date, uuid)
    company_data = load_company_data_by_table_name(uuid)
    other_data.update(company_data)
    return jsonify(other_data)


def http_get(company_id, token):
    # TODO 等第三方提供url
    url = "https://example.com/api/v1/company_data/" + company_id
    headers = {
        "Content-Type": "application/json",
        "Authorization": token
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        response_data = response.json()
        return jsonify(response_data)
    else:
        return {"status": "error", "message": response.text}, response.status_code


@app.route('/api/save_from_excel', methods=['POST'])
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
@app.route('/api/load_data', methods=['POST'])
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
@app.route('/api/load_company_data', methods=['POST'])
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
@app.route('/api/load_platform_config', methods=['GET'])
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
@app.route('/api/load_config', methods=['GET'])
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
    insert_into_remote_db_257(date, cur_data)
    insert_into_remote_db_258(date, cur_data)
    insert_into_remote_db_259(date, cur_data)
    insert_into_remote_db_260(date, cur_data)
    return


def insert_into_remote_db_260(date, cur_data, uuid):
    """
    企业从业人员信息
    """
    try:
        remote_db.ping(reconnect=True)
        remote_cursor = remote_db.cursor()
        print(remote_cursor)
        select_sql = f'''select COUNT(*) from pres302010260 where `cjsj`='{date}'; '''
        remote_cursor.execute(select_sql)
        exist_data = remote_cursor.fetchall()
        has_data = exist_data[0][0] == 1
        print(has_data)
        insert_data = json.loads(cur_data)
        print(insert_data)
        cyryqmrs = insert_data.get('company_employee_1', '')
        cjsj = date
        nxrs = insert_data.get('company_employee_3', '')
        zcjysglry = insert_data.get('company_employee_5', '')
        zyjsry = insert_data.get('company_employee_7', '')
        cyrypjrs = insert_data.get('company_employee_9', '')
        cyrygzze = insert_data.get('company_employee_11', '')
        if has_data:
            update_sql = f'''update pres302010260 set `cyryqmrs` = '{cyryqmrs}', `nxrs` = '{nxrs}', `zcjysglry` = '{zcjysglry}', `zyjsry` = '{zyjsry}', `cyrypjrs` = '{cyrypjrs}', `cyrygzze` = '{cyrygzze}' where `cjsj` = '{cjsj}' '''
            remote_cursor.execute(update_sql)
        else:
            insert_sql = f'''INSERT INTO `pres302010260` (`cyryqmrs`, `cjsj`, `nxrs`, `zcjysglry`, `zyjsry`, `cyrypjrs`, `cyrygzze`) VALUES ('{cyryqmrs}', '{cjsj}', '{nxrs}', '{zcjysglry}', '{zyjsry}', '{cyrypjrs}', '{cyrygzze}') '''
            print(insert_sql)
            remote_cursor.execute(insert_sql)
        remote_cursor.close()
    except Exception as e:
        print(e)
        return
    return


def insert_into_remote_db_259(date, cur_data, uuid):
    """
    企业从业人员信息
    """
    try:
        remote_db.ping(reconnect=True)
        remote_cursor = remote_db.cursor()
        select_sql = f'''select COUNT(*) from pres302010259 where `cjsj`='{date}'; '''
        remote_cursor.execute(select_sql)
        exist_data = remote_cursor.fetchall()
        has_data = exist_data[0][0] == 1
        insert_data = json.loads(cur_data)
        cjsj = date
        mdtbfckxse = insert_data.get('Tax_companyInfo_37', '')
        msxse = insert_data.get('Tax_companyInfo_43', '')
        xxse = insert_data.get('Tax_companyInfo_61', '')
        jxse = insert_data.get('Tax_companyInfo_67', '')
        sqldse = insert_data.get('Tax_companyInfo_73', '')
        mdtytse = insert_data.get('Tax_companyInfo_85', '')
        ydksehj = insert_data.get('Tax_companyInfo_97', '')
        sjdkse = insert_data.get('Tax_companyInfo_103', '')
        ynse = insert_data.get('Tax_companyInfo_109', '')
        if has_data:
            update_sql = f'''update pres302010259 set `mdtbfckxse` = '{mdtbfckxse}', `msxse` = '{msxse}', `xxse` = '{xxse}', `jxse` = '{jxse}', `sqldse` = '{sqldse}', `mdtytse` = '{mdtytse}', `ydksehj` = '{ydksehj}', `sjdkse` = '{sjdkse}', `ynse` = '{ynse}' where `cjsj` = '{cjsj}' '''
            remote_cursor.execute(update_sql)
        else:
            insert_sql = f'''INSERT INTO `pres302010259` (`cjsj`, `mdtbfckxse`, `msxse`, `xxse`, `jxse`, `sqldse`, `mdtytse`, `ydksehj`, `sjdkse`, `ynse`) VALUES ('{cjsj}', '{mdtbfckxse}', '{msxse}', '{xxse}', '{jxse}', '{sqldse}', '{mdtytse}', '{ydksehj}', '{sjdkse}', '{ynse}') '''
            remote_cursor.execute(insert_sql)
        remote_cursor.close()
    except Exception as e:
        print(e)
        return
    return


def insert_into_remote_db_258(date, cur_data, uuid):
    """
    企业从业人员信息
    """
    try:
        remote_db.ping(reconnect=True)
        remote_cursor = remote_db.cursor()
        select_sql = f'''select COUNT(*) from pres302010258 where `cjsj`='{date}'; '''
        remote_cursor.execute(select_sql)
        exist_data = remote_cursor.fetchall()
        has_data = exist_data[0][0] == 1
        insert_data = json.loads(cur_data)
        cjsj = date
        cyryqors = insert_data.get('company_employee_1', '')
        nx = insert_data.get('company_employee_3', '')
        zgzg = insert_data.get('Statisitc_salary_13', '')
        lwpqry = insert_data.get('Statisitc_salary_17', '')
        qtcyry = insert_data.get('Statisitc_salary_21', '')
        zcjysglry = insert_data.get('company_employee_5', '')
        zyjsry = insert_data.get('company_employee_7', '')
        bsryhygry = insert_data.get('Statisitc_salary_33', '')
        shscfwhshfwry = insert_data.get('Statisitc_salary_37', '')
        sczzjygry = insert_data.get('Statisitc_salary_41', '')
        cyrypjrs = insert_data.get('company_employee_9', '')
        cyryypjgz = insert_data.get('Statisitc_salary_47', '')
        if has_data:
            update_sql = f'''update pres302010258 set `cyryqors` = '{cyryqors}', `nx` = '{nx}', `zgzg` = '{zgzg}', `lwpqry` = '{lwpqry}', `qtcyry` = '{qtcyry}', `zcjysglry` = '{zcjysglry}', `zyjsry` = '{zyjsry}', `bsryhygry` = '{bsryhygry}', `shscfwhshfwry` = '{shscfwhshfwry}', `sczzjygry` = '{sczzjygry}', `cyrypjrs` = '{cyrypjrs}', `cyryypjgz` = '{cyryypjgz}' where `cjsj` = '{cjsj}' '''
            remote_cursor.execute(update_sql)
        else:
            insert_sql = f'''INSERT INTO `pres302010258` (`cjsj`, `cyryqors`, `nx`, `zgzg`, `lwpqry`, `qtcyry`, `zcjysglry`, `zyjsry`, `bsryhygry`, `shscfwhshfwry`, `sczzjygry`, `cyrypjrs`, `cyryypjgz`) VALUES ('{cjsj}', '{cyryqors}', '{nx}', '{zgzg}', '{lwpqry}', '{qtcyry}', '{zcjysglry}', '{zyjsry}', '{bsryhygry}', '{shscfwhshfwry}', '{sczzjygry}', '{cyrypjrs}', '{cyryypjgz}') '''
            remote_cursor.execute(insert_sql)
        remote_cursor.close()
    except Exception as e:
        print(e)
        return
    return


def insert_into_remote_db_257(date, cur_data, uuid):
    """
    企业从业人员信息
    """
    try:
        remote_db.ping(reconnect=True)
        remote_cursor = remote_db.cursor()
        select_sql = f'''select COUNT(*) from pres302010257 where `cjsj`='{date}'; '''
        remote_cursor.execute(select_sql)
        exist_data = remote_cursor.fetchall()
        has_data = exist_data[0][0] == 1
        insert_data = json.loads(cur_data)
        cjsj = date
        czzgjbylbx = insert_data.get('GongShang_sercurity_3', '')
        sybx = insert_data.get('GongShang_sercurity_4', '')
        zgjbylbx = insert_data.get('GongShang_sercurity_5', '')
        gsbx = insert_data.get('GongShang_sercurity_6', '')
        sybxs = insert_data.get('GongShang_sercurity_7', '')
        dwcjczzgjbylbxjfjs = insert_data.get('GongShang_sercurity_8', '')
        dwcjsybxjfjss = insert_data.get('GongShang_sercurity_9', '')
        dwcjzgjbylbxjfjs = insert_data.get('GongShang_sercurity_10', '')
        dwcjsybxjfjs = insert_data.get('GongShang_sercurity_11', '')
        cjczzgjbylbxbqsjjfjee = insert_data.get('GongShang_sercurity_12', '')
        cjsybxbqsjjfje = insert_data.get('GongShang_sercurity_13', '')
        cjzgjbylbxbqsjjfje = insert_data.get('GongShang_sercurity_14', '')
        cjgsbxbqsjjfjee = insert_data.get('GongShang_sercurity_15', '')
        cjsybxbqsjjfjeer = insert_data.get('GongShang_sercurity_16', '')
        dwcjczzgjbylbxljqjje = insert_data.get('GongShang_sercurity_17', '')
        dwcjsybxljqjjeee = insert_data.get('GongShang_sercurity_18', '')
        dwcjzgjbylbxljqjje = insert_data.get('GongShang_sercurity_19', '')
        dwecjgsbxljqjjes = insert_data.get('GongShang_sercurity_20', '')
        dwecjsybxljqjje = insert_data.get('GongShang_sercurity_21', '')
        if has_data:
            update_sql = f'''update pres302010257 set `cyryqors` = '{czzgjbylbx}', `nx` = '{sybx}', `zgzg` = '{zgjbylbx}', `lwpqry` = '{gsbx}', `qtcyry` = '{sybxs}', `zcjysglry` = '{dwcjczzgjbylbxjfjs}', `zyjsry` = '{dwcjsybxjfjss}', `bsryhygry` = '{dwcjzgjbylbxjfjs}', `shscfwhshfwry` = '{dwcjsybxjfjs}', `sczzjygry` = '{cjczzgjbylbxbqsjjfjee}', `cyrypjrs` = '{cjsybxbqsjjfje}', `cyryypjgz` = '{cjzgjbylbxbqsjjfje}', `zcjysglry` = '{cjgsbxbqsjjfjee}', `zyjsry` = '{cjsybxbqsjjfjeer}', `bsryhygry` = '{dwcjczzgjbylbxljqjje}', `shscfwhshfwry` = '{dwcjsybxljqjjeee}', `sczzjygry` = '{dwcjzgjbylbxljqjje}', `cyrypjrs` = '{dwecjgsbxljqjjes}', `cyryypjgz` = '{dwecjsybxljqjje}' where `cjsj` = '{cjsj}' '''
            remote_cursor.execute(update_sql)
        else:
            insert_sql = f'''INSERT INTO `pres302010257` (`cjsj`, `czzgjbylbx`, `sybx`, `zgjbylbx`, `gsbx`, `sybxs`, `dwcjczzgjbylbxjfjs`, `dwcjsybxjfjss`, `dwcjzgjbylbxjfjs`, `dwcjsybxjfjs`, `cjczzgjbylbxbqsjjfjee`, `cjsybxbqsjjfje`, `cjzgjbylbxbqsjjfje`, `cjgsbxbqsjjfjee`, `cjsybxbqsjjfjeer`, `dwcjczzgjbylbxljqjje`, `dwcjsybxljqjjeee`, `dwcjzgjbylbxljqjje`, `dwecjgsbxljqjjes`, `dwecjsybxljqjje`) VALUES ('{cjsj}', '{czzgjbylbx}', '{sybx}', '{zgjbylbx}', '{gsbx}', '{sybxs}', '{dwcjczzgjbylbxjfjs}', '{dwcjsybxjfjss}', '{dwcjzgjbylbxjfjs}', '{dwcjsybxjfjs}', '{cjczzgjbylbxbqsjjfjee}', '{cjsybxbqsjjfje}', '{cjzgjbylbxbqsjjfje}', '{cjgsbxbqsjjfjee}', '{cjsybxbqsjjfjeer}', '{dwcjczzgjbylbxljqjje}', '{dwcjsybxljqjjeee}', '{dwcjzgjbylbxljqjje}', '{dwecjgsbxljqjjes}', '{dwecjsybxljqjje}') '''
            remote_cursor.execute(insert_sql)
        remote_cursor.close()
    except Exception as e:
        print(e)
        return
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
@app.route('/api/get_ratio_config')
def get_ratio_config():
    table = request.args.get('table')
    cur_map = {
        'CompanyRunningSumInfo': {
            'company_runningsum_1': 0.001,
            'company_runningsum_1': 0.001,
            'company_runningsum_2': 0.001,
            'company_runningsum_3': 0.001,
            'company_runningsum_33': 0.001,
            'company_runningsum_4': 0.001,
            'company_runningsum_5': 0.001,
            'company_runningsum_6': 0.001,
            'company_runningsum_7': 0.001,
            'company_runningsum_8': 0.001,
            'company_runningsum_9': 0.001,
            'company_runningsum_10': 0.001,
            'company_runningsum_11': 0.001,
            'company_runningsum_12': 0.001,
            'company_runningsum_13': 0.001,
            'company_runningsum_14': 0.001,
            'company_runningsum_15': 0.001,
            'company_runningsum_16': 0.001,
            'company_runningsum_17': 0.001,
            'company_runningsum_18': 0.001,
            'company_runningsum_19': 0.001,
            'company_runningsum_20': 0.001,
            'company_runningsum_21': 0.001,
            'company_runningsum_22': 0.001,
            'company_runningsum_23': 0.001,
            'company_runningsum_24': 0.001,
            'company_runningsum_25': 0.001,
            'company_runningsum_26': 0.001,
            'company_runningsum_27': 0.001,
            'company_runningsum_28': 0.001,
            'company_runningsum_29': 0.001,
            'company_runningsum_30': 0.001,
            'company_runningsum_31': 0.001,
            'company_runningsum_32': 0.001,
            'Tech_EcoInfo_5': 0.001
        },
        'CompanyResearchInfo': {
            'company_research_6': 0.001,
            'company_research_7': 0.001,
            'company_research_8': 0.001,
            'company_research_9': 0.001,
            'company_research_10': 0.001,
            'company_research_11': 0.001,
            'company_research_12': 0.001,
            'company_research_13': 0.001,
            'company_research_14': 0.001,
            'company_research_15': 0.001,
            'company_research_16': 0.001,
            'company_research_17': 0.001,
            'company_research_18': 0.001,
            'company_research_19': 0.001,
            'company_research_20': 0.001,
            'company_research_21': 0.001,
            'company_research_22': 0.001,
            'company_research_23': 0.001,
            'company_research_24': 0.001,
            'company_research_25': 0.001,
            'company_research_30': 0.001,
            'company_research_35': 0.001,
            'company_research_36': 0.001,
            'company_research_41': 0.001,
            'company_research_42': 0.001,
            'company_research_43': 0.001,
            'company_research_44': 0.001
        },
        'FinanceStatusInfo': {
            'FinanceStatusInfo_2': 0.001,
            'FinanceStatusInfo_127_1': 0.001,
            'FinanceStatusInfo_5': 0.001,
            'company_runningsum_20': 0.001,
            'FinanceStatusInfo_11': 0.001,
            'FinanceStatusInfo_13': 0.001,
            'FinanceStatusInfo_17': 0.001,
            'FinanceStatusInfo_20': 0.001,
            'FinanceStatusInfo_23': 0.001,
            'FinanceStatusInfo_26': 0.001,
            'FinanceStatusInfo_29': 0.001,
            'company_runningsum_24': 0.001,
            'FinanceStatusInfo_35': 0.001,
            'FinanceStatusInfo_38': 0.001,
            'FinanceStatusInfo_41': 0.001,
            'company_runningsum_31': 0.001,
            'company_runningsum_32': 0.001,
            'FinanceStatusInfo_50': 0.001,
            'FinanceStatusInfo_53': 0.001,
            'FinanceStatusInfo_134': 0.001,
            'company_runningsum_3': 0.001,
            'company_runningsum_33': 0.001,
            'company_runningsum_4': 0.001,
            'company_runningsum_2': 0.001,
            'company_runningsum_4': 0.001,
            'company_runningsum_5': 0.001,
            'company_runningsum_6': 0.001,
            'company_runningsum_7': 0.001,
            'company_runningsum_8': 0.001,
            'FinanceStatusInfo_74': 0.001,
            'FinanceStatusInfo_77': 0.001,
            'company_runningsum_9': 0.001,
            'company_runningsum_10': 0.001,
            'company_runningsum_11': 0.001,
            'company_runningsum_12': 0.001,
            'company_runningsum_25': 0.001,
            'company_runningsum_27': 0.001,
            'company_runningsum_13': 0.001,
            'company_runningsum_14': 0.001,
            'company_runningsum_15': 0.001,
            'company_runningsum_16': 0.001,
            'company_runningsum_17': 0.001,
            'company_runningsum_21': 0.001,
            'FinanceStatusInfo_116': 0.001,
            'company_runningsum_23': 0.001,
            'company_runningsum_19': 0.001,
            'FinanceStatusInfo_125': 0.001,
            'FinanceStatusInfo_131': 0.001
        },
        'GongShangCompanyInfo': {
            'GongShang_CompanyInfo_13': 0.0001,
            'GongShang_CompanyInfo_14': 0.0001,
            'shangwu_investor7': 0.0001
        },
        'JoinedSecurityInfo': {
            'GongShang_sercurity_8': 0.0001,
            'GongShang_sercurity_9': 0.0001,
            'GongShang_sercurity_10': 0.0001,
            'GongShang_sercurity_11': 0.0001,
            'GongShang_sercurity_12': 0.0001,
            'GongShang_sercurity_13': 0.0001,
            'GongShang_sercurity_14': 0.0001,
            'GongShang_sercurity_15': 0.0001,
            'GongShang_sercurity_16': 0.0001,
            'GongShang_sercurity_17': 0.0001,
            'GongShang_sercurity_18': 0.0001,
            'GongShang_sercurity_19': 0.0001,
            'GongShang_sercurity_20': 0.0001,
            'GongShang_sercurity_21': 0.0001
        },
        'CompanyEcoInfo': {
            'Tech_EcoInfo_3': 0.001,
            'company_runningsum_1': 0.001,
            'company_runningsum_3': 0.001,
            'Tech_EcoInfo_9': 0.001,
            'Tech_EcoInfo_11': 0.001,
            'Tech_EcoInfo_13': 0.001,
            'Tech_EcoInfo_15': 0.001,
            'Tech_EcoInfo_17': 0.001,
            'Tech_EcoInfo_19': 0.001,
            'Tech_EcoInfo_21': 0.001,
            'Tech_EcoInfo_23': 0.001,
            'Tech_EcoInfo_25': 0.001,
            'Tech_EcoInfo_27': 0.001,
            'Tech_EcoInfo_29': 0.001,
            'Tech_EcoInfo_31': 0.001,
            'Tech_EcoInfo_33': 0.001,
            'company_runningsum_2': 0.001,
            'company_runningsum_4': 0.001,
            'company_runningsum_5': 0.001,
            'company_runningsum_6': 0.001,
            'company_runningsum_7': 0.001,
            'company_runningsum_8': 0.001,
            'company_runningsum_9': 0.001,
            'company_runningsum_10': 0.001,
            'company_runningsum_11': 0.001,
            'company_runningsum_12': 0.001,
            'company_runningsum_25': 0.001,
            'company_runningsum_27': 0.001,
            'company_runningsum_13': 0.001,
            'company_runningsum_14': 0.001,
            'company_runningsum_15': 0.001,
            'company_runningsum_16': 0.001,
            'company_runningsum_17': 0.001,
            'GongShang_property_6': 0.001,
            'company_runningsum_21': 0.001,
            'GongShang_property_7': 0.001,
            'Tech_EcoInfo_75': 0.001,
            'Tech_EcoInfo_77': 0.001,
            'Tech_EcoInfo_79': 0.001,
            'Tech_EcoInfo_81': 0.001,
            'Tech_EcoInfo_83': 0.001,
            'Tech_EcoInfo_85': 0.001,
            'Tech_EcoInfo_87': 0.001,
            'Tech_EcoInfo_89': 0.001,
            'company_runningsum_19': 0.001,
            'company_runningsum_23': 0.001,
            'FinanceStatusInfo_38': 0.001,
            'company_runningsum_20': 0.001,
            'Tech_EcoInfo_99': 0.001,
            'Tech_EcoInfo_101': 0.001,
            'company_runningsum_22': 0.001,
            'company_runningsum_24': 0.001,
            'company_runningsum_26': 0.001,
            'Tech_EcoInfo_109': 0.001,
            'company_runningsum_29': 0.001,
            'company_runningsum_30': 0.001,
            'Tech_EcoInfo_115': 0.001,
            'company_runningsum_31': 0.001,
            'company_runningsum_32': 0.001,
            'Tech_EcoInfo_121': 0.001,
            'Tech_EcoInfo_123': 0.001,
            'Tech_EcoInfo_125': 0.001,
            'Tech_EcoInfo_127': 0.001
        },
        'ResearchDevelopActivity': {
            'Tech_activity_13': 0.001,
            'Tech_activity_15': 0.001,
            'Tech_activity_17': 0.001,
            'company_research_9': 0.001,
            'company_research_10': 0.001,
            'Tech_activity_23': 0.001,
            'Tech_activity_25': 0.001,
            'Tech_activity_27': 0.001,
            'Tech_activity_29': 0.001,
            'Tech_activity_31': 0.001,
            'Tech_activity_33': 0.001,
            'Tech_activity_35': 0.001,
            'Tech_activity_37': 0.001,
            'Tech_activity_39': 0.001,
            'Tech_activity_41': 0.001,
            'Tech_activity_43': 0.001,
            'Tech_activity_45': 0.001,
            'Tech_activity_47': 0.001,
            'Tech_activity_49': 0.001,
            'Tech_activity_51': 0.001,
            'Tech_activity_61': 0.001,
            'Tech_activity_93': 0.001,
            'Tech_activity_95': 0.001,
            'company_research_35': 0.001,
            'company_research_36': 0.001,
            'Tech_activity_145': 0.001,
            'Tech_activity_151': 0.001,
            'Tech_activity_153': 0.001,
            'Tech_activity_155': 0.001,
            'Tech_activity_157': 0.001
        },
        'HighTechCompanyStat': {
            'company_basicinfo_45': 0.0001
        },
        'InfoTechMonthlyForm': {
            'company_runningsum_3': 0.0001,
            'Gongxin_basic3': 0.0001,
            'Gongxin_soft1': 0.0001,
            'Gongxin_soft2': 0.0001,
            'Gongxin_soft3': 0.0001,
            'Gongxin_soft4': 0.0001,
            'Gongxin_soft5': 0.0001,
            'Gongxin_soft6': 0.0001,
            'Gongxin_soft7': 0.0001,
            'Gongxin_soft8': 0.0001,
            'Gongxin_soft9': 0.0001,
            'company_runningsum_33': 0.0001,
            'Gongxin_soft13': 0.0001,
            'Gongxin_soft14': 0.0001,
            'company_runningsum_17': 0.0001,
            'Gongxin_soft15': 0.0001,
            'company_employee_11': 0.0001,
            'Gongxin_soft10': 0.1376,
            'Gongxin_soft11': 0.1376,
            'Gongxin_soft12': 0.1376
        },
        'ShangwuBasicInfo': {
            'company_runningsum_23': 0.0001
        },
        'ShangwuInvestorInfo': {
            'shangwu_investor7': 0.0001,
            'shangwu_investor10': 0.0001,
            'shangwu_investor6': 0.0001
        },
        'ShangwuOperationInfo': {
            'company_runningsum_1': 0.0001,
            'company_runningsum_3': 0.0001,
            'company_runningsum_2': 0.0001,
            'tax_benefits_month_5': 0.0001,
            'company_runningsum_7': 0.0001,
            'GongShang_property_7': 0.0001,
            'company_runningsum_19': 0.0001,
            'shangwu_operation10': 0.0001,
            'company_runningsum_21': 0.0001,
            'shangwu_operation12': 0.0001,
            'shangwu_operation13': 0.0001,
            'company_runningsum_17': 0.0001,
            'GongShang_property_6': 0.0001,
            'shangwu_operation16': 0.0001,
            'shangwu_operation17': 0.0001,
            'shangwu_operation18': 0.0001,
            'shangwu_operation19': 0.0001,
            'shangwu_operation20': 0.0001,
            'shangwu_operation21': 0.0001,
            'shangwu_operation24': 0.0001,
            'shangwu_operation25': 0.0001,
            'shangwu_operation26': 0.0001,
            'Tech_EcoInfo_79': 0.0001,
            'company_runningsum_18': 0.0001,
            'company_runningsum_20': 0.0001,
            'tax_debt_7': 0.0001,
            'Tech_EcoInfo_99': 0.0001,
            'tax_debt_14': 0.0001,
            'company_runningsum_22': 0.0001,
            'company_runningsum_24': 0.0001,
            'company_runningsum_30': 0.0001,
            'company_runningsum_29': 0.0001,
            'tax_debt_32': 0.0001,
            'tax_debt_35': 0.0001,
            'property_29_yearEnd_2': 0.0001,
            'company_runningsum_31': 0.0001,
            'company_runningsum_32': 0.0001,
            'tax_debt_48': 0.0001,
            'tax_debt_49': 0.0001,
            'tax_debt_51': 0.0001,
            'shangwu_operation46': 0.0001,
            'shangwu_operation47': 0.0001,
            'company_runningsum_32': 0.0001,
            'shangwu_operation49': 0.0001,
            'shangwu_operation50': 0.0001,
            'shangwu_operation51': 0.0001,
            'shangwu_operation52': 0.0001,
            'shangwu_operation53': 0.0001,
            'shangwu_operation54': 0.0001,
            'shangwu_operation55': 0.0001,
            'shangwu_operation56': 0.0001,
            'shangwu_operation57': 0.0001,
            'shangwu_operation58': 0.0001,
            'shangwu_operation1': 0.1376,
            'Tech_EcoInfo_29': 0.1376,
            'shangwu_operation22': 0.1376,
            'shangwu_operation23': 0.1376
        }
    }
    return cur_map.get(table, {})


@app.route('/api/parse_table', methods=['POST'])
def parse_table():
    request_data = request.get_json()
    parse_data = request_data['parse_data']
    table_type = request_data['type']
    uuid = request_data['uuid']
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
    exist_data = load_data_by_table_name('2026-01', uuid)
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


@app.route('/api/fill_excel', methods=['GET'])
def download_xlsx():
    table_name = request.args.get('table_name')
    uuid = request.args.get('uuid')
    excel_path = prepare_excel(table_name, uuid)

    if not os.path.exists(excel_path):
        return "文件不存在", 404
    return send_file(excel_path, as_attachment=True)


def prepare_excel(table, uuid):
    # Load data
    table_config = load_config_by_table_name(table)
    data_pool = load_data_by_company_id(datetime.datetime.now().strftime('%Y-%m'), table_config[0], uuid)

    data = {}
    for item in data_pool:
        data[item['key']] = item['value']

    return fill_excel_table(table, data)


def fill_excel_table(table, data_pool):
    excel_structure = parse_excel.parse_json_config('asset/' + table + '.json')

    # fill excel data | use Excel key get value in data pool
    for key in excel_structure:
        if key in data_pool:
            excel_structure[key]['value'] = data_pool[key]

    # Save excel to temporary path
    excel_save_path = os.path.join(
        'temp_' + table + '_excel_' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '.xlsx')
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


def load_data_by_company_id(date, table_config, uuid):
    input_config = {}
    # for config_item in table_config:
    platform = table_config['platform_name']
    table_name = table_config['table_name']
    platform_config = table_config['platform_config']
    if platform not in input_config.keys():
        input_config[platform] = {}
    input_config[platform].update({table_name: platform_config})
    company_data = load_company_data_by_table_name(uuid)
    pool = load_data_by_table_name(date, uuid)
    pool.update(company_data)
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


@app.route('/api/download_exe', methods=['GET'])
def download_exe():
    exe_path = "client.exe"
    if not os.path.exists(exe_path):
        return "文件不存在", 404
    return send_file(exe_path, as_attachment=True)


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
