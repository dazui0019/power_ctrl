import pyvisa
import time

class PowerSupplyController:
    def __init__(self, resource_address, verbose=True):
        """
        初始化电源控制器
        :param resource_address: VISA 资源地址 (例如: 'USB0::0xXXXX::0xXXXX::SERIAL::INSTR')
        :param verbose: 是否打印连接信息
        """
        self.rm = pyvisa.ResourceManager()
        self.address = resource_address
        self.verbose = verbose
        self.instrument = None

    def _log(self, message):
        """内部日志方法"""
        if self.verbose:
            print(message)

    def connect(self):
        """连接到电源"""
        try:
            self.instrument = self.rm.open_resource(self.address)
            self._log(f"成功连接到设备: {self.address}")
            # 查询设备标识
            idn = self.instrument.query('*IDN?')
            self._log(f"设备标识: {idn.strip()}")
        except Exception as e:
            # 连接失败属于严重错误，打印详细信息
            print(f"连接失败: {e}")
            raise

    def set_voltage(self, voltage):
        """设置电压"""
        if self.instrument:
            command = f'VOLT {voltage}'
            self.instrument.write(command)
            self._log(f"设置电压为: {voltage}V")

    def set_current(self, current):
        """设置电流限制"""
        if self.instrument:
            command = f'CURR {current}'
            self.instrument.write(command)
            self._log(f"设置电流为: {current}A")

    def output_on(self):
        """打开输出"""
        if self.instrument:
            self.instrument.write('OUTP ON')
            self._log("输出已打开")

    def output_off(self):
        """关闭输出"""
        if self.instrument:
            self.instrument.write('OUTP OFF')
            self._log("输出已关闭")

    def set_output(self, enabled: bool):
        """
        统一控制输出状态
        :param enabled: True 打开, False 关闭
        """
        if enabled:
            self.output_on()
        else:
            self.output_off()

    def set_local_mode(self):
        """
        切换回本地控制模式 (面板按键解锁)
        """
        if self.instrument:
            try:
                # 尝试发送 SCPI 命令切换到本地模式
                self.instrument.write('SYST:LOC')
                self._log("已发送切换本地模式指令 (SYST:LOC)")
            except Exception as e:
                self._log(f"切换本地模式失败: {e}")
                # 某些设备可能需要使用 GTL (Go To Local)
                # 但这取决于具体的接口类型 (GPIB/USB/LAN)

    def measure_voltage(self):
        """读取实际电压"""
        if self.instrument:
            # MEAS:VOLT? 是常用的 SCPI 查询命令
            return float(self.instrument.query('MEAS:VOLT?'))
        return 0.0

    def measure_current(self):
        """读取实际电流"""
        if self.instrument:
            return float(self.instrument.query('MEAS:CURR?'))
        return 0.0

    def close(self):
        """断开连接"""
        if self.instrument:
            self.instrument.close()

def list_resources(verbose=True):
    """列出所有可用的 VISA 资源"""
    rm = pyvisa.ResourceManager()
    if verbose:
        print("扫描到的 VISA 资源:")
    resources = rm.list_resources()
    
    formatted_resources = []
    
    # 已知厂商 ID (Vendor ID) 映射表
    KNOWN_VENDORS = {
        0x2EC7: "ITECH",  # 艾德克斯
        0x0B21: "Yokogawa",
        0x0957: "Agilent/Keysight",
        0x0699: "Tektronix",
        0x1AB1: "Rigol"
    }

    for res in resources:
        display_res = res
        extra_info = ""
        
        # 尝试将 USB 资源的 VID/PID 格式化为十六进制显示 (例如: USB0::0x1234::0x5678::...)
        if res.startswith('USB'):
            parts = res.split('::')
            if len(parts) >= 3:
                try:
                    # 处理 Vendor ID (parts[1])
                    vid_val = int(parts[1], 0) # 支持 0x 前缀或纯数字
                    if not parts[1].lower().startswith('0x'):
                        parts[1] = f"0x{vid_val:04X}"
                    
                    # 尝试识别厂商
                    if vid_val in KNOWN_VENDORS:
                        extra_info = f" ({KNOWN_VENDORS[vid_val]})"

                    # 处理 Product ID (parts[2])
                    if not parts[2].lower().startswith('0x'):
                        parts[2] = f"0x{int(parts[2], 0):04X}"
                        
                    display_res = "::".join(parts)
                except ValueError:
                    # 如果转换失败(非数字)，保持原样
                    pass
        
        if verbose:
            print(f" - {display_res}{extra_info}")
        formatted_resources.append(display_res)
        
    return formatted_resources

def test_voltage_control_cycle(ps, voltage_1, voltage_2, duration=2):
    """
    演示功能：修改电压和控制电压输出和关断
    流程：设置电压1 -> 打开 -> 延时 -> 修改为电压2 -> 延时 -> 关闭
    """
    print(f"\n=== 开始电压控制测试循环 ===")
    
    # 1. 设置初始电压并打开
    print(f"Step 1: 设置初始电压 {voltage_1}V 并打开输出")
    ps.set_voltage(voltage_1)
    ps.set_output(True)
    time.sleep(1)
    print(f"  -> 读取: {ps.measure_voltage():.3f}V")
    
    time.sleep(duration)
    
    # 2. 运行中修改电压
    print(f"Step 2: 修改电压为 {voltage_2}V (输出保持打开)")
    ps.set_voltage(voltage_2)
    time.sleep(1)
    print(f"  -> 读取: {ps.measure_voltage():.3f}V")
    
    time.sleep(duration)
    
    # 3. 关闭输出
    print("Step 3: 关闭输出")
    ps.set_output(False)
    print("=== 测试循环结束 ===\n")

def interactive_control(ps):
    """
    交互式控制模式
    """
    print("\n=== 进入交互式控制模式 ===")
    print("可用命令:")
    print("  v <数值>   : 设置电压 (例如: v 5.0)")
    print("  c <数值>   : 设置电流 (例如: c 1.0)")
    print("  on         : 打开输出")
    print("  off        : 关闭输出")
    print("  loc        : 切换到本地模式 (解锁面板)")
    print("  m          : 测量当前电压和电流")
    print("  l          : 列出所有可用资源")
    print("  q          : 退出")
    print("============================\n")

    while True:
        try:
            user_input = input("CMD> ").strip().lower()
            
            if not user_input:
                continue
                
            parts = user_input.split()
            cmd = parts[0]
            
            if cmd in ['q', 'quit', 'exit']:
                print("退出交互模式...")
                break
                
            elif cmd == 'v':
                if len(parts) > 1:
                    try:
                        volts = float(parts[1])
                        ps.set_voltage(volts)
                    except ValueError:
                        print("错误: 电压值必须是数字")
                else:
                    print("错误: 请提供电压值 (例如: v 5.0)")
                    
            elif cmd == 'c':
                if len(parts) > 1:
                    try:
                        amps = float(parts[1])
                        ps.set_current(amps)
                    except ValueError:
                        print("错误: 电流值必须是数字")
                else:
                    print("错误: 请提供电流值 (例如: c 1.0)")
                    
            elif cmd == 'on':
                ps.set_output(True)
                
            elif cmd == 'off':
                ps.set_output(False)

            elif cmd in ['loc', 'local']:
                ps.set_local_mode()
                
            elif cmd in ['m', 'meas', 'measure']:
                v = ps.measure_voltage()
                c = ps.measure_current()
                print(f"测量结果: {v:.4f} V, {c:.4f} A")
                
            elif cmd in ['l', 'list']:
                list_resources()
                
            else:
                print(f"未知命令: {cmd}")
                
        except KeyboardInterrupt:
            print("\n检测到中断，正在退出...")
            break
        except Exception as e:
            print(f"执行出错: {e}")

if __name__ == "__main__":
    # 1. 首先列出资源，帮助找到正确的地址
    available_resources = list_resources()
    
    if not available_resources:
        print("\n未找到任何 VISA 设备。请确保设备已连接并安装了驱动。")
        # 模拟一个地址用于演示代码逻辑
        # power_supply_address = 'USB0::0x1234::0x5678::SN123456::INSTR'
    else:
        # 自动搜索 ITECH IT6722 设备 (0x2EC7::0x6700)
        target_vid = "0x2EC7"
        target_pid = "0x6700"
        power_supply_address = None

        print(f"\n正在搜索目标设备 ITECH (VID={target_vid}, PID={target_pid})...")
        
        for res in available_resources:
            # 简单检查资源字符串中是否包含目标 VID 和 PID
            # 注意：list_resources 返回的字符串已经是格式化过的 (含 0x 前缀)
            if target_vid.upper() in res.upper() and target_pid.upper() in res.upper():
                power_supply_address = res
                print(f"-> 找到目标设备: {res}")
                break
        
        if power_supply_address:
            print(f"\n尝试连接到: {power_supply_address}")
            ps = PowerSupplyController(power_supply_address)
            try:
                ps.connect()
                # 进入交互式控制模式
                interactive_control(ps)
            except Exception as e:
                print(f"运行过程中出错: {e}")
            finally:
                ps.close()
        else:
            print(f"错误: 未找到目标设备 (VID={target_vid}, PID={target_pid})")
            print("可用设备列表:")
            for res in available_resources:
                print(f" - {res}")