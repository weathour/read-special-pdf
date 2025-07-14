
# pdf_json_checker/run_organizer.py
"""
PDF整理器启动脚本
"""

from pdf_organizer import PDFOrganizer
import sys

def main():
    """主函数"""
    print("🚀 PDF整理器")
    print("="*40)
    
    try:
        # 初始化整理器
        organizer = PDFOrganizer()
        
        # 执行整理
        summary = organizer.organize_and_copy("./output")
        
        print(f"\n💡 建议操作:")
        print(f"1. 检查 ./output/missing_pdfs.json 了解缺失的PDF")
        print(f"2. 检查 ./output/orphaned_pdfs/ 中的孤立PDF是否需要处理")
        print(f"3. 使用 ./output/matched_pdfs/ 中的PDF进行后续处理")
        
        return summary
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
