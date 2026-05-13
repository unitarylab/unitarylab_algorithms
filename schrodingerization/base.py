from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.collections import PolyCollection
import ast

def create_algorithm_logger(
    algorithm_file: str, 
    log_name: str = None,
    log_dir: str = None,
    console_output: bool = True,
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 5,
    force_reconfigure: bool = False,
) -> logging.Logger:
    """
    为算法创建独立的日志记录器，日志文件保存在算法文件夹下
    
    :param algorithm_file: 算法文件路径，通常传入 __file__
    :param log_name: 日志名称，默认使用算法文件夹名
    :param log_dir: 日志目录，默认使用算法文件所在目录
    :param console_output: 是否输出到控制台，默认 True
    :param max_bytes: 单个日志文件最大字节数，默认 50MB
    :param backup_count: 保留的备份日志文件数量，默认 5
    :param force_reconfigure: 是否强制重新配置（热重载时使用），默认 False
    :return: 配置好的 Logger 实例
    
    使用示例:
        # 基本用法 - 日志保存在算法文件夹下
        logger = create_algorithm_logger(__file__)
        logger.info("算法开始执行")
        
        # 指定日志目录
        logger = create_algorithm_logger(__file__, log_dir="/path/to/logs")
        
        # 禁用控制台输出（仅写入文件）
        logger = create_algorithm_logger(__file__, console_output=False)
    """
    # 获取算法所在目录（确保使用绝对路径）
    algo_path = Path(algorithm_file).resolve()
    if not algo_path.is_file():
        algo_dir = algo_path
    else:
        algo_dir = algo_path.parent

    # 确定日志目录
    if log_dir:
        actual_log_dir = Path(log_dir).resolve()
    else:
        actual_log_dir = algo_dir
    
    # 确保日志目录存在
    actual_log_dir.mkdir(parents=True, exist_ok=True)
    
    # 默认使用文件夹名作为日志名称
    if log_name is None:
        log_name = algo_dir.name
    
    # 创建 logger
    logger_name = f"algorithm.{log_name}"
    logger = logging.getLogger(logger_name)
    
    # 检查是否已配置，以及配置的路径是否正确
    configured_path = getattr(logger, "_algo_log_dir", None)
    if not force_reconfigure and getattr(logger, "_algo_configured", False):
        # 如果日志目录发生变化，需要重新配置
        if configured_path == str(actual_log_dir):
            return logger
        # 路径变化，需要重新配置
    
    # 标记为已配置，并记录日志目录路径
    logger._algo_configured = True
    logger._algo_log_dir = str(actual_log_dir)
    
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers.clear()
    
    # 日志格式 - 包含时间戳和算法名称
    formatter = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d [%(levelname)-5s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # 沙箱容器中 stdout 会被宿主机 _stream_logs_to_file 再次写入 algorithm.log，
    # 而 RotatingFileHandler 也直接写入同一个文件，导致日志重复。
    # 检测沙箱环境后跳过 StreamHandler，仅保留文件写入。
    _in_sandbox = (
        os.environ.get("TASK_ID") is not None
        and os.environ.get("ALGO_PARAMS") is not None
    )
    if console_output and not _in_sandbox:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 算法日志文件 - 保存在算法文件夹内
    log_file = actual_log_dir / "algorithm.log"
    try:
        file_handler = RotatingFileHandler(
            filename=str(log_file),  # 确保路径是字符串
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        # 调试：输出日志文件路径到控制台
        print(f"[AlgoLogger] 创建日志文件: {log_file}")
    except (OSError, PermissionError) as e:
        # 如果无法创建日志文件，记录到控制台
        print(f"[AlgoLogger] 无法创建日志文件 {log_file}: {e}")
        if console_output:
            logger.warning(f"无法创建日志文件 {log_file}: {e}")
    
    # 错误日志文件 - 单独记录错误
    error_log_file = actual_log_dir / "algorithm_error.log"
    try:
        error_handler = RotatingFileHandler(
            filename=str(error_log_file),  # 确保路径是字符串
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    except (OSError, PermissionError) as e:
        if console_output:
            logger.warning(f"无法创建错误日志文件 {error_log_file}: {e}")
    
    return logger

class BaseAlgorithm(ABC):
    """所有方程算法模块的基类"""
    
    def __init__(self):
        self.color = "#DBB924"
        self.algo_dir = None
        self.logger = None

    @abstractmethod
    def run(self, params: str) -> Dict[str, Any]:
        """
        执行算法逻辑
        :param params: 输入参数，JSON 字符串格式
        :return: 算法执行结果字典
        """
        pass

    def parse_params(self, params) -> Any:
        """
        解析参数，兼容 JSON 字符串和已解析的 dict/list。
        :param params: JSON 字符串或已解析的 Python 对象
        :return: 解析后的 Python 对象
        :raises ValueError: JSON 解析失败时抛出
        """
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except (json.JSONDecodeError, ValueError):
                params = ast.literal_eval(params)
        return params

    def set_plt(self, color='white', font_num=2):
        # plt.rcParams.update({
        #     "font.family": 'Times New Roman',
        #     # "font.size": 18 * font_num,           # 全局默认字体大小
        #     # "axes.titlesize": 20 * font_num,      # 标题字体大小
        #     # "axes.labelsize": 18 * font_num,      # 坐标轴标签字体大小
        #     # "xtick.labelsize": 16 * font_num,     # x轴刻度标签字体大小
        #     # "ytick.labelsize": 16 * font_num,     # y轴刻度标签字体大小
        #     # "legend.fontsize": 16 * font_num,     # 图例字体大小
        # })
            
        plt.rcParams.update({
            "text.color": color,       # 标题、坐标轴标签等
            "axes.labelcolor": color,  # 坐标轴标签
            "axes.edgecolor": color,   # 坐标轴边框
            "xtick.color": color,      # x轴刻度标签
            "ytick.color": color,      # y轴刻度标签
        })

    def _plot_1d(
        self,
        ax,
        x,
        u,
        label = 'u'
    ):
        """
        在输入的 ax 上画图

        :param ax: matplotlib 的 axes 对象
        :param name: 图标题
        :param x: 空间网格点
        :param u: 最终时刻的温度分布
        :param label: 标签
        """

        # ax背景透明
        ax.set_facecolor('none')

        # 绘制结果
        ax.plot(x, u, '#1F52F0', linewidth=2, label=label)
        
        # 创建渐变填充效果
        self._add_gradient_fill(ax, x, u)

        # 设置标题和标签
        ax.set_xlabel("x", fontsize=12)
        ax.set_ylabel(label, fontsize=12)
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)

    def _add_gradient_fill(self, ax, x, y, alpha_start=1, alpha_end=0.15):
        """
        添加垂直渐变填充效果
        
        :param ax: matplotlib 的 axes 对象
        :param x: x坐标
        :param y: y坐标
        :param alpha_start: 起始透明度（曲线处）
        :param alpha_end: 结束透明度（底部）
        """
        # 创建渐变色映射 - 从蓝色到透明（垂直方向）
        colors = [(0.1216, 0.3216, 0.9412, alpha_start), (0.1216, 0.3216, 0.9412, alpha_end)]
        cmap = LinearSegmentedColormap.from_list('gradient_fill', colors, N=256)
        
        # 获取坐标轴范围
        ymin, ymax = ax.get_ylim()
        xmin, xmax = ax.get_xlim()
        
        # 创建垂直渐变图像（从上到下：1->0，即从曲线处到底部）
        gradient = np.linspace(1, 0, 256).reshape(-1, 1)
        
        # 绘制渐变背景
        im = ax.imshow(gradient, aspect='auto', cmap=cmap, 
                      extent=[xmin, xmax, ymin, ymax], 
                      origin='lower', zorder=0)
        
        # 创建曲线路径用于裁剪
        from matplotlib.path import Path
        from matplotlib.patches import PathPatch
        
        # 创建闭合路径（从曲线到底部）
        vertices = [(x[0], 0)] + [(x[i], y[i]) for i in range(len(x))] + [(x[-1], 0)]
        codes = [Path.MOVETO] + [Path.LINETO] * (len(vertices) - 1)
        path = Path(vertices, codes)
        
        # 创建裁剪路径
        patch = PathPatch(path, facecolor='none', edgecolor='none', zorder=1)
        ax.add_patch(patch)
        
        # 将渐变图像裁剪到曲线下方
        im.set_clip_path(patch)

    def _generate_solution_plot_1d(
        self,
        name: str,
        x,
        u,
        label = 'u',
        xlabel = 'x',
        ylabel = 'Value',
        refcolor='black',
        format: str = 'svg',
        combine_in_one_plot: bool = False
    ) -> str:
        """
        生成计算结果图并保存到algo_dir下
        """

        color = "#DBB924"

        self.set_plt(color)
        
        filepath = os.path.join(self.algo_dir, f"{name.replace(' ', '_')}_solution.{format}")
        
        if isinstance(u, dict):
            solutions = u
        else:
            solutions = {label: u}

        num_solutions = len(solutions)

        if combine_in_one_plot and num_solutions > 1:
            #只创建一个子图
            fig, axes = plt.subplots(figsize=(10, 6), dpi=300)

            colors = [
                '#1F52F0',  # 主要蓝色
                '#FF9800',  # 橙色
                "#FFD92F",  # 黄色
                '#4CAF50',  # 绿色
                '#9C27B0',  # 紫色
                '#00BCD4',  # 青色
            ]

            # 定义线宽列表
            line_widths = [
                2.5,  # 第一条线：粗
                1.5,  # 第二条线：中
                1.0,  # 第三条线：细
                1.5,  # 第四条线：中
                2.0,  # 第五条线：粗
                1.0   # 第六条线：细
            ]
            for idx, (label_key, u_value) in enumerate(solutions.items()):
                line_color = colors[idx % len(colors)]
            
                # 获取线宽，如果列表不够长则循环使用
                line_width = line_widths[idx % len(line_widths)]
            
                axes.set_facecolor('none')
            
                # 绘制曲线
                axes.plot(x, u_value, line_color, linewidth=line_width, label=label_key)

                self._add_gradient_fill(axes, x, u_value)
      
            # 设置标题和标签
            axes.set_title(name)
            axes.set_xlabel(xlabel, fontsize=12)
            axes.set_ylabel(ylabel, fontsize=12)
            axes.legend(loc="upper right")
            axes.grid(True, alpha=0.3)

            # 根据主题决定保存的背景色
            if color == 'white':  # 暗色主题
                save_facecolor = 'black'
            else:  # 亮色主题
                save_facecolor = 'white'

            fig.savefig(filepath, format=format, bbox_inches="tight", 
                edgecolor='none', transparent=True)
            plt.close(fig)
            
        else:
            if num_solutions == 1:
                fig, axes = plt.subplots(figsize=(10, 6), dpi=300)
                axes = [axes]
            else:
                fig, axes = plt.subplots(num_solutions, 1, figsize=(10, 6 * num_solutions), dpi=300)

            for idx, (label_key, u_value) in enumerate(solutions.items()):
                self._plot_1d(axes[idx], x, u_value, label_key)
            
            # 标题
            axes[0].set_title(name)
            axes[0].set_xlabel(xlabel)
            axes[0].set_ylabel(ylabel)

            fig.savefig(filepath, format=format, bbox_inches="tight", transparent=True)
            plt.close(fig)
            
        self.logger.debug(f"Solution plot saved to: {filepath}")
        return filepath
    
    def _generate_circuit_plots(
        self,
        name: str,
        qc,
        H1 = None,
        H2 = None,
        format: str = 'svg'
    ) -> list:
        """
        生成多个量子电路图并保存到算法文件夹

        :param qc: 量子电路
        :param H1: 量子电路
        :param H2: 量子电路
        :param name: 图标题
        :return: 保存的文件信息列表
        """
        
        circuit_files = []
        base_name = name.replace(" ", "_")
        
        # 生成完整电路图
        filename1 = f'{base_name}_circuit_full.{format}'
        circuit_path1 = os.path.join(self.algo_dir, filename1)
        qc.draw(filename=circuit_path1, title=f"{name} (Schro)")
        circuit_files.append({
            "format": format,
            "filename": filename1,
        })
        
        # 生成H1电路图
        if H1:
            filename2 = f'{base_name}_circuit_H1.{format}'
            circuit_path2 = os.path.join(self.algo_dir, filename2)
            H1.decompose().draw(filename=circuit_path2, title=f"{name} (H1)")
            circuit_files.append({
                "format": format,
                "filename": filename2,
            })
        
        # 生成H2电路图
        if H2:
            filename3 = f'{base_name}_circuit_H2.{format}'
            circuit_path3 = os.path.join(self.algo_dir, filename3)
            H2.decompose().draw(filename=circuit_path3, title=f"{name} (H2)")
            circuit_files.append({
                "format": format,
                "filename": filename3,
            })

        self.logger.debug(f"Quantum circuit diagrams saved to: {self.algo_dir}")
        self.logger.info(f"Generated {len(circuit_files)} quantum circuit diagrams")
        return circuit_files

    def _generate_solution_plot(
        self,
        name: str,
        x,
        u,
        label = 'u',
        xlabel = 'x',
        ylabel = 'Value',
        refcolor='black',
        format: str = 'svg',
        combine_in_one_plot: bool = False
    ) -> str:
        """
        生成计算结果图并保存到algo_dir下
        """

        return self._generate_solution_plot_1d(name, x, u, label, xlabel, ylabel, refcolor, format, combine_in_one_plot)    
