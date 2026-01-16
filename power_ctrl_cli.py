import argparse
import sys
import time
# 导入同目录下的 power_supply_control 模块中的类和函数
try:
    from power_supply_control import PowerSupplyController, list_resources
except ImportError:
    # 如果导入失败，可能是因为在其他路径运行，尝试添加当前路径到 sys.path
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from power_supply_control import PowerSupplyController, list_resources

def main():
    parser = argparse.ArgumentParser(
        description="电源控制命令行工具 (CLI)",
        epilog="示例: python power_ctrl_cli.py -v 12.0 -c 2.0 -o on"
    )
    
    # 定义命令行参数
    parser.add_argument("-v", "--voltage", type=float, help="设置电压 (V)")
    parser.add_argument("-c", "--current", type=float, help="设置电流限制 (A)")
    parser.add_argument("-o", "--output", choices=['on', 'off'], help="控制输出开关 (on/off)")
    parser.add_argument("-a", "--address", help="指定 VISA 资源地址 (留空则自动搜索第一个)")
    parser.add_argument("-m", "--measure", action="store_true", help="执行完操作后测量并显示当前电压电流")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有可用 VISA 资源并退出")
    
    args = parser.parse_args()

    # 如果请求列出资源
    if args.list:
        list_resources()
        sys.exit(0)

    # 如果没有传入任何操作参数且不是仅测量，打印帮助
    if args.voltage is None and args.current is None and args.output is None and not args.measure:
        parser.print_help()
        print("\n[提示] 请至少指定一个操作参数。")
        print("例如: python power_ctrl_cli.py -v 5.0 -o on")
        sys.exit(0)

    # 1. 确定资源地址
    address = args.address
    if not address:
        # 自动搜索
        resources = list_resources()
        if not resources:
            print("错误: 未找到任何 VISA 设备。请检查连接。")
            sys.exit(1)
        address = resources[0]
        print(f"自动选择设备: {address}")
    else:
        print(f"使用指定设备: {address}")
    
    # 2. 初始化控制器
    ps = PowerSupplyController(address)
    
    try:
        ps.connect()
        
        # 3. 按顺序执行操作
        # 建议顺序：先设置参数，再开输出
        
        if args.voltage is not None:
            ps.set_voltage(args.voltage)
            
        if args.current is not None:
            ps.set_current(args.current)
            
        if args.output is not None:
            if args.output == 'on':
                ps.set_output(True)
            else:
                ps.set_output(False)

        # 4. 如果请求测量，或者刚刚打开了输出，进行一次测量反馈
        if args.measure or args.output == 'on':
            # 给一点时间让电源响应（特别是刚打开输出时）
            time.sleep(0.5) 
            v = ps.measure_voltage()
            c = ps.measure_current()
            print(f"当前状态: {v:.4f} V, {c:.4f} A")

    except Exception as e:
        print(f"执行出错: {e}")
        sys.exit(1)
    finally:
        ps.close()

if __name__ == "__main__":
    main()