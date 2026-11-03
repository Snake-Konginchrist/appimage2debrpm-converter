#!/usr/bin/env python3
"""
AppImage转DEB/RPM包转换器
主程序入口点

使用方法:
    python main.py app.AppImage --format deb --output ./packages/
    python main.py app.AppImage --format rpm --maintainer "Your Name <email@example.com>"
    python main.py app.AppImage --format both --config config.json
"""

import sys
import os
import traceback
from typing import List

# 添加当前目录到Python路径，以便导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import parse_arguments
from core.appimage import AppImageExtractor
from local_deb.deb_builder import DebBuilder
from local_rpm.rpm_builder import RpmBuilder


def convert_to_deb(extractor: AppImageExtractor, output_dir: str, config: dict) -> str:
    """
    转换AppImage为DEB包
    
    Args:
        extractor: AppImage提取器
        output_dir: 输出目录
        config: 包配置
    
    Returns:
        生成的DEB包路径
    """
    print("开始构建DEB包...")
    
    # 创建DEB构建器
    deb_builder = DebBuilder(extractor.info, extractor.extracted_dir)
    deb_builder.set_package_config(config)
    
    print(f"  包名: {deb_builder.get_package_name(preserve_case=True)}")
    print(f"  版本: {deb_builder.get_package_version('deb')}")
    print(f"  架构: {deb_builder.get_architecture('deb')}")
    
    try:
        # 准备构建目录
        deb_builder.prepare_build_directory()
        print("  [1/5] 准备构建目录完成")
        
        # 创建包结构
        deb_builder.create_package_structure()
        print("  [2/5] 创建包目录结构完成")
        
        # 复制应用程序文件
        deb_builder.copy_application_files()
        print("  [3/5] 复制应用程序文件完成")
        
        # 生成元数据文件
        deb_builder.generate_metadata_files()
        print("  [4/5] 生成元数据文件完成")
        
        # 构建包
        deb_path = deb_builder.build_package(output_dir)
        print(f"  [5/5] 构建DEB包完成: {deb_path}")
        
        return deb_path
        
    finally:
        # 清理临时文件
        deb_builder.cleanup()


def convert_to_rpm(extractor: AppImageExtractor, output_dir: str, config: dict) -> str:
    """
    转换AppImage为RPM包
    
    Args:
        extractor: AppImage提取器
        output_dir: 输出目录
        config: 包配置
    
    Returns:
        生成的RPM包路径
    """
    print("开始构建RPM包...")
    
    # 创建RPM构建器
    rpm_builder = RpmBuilder(extractor.info, extractor.extracted_dir)
    rpm_builder.set_package_config(config)
    
    print(f"  包名: {rpm_builder.get_package_name()}")
    print(f"  版本: {rpm_builder.get_package_version('rpm')}")
    print(f"  架构: {rpm_builder.get_architecture('rpm')}")
    
    try:
        # 准备构建目录
        rpm_builder.prepare_build_directory()
        print("  [1/5] 准备构建目录完成")
        
        # 创建包结构
        rpm_builder.create_package_structure()
        print("  [2/5] 创建包目录结构完成")
        
        # 复制应用程序文件
        rpm_builder.copy_application_files()
        print("  [3/5] 复制应用程序文件完成")
        
        # 生成元数据文件
        rpm_builder.generate_metadata_files()
        print("  [4/5] 生成元数据文件完成")
        
        # 构建包
        rpm_path = rpm_builder.build_package(output_dir)
        print(f"  [5/5] 构建RPM包完成: {rpm_path}")
        
        return rpm_path
        
    finally:
        # 清理临时文件
        rpm_builder.cleanup()


def main() -> int:
    """
    主函数
    
    Returns:
        程序退出码
    """
    try:
        # 解析命令行参数
        args, config = parse_arguments()
        
        print(f"正在处理AppImage文件: {args.appimage}")
        
        # 创建AppImage提取器
        extractor = AppImageExtractor(args.appimage)
        
        try:
            # 提取AppImage内容
            extracted_dir = extractor.extract()
            
            # 解析元数据
            app_info = extractor.parse_metadata()
            
            print(f"应用程序信息:")
            print(f"  名称: {app_info.name}")
            print(f"  版本: {app_info.version}")
            print(f"  描述: {app_info.description}")
            print(f"  大小: {app_info.size // 1024}KB")
            if app_info.categories:
                print(f"  分类: {', '.join(app_info.categories)}")
            if app_info.executable:
                print(f"  可执行文件: {app_info.executable}")
            if app_info.icon:
                print(f"  图标: {app_info.icon}")
            if app_info.desktop_file:
                print(f"  .desktop文件: {app_info.desktop_file}")
            
            # 生成的包文件列表
            generated_packages: List[str] = []
            
            # 根据指定格式进行转换
            if args.format in ['deb', 'both']:
                try:
                    deb_path = convert_to_deb(extractor, args.output, config)
                    generated_packages.append(deb_path)
                except Exception as e:
                    print(f"构建DEB包失败: {e}")
                    if args.verbose:
                        traceback.print_exc()
                    if args.format == 'deb':
                        return 1
            
            if args.format in ['rpm', 'both']:
                try:
                    rpm_path = convert_to_rpm(extractor, args.output, config)
                    generated_packages.append(rpm_path)
                except Exception as e:
                    print(f"构建RPM包失败: {e}")
                    if args.verbose:
                        traceback.print_exc()
                    if args.format == 'rpm':
                        return 1
            
            # 显示结果
            if generated_packages:
                print("\n" + "=" * 60)
                print("转换完成！生成的包文件:")
                for package in generated_packages:
                    print(f"  {package}")
                print("=" * 60)
                return 0
            else:
                print("错误：没有成功生成任何包文件")
                return 1
                
        finally:
            # 清理临时文件（除非指定保留）
            if not args.keep_temp:
                extractor.cleanup()
            else:
                print(f"临时文件保留在: {extractor.temp_dir}")
    
    except KeyboardInterrupt:
        print("\n用户中断操作")
        return 130
    
    except Exception as e:
        print(f"程序执行出错: {e}")
        if 'args' in locals() and getattr(args, 'verbose', False):
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main()) 
