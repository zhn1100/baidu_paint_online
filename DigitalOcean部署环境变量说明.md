# DigitalOcean 部署环境变量配置说明

## 🚀 环境变量设置

在 DigitalOcean 部署时，您需要在应用的环境变量中设置以下配置：

### 必需的环境变量

#### 1. 数据库连接配置（两种方式任选其一）

**方式一：使用 DATABASE_URL（推荐）**
```
DATABASE_URL=${db.DATABASE_URL}
```

**方式二：使用分开的环境变量**
```
DB_HOST=app-57144e7e-9f1f-415b-bfee-10a39ba473a2-do-user-29788603-0.m.db.ondigitalocean.com
DB_PORT=25060
DB_NAME=db
DB_USER=db
DB_PASSWORD=您的数据库密码
DB_SSLMODE=require
```

#### 2. 应用安全配置
```
SECRET_KEY=您的安全密钥（至少32位随机字符串）
```

### 可选的环境变量

#### 3. 应用配置
```
FLASK_ENV=production
FLASK_DEBUG=0
PORT=5000
```

#### 4. 会话安全配置（生产环境推荐）
```
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
```

## 🔧 环境变量生成方法

### 生成 SECRET_KEY
```bash
# 在终端中运行
python -c "import secrets; print(secrets.token_hex(32))"
```

### 示例 SECRET_KEY
```
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## 📋 DigitalOcean App Platform 配置步骤

### 1. 在 DigitalOcean 控制台设置环境变量

1. 进入您的 App 页面
2. 点击 "Settings" 标签
3. 找到 "App-Level Environment Variables" 部分
4. 添加上述所有必需的环境变量

### 2. 环境变量格式
- **键**: `DB_HOST`
- **值**: `app-57144e7e-9f1f-415b-bfee-10a39ba473a2-do-user-29788603-0.m.db.ondigitalocean.com`
- **作用范围**: 选择 "Run Time"

### 3. 验证环境变量
应用启动后，检查日志中是否显示：
```
✅ Database connection successful
```

## 🛡️ 安全注意事项

### 1. 保护数据库密码
- 不要在代码中硬编码密码
- 使用环境变量管理敏感信息
- 定期轮换数据库密码

### 2. SECRET_KEY 安全
- 使用足够长度的随机字符串
- 不同环境使用不同的 SECRET_KEY
- 定期更换 SECRET_KEY

### 3. 数据库连接安全
- 使用 SSL 连接 (sslmode=require)
- 限制数据库访问 IP
- 定期备份数据库

## 🔄 开发环境与生产环境差异

### 开发环境 (.env 文件)
```
# .env 文件内容
SECRET_KEY=development-secret-key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dev_db
DB_USER=dev_user
DB_PASSWORD=dev_password
DB_SSLMODE=disable
```

### 生产环境 (DigitalOcean 环境变量)
- 使用 DigitalOcean 管理界面设置
- 不需要 .env 文件
- 自动应用 SSL 加密

## 📊 环境变量验证脚本

您可以创建一个简单的验证脚本来检查环境变量：

```python
# check_env.py
import os

required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'SECRET_KEY']

print("🔍 检查环境变量...")
for var in required_vars:
    value = os.environ.get(var)
    if value:
        print(f"✅ {var}: 已设置")
    else:
        print(f"❌ {var}: 未设置")

print("🎯 环境变量检查完成")
```

## 🚨 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查所有数据库环境变量是否正确
   - 验证数据库密码
   - 确认网络连接和防火墙设置

2. **SECRET_KEY 错误**
   - 确保 SECRET_KEY 已设置且足够长
   - 检查是否有特殊字符导致解析问题

3. **SSL 连接问题**
   - 确认 `DB_SSLMODE=require`
   - 检查数据库证书配置

### 日志检查
在 DigitalOcean App Platform 中查看应用日志：
1. 进入 App 页面
2. 点击 "Logs" 标签
3. 检查启动日志和错误信息

## ✅ 部署检查清单

- [ ] 所有必需环境变量已设置
- [ ] 数据库连接正常
- [ ] SECRET_KEY 已配置
- [ ] SSL 连接启用
- [ ] 应用启动无错误

现在您的应用已经准备好部署到 DigitalOcean！🎉
