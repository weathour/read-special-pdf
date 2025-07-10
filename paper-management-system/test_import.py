
#!/usr/bin/env python3
# test_import.py - 测试JSON文件导入功能

import os
import json
import sqlite3
from pathlib import Path
from paper_manager import PaperManager

def test_json_file(json_path):
    """测试单个JSON文件的结构"""
    print(f"\n=== 测试JSON文件: {json_path} ===")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ JSON文件加载成功")
        print(f"📁 file_name: {data.get('file_name', 'N/A')}")
        
        # 检查structured_info
        structured_info = data.get('structured_info', {})
        if isinstance(structured_info, str):
            try:
                structured_info = json.loads(structured_info)
                print(f"✅ structured_info 解析成功 (原为字符串)")
            except:
                print(f"❌ structured_info 解析失败")
                return False
        elif isinstance(structured_info, dict):
            print(f"✅ structured_info 格式正确 (字典)")
        else:
            print(f"❌ structured_info 格式错误: {type(structured_info)}")
            return False
        
        # 检查关键字段
        fields = ['title_cn', 'title_en', 'category', 'abstract', 'authors', 'publication_year']
        for field in fields:
            value = structured_info.get(field)
            if value:
                print(f"✅ {field}: {str(value)[:50]}...")
            else:
                print(f"⚠️  {field}: 空值")
        
        # 检查列表字段
        list_fields = ['topics', 'keywords', 'authors']
        for field in list_fields:
            value = structured_info.get(field)
            if isinstance(value, list):
                print(f"✅ {field}: 列表格式, {len(value)} 项")
            elif isinstance(value, dict):
                print(f"📝 {field}: 字典格式, {len(value)} 项 (将转换为列表)")
            else:
                print(f"⚠️  {field}: {type(value)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_import_folder(folder_path):
    """测试文件夹导入"""
    print(f"\n=== 测试文件夹导入: {folder_path} ===")
    
    folder_path = Path(folder_path)
    if not folder_path.exists():
        print(f"❌ 文件夹不存在: {folder_path}")
        return
    
    json_files = list(folder_path.rglob('*.json'))
    print(f"📁 找到 {len(json_files)} 个JSON文件")
    
    if not json_files:
        print("❌ 没有找到JSON文件")
        return
    
    # 测试前几个文件
    test_count = min(3, len(json_files))
    print(f"📝 测试前 {test_count} 个文件...")
    
    for i, json_file in enumerate(json_files[:test_count]):
        success = test_json_file(json_file)
        if not success:
            print(f"❌ 文件 {i+1} 测试失败")
            break
    
    # 尝试导入
    print(f"\n📥 尝试导入到数据库...")
    try:
        manager = PaperManager()
        imported_count, failed_files = manager.import_json_folder(folder_path)
        
        print(f"✅ 导入完成: {imported_count} 个成功")
        if failed_files:
            print(f"❌ 失败文件: {len(failed_files)} 个")
            for fail in failed_files[:3]:  # 只显示前3个
                print(f"   - {fail}")
        
        # 检查数据库
        stats = manager.get_statistics()
        print(f"📊 数据库统计: {stats['total_papers']} 篇论文")
        print(f"📊 分类数: {len(stats['by_category'])}")
        print(f"📊 年份数: {len(stats['by_year'])}")
        
        # 测试搜索
        print(f"\n🔍 测试搜索功能...")
        papers, total = manager.search_papers(query="", limit=5)
        print(f"✅ 搜索结果: {total} 篇论文")
        
        if papers:
            print("📋 前5篇论文:")
            for i, paper in enumerate(papers[:5]):
                title = paper['title_cn'] or paper['title_en'] or paper['file_name']
                print(f"   {i+1}. {title[:60]}...")
        
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🧪 论文管理系统 - JSON导入测试")
    print("=" * 50)
    
    # 获取用户输入
    while True:
        folder_path = input("\n请输入JSON文件夹路径 (或按Enter使用默认路径): ").strip()
        
        if not folder_path:
            # 尝试一些默认路径
            possible_paths = [
                "./json_papers",
                "../json_papers", 
                "~/PaperReader/read-special-pdf/json_papers",
                "/home/jia/PaperReader/read-special-pdf/json_papers"
            ]
            
            for path in possible_paths:
                expanded_path = Path(path).expanduser()
                if expanded_path.exists():
                    folder_path = str(expanded_path)
                    print(f"✅ 使用默认路径: {folder_path}")
                    break
            
            if not folder_path:
                print("❌ 没有找到默认路径，请手动输入")
                continue
        
        # 测试路径
        if Path(folder_path).exists():
            test_import_folder(folder_path)
            break
        else:
            print(f"❌ 路径不存在: {folder_path}")
            continue
    
    print("\n🎉 测试完成!")
    print("💡 如果导入成功，现在可以启动论文管理系统:")
    print("   python run_paper_manager.py")

if __name__ == "__main__":
    main()
