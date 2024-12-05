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
    with open('config.json', 'r') as f:
        result = list()
        data = json.load(f).get('page_config')
        for item in data:
            name = item.get('name')
            title_tag = item.get('title_tag')
            url = item.get('url')
            img = item.get('img')
            config_list = json.dumps(item.get('config_list'), ensure_ascii=False)
            sql = f'''INSERT INTO `platform_info_tbl` VALUES (NULL, '{name}', '{title_tag}', '{url}', '{img}', '{config_list}')'''
            cursor = db.cursor()
            cursor.execute(sql)
            db.commit()