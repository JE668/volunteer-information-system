#!/usr/bin/env python3
"""
从 Excel 导入分数线数据到 SQLite 数据库
为普通高中创建 A 类计划和 B 计划两份记录
"""

import pandas as pd
import sqlite3
import os
import re

EXCEL_FILE = 'data/分数线数据库.xlsx'
DB_FILE = 'data/zs_scores.db'

def extract_number(val):
    """提取字符串中的数字"""
    if pd.isna(val) or val == '' or val == '/':
        return None
    if isinstance(val, (int, float)):
        return int(val)
    val_str = str(val).strip()
    if val_str == '/' or val_str == '':
        return None
    match = re.search(r'\d+', val_str)
    if match:
        return int(match.group())
    return None

def to_str(val):
    """转换为字符串，处理 NA 值"""
    if pd.isna(val) or val == '/':
        return None
    return str(val).strip() if val else None

def import_data():
    if not os.path.exists(EXCEL_FILE):
        print(f"错误：Excel 文件不存在：{EXCEL_FILE}")
        return False
    
    # 读取 Excel
    print(f"读取 Excel 文件：{EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE, sheet_name='Sheet1')
    print(f"读取到 {len(df)} 行数据")
    print(f"原始列名：{list(df.columns)}")
    
    # 将 '/' 替换为 NaN
    df = df.replace('/', pd.NA)
    
    # 提取数字列
    print("\n处理数字列...")
    df['min_score_clean'] = df['出档分数线'].apply(extract_number)
    df['rank_order_clean'] = df['最低同分位次'].apply(extract_number)
    df['total_score_req_clean'] = df['中考总分最低要求'].apply(extract_number)
    
    # 特殊处理：学校类别
    print("处理学校类别...")
    df['school_type'] = df['学校类别'].apply(lambda x: x if pd.notna(x) and x != '' else None)
    df.loc[df['school_type'].isna(), 'school_type'] = df['计划类别'].apply(
        lambda x: '中职学校' if x == '中职学校' else '普通高中'
    )
    
    # 特殊处理：学校属性
    print("处理学校属性...")
    df['school_attr'] = df['学校属性'].apply(lambda x: x if pd.notna(x) and x != '' else None)
    df.loc[df['school_attr'].isna(), 'school_attr'] = df['计划属性']
    
    print(f"\n学校类别分布:\n{df['school_type'].value_counts()}")
    print(f"\n计划类别分布:\n{df['计划类别'].value_counts()}")
    
    # 连接数据库
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 清空旧数据
    print("\n清空旧数据...")
    cursor.execute('DELETE FROM scores')
    cursor.execute('DELETE FROM sqlite_sequence WHERE name="scores"')
    conn.commit()
    
    # 插入新数据
    print("插入新数据...")
    insert_sql = '''
    INSERT INTO scores (
        year, batch, plan_type, score_type, school_type, school_code, school_name,
        school_attr, fee_type, major_code, major_name,
        junior_school, min_score, rank_order, total_score_req,
        subject_grade_req, subject_grade_total_req, quality_eval_req,
        source, policy_note, remark
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    rows_to_insert = []
    insert_count = 0
    
    for idx, row in df.iterrows():
        # 确定 score_type（根据计划类别和学校类别）
        plan_cat = row['计划类别']
        school_cat = row['school_type']
        
        # 确定要插入的计划类型列表
        if plan_cat == '中职学校':
            plan_types = ['中职学校']
        elif plan_cat == '指标生':
            plan_types = ['指标生']
        elif plan_cat == '艺术生':
            plan_types = ['艺术生']
        elif plan_cat == '学科类自主招生':
            plan_types = ['学科类自主招生']
        elif plan_cat == '港澳台班':
            plan_types = ['港澳台班']
        elif plan_cat == '外国语班':
            plan_types = ['外国语班']
        elif plan_cat == '3+4 中本贯通':
            plan_types = ['3+4 中本贯通']
        elif plan_cat == '普通高中':
            # 普通高中：创建 A 类计划和 B 类计划两份记录
            plan_types = ['A 类计划', 'B 类计划']
        else:
            # 其他情况：创建 A 类计划和 B 类计划
            plan_types = ['A 类计划', 'B 类计划']
        
        for p_type in plan_types:
            # 确定 score_type
            if p_type in ['中职学校', '指标生', '艺术生', '学科类自主招生', '港澳台班', '外国语班', '3+4 中本贯通']:
                score_type = p_type
            else:
                score_type = '普通高中'
            
            rows_to_insert.append((
                int(row['年份']) if pd.notna(row['年份']) else None,
                row['批次'],
                p_type,  # plan_type
                score_type,
                row['school_type'],
                row['学校代码'],
                row['学校名称'],
                row['school_attr'],
                row['收费类型'],
                to_str(row['专业代码']),
                to_str(row['专业名称']),
                row['指标生初中学校'] if pd.notna(row['指标生初中学校']) else None,
                int(row['min_score_clean']) if pd.notna(row['min_score_clean']) else None,
                int(row['rank_order_clean']) if pd.notna(row['rank_order_clean']) else None,
                int(row['total_score_req_clean']) if pd.notna(row['total_score_req_clean']) else None,
                to_str(row['考查科目等级最低要求']),
                to_str(row['考查科目等级总分最低要求']),
                to_str(row['综合素质评价要求']),
                to_str(row['分数来源']),
                None,  # policy_note
                None   # remark
            ))
            
            insert_count += 1
            
            # 批量插入，每 1000 条提交一次
            if len(rows_to_insert) >= 1000:
                cursor.executemany(insert_sql, rows_to_insert)
                conn.commit()
                print(f"已插入 {insert_count} 行")
                rows_to_insert = []
    
    # 插入剩余数据
    if rows_to_insert:
        cursor.executemany(insert_sql, rows_to_insert)
        conn.commit()
    
    print(f"\n✓ 成功导入 {insert_count} 行数据")
    
    # 验证结果
    print("\n=== 导入后数据验证 ===")
    cursor.execute("SELECT COUNT(*) FROM scores")
    total = cursor.fetchone()[0]
    print(f"总记录数：{total}")
    
    cursor.execute("SELECT school_type, COUNT(*) FROM scores GROUP BY school_type")
    print("\n学校类别分布:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    cursor.execute("SELECT plan_type, COUNT(*) FROM scores GROUP BY plan_type ORDER BY plan_type")
    print("\n计划类别分布:")
    for row in cursor.fetchall():
        print(f"  {row[0] or 'NULL'}: {row[1]}")
    
    print("\n=== 普通高中示例数据（A 类计划） ===")
    cursor.execute("SELECT school_name, plan_type, school_attr, fee_type, min_score FROM scores WHERE school_type='普通高中' AND plan_type='A 类计划' LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
    
    print("\n=== 普通高中示例数据（B 类计划） ===")
    cursor.execute("SELECT school_name, plan_type, school_attr, fee_type, min_score FROM scores WHERE school_type='普通高中' AND plan_type='B 类计划' LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]}")
    
    print("\n=== 中职学校示例数据 ===")
    cursor.execute("SELECT school_name, plan_type, school_attr, fee_type, major_name, min_score FROM scores WHERE school_type='中职学校' LIMIT 5")
    for row in cursor.fetchall():
        print(f"  {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}")
    
    conn.close()
    return True

if __name__ == '__main__':
    import_data()
