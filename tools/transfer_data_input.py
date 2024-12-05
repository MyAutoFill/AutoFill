import json

import pymysql

db = pymysql.connect(
    host='119.3.122.142',
    port=3306,
    user='root',
    password='root@123',
    db='data',
    autocommit=True
)

if __name__ == '__main__':
    with open('data.json', 'r') as f:
        data = json.load(f).get('data_input_config')
        for platform in data.keys():
            for table in data[platform].keys():
                print(platform)
                print(table)
                real_json = json.dumps(data[platform][table], ensure_ascii=False)
                sql = f'''INSERT INTO `platform_config_tbl` VALUES (NULL, '{platform}', '{table}', '{real_json}')'''
                cursor = db.cursor()
                cursor.execute(sql)
                db.commit()
