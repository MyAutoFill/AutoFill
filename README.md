# AutoFill
自动生成

## 待实现功能及优化点：
### 前端
- [ ] 【高】数据填写页面重新设计，按表为颗粒度进行显示，多个表格共同出现的数据直接填充。
- [ ] 【中】放大数据填写页面字体大小
- [ ] 【中】适配债务平台（待需求澄清）
- [ ] 【中】启动填充弹窗增大并放置在最顶层
- [ ] 【中】数据配置页：增加两个平台其他表格中的数据项，并对数据填充进行重新分类。
- [ ] 【中】代码优化：对data.json写入时判断内容是否为空
- [ ] 【中】代码优化：使用在线cdn引用css和js，改为引用本地的
- [ ] 【低】首页信息重新设计，操作流程在帮助页面中进行显示
- [ ] 【低】数据配置页：其他样式优化
- [ ] 【低】在数据保存之后，点击生成，可以看到表格预填写的样子（提供预览按钮，点击后弹出预填写后的样子）
- [ ] 【低】增加更多页面提醒，离线状态下登入会很慢。例如：填充完成后，提示请仔细检查后点击上报（具体需求待细化）

# 功能
- [ ] 【高】开发往期数据页面
- [ ] 【高】不同平台配置数据单位，页面需要填充的数据都为元，填充时根据不同平台的要求转换为千元或小数点后两位（后面我会细化这个需求）
- [ ] 【高】配置信息和数据填充的信息分离，配置单独形成一个文件
- [ ] 【高】数据信息按月份分类存储，每次打开数据存储页默认显示最新一个填写的数据，到了新的月份如果第一次填写则显示为空
- [ ] 【高】填写后的数据存储结构，基于这个结构展示企业往期数据
- [ ] 【中】功能优化：数据输入页支持一键清空所有数据
- [ ] 【中】功能优化：某些操作需要给用户提示，如提交或关闭程序等
- [ ] 【中】每次只打开一个页面进行填充，用户点击下一个页面后自动关闭上一个填充页面以及启动填充弹窗。
- [ ] 【中】程序启动时打开一个新的窗口而不是现在运行浏览器的新tab
- [ ] 【低】月报、季报根据时间自动生成，在数据填充也增加按钮“生成月报/季报/半年报/年报”，点击后给用户展示自动生成的数据（待确定季报的数据）。
- [ ] 【低】研究是否可以在安装后自动设置桌面快捷方式。
- [ ] 【低】代码优化：添加注释，函数解耦，便于未来拓展。

# 文档
- [ ] 【中】前端文档
- [ ] 【中】系统技术文档
- [ ] 【中】对外介绍以及操作指南
