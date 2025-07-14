#!/bin/bash

# 检查是否提供了目录参数
if [ -z "$1" ]; then
    echo "错误：请提供一个目录作为参数。"
    exit 1
fi

# 检查目录是否存在
if [ ! -d "$1" ]; then
    echo "错误：目录 '$1' 不存在。"
    exit 1
fi

# 获取绝对路径
target_dir=$(realpath "$1")

echo "正在查看目录: $target_dir"
echo "====================================="

# 列出所有文件夹名
echo "文件夹列表:"
find "$target_dir" -maxdepth 3 -type d -print | sed "s|^$target_dir/||" | sort
echo "-------------------------------------"

# 列出所有指定格式的文件
echo "文件列表 (py, html, js, css):"
find "$target_dir" -maxdepth 3 -type f \( -name "*.py" -o -name "*.html" -o -name "*.js" -o -name "*.css" \) -print | sed "s|^$target_dir/||" | sort
echo "====================================="

echo "已完成查看目录及其下三层内容。"    
