
#!/bin/bash
# start_pdf_generator.sh

echo "🚀 启动 PDF 智能笔记生成器..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 切换到 PDF 生成器目录并启动
cd pdf-note-generator || exit
echo "📝 PDF 智能笔记生成器正在启动..."
echo "🌐 访问地址：http://localhost:5000"
echo "💡 按 Ctrl+C 停止服务"
python app.py
