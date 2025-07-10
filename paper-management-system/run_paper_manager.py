
#!/usr/bin/env python3
# run_paper_manager.py - 启动论文管理系统

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
        'sqlite3',
        'pathlib',
        'markdown',
        'jieba'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install flask markdown jieba")
        return False
    
    return True

def create_templates_folder():
    """创建templates文件夹"""
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    # 检查是否需要创建模板文件
    template_files = ['base.html', 'index.html', 'search.html', 'paper_detail.html', 'import.html', 'statistics.html']
    
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
    webbrowser.open('http://localhost:5001')

def main():
    print("🚀 论文管理系统启动器")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查模板文件夹
    if not create_templates_folder():
        sys.exit(1)
    
    # 创建必要的文件夹
    os.makedirs('json_papers', exist_ok=True)
    
    print("✅ 所有检查通过")
    print("🌐 启动论文管理系统...")
    print("📝 浏览器将自动打开 http://localhost:5001")
    print("🔧 使用 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 延迟打开浏览器
    Timer(2.0, open_browser).start()
    
    # 启动Flask应用
    try:
        from paper_manager import app
        app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
    except KeyboardInterrupt:
        print("\n⏹️  论文管理系统已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
