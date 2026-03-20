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

def add_hidden_alias(container, *option_strings, dest, **kwargs):
    """为旧参数名保留兼容别名，但不在帮助中显示。"""
    kwargs.setdefault("help", argparse.SUPPRESS)
    kwargs.setdefault("default", argparse.SUPPRESS)
    container.add_argument(*option_strings, dest=dest, **kwargs)

def main():
    parser = argparse.ArgumentParser(
        description="电源控制命令行工具 (CLI)",
        epilog=(
            "示例: python power_ctrl_cli.py -v 12.0 -c 2.0 -o on / "
            "python power_ctrl_cli.py -v 12.0 --ramp-from 26.0 "
            "--ramp-step 0.1 --ramp-interval-ms 1000"
        )
    )

    basic_group = parser.add_argument_group("基础控制")
    ramp_group = parser.add_argument_group("斜坡调压")
    cycle_group = parser.add_argument_group("周期上下电")
    other_group = parser.add_argument_group("其他")

    basic_group.add_argument("-v", "--voltage", type=float, help="设置电压，或作为斜坡调压的目标电压 (V)")
    basic_group.add_argument("-c", "--current", type=float, help="设置电流限制 (A)")
    basic_group.add_argument("-o", "--output", choices=['on', 'off'], help="控制输出开关 (on/off)")

    ramp_group.add_argument("--ramp-from", dest="ramp_from", type=float, help="斜坡调压起始电压 (V)")
    ramp_group.add_argument("--ramp-step", dest="ramp_step", type=float, help="斜坡调压每步变化电压 (V，默认 0.1)")
    ramp_group.add_argument("--ramp-interval-ms", dest="ramp_interval_ms", type=float, help="斜坡调压每步等待时间 (毫秒，默认 1000)")
    add_hidden_alias(ramp_group, "--ramp-start-voltage", dest="ramp_from", type=float)
    add_hidden_alias(ramp_group, "--ramp-step-voltage", dest="ramp_step", type=float)
    add_hidden_alias(ramp_group, "--ramp-step-time", dest="ramp_interval_ms", type=float)

    cycle_group.add_argument("--cycles", dest="cycles", type=int, help="周期上下电执行次数")
    cycle_group.add_argument("--cycle-on-ms", dest="cycle_on_ms", type=float, help="每次上电保持时长 (毫秒，默认 0)")
    cycle_group.add_argument("--cycle-off-ms", dest="cycle_off_ms", type=float, help="每次断电保持时长 (毫秒，默认 0)")
    cycle_group.add_argument("--cycle-end", dest="cycle_end", choices=['on', 'off'], default='off', help="周期结束后的输出状态 (默认 off)")
    add_hidden_alias(cycle_group, "--cycle-count", dest="cycles", type=int)
    add_hidden_alias(cycle_group, "--cycle-on-time", dest="cycle_on_ms", type=float)
    add_hidden_alias(cycle_group, "--cycle-off-time", dest="cycle_off_ms", type=float)
    add_hidden_alias(cycle_group, "--cycle-end-output", dest="cycle_end", choices=['on', 'off'])

    other_group.add_argument("-a", "--address", help="指定 VISA 资源地址 (留空则自动搜索第一个)")
    other_group.add_argument("-m", "--measure", action="store_true", help="执行完操作后测量并显示当前电压电流")
    other_group.add_argument("-t", "--comm-test", action="store_true", help="仅测试与设备通信 (查询 *IDN? 后退出)")
    other_group.add_argument("--settle-time", type=float, default=0.0, help="测量前等待时间 (秒，默认 0)")
    other_group.add_argument("--local", action="store_true", help="执行完毕后将设备切换回本地模式 (解锁面板)")
    other_group.add_argument("-l", "--list", action="store_true", help="列出所有可用 VISA 资源并退出")
    other_group.add_argument("--verbose", action="store_true", help="显示详细执行过程")
    
    args = parser.parse_args()
    ramp_step = args.ramp_step if args.ramp_step is not None else 0.1
    ramp_interval_ms = args.ramp_interval_ms if args.ramp_interval_ms is not None else 1000.0
    cycle_on_ms = args.cycle_on_ms if args.cycle_on_ms is not None else 0.0
    cycle_off_ms = args.cycle_off_ms if args.cycle_off_ms is not None else 0.0

    if args.settle_time < 0:
        parser.error("--settle-time 不能为负数")
    if args.ramp_from is None and (args.ramp_step is not None or args.ramp_interval_ms is not None):
        parser.error("使用 --ramp-step 或 --ramp-interval-ms 时必须同时指定 --ramp-from")
    if args.ramp_from is not None and args.voltage is None:
        parser.error("使用 --ramp-from 时必须同时指定 -v/--voltage 作为目标电压")
    if ramp_step <= 0:
        parser.error("--ramp-step 必须大于 0")
    if ramp_interval_ms < 0:
        parser.error("--ramp-interval-ms 不能为负数")
    if args.cycles is not None and args.cycles < 1:
        parser.error("--cycles 必须大于 0")
    if cycle_on_ms < 0:
        parser.error("--cycle-on-ms 不能为负数")
    if cycle_off_ms < 0:
        parser.error("--cycle-off-ms 不能为负数")
    if args.cycles is None and (cycle_on_ms > 0 or cycle_off_ms > 0):
        parser.error("使用 --cycle-on-ms 或 --cycle-off-ms 时必须同时指定 --cycles")
    if args.cycles is None and args.cycle_end != 'off':
        parser.error("使用 --cycle-end 时必须同时指定 --cycles")
    if args.cycles is not None and args.output is not None:
        parser.error("--cycles 不能与 -o/--output 同时使用")

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
        and args.cycles is None
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
        
        if args.current is not None:
            ps.set_current(args.current)

        if args.ramp_from is not None and args.output == 'on':
            ps.set_output(True)

        if args.ramp_from is not None:
            ps.ramp_voltage(
                args.ramp_from,
                args.voltage,
                step_voltage=ramp_step,
                step_interval=ramp_interval_ms / 1000.0,
            )
        elif args.voltage is not None:
            ps.set_voltage(args.voltage)
            
        if args.cycles is not None:
            ps.cycle_output(
                args.cycles,
                cycle_on_ms / 1000.0,
                cycle_off_ms / 1000.0,
                final_output=(args.cycle_end == 'on'),
            )
        elif args.output is not None and not (args.ramp_from is not None and args.output == 'on'):
            if args.output == 'on':
                ps.set_output(True)
            else:
                ps.set_output(False)

        # 5. 如果请求测量，或者刚刚打开了输出，进行一次测量反馈
        if (
            args.measure
            or (args.output == 'on' and args.verbose)
            or (
                args.cycles is not None
                and args.cycle_end == 'on'
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

    except KeyboardInterrupt:
        if not args.comm_test:
            print("\n操作已被 Ctrl+C 中断。")
            if args.local:
                try:
                    ps.set_local_mode()
                except Exception:
                    pass
        sys.exit(130)
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
