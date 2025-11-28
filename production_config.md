# 生产环境配置指南

## 1. 会话安全配置

### 环境变量设置
在生产环境中，请设置以下环境变量：

```bash
# 设置强密钥（32字节以上）
export SECRET_KEY="your-very-secure-random-secret-key-here"

# 启用HTTPS（推荐）
export FLASK_ENV=production
```

### 生产环境会话配置
在 `app.py` 中，生产环境应启用以下设置：

```python
app.config.update(
    SESSION_COOKIE_SECURE=True,    # 启用HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # 防止XSS攻击
    SESSION_COOKIE_SAMESITE='Lax', # CSRF保护
    PERMANENT_SESSION_LIFETIME=timedelta(days=7)
)
```

## 2. 并发控制机制

### 数据库层面
- **唯一约束**：`UNIQUE(space_id, username, x, y)` 确保每个用户对每个像素只能完成一次
- **事务处理**：批量提交使用数据库事务确保原子性
- **冲突处理**：重复提交自动忽略，不会中断批量操作

### 应用层面
- **乐观锁**：在提交前不锁定资源，通过唯一约束处理冲突
- **前端防重复**：批量选择模式限制40个像素，防止过度提交
- **错误处理**：友好的冲突提示，不影响其他像素的提交

### 冲突处理策略
1. **重复提交**：自动忽略，返回成功状态
2. **其他用户完成**：记录冲突像素，继续处理其他像素
3. **网络超时**：前端自动重试机制

## 3. 性能优化

### 批量提交优势
- **网络请求**：从N次减少到1次
- **数据库写入**：使用事务批量处理
- **用户体验**：减少等待时间

### 数据库优化
- **索引**：关键字段已建立索引
- **数据分离**：固定元数据与动态完成记录分离
- **归档机制**：自动归档不活跃空间

## 4. 部署建议

### 开发环境
```bash
# 无需额外配置，系统会自动生成开发密钥
python app.py
```

### 生产环境
```bash
# 设置环境变量后运行
export SECRET_KEY="your-production-secret-key"
export FLASK_ENV=production
python app.py
```

### 使用Gunicorn（推荐）
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 5. 安全最佳实践

1. **定期更换密钥**：生产环境定期更换SECRET_KEY
2. **HTTPS强制**：生产环境必须启用HTTPS
3. **访问控制**：确保只有授权用户可以访问API
4. **数据备份**：定期备份数据库文件
5. **监控日志**：监控系统运行状态和错误日志

## 6. 故障排除

### 常见问题
1. **会话丢失**：检查SECRET_KEY是否一致
2. **数据库锁**：SQLite并发写入限制，考虑使用PostgreSQL
3. **内存使用**：大图片处理时注意内存限制
4. **网络超时**：调整前端重试机制

### 性能监控
- 监控数据库文件大小
- 跟踪批量提交成功率
- 检查冲突率统计
