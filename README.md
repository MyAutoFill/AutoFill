# AutoFill
自动生成

## 待实现功能及优化点：
### 前端
- [ ] 【高】数据填写页面，报表预览页面，报表报送页面通过tab页面的形式展现，每个页面分别为一个tab。 ———— 家成做一个简易的，鹏飞调查是否有现成可以用的模板。
- [ ] 【高】数据填写页面将左侧折叠tab变更为一级目录：XX局，二级目录：文档中的表格 参考4.3.2.5.12。 ———— 家成
- [ ] 【高】数据填写页面右侧变更为文档中的表格，适配所有表格。———— 家成调查一个成熟的方法，交给鹏飞来做
- [ ] 【中】数据填写页面表格中的数据项变更为input，下侧设置四个按钮 修改、保存、取消、检查，input默认disable，点击修改变成可编辑，点击保存无论是否有空白或者必填项未填都保存数据，点击取消恢复最初始的数据，点击检查后未填的input标红展示。———— 家成
- [ ] 【低】数据每分钟保存一次，点击取消按钮仍然能恢复至初始数据。
- [ ] 【中】区分数据的单位。
- [ ] 【低】数据填写页面请选择查看时间变为 填表日期，默认为当前月可以修改。
      
- [ ] 【中】报表预览页面左侧目录显示为一级为数据要求部门，如国家税务局、国家统计局、国家市场监督管理局、市人社局、市工会等，第二级为系统名称，第三级为数据填报的具体报表
- [ ] 【高】右侧展示具体报表填充数据后生成的图片 ———— 家祺抠图，鹏飞提供表格页面截图（1 清晰度要高；2 截取最新的图；3 截图内容和数据填写匹配）
- [ ] 【低】增加逻辑检查按钮，点击后给用户显示检查结果，如：共有数据项XX，已填写XX，未填写XX，错误数据项：0

- [ ] 【高】数据库 —— 鹏飞联系哈工大
- [ ] 【中】登录页面
- [ ] 【】
      


### pyinstaller 打包命令
```
C:\Users\pengf\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts\pyinstaller.exe -F --add-data "static;static" --add-data "labels;labels" --add-data "images;images" --add-data "templates;templates" --add-data "data.json;data.json" --add-data "config.json;config.json" --icon=logo.ico app.py  
```
