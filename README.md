# 像素图像处理工具

![部署状态](https://img.shields.io/badge/部署-在线-success) ![平台-DigitalOcean](https://img.shields.io/badge/平台-DigitalOcean-blue) ![数据库-PostgreSQL](https://img.shields.io/badge/数据库-PostgreSQL-green)

一个基于Python + HTML的像素图像处理软件，可以将任意比例的像素风图片转换为严格像素网格的图片，并生成填色列表。

**🌐 在线访问**：https://baidupaint-4sb3p.ondigitalocean.app/

## 🚀 功能特点

- 📸 **图像上传**：支持任意比例的像素风图片
- 🎯 **像素化处理**：设置网格大小进行精确像素化
- 🎨 **智能颜色量化**：减少颜色位深，生成调色板
- 📋 **填色列表**：生成等待填色的像素区域列表
- 👥 **多人协作**：支持多人同时填色，实时同步
- 🖼️ **像素保持**：使用最近邻插值避免图像模糊
- 📱 **响应式界面**：适配各种设备屏幕

## 🏗️ 项目结构

```
baidu_paint_online/
├── app.py                      # Flask后端主程序
├── database_postgres.py        # PostgreSQL数据库管理器
├── image_processor.py          # 图像处理核心模块
├── requirements.txt            # Python依赖包
├── run.py                      # 便捷启动脚本
├── README.md                   # 项目说明文档
├── DigitalOcean部署环境变量说明.md # 生产环境部署指南
├── templates/                  # HTML模板目录
│   ├── index.html             # 首页（创建/加入空间）
│   ├── join.html              # 加入空间页面
│   ├── space.html             # 空间详情页面
│   └── error.html             # 错误页面
├── static/                    # 静态文件目录
├── uploads/                   # 上传文件目录
└── .git/                      # Git版本控制
```

## 🌐 在线部署

### 生产环境（已部署）
项目已成功部署到 DigitalOcean App Platform：

**访问地址**：https://baidupaint-4sb3p.ondigitalocean.app/

### 开发环境

#### 1. 安装依赖
```bash
pip install -r requirements.txt
```

#### 2. 运行应用
```bash
# 方式一：使用便捷启动脚本（推荐）
python run.py

# 方式二：直接运行
python app.py
```

#### 3. 访问应用
在浏览器中打开：http://localhost:5000

### 部署指南
详细的生产环境部署指南请参考：[DigitalOcean部署环境变量说明.md](DigitalOcean部署环境变量说明.md)

## 📖 使用说明

### 1. 创建空间
1. 访问在线应用：https://baidupaint-4sb3p.ondigitalocean.app/
2. 输入空间名称、用户名和描述
3. 上传像素风图片
4. 设置网格大小（默认128像素）
5. 点击"创建空间"按钮

### 2. 加入空间
1. 获取空间的加入密钥（由创建者分享）
2. 访问加入页面：https://baidupaint-4sb3p.ondigitalocean.app/join/<加入密钥>
3. 输入用户名加入空间

### 3. 协作填色
1. 在空间页面查看像素网格
2. 选择要填色的像素区域
3. 查看颜色调色板提示
4. 标记像素为已完成
5. 支持批量选择（最多40个像素）

### 4. 开发环境使用
如需在本地开发环境测试：
1. 运行 `python run.py` 启动本地服务器
2. 访问 http://localhost:5000
3. 使用方式与在线版本相同

## 🛠️ 技术架构

### 后端技术栈
- **Flask**: 轻量级Web框架
- **PostgreSQL**: 生产级数据库（通过`database_postgres.py`管理）
- **Pillow**: 专业图像处理库
- **NumPy**: 高性能数值计算
- **psycopg2**: PostgreSQL数据库适配器

### 前端技术栈
- **HTML5 + CSS3**: 现代Web标准
- **JavaScript**: 异步交互和动态更新
- **响应式设计**: 适配桌面和移动设备

### 核心算法
1. **像素化处理**：
   - 最近邻插值缩放，保持像素感
   - 颜色量化到256色
   - 智能调色板生成

2. **协作机制**：
   - 实时像素状态同步
   - 批量提交优化（减少网络请求）
   - 冲突检测和解决

3. **数据管理**：
   - PostgreSQL事务支持
   - JSON序列化优化
   - 自动归档不活跃空间

## 🌐 部署支持

### 数据库支持
- ✅ **PostgreSQL**: 生产环境推荐（已配置）
- ⚠️ **SQLite**: 仅适用于开发测试（已移除）

### 云平台部署
- ✅ **DigitalOcean App Platform**: 完整支持
- ✅ **Heroku**: 兼容支持
- ✅ **任何支持Python的云平台**

### 环境变量配置
生产环境需要配置以下环境变量：
- `DATABASE_URL`: PostgreSQL连接字符串
- `SECRET_KEY`: 应用安全密钥
- 其他数据库连接参数

详细配置请参考：[DigitalOcean部署环境变量说明.md](DigitalOcean部署环境变量说明.md)

## 🔧 开发指南

### 代码结构
- `app.py`: 主应用逻辑和路由定义
- `database_postgres.py`: 数据库操作封装
- `image_processor.py`: 图像处理算法
- `run.py`: 开发环境启动脚本

### 扩展功能
1. **添加新的图像处理算法**：修改`image_processor.py`
2. **扩展数据库模型**：修改`database_postgres.py`中的表结构
3. **添加新的API端点**：在`app.py`中添加新的路由函数
4. **修改前端界面**：编辑`templates/`目录下的HTML文件

## 📄 许可证

本项目采用MIT许可证。详见项目根目录的LICENSE文件（如有）。

## 🤝 贡献指南

1. Fork本仓库
2. 创建功能分支：`git checkout -b feature/新功能`
3. 提交更改：`git commit -am '添加新功能'`
4. 推送到分支：`git push origin feature/新功能`
5. 创建Pull Request

## 🐛 问题反馈

如遇到问题，请：
1. 检查日志文件中的错误信息
2. 确认环境变量配置正确
3. 验证数据库连接状态
4. 在GitHub Issues中提交问题报告

---

**注意**：本项目已从SQLite迁移到PostgreSQL，支持生产环境部署。旧版SQLite相关文件已移除。
