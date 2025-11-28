#!/usr/bin/env python3
"""
像素图像处理工具 - 启动脚本
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查并安装依赖"""
    print("🔍 检查依赖包...")
    
    try:
        import flask
        import PIL
        import numpy
        import werkzeug
        print("✅ 所有依赖包已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("正在安装依赖包...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ 依赖包安装成功")
            return True
        except subprocess.CalledProcessError:
            print("❌ 依赖包安装失败，请手动运行: pip install -r requirements.txt")
            return False

def main():
    """主函数"""
    print("🎨 像素图像处理工具")
    print("=" * 40)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查必要的目录
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print("\n🚀 启动Web服务器...")
    print("📱 应用将在 http://localhost:5000 启动")
    print("⏹️  按 Ctrl+C 停止服务器\n")
    
    try:
        # 导入并运行Flask应用
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
