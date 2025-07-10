
#!/usr/bin/env python3
# run_web_app.py - 启动Flask Web应用

import os
import sys
import webbrowser
import time
from threading import Timer
from pathlib import Path

def check_dependencies():
    """检查依赖项"""
    required_packages = [
        'flask',
        'requests',
        'pathlib',
        'sqlite3'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install flask requests")
        return False
    
    return True

def check_files():
    """检查必要文件"""
    required_files = [
        'app.py',
        'main_optimized.py',
        'config.py',
        'file_manager.py',
        'note_generator.py',
        'pdf_processor_optimized.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少文件: {', '.join(missing_files)}")
        return False
    
    return True

def create_templates_folder():
    """创建templates文件夹和必要的模板文件"""
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # 检查是否需要创建模板文件
    template_files = ['base.html', 'index.html', 'config.html', 'history.html', 'cleanup.html']
    
    for template in template_files:
        template_path = templates_dir / template
        if not template_path.exists():
            print(f"⚠️  模板文件 {template} 不存在")
            print("请确保已经创建了所有必要的HTML模板文件")
            return False
    
    return True

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

def main():
    print("🚀 PDF处理器Web界面启动器")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查文件
    if not check_files():
        sys.exit(1)
    
    # 检查模板文件夹
    if not create_templates_folder():
        sys.exit(1)
    
    # 创建必要的文件夹
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('web_outputs', exist_ok=True)
    
    print("✅ 所有检查通过")
    print("🌐 启动Web服务器...")
    print("📝 浏览器将自动打开 http://localhost:5000")
    print("🔧 使用 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 延迟打开浏览器
    Timer(2.0, open_browser).start()
    
    # 启动Flask应用
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        print("\n⏹️  服务器已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
