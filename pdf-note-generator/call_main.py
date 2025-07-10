import subprocess

def main():
    # 直接指定输入输出目录
    input_dir = './input_pdfs/'
    output_dir = './output_notes/'

    command = [
        'python', 'main_optimized.py',
        '-i', input_dir,
        '-o', output_dir
    ]

    # 运行主程序
    print(f"正在执行命令: {' '.join(command)}")
    subprocess.run(command)

if __name__ == "__main__":
    main()