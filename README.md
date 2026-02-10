# 电源控制脚本 (Power Supply Control Scripts)

本目录包含用于通过 PyVISA 控制可编程电源（支持 SCPI 指令）的 Python 脚本。

已在`ITECH IT6722`上测试通过。

## 📋 环境要求 (Requirements)

*   Python 3.x
*   `pyvisa`
*   `pyvisa-py` (可选，作为纯 Python 后端)
*   NI-VISA 驱动 (可选，推荐用于 Windows)

### 使用 uv 管理环境 (推荐)

本项目推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理和运行。

1. **运行脚本：**
   使用 `uv run` 来执行脚本：
   ```bash
   uv run power_supply_control.py
   ```

## 🐧 Linux USB 权限配置 (Linux Setup)

如果使用 USB 连接且无法识别设备（`lsusb` 可见但脚本无法列出），通常是权限问题。请按以下步骤添加 `udev` 规则：

1. **创建规则文件** (针对 ITECH IT6722 `2ec7:6700`)：
   ```bash
   echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="2ec7", ATTRS{idProduct}=="6700", MODE="0666"' | sudo tee /etc/udev/rules.d/99-itech.rules
   ```

2. **重载规则并重新插拔设备**：
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```
   (执行完后请拔掉 USB 再重新插入)

## 📂 文件说明 (Files)

### 1. `power_supply_control.py`
核心控制库及交互式工具。包含 `PowerSupplyController` 类，封装了常用的 SCPI 指令（VOLT, CURR, OUTP, MEAS 等）。

**功能特点：**
*   **自动设备识别**：增强了 `list_resources` 功能，能够解析 USB ID 并显示常见仪器厂商（如 ITECH, Yokogawa, Keysight, Tektronix, Rigol 等）。
*   **智能连接**：默认优先搜索并连接 **ITECH IT6722** 电源 (VID: 0x2EC7, PID: 0x6700)。若未找到特定设备，将列出所有可用资源。

**直接运行模式（交互式）：**
直接运行该脚本将尝试连接目标电源并进入交互式命令行界面，方便手动调试。
```bash
uv run power_supply_control.py
```
**支持的交互命令：**
*   `v <数值>` : 设置电压 (例如 `v 12.0`)
*   `c <数值>` : 设置电流限制 (例如 `c 2.0`)
*   `on` / `off`: 打开或关闭输出
*   `loc`      : 切换到本地模式 (解锁前面板按键)
*   `m` : 测量当前电压和电流
*   `l` : 列出所有可用资源
*   `q` : 退出

### 2. `power_ctrl_cli.py`
命令行参数工具。专为自动化脚本或批处理设计，通过命令行参数直接执行操作并退出。

**特点：**
*   **安全连接**：默认仅自动连接 **ITECH IT6722** 设备。如需控制其他设备，需明确指定地址。
*   **静默模式**：默认情况下，执行成功仅输出 `Success`（除非指定 `-m` 测量），执行失败输出详细错误。
*   **本地模式切换**：使用 `--local` 参数可在操作完成后自动解锁电源面板按键（退出 RMT 模式）。
*   **详细模式**：使用 `--verbose` 参数可查看详细执行过程。

**使用示例：**

*   **列出所有可用设备：**
    ```bash
    uv run power_ctrl_cli.py -l
    ```

*   **设置 5V，限流 1A 并打开输出（详细模式）：**
    ```bash
    uv run power_ctrl_cli.py -v 5.0 -c 1.0 -o on --verbose
    ```

*   **关闭输出：**
    ```bash
    uv run power_ctrl_cli.py -o off
    ```

*   **设置 5V，限流 1A，打开输出，并在结束后解锁面板：**
    ```bash
    uv run power_ctrl_cli.py -v 5.0 -c 1.0 -o on --local
    ```

*   **仅测量当前状态：**
    ```bash
    uv run power_ctrl_cli.py -m
    ```

*   **查看帮助：**
    ```bash
    uv run power_ctrl_cli.py -h
    ```

## ⚠️ 注意事项
1. **设备连接策略**：
    *   `power_supply_control.py`：优先自动连接 ITECH IT6722 设备。
    *   `power_ctrl_cli.py`：**强制**自动搜索并连接 ITECH IT6722 设备。如果需要控制其他设备，**必须**使用 `-a` 参数指定地址。
2. 确保电源设备已开启并连接到电脑（USB/串口/网口）。