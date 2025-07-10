
import sys
import time
from typing import Optional, Callable
from pathlib import Path
import threading
import os

class ProgressDisplay:
    """优化的进度显示系统"""
    
    def __init__(self, quiet_mode: bool = False):
        self.quiet_mode = quiet_mode
        self.current_file = ""
        self.current_step = ""
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 0.5  # 更新间隔（秒）
        self._lock = threading.Lock()
        
        # 获取终端宽度
        self.terminal_width = self._get_terminal_width()
        
        # 清理标志
        self.need_cleanup = False
        
    def _get_terminal_width(self) -> int:
        """获取终端宽度"""
        try:
            return os.get_terminal_size().columns
        except:
            return 80
    
    def show_file_progress(self, file_path: Path, current: int, total: int, 
                          step: str = "", extra_info: str = ""):
        """显示文件处理进度"""
        if self.quiet_mode:
            return
        
        current_time = time.time()
        
        # 限制更新频率
        if current_time - self.last_update < self.update_interval and current != total:
            return
        
        with self._lock:
            self.current_file = file_path.name
            self.current_step = step
            self.last_update = current_time
            
            # 计算进度
            progress = current / total if total > 0 else 0
            
            # 创建进度条
            bar_width = min(40, self.terminal_width - 50)
            filled_width = int(bar_width * progress)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)
            
            # 计算时间
            elapsed_time = current_time - self.start_time
            if progress > 0:
                eta = (elapsed_time / progress) * (1 - progress)
                eta_str = self._format_time(eta)
            else:
                eta_str = "未知"
            
            # 构建显示文本
            file_display = self._truncate_text(file_path.name, 25)
            step_display = self._truncate_text(step, 20)
            
            display_text = f"\r📄 {file_display} | {step_display} | [{bar}] {progress:.1f}% | ETA: {eta_str}"
            
            if extra_info:
                display_text += f" | {extra_info}"
            
            # 清理行并显示
            sys.stdout.write("\r" + " " * min(self.terminal_width, 120))
            sys.stdout.write(display_text)
            sys.stdout.flush()
            
            self.need_cleanup = True
            
            # 如果完成，添加换行
            if current == total:
                sys.stdout.write("\n")
                sys.stdout.flush()
                self.need_cleanup = False
    
    def show_overall_progress(self, current_file: int, total_files: int, 
                            current_file_name: str, status: str = ""):
        """显示整体进度"""
        if self.quiet_mode:
            return
        
        current_time = time.time()
        
        # 限制更新频率
        if current_time - self.last_update < self.update_interval and current_file != total_files:
            return
        
        with self._lock:
            self.last_update = current_time
            
            # 计算进度
            progress = current_file / total_files if total_files > 0 else 0
            
            # 创建进度条
            bar_width = min(50, self.terminal_width - 40)
            filled_width = int(bar_width * progress)
            bar = "█" * filled_width + "░" * (bar_width - filled_width)
            
            # 计算时间
            elapsed_time = current_time - self.start_time
            if progress > 0:
                eta = (elapsed_time / progress) * (1 - progress)
                eta_str = self._format_time(eta)
            else:
                eta_str = "未知"
            
            # 构建显示文本
            file_display = self._truncate_text(current_file_name, 30)
            
            display_text = f"\r🚀 总进度 [{bar}] {current_file}/{total_files} ({progress:.1f}%) | ETA: {eta_str} | {file_display}"
            
            if status:
                display_text += f" | {status}"
            
            # 清理行并显示
            sys.stdout.write("\r" + " " * min(self.terminal_width, 120))
            sys.stdout.write(display_text)
            sys.stdout.flush()
            
            self.need_cleanup = True
            
            # 如果完成，添加换行
            if current_file == total_files:
                sys.stdout.write("\n")
                sys.stdout.flush()
                self.need_cleanup = False
    
    def show_processing_step(self, step: str, details: str = ""):
        """显示处理步骤"""
        if self.quiet_mode:
            return
        
        with self._lock:
            # 清理之前的行
            if self.need_cleanup:
                sys.stdout.write("\r" + " " * min(self.terminal_width, 120) + "\r")
            
            display_text = f"🔄 {step}"
            if details:
                display_text += f" | {details}"
            
            sys.stdout.write(display_text + "\n")
            sys.stdout.flush()
            
            self.need_cleanup = False
    
    def show_success(self, message: str):
        """显示成功消息"""
        if self.quiet_mode:
            return
        
        with self._lock:
            if self.need_cleanup:
                sys.stdout.write("\r" + " " * min(self.terminal_width, 120) + "\r")
            
            sys.stdout.write(f"✅ {message}\n")
            sys.stdout.flush()
            
            self.need_cleanup = False
    
    def show_error(self, message: str):
        """显示错误消息"""
        if self.quiet_mode:
            return
        
        with self._lock:
            if self.need_cleanup:
                sys.stdout.write("\r" + " " * min(self.terminal_width, 120) + "\r")
            
            sys.stdout.write(f"❌ {message}\n")
            sys.stdout.flush()
            
            self.need_cleanup = False
    
    def show_warning(self, message: str):
        """显示警告消息"""
        if self.quiet_mode:
            return
        
        with self._lock:
            if self.need_cleanup:
                sys.stdout.write("\r" + " " * min(self.terminal_width, 120) + "\r")
            
            sys.stdout.write(f"⚠️ {message}\n")
            sys.stdout.flush()
            
            self.need_cleanup = False
    
    def show_info(self, message: str):
        """显示信息"""
        if self.quiet_mode:
            return
        
        with self._lock:
            if self.need_cleanup:
                sys.stdout.write("\r" + " " * min(self.terminal_width, 120) + "\r")
            
            sys.stdout.write(f"ℹ️ {message}\n")
            sys.stdout.flush()
            
            self.need_cleanup = False
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m{seconds%60:.0f}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h{minutes:.0f}m"
    
    def cleanup(self):
        """清理显示"""
        if self.need_cleanup:
            sys.stdout.write("\r" + " " * min(self.terminal_width, 120) + "\r")
            sys.stdout.flush()
            self.need_cleanup = False

class QuietProgressDisplay(ProgressDisplay):
    """安静模式的进度显示"""
    
    def __init__(self):
        super().__init__(quiet_mode=True)
        self.last_overall_update = 0
        self.overall_update_interval = 5.0  # 每5秒更新一次总进度
    
    def show_overall_progress(self, current_file: int, total_files: int, 
                            current_file_name: str, status: str = ""):
        """在安静模式下只显示总进度"""
        current_time = time.time()
        
        # 只在指定间隔或完成时更新
        if (current_time - self.last_overall_update < self.overall_update_interval and 
            current_file != total_files):
            return
        
        self.last_overall_update = current_time
        
        progress = current_file / total_files if total_files > 0 else 0
        elapsed_time = current_time - self.start_time
        
        if progress > 0:
            eta = (elapsed_time / progress) * (1 - progress)
            eta_str = self._format_time(eta)
        else:
            eta_str = "未知"
        
        print(f"📊 进度: {current_file}/{total_files} ({progress:.1f}%) | "
              f"当前: {current_file_name} | ETA: {eta_str}")
    
    def show_processing_step(self, step: str, details: str = ""):
        """在安静模式下显示重要步骤"""
        print(f"🔄 {step}")
    
    def show_success(self, message: str):
        """显示成功消息"""
        print(f"✅ {message}")
    
    def show_error(self, message: str):
        """显示错误消息"""
        print(f"❌ {message}")
    
    def show_warning(self, message: str):
        """显示警告消息"""
        print(f"⚠️ {message}")
