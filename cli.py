"""
命令行界面模块
处理命令行参数解析和用户交互
"""

import argparse
import os
import sys
from typing import Dict, Any, Optional


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器
    
    Returns:
        配置好的ArgumentParser对象
    """
    parser = argparse.ArgumentParser(
        description='AppImage转DEB/RPM包转换器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s app.AppImage --format deb --output ./packages/
  %(prog)s app.AppImage --format rpm --maintainer "Your Name <email@example.com>"
  %(prog)s app.AppImage --format both --config config.json
        """
    )
    
    # 必需参数
    parser.add_argument(
        'appimage',
        help='要转换的AppImage文件路径'
    )
    
    # 输出格式
    parser.add_argument(
        '--format', '-f',
        choices=['deb', 'rpm', 'both'],
        default='deb',
        help='输出包格式 (默认: deb)'
    )
    
    # 输出目录
    parser.add_argument(
        '--output', '-o',
        default='./output',
        help='输出目录路径 (默认: ./output)'
    )
    
    # 包配置选项
    config_group = parser.add_argument_group('包配置选项')
    
    config_group.add_argument(
        '--maintainer', '-m',
        help='维护者信息 (格式: "姓名 <邮箱>")'
    )

    config_group.add_argument(
        '--section',
        help='DEB包分类 (未配置时为 misc)'
    )

    config_group.add_argument(
        '--priority',
        help='DEB包优先级 (未配置时为 optional)'
    )

    config_group.add_argument(
        '--depends',
        nargs='*',
        help='依赖包列表 (用空格分隔，覆盖配置文件中的DEB和RPM依赖)'
    )
    
    config_group.add_argument(
        '--license',
        help='软件许可证'
    )
    
    config_group.add_argument(
        '--homepage',
        help='项目主页URL'
    )
    
    config_group.add_argument(
        '--architecture', '--arch',
        help='目标架构 (如: amd64, x86_64)'
    )
    
    # 配置文件
    parser.add_argument(
        '--config', '-c',
        help='配置文件路径 (JSON格式)'
    )
    
    # 其他选项
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细输出'
    )
    
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='保留临时文件 (用于调试)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='AppImage转换器 1.0.0'
    )
    
    return parser


def load_config_file(config_path: str) -> Dict[str, Any]:
    """
    从JSON文件加载配置
    
    Args:
        config_path: 配置文件路径
    
    Returns:
        配置字典
    """
    import json
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"错误：配置文件不存在: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误：配置文件格式无效: {e}")
        sys.exit(1)


def merge_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    合并命令行参数和配置文件
    
    Args:
        args: 解析后的命令行参数
    
    Returns:
        合并后的配置字典
    """
    config = {}
    
    # 如果指定了配置文件，先加载配置文件
    if args.config:
        config = load_config_file(args.config)
    
    # 命令行参数覆盖配置文件中的设置
    if args.maintainer:
        config['maintainer'] = args.maintainer

    # 保留原有参数，并确保显式命令行参数优先于新的嵌套配置。
    if args.section is not None:
        config['section'] = args.section
        config.setdefault('deb', {})['section'] = args.section

    if args.priority is not None:
        config['priority'] = args.priority
        config.setdefault('deb', {})['priority'] = args.priority

    if args.depends is not None:
        config['depends'] = args.depends
        config['requires'] = args.depends
        config.setdefault('deb', {})['depends'] = args.depends
        config.setdefault('rpm', {})['requires'] = args.depends
    
    if args.license:
        config['license'] = args.license
    
    if args.homepage:
        config['homepage'] = args.homepage
    
    if args.architecture:
        config['architecture'] = args.architecture
    
    return config


def validate_args(args: argparse.Namespace) -> None:
    """
    验证命令行参数
    
    Args:
        args: 解析后的命令行参数
    """
    # 检查AppImage文件是否存在
    if not os.path.isfile(args.appimage):
        print(f"错误：AppImage文件不存在: {args.appimage}")
        sys.exit(1)
    
    # 检查AppImage文件是否可执行
    if not os.access(args.appimage, os.X_OK):
        print(f"警告：AppImage文件不可执行: {args.appimage}")
    
    # 创建输出目录
    if not os.path.exists(args.output):
        try:
            os.makedirs(args.output, exist_ok=True)
        except OSError as e:
            print(f"错误：无法创建输出目录 {args.output}: {e}")
            sys.exit(1)
    
    # 验证维护者信息格式
    if args.maintainer:
        import re
        if not re.match(r'^.+\s+<.+@.+>$', args.maintainer):
            print(f"警告：维护者信息格式可能不正确: {args.maintainer}")
            print("建议格式: '姓名 <邮箱@域名.com>'")


def print_summary(args: argparse.Namespace, config: Dict[str, Any]) -> None:
    """
    打印转换任务摘要
    
    Args:
        args: 解析后的命令行参数
        config: 合并后的配置
    """
    print("=" * 60)
    print("AppImage转换器 - 任务摘要")
    print("=" * 60)
    print(f"输入文件: {args.appimage}")
    print(f"输出格式: {args.format}")
    print(f"输出目录: {args.output}")
    
    if config:
        print("\n包配置:")
        _print_config_dict(config, indent="  ")
    
    print("=" * 60)


def _print_config_dict(config: Dict[str, Any], indent: str) -> None:
    """
    递归打印配置字典，嵌套子对象（deb/rpm）缩进显示
    
    Args:
        config: 配置字典
        indent: 缩进字符串
    """
    for key, value in config.items():
        if isinstance(value, dict):
            print(f"{indent}{key}:")
            _print_config_dict(value, indent + "  ")
        elif value:
            print(f"{indent}{key}: {value}")


def parse_arguments() -> tuple[argparse.Namespace, Dict[str, Any]]:
    """
    解析命令行参数并返回配置
    
    Returns:
        元组 (解析后的参数, 合并后的配置)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # 验证参数
    validate_args(args)
    
    # 合并配置
    config = merge_config(args)
    
    # 如果启用详细输出，打印摘要
    if args.verbose:
        print_summary(args, config)
    
    return args, config 
