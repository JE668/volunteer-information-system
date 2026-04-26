#!/usr/bin/env python3
"""
数据迁移脚本：修复学校属性 (school_attr) 列的数据

问题分析：
1. 中职学校的 school_attr 错误地存储了"民办"等值，应该存储"国家重点"、"省重点"等
2. 需要将"中职学校"从 school_attr 移动到 school_type（已存在）
3. 普通高中的 school_attr 应该存储学校属性信息

修复策略：
1. 对于中职学校：
   - school_attr 原本是"公办"/"民办"，这些实际是 fee_type 的信息
   - 需要将 fee_type 设置为正确的值（公费/自费）
   - school_attr 应该根据学校名称判断或设置为"中职"
   
2. 对于普通高中：
   - 保持 school_attr 为"公办"、"民办"等
   - plan_type 已经是"A 类计划"、"B 类计划"
"""

import sqlite3
import os

DB_PATH = 'data/zs_scores.db'

def migrate_data():
    if not os.path.exists(DB_PATH):
        print(f"错误：数据库文件 {DB_PATH} 不存在")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("开始数据迁移...")
    
    # 1. 先查看当前数据分布
    print("\n=== 迁移前数据分布 ===")
    cursor.execute("""
        SELECT school_type, plan_type, school_attr, fee_type, COUNT(*) as count 
        FROM scores 
        GROUP BY school_type, plan_type, school_attr, fee_type
        ORDER BY school_type, plan_type, school_attr, fee_type
    """)
    for row in cursor.fetchall():
        print(f"{row['school_type']} | {row['plan_type'] or 'NULL'} | {row['school_attr'] or 'NULL'} | {row['fee_type'] or 'NULL'} | {row['count']}")
    
    # 2. 修复中职学校数据
    print("\n=== 修复中职学校数据 ===")
    
    # 中职学校的 school_attr 应该是学校属性（如"国家重点"、"省重点"等）
    # 但目前存储的是"公办"/"民办"，这其实是 fee_type 的信息
    # 我们需要：
    # - 将 school_attr='公办' 的中职学校，fee_type 设为'公费'
    # - 将 school_attr='民办' 的中职学校，fee_type 设为'自费'
    # - school_attr 设为空或"中职"
    
    cursor.execute("""
        UPDATE scores 
        SET 
            fee_type = CASE 
                WHEN school_attr = '公办' THEN '公费'
                WHEN school_attr = '民办' THEN '自费'
                ELSE fee_type
            END,
            school_attr = '中职学校'
        WHERE school_type = '中职学校'
        AND (school_attr = '公办' OR school_attr = '民办')
    """)
    print(f"已更新中职学校记录数：{cursor.rowcount}")
    
    # 3. 修复普通高中数据
    print("\n=== 修复普通高中数据 ===")
    
    # 普通高中应该有 plan_type (A 类计划/B 类计划) 和 school_attr (公办/民办)
    # 检查是否有普通高中缺少 school_attr
    cursor.execute("""
        SELECT COUNT(*) as count FROM scores 
        WHERE school_type = '普通高中' 
        AND (school_attr IS NULL OR school_attr = '')
    """)
    missing_attr = cursor.fetchone()['count']
    print(f"普通高中缺少 school_attr 的记录数：{missing_attr}")
    
    # 4. 提交更改
    conn.commit()
    
    # 5. 验证结果
    print("\n=== 迁移后数据分布 ===")
    cursor.execute("""
        SELECT school_type, plan_type, school_attr, fee_type, COUNT(*) as count 
        FROM scores 
        GROUP BY school_type, plan_type, school_attr, fee_type
        ORDER BY school_type, plan_type, school_attr, fee_type
    """)
    for row in cursor.fetchall():
        print(f"{row['school_type']} | {row['plan_type'] or 'NULL'} | {row['school_attr'] or 'NULL'} | {row['fee_type'] or 'NULL'} | {row['count']}")
    
    # 6. 显示示例数据
    print("\n=== 普通高中示例数据 ===")
    cursor.execute("""
        SELECT school_name, plan_type, school_attr, fee_type, batch 
        FROM scores 
        WHERE school_type = '普通高中'
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"{row['school_name']} | {row['plan_type']} | {row['school_attr']} | {row['fee_type']} | {row['batch']}")
    
    print("\n=== 中职学校示例数据 ===")
    cursor.execute("""
        SELECT school_name, major_name, school_attr, fee_type, batch 
        FROM scores 
        WHERE school_type = '中职学校'
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"{row['school_name']} | {row['major_name']} | {row['school_attr']} | {row['fee_type']} | {row['batch']}")
    
    conn.close()
    print("\n✓ 数据迁移完成")
    return True

if __name__ == '__main__':
    migrate_data()
