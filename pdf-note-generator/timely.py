import time
from datetime import datetime
import subprocess

stop_time = datetime(2025, 7, 14, 0, 35, 00)

# 指定的特定指令
def specific_command():
    # 直接指定输入输出目录
    input_dir = '/home/jia/PaperReader/read-special-pdf/pdf-json-checker/output/orphaned_pdfs'
    output_dir = '/home/jia/PaperReader/read-special-pdf/pdf-json-outputs'

    command = [
        'python3', 'main_optimized.py',
        '-i', input_dir,
        '-o', output_dir
    ]

    # 运行主程序
    print(f"正在执行命令: {' '.join(command)}")
    subprocess.run(command)

# 持续打印当前时间，直到超过设定的停止时间
while True:
    current_time = datetime.now()
    time_remaining = stop_time - current_time  # 计算剩余时间
    seconds_remaining = int(time_remaining.total_seconds())  # 转换为秒数

    print("当前时间:", current_time.strftime("%Y-%m-%d %H:%M:%S"))
    print("距离开始读论文的时间还有:", seconds_remaining, "秒")

    if current_time >= stop_time:
        break
    
    time.sleep(1)  # 等待1秒

# 执行特定指令
specific_command()