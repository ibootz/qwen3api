#!/usr/bin/env python3
"""
端口清理脚本
用于清理被占用的8220端口
"""
import subprocess
import sys
import os
import signal
import time

def get_process_using_port(port):
    """获取使用指定端口的进程信息"""
    try:
        # 使用lsof获取端口占用信息
        result = subprocess.run(
            ["lsof", "-t", f"-i:{port}"],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')
        return [pid for pid in pids if pid]
    except FileNotFoundError:
        # 如果lsof不可用，尝试使用netstat
        try:
            result = subprocess.run(
                ["netstat", "-tulpn"],
                capture_output=True,
                text=True
            )
            lines = result.stdout.split('\n')
            for line in lines:
                if f":{port}" in line:
                    parts = line.split()
                    if len(parts) >= 7:
                        pid_port = parts[6]
                        if '/' in pid_port:
                            pid = pid_port.split('/')[0]
                            return [pid]
        except FileNotFoundError:
            pass
    return []

def kill_process(pid):
    """安全终止进程"""
    try:
        pid = int(pid)
        print(f"正在终止进程 {pid}...")
        
        # 先尝试优雅终止
        os.kill(pid, signal.SIGTERM)
        
        # 等待2秒
        for _ in range(20):
            try:
                os.kill(pid, 0)  # 检查进程是否还在
                time.sleep(0.1)
            except ProcessLookupError:
                print(f"✅ 进程 {pid} 已成功终止")
                return True
        
        # 如果还在，强制终止
        try:
            os.kill(pid, signal.SIGKILL)
            print(f"✅ 进程 {pid} 已强制终止")
            return True
        except ProcessLookupError:
            print(f"✅ 进程 {pid} 已不存在")
            return True
            
    except (ValueError, ProcessLookupError):
        print(f"❌ 进程 {pid} 不存在或已终止")
        return False
    except PermissionError:
        print(f"❌ 无权限终止进程 {pid}")
        return False

def cleanup_port(port=8220):
    """清理指定端口"""
    print(f"🔍 检查端口 {port} 占用情况...")
    
    pids = get_process_using_port(port)
    
    if not pids:
        print(f"✅ 端口 {port} 未被占用")
        return True
    
    print(f"📋 发现 {len(pids)} 个进程占用端口 {port}")
    
    for pid in pids:
        kill_process(pid)
    
    # 再次检查
    time.sleep(1)
    remaining_pids = get_process_using_port(port)
    
    if not remaining_pids:
        print(f"✅ 端口 {port} 已成功清理")
        return True
    else:
        print(f"❌ 仍有进程占用端口 {port}: {remaining_pids}")
        return False

def main():
    """主函数"""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8220
    
    print("🧹 Qwen API 端口清理工具")
    print("=" * 30)
    
    success = cleanup_port(port)
    
    if success:
        print("\n🎉 端口清理完成，现在可以启动服务了！")
        print(f"运行: python run.py")
    else:
        print("\n❌ 端口清理失败，请手动处理")
        sys.exit(1)

if __name__ == "__main__":
    main()
