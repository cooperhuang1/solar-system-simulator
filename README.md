# 太阳系模拟器 · Solar System Simulator

一个基于 Python + Tkinter 的实时三维太阳系轨道仿真程序，无需任何第三方图形库。

![preview](https://img.shields.io/badge/Python-3.10%2B-blue) ![license](https://img.shields.io/badge/license-MIT-green)

## 功能特性

- 八大行星实时轨道仿真，基于真实 J2000.0 开普勒轨道根数
- 3D 透视投影，支持鼠标拖拽旋转视角、滚轮缩放
- 时间倍率 1~900 天/秒，启动自动同步当前日期
- 焦点跟随模式，可锁定任意行星
- 侧边栏遥测面板：实时显示天体物理参数和轨道数据
- 紧凑/线性两种轨道比例模式

## 快速开始

### 方式一：直接运行（需要 Python 3.10+）

```bash
git clone https://github.com/YOUR_USERNAME/solar-system-simulator.git
cd solar-system-simulator
python -m solar_system_app
```

### 方式二：下载可执行文件

前往 [Releases](../../releases) 页面下载 `SolarSystemSimulator.exe`，双击运行，无需安装 Python。

## 操作说明

| 操作 | 功能 |
|------|------|
| 鼠标拖拽 | 旋转视角 |
| 滚轮 | 缩放 |
| 左键单击 | 选中天体 |
| `Space` | 暂停 / 继续 |
| `+` / `-` | 加速 / 减速时间 |
| `← →` | 切换选中天体 |
| `0` | 聚焦太阳 |
| `1`~`8` | 直接跳转对应行星 |
| `L` | 切换标签显示 |
| `T` | 切换轨迹显示 |
| `F` | 切换跟随模式 |
| `R` | 重置视角 |

## 项目结构

```
solar_system_app/
├── __main__.py       # 入口
├── application.py    # 应用主控，事件绑定，游戏循环
├── models.py         # 数据模型（dataclass）
├── catalog.py        # 天体数据库
├── orbit.py          # 开普勒轨道引擎
├── camera.py         # 相机系统，透视投影
└── renderer.py       # Canvas 渲染引擎
```

## 依赖

仅使用 Python 标准库，无需额外安装。

## License

MIT
