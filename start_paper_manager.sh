
#!/bin/bash
# start_paper_manager.sh

echo "🚀 启动论文数据库管理系统..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 切换到论文管理系统目录并启动
cd paper-management-system || exit
echo "📚 论文数据库管理系统正在启动..."
echo "🌐 访问地址：http://localhost:5001"
echo "💡 按 Ctrl+C 停止服务"
python run_paper_manager.py
