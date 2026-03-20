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
        epilog=(
            "示例: python power_ctrl_cli.py -v 12.0 -c 2.0 -o on / "
            "python power_ctrl_cli.py --cycle-count 5 --cycle-on-time 3000 "
            "--cycle-off-time 2000 --cycle-end-output on"
        )
    )
    
    # 定义命令行参数
    parser.add_argument("-v", "--voltage", type=float, help="设置电压 (V)")
    parser.add_argument("-c", "--current", type=float, help="设置电流限制 (A)")
    parser.add_argument("-o", "--output", choices=['on', 'off'], help="控制输出开关 (on/off)")
    parser.add_argument("-a", "--address", help="指定 VISA 资源地址 (留空则自动搜索第一个)")
    parser.add_argument("-m", "--measure", action="store_true", help="执行完操作后测量并显示当前电压电流")
    parser.add_argument("-t", "--comm-test", action="store_true", help="仅测试与设备通信 (查询 *IDN? 后退出)")
    parser.add_argument("--settle-time", type=float, default=0.0, help="测量前等待时间 (秒，默认 0)")
    parser.add_argument("--cycle-count", type=int, help="执行周期上下电的次数")
    parser.add_argument("--cycle-on-time", type=float, default=0.0, help="每次上电保持时长 (毫秒，默认 0)")
    parser.add_argument("--cycle-off-time", type=float, default=0.0, help="每次断电保持时长 (毫秒，默认 0)")
    parser.add_argument(
        "--cycle-end-output",
        choices=['on', 'off'],
        default='off',
        help="周期上下电结束后的输出状态 (默认 off)",
    )
    parser.add_argument("--local", action="store_true", help="执行完毕后将设备切换回本地模式 (解锁面板)")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有可用 VISA 资源并退出")
    parser.add_argument("--verbose", action="store_true", help="显示详细执行过程")
    
    args = parser.parse_args()
    if args.settle_time < 0:
        parser.error("--settle-time 不能为负数")
    if args.cycle_count is not None and args.cycle_count < 1:
        parser.error("--cycle-count 必须大于 0")
    if args.cycle_on_time < 0:
        parser.error("--cycle-on-time 不能为负数")
    if args.cycle_off_time < 0:
        parser.error("--cycle-off-time 不能为负数")
    if args.cycle_count is None and (args.cycle_on_time > 0 or args.cycle_off_time > 0):
        parser.error("使用 --cycle-on-time 或 --cycle-off-time 时必须同时指定 --cycle-count")
    if args.cycle_count is None and args.cycle_end_output != 'off':
        parser.error("使用 --cycle-end-output 时必须同时指定 --cycle-count")
    if args.cycle_count is not None and args.output is not None:
        parser.error("--cycle-count 不能与 -o/--output 同时使用")

    # 如果请求列出资源
    if args.list:
        resources = list_resources(verbose=args.verbose)
        if not args.verbose:
            if resources:
                print("可用 VISA 资源:")
                for res in resources:
                    print(f" - {res}")
            else:
                print("未找到可用的 VISA 资源。")
        sys.exit(0)

    # 如果没有传入任何操作参数且不是仅测量，打印帮助
    if (
        args.voltage is None
        and args.current is None
        and args.output is None
        and args.cycle_count is None
        and not args.measure
        and not args.local
        and not args.comm_test
    ):
        parser.print_help()
        print("\n[提示] 请至少指定一个操作参数。")
        print("例如: python power_ctrl_cli.py -v 5.0 -o on")
        sys.exit(0)

    # 1. 确定资源地址
    address = args.address
    if not address:
        # 自动搜索 ITECH IT6722 (VID=0x2EC7, PID=0x6700)
        # 注意: list_resources() 会打印扫描到的资源列表
        resources = list_resources(verbose=(args.verbose and not args.comm_test))
        
        target_vid = "0x2EC7"
        target_pid = "0x6700"
        
        for res in resources:
            # 资源字符串已经过格式化，包含 0xVID 和 0xPID
            if target_vid in res and target_pid in res:
                address = res
                break
        
        if not address:
            if args.comm_test:
                print("failed")
            else:
                print(f"\n错误: 未找到 ITECH IT6722 设备 (VID={target_vid}, PID={target_pid})")
                print("请确认设备已连接并开启。")
                # resources 列表已经在 list_resources() 中打印过了，这里不再重复打印
            sys.exit(1)
    else:
        # print(f"使用指定设备: {address}")
        pass
    
    # 2. 初始化控制器
    ps = PowerSupplyController(address, verbose=(args.verbose and not args.comm_test))
    
    try:
        ps.connect(check_idn=False)

        # 3. 通信测试：连接成功后再做一次 *IDN? 查询确认链路可用
        if args.comm_test:
            ps.instrument.query('*IDN?')
            print("Success")
            return
        
        # 4. 按顺序执行操作
        # 建议顺序：先设置参数，再开输出
        
        if args.voltage is not None:
            ps.set_voltage(args.voltage)
            
        if args.current is not None:
            ps.set_current(args.current)
            
        if args.cycle_count is not None:
            ps.cycle_output(
                args.cycle_count,
                args.cycle_on_time / 1000.0,
                args.cycle_off_time / 1000.0,
                final_output=(args.cycle_end_output == 'on'),
            )
        elif args.output is not None:
            if args.output == 'on':
                ps.set_output(True)
            else:
                ps.set_output(False)

        # 5. 如果请求测量，或者刚刚打开了输出，进行一次测量反馈
        if (
            args.measure
            or (args.output == 'on' and args.verbose)
            or (
                args.cycle_count is not None
                and args.cycle_end_output == 'on'
                and args.verbose
            )
        ):
            if args.settle_time > 0:
                # 给设备时间稳定输出，默认不等待以缩短 step 执行时长
                time.sleep(args.settle_time)
            v = ps.measure_voltage()
            c = ps.measure_current()
            print(f"当前状态: {v:.4f} V, {c:.4f} A")
        elif not args.verbose:
            print("Success")

        # 6. 如果需要切换回本地模式
        if args.local:
            ps.set_local_mode()

    except Exception as e:
        if args.comm_test:
            print("failed")
        else:
            print(f"执行出错: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
        sys.exit(1)
    finally:
        ps.close()

if __name__ == "__main__":
    main()
