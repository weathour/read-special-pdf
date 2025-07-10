
# app.py - 修复版Flask Web界面
import os
import sys
import json
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
import zipfile
import io

# 导入您的现有模块
from main_optimized import OptimizedPDFNoteGenerator
from config import load_config, save_config
from file_manager import FileManager

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'web_outputs'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# 全局变量用于跟踪处理状态
processing_status = {
    'is_processing': False,
    'current_file': '',
    'progress': 0,
    'total_files': 0,
    'processed_files': 0,
    'failed_files': 0,
    'skipped_files': 0,  # 新增：跳过的文件数
    'message': '',
    'start_time': None,
    'elapsed_time': 0,
    'logs': [],
    'should_stop': False,
    'output_folder': None
}

# 确保必要的文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

class WebProgressCallback:
    """Web进度回调类"""
    def __init__(self):
        self.logs = []
    
    def update_progress(self, current, total, message=""):
        global processing_status
        processing_status['progress'] = int((current / total) * 100) if total > 0 else 0
        processing_status['current_file'] = message
        processing_status['processed_files'] = current
        processing_status['total_files'] = total
        
        # 计算运行时间
        if processing_status['start_time']:
            processing_status['elapsed_time'] = time.time() - processing_status['start_time']
        
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': f"处理进度: {current}/{total} - {message}"
        }
        processing_status['logs'].append(log_entry)
        
        # 保持日志数量不超过100条
        if len(processing_status['logs']) > 100:
            processing_status['logs'] = processing_status['logs'][-100:]

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/config')
def config_page():
    """配置页面"""
    config = load_config('config.json')
    return render_template('config.html', config=config)

@app.route('/save_config', methods=['POST'])
def save_config_route():
    """保存配置"""
    try:
        config_data = request.json
        save_config('config.json', config_data)
        return jsonify({'success': True, 'message': '配置保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'配置保存失败: {str(e)}'})

@app.route('/scan_folder', methods=['POST'])
def scan_folder():
    """扫描文件夹中的PDF文件（递归扫描）并检查处理状态"""
    try:
        data = request.json
        folder_path = data.get('folder_path', '').strip()
        
        if not folder_path:
            return jsonify({'success': False, 'message': '请输入文件夹路径'})
        
        folder_path = Path(folder_path)
        if not folder_path.exists():
            return jsonify({'success': False, 'message': '文件夹不存在'})
        
        if not folder_path.is_dir():
            return jsonify({'success': False, 'message': '路径不是文件夹'})
        
        # 使用递归扫描PDF文件，与原始代码一致
        pdf_files = []
        try:
            for pattern in ['*.pdf', '*.PDF']:
                pdf_files.extend(folder_path.rglob(pattern))  # 使用rglob进行递归扫描
            pdf_files = sorted(list(set(pdf_files)))
        except Exception as e:
            return jsonify({'success': False, 'message': f'扫描文件时出错: {str(e)}'})
        
        if not pdf_files:
            return jsonify({'success': False, 'message': '文件夹中没有找到PDF文件（包括子文件夹）'})
        
        # 加载配置以计算配置哈希
        config = load_config('config.json')
        file_manager = FileManager()
        config_hash = file_manager.calculate_config_hash(config)
        
        # 整理文件信息，包括子文件夹信息和处理状态
        file_info = []
        directories = {}
        total_size = 0
        processed_count = 0
        new_count = 0
        config_changed_count = 0
        
        for pdf_file in pdf_files:
            try:
                # 计算相对路径
                rel_path = pdf_file.relative_to(folder_path)
                parent_dir = str(rel_path.parent) if rel_path.parent != Path('.') else '根目录'
                
                file_size = pdf_file.stat().st_size
                
                # 检查文件是否已处理
                existing_record = file_manager.is_file_processed(pdf_file, config_hash)
                
                status = 'new'
                status_text = '新文件'
                
                if existing_record:
                    if existing_record.get('config_changed', False):
                        status = 'config_changed'
                        status_text = '配置已更改'
                        config_changed_count += 1
                    elif existing_record.get('output_json_path') and not Path(existing_record['output_json_path']).exists():
                        status = 'output_missing'
                        status_text = '输出文件丢失'
                        config_changed_count += 1
                    else:
                        status = 'processed'
                        status_text = '已处理'
                        processed_count += 1
                else:
                    new_count += 1
                
                file_info.append({
                    'name': pdf_file.name,
                    'path': str(pdf_file),
                    'relative_path': str(rel_path),
                    'parent_dir': parent_dir,
                    'size': file_size,
                    'size_mb': round(file_size / 1024 / 1024, 2),
                    'status': status,
                    'status_text': status_text
                })
                
                # 统计文件夹信息
                if parent_dir not in directories:
                    directories[parent_dir] = {'count': 0, 'size': 0}
                directories[parent_dir]['count'] += 1
                directories[parent_dir]['size'] += file_size
                total_size += file_size
            except Exception as e:
                print(f"处理文件 {pdf_file} 时出错: {e}")
                continue
        
        # 按文件名排序
        file_info.sort(key=lambda x: x['name'])
        
        session['scanned_folder'] = str(folder_path)
        session['scanned_files'] = file_info
        
        # 构造详细的返回消息
        need_process_count = new_count + config_changed_count
        
        return jsonify({
            'success': True,
            'message': f'扫描完成！总共找到 {len(file_info)} 个PDF文件，已处理 {processed_count} 个，需要处理 {need_process_count} 个',
            'files': file_info,
            'folder_path': str(folder_path),
            'directories': directories,
            'total_size': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'processing_summary': {
                'total_files': len(file_info),
                'processed_files': processed_count,
                'new_files': new_count,
                'config_changed_files': config_changed_count,
                'need_process_files': need_process_count
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'扫描失败: {str(e)}'})

@app.route('/check_duplicates', methods=['POST'])
def check_duplicates():
    """检查文件是否已处理过"""
    try:
        data = request.json
        files = data.get('files', [])
        
        if not files:
            return jsonify({'success': False, 'message': '没有提供文件列表'})
        
        # 加载配置以计算配置哈希
        config = load_config('config.json')
        file_manager = FileManager()
        config_hash = file_manager.calculate_config_hash(config)
        
        file_status = []
        total_files = len(files)
        new_files = 0
        processed_files = 0
        config_changed_files = 0
        
        for file_info in files:
            file_path = Path(file_info['path'])
            
            # 检查文件是否已处理
            existing_record = file_manager.is_file_processed(file_path, config_hash)
            
            status = {
                'path': str(file_path),
                'name': file_path.name,
                'size_mb': file_info.get('size_mb', 0),
                'processed': False,
                'config_changed': False,
                'output_missing': False,
                'skip_reason': None
            }
            
            if existing_record:
                status['processed'] = True
                
                if existing_record.get('config_changed', False):
                    status['config_changed'] = True
                    status['skip_reason'] = '配置已更改'
                    config_changed_files += 1
                elif existing_record.get('output_json_path') and not Path(existing_record['output_json_path']).exists():
                    status['output_missing'] = True
                    status['skip_reason'] = '输出文件丢失'
                    config_changed_files += 1
                else:
                    status['skip_reason'] = '已处理'
                    processed_files += 1
            else:
                new_files += 1
            
            file_status.append(status)
        
        return jsonify({
            'success': True,
            'file_status': file_status,
            'summary': {
                'total_files': total_files,
                'new_files': new_files,
                'processed_files': processed_files,
                'config_changed_files': config_changed_files,
                'files_to_process': new_files + config_changed_files
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'检查失败: {str(e)}'})

@app.route('/upload', methods=['POST'])
def upload_files():
    """上传PDF文件"""
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    uploaded_files = []
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    
    # 创建当前上传的时间戳文件夹
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    current_upload_folder = upload_folder / timestamp
    current_upload_folder.mkdir(exist_ok=True)
    
    try:
        for file in files:
            if file and file.filename.lower().endswith('.pdf'):
                filename = secure_filename(file.filename)
                filepath = current_upload_folder / filename
                file.save(str(filepath))
                uploaded_files.append({
                    'name': filename,
                    'size': filepath.stat().st_size,
                    'path': str(filepath)
                })
        
        session['current_upload_folder'] = str(current_upload_folder)
        return jsonify({
            'success': True, 
            'message': f'成功上传 {len(uploaded_files)} 个文件',
            'files': uploaded_files,
            'upload_folder': str(current_upload_folder)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'文件上传失败: {str(e)}'})

@app.route('/process', methods=['POST'])
def process_files():
    """处理PDF文件"""
    global processing_status
    
    if processing_status['is_processing']:
        return jsonify({'success': False, 'message': '正在处理中，请稍候'})
    
    try:
        data = request.json
        input_folder = data.get('input_folder', '').strip()
        output_folder = data.get('output_folder', '').strip()
        force_reprocess = data.get('force_reprocess', False)
        use_scanned_folder = data.get('use_scanned_folder', False)
        
        # 确定输入文件夹
        if use_scanned_folder:
            input_folder = session.get('scanned_folder')
        elif not input_folder:
            input_folder = session.get('current_upload_folder')
        
        if not input_folder or not Path(input_folder).exists():
            return jsonify({'success': False, 'message': '输入文件夹不存在或未指定'})
        
        # 确定输出文件夹
        if not output_folder:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_folder = str(Path(app.config['OUTPUT_FOLDER']) / f"output_{timestamp}")
        
        # 创建输出文件夹
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 重置处理状态
        processing_status.update({
            'is_processing': True,
            'current_file': '',
            'progress': 0,
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'message': '正在初始化...',
            'start_time': time.time(),
            'elapsed_time': 0,
            'logs': [],
            'should_stop': False,
            'output_folder': str(output_path)
        })
        
        # 在后台线程中处理
        thread = threading.Thread(
            target=background_process,
            args=(input_folder, output_path, force_reprocess)
        )
        thread.daemon = True
        thread.start()
        
        session['current_output_folder'] = str(output_path)
        
        return jsonify({
            'success': True,
            'message': '处理已开始',
            'output_folder': str(output_path)
        })
        
    except Exception as e:
        processing_status['is_processing'] = False
        return jsonify({'success': False, 'message': f'处理启动失败: {str(e)}'})

@app.route('/stop_processing', methods=['POST'])
def stop_processing():
    """停止处理"""
    global processing_status
    
    if not processing_status['is_processing']:
        return jsonify({'success': False, 'message': '当前没有正在处理的任务'})
    
    processing_status['should_stop'] = True
    
    log_entry = {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'message': '🛑 用户请求停止处理...'
    }
    processing_status['logs'].append(log_entry)
    
    return jsonify({'success': True, 'message': '正在停止处理...'})

def background_process(input_folder, output_folder, force_reprocess):
    """后台处理函数"""
    global processing_status
    
    try:
        # 加载配置
        config = load_config('config.json')
        
        # 创建处理器，使用原始处理逻辑
        processor = OptimizedPDFNoteGenerator(config)
        
        # 获取处理统计信息
        original_process_directory = processor.process_directory
        
        def enhanced_process_directory(input_dir, output_dir, force_reprocess=False):
            """增强的处理目录方法，集成Web状态更新"""
            
            # 扫描文件
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message': f'🔍 开始扫描PDF文件: {input_dir}'
            }
            processing_status['logs'].append(log_entry)
            
            pdf_files = processor._get_all_pdf_files(Path(input_dir))
            
            if not pdf_files:
                processing_status['message'] = '没有找到PDF文件'
                return {'total_files': 0, 'processed_files': 0, 'failed_files': 0, 'skipped_files': 0}
            
            processing_status['total_files'] = len(pdf_files)
            
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message': f'📋 找到 {len(pdf_files)} 个PDF文件'
            }
            processing_status['logs'].append(log_entry)
            
            # 显示文件分布
            processor._show_file_distribution(pdf_files, Path(input_dir))
            
            # 过滤需要处理的文件
            if not force_reprocess:
                log_entry = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'message': '🔄 检查已处理的文件...'
                }
                processing_status['logs'].append(log_entry)
                
                files_to_process = processor._filter_files_to_process(pdf_files)
                processing_status['skipped_files'] = len(pdf_files) - len(files_to_process)
                
                if processing_status['skipped_files'] > 0:
                    log_entry = {
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'message': f'⏭️ 跳过 {processing_status["skipped_files"]} 个已处理的文件'
                    }
                    processing_status['logs'].append(log_entry)
            else:
                files_to_process = pdf_files
                log_entry = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'message': '🔄 强制重新处理所有文件'
                }
                processing_status['logs'].append(log_entry)
            
            if not files_to_process:
                log_entry = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'message': '✅ 所有文件都已处理过'
                }
                processing_status['logs'].append(log_entry)
                processing_status['message'] = '所有文件都已处理过'
                return {'total_files': len(pdf_files), 'processed_files': 0, 'failed_files': 0, 'skipped_files': len(pdf_files)}
            
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message': f'🚀 开始处理 {len(files_to_process)} 个文件'
            }
            processing_status['logs'].append(log_entry)
            
            # 逐个处理文件
            for i, pdf_file in enumerate(files_to_process):
                if processing_status['should_stop']:
                    log_entry = {
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'message': f'🛑 处理被中断，已完成 {i} 个文件'
                    }
                    processing_status['logs'].append(log_entry)
                    break
                
                processing_status['current_file'] = pdf_file.name
                processing_status['message'] = f'正在处理: {pdf_file.name}'
                
                log_entry = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'message': f'📄 [{i+1}/{len(files_to_process)}] 处理: {pdf_file.name}'
                }
                processing_status['logs'].append(log_entry)
                
                try:
                    start_time = time.time()
                    processor._process_single_file(pdf_file, output_dir)
                    end_time = time.time()
                    
                    processing_status['processed_files'] += 1
                    processing_status['progress'] = int(((i + 1) / len(files_to_process)) * 100)
                    
                    log_entry = {
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'message': f'✅ 完成: {pdf_file.name} (耗时: {end_time - start_time:.2f}s)'
                    }
                    processing_status['logs'].append(log_entry)
                    
                except Exception as e:
                    processing_status['failed_files'] += 1
                    processing_status['progress'] = int(((i + 1) / len(files_to_process)) * 100)
                    
                    log_entry = {
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'message': f'❌ 失败: {pdf_file.name} - {str(e)}'
                    }
                    processing_status['logs'].append(log_entry)
                    
                    # 记录失败
                    try:
                        processor.file_manager.record_processing(
                            pdf_file, processor.config_hash,
                            success=False, error_message=str(e)
                        )
                    except Exception as db_e:
                        log_entry = {
                            'timestamp': datetime.now().strftime('%H:%M:%S'),
                            'message': f'⚠️ 数据库记录失败: {str(db_e)}'
                        }
                        processing_status['logs'].append(log_entry)
                    
                    # 如果不是中断，继续处理下一个文件
                    if not processing_status['should_stop']:
                        continue
                    else:
                        break
            
            return {
                'total_files': len(pdf_files),
                'processed_files': processing_status['processed_files'],
                'failed_files': processing_status['failed_files'],
                'skipped_files': processing_status['skipped_files']
            }
        
        # 使用增强的处理方法
        result = enhanced_process_directory(
            Path(input_folder),
            Path(output_folder),
            force_reprocess=force_reprocess
        )
        
        # 处理完成或被中断
        if processing_status['should_stop']:
            processing_status.update({
                'is_processing': False,
                'message': '处理已被中断'
            })
            
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message': f'🛑 处理被中断! 成功: {result["processed_files"]}, 失败: {result["failed_files"]}, 跳过: {result["skipped_files"]}'
            }
            processing_status['logs'].append(log_entry)
        else:
            processing_status.update({
                'is_processing': False,
                'progress': 100,
                'message': '处理完成'
            })
            
            log_entry = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message': f'🎉 处理完成! 成功: {result["processed_files"]}, 失败: {result["failed_files"]}, 跳过: {result["skipped_files"]}'
            }
            processing_status['logs'].append(log_entry)
        
    except Exception as e:
        processing_status.update({
            'is_processing': False,
            'message': f'处理失败: {str(e)}'
        })
        
        log_entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message': f'❌ 处理失败: {str(e)}'
        }
        processing_status['logs'].append(log_entry)

@app.route('/status')
def get_status():
    """获取处理状态"""
    global processing_status
    
    # 实时更新运行时间
    if processing_status['is_processing'] and processing_status['start_time']:
        processing_status['elapsed_time'] = time.time() - processing_status['start_time']
    
    return jsonify(processing_status)

@app.route('/download_results')
def download_results():
    """下载处理结果"""
    output_folder = session.get('current_output_folder')
    if not output_folder or not Path(output_folder).exists():
        return jsonify({'success': False, 'message': '没有可下载的结果'})
    
    try:
        # 创建ZIP文件
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            output_path = Path(output_folder)
            for file_path in output_path.rglob('*'):
                if file_path.is_file():
                    # 计算相对路径
                    relative_path = file_path.relative_to(output_path)
                    zipf.write(file_path, relative_path)
        
        memory_file.seek(0)
        
        filename = f"pdf_processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'})

@app.route('/open_output_folder', methods=['POST'])
def open_output_folder():
    """打开输出文件夹"""
    try:
        output_folder = processing_status.get('output_folder') or session.get('current_output_folder')
        if not output_folder or not Path(output_folder).exists():
            return jsonify({'success': False, 'message': '输出文件夹不存在'})
        
        # 跨平台打开文件夹
        import subprocess
        import platform
        
        if platform.system() == 'Windows':
            os.startfile(output_folder)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.Popen(['open', output_folder])
        else:  # Linux
            subprocess.Popen(['xdg-open', output_folder])
        
        return jsonify({'success': True, 'message': '已打开输出文件夹'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'打开失败: {str(e)}'})

@app.route('/history')
def history():
    """处理历史页面"""
    file_manager = FileManager()
    history_data = file_manager.get_processing_history(50)
    stats = file_manager.get_statistics()
    return render_template('history.html', history=history_data, stats=stats)

@app.route('/cleanup')
def cleanup():
    """清理页面"""
    return render_template('cleanup.html')

@app.route('/cleanup_old', methods=['POST'])
def cleanup_old():
    """清理旧记录"""
    try:
        days = int(request.form.get('days', 30))
        file_manager = FileManager()
        count = file_manager.cleanup_old_records(days)
        flash(f'成功清理了 {count} 条失败记录')
        return redirect(url_for('cleanup'))
    except Exception as e:
        flash(f'清理失败: {str(e)}')
        return redirect(url_for('cleanup'))

@app.route('/clear_uploads', methods=['POST'])
def clear_uploads():
    """清空上传文件夹"""
    try:
        upload_folder = Path(app.config['UPLOAD_FOLDER'])
        if upload_folder.exists():
            shutil.rmtree(upload_folder)
            upload_folder.mkdir(exist_ok=True)
        flash('上传文件夹已清空')
        return redirect(url_for('cleanup'))
    except Exception as e:
        flash(f'清空失败: {str(e)}')
        return redirect(url_for('cleanup'))

@app.route('/clear_outputs', methods=['POST'])
def clear_outputs():
    """清空输出文件夹"""
    try:
        output_folder = Path(app.config['OUTPUT_FOLDER'])
        if output_folder.exists():
            shutil.rmtree(output_folder)
            output_folder.mkdir(exist_ok=True)
        flash('输出文件夹已清空')
        return redirect(url_for('cleanup'))
    except Exception as e:
        flash(f'清空失败: {str(e)}')
        return redirect(url_for('cleanup'))

if __name__ == '__main__':
    print("🚀 启动增强版Flask PDF处理器Web界面")
    print("📝 请在浏览器中访问: http://localhost:5000")
    print("🔧 使用Ctrl+C停止服务器")
    
    # 开发环境配置
    app.run(debug=True, host='0.0.0.0', port=5000)
