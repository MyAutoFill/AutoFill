import base64
from flask import Flask, render_template, request

from DrissionPage import ChromiumPage, ChromiumOptions

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return render_template('index.html')


@app.route('/input')
def input_data():  # put application's code here
    return render_template('input.html')


@app.route('/dashboard')
def dashboard():  # put application's code here
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
        # tab.ele('@name=' + 'c1_3_4')

    # chrome_options = Options()
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-web-security")
    # chrome_options.add_experimental_option('detach', True)
    # driver = webdriver.WebDriver(options=chrome_options)
    # driver.get('http://127.0.0.1:5000/dashboard')
    # tik_tok = 0
    # while tik_tok < 300:
    #     print(tik_tok)
    #     tik_tok += 1
    #     sleep(1)
    #     handler = driver.current_window_handle
    #     print(driver.current_url)
    #     print(handler.title())
    #     try:
    #         for item in config:
    #             cur_element = driver.find_element(By.NAME, item.get('name'))
    #             print(cur_element)
    #             # cur_element.send_keys(item.get('value'))
    #     except NoSuchElementException:
    #         continue
    return {}


if __name__ == '__main__':
    app.run()
