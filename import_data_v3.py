#!/usr/bin/env python3
"""
数据导入脚本 v4 (重构版)
适配 [分数线数据库.xlsx]
"""
import sqlite3
import pandas as pd
import os

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'zs_scores.db')
DATA_FILE = os.getenv('DATA_FILE_PATH', 'data/分数线数据库.xlsx')

def clean_score(val):
    if pd.isna(val) or val == '/': return None
    try: return int(float(val))
    except: return None

def clean_str(val):
    if pd.isna(val) or val == '/': return ''
    return str(val).strip()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS scores')
    c.execute('DROP TABLE IF EXISTS quota')
    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            batch TEXT NOT NULL,
            score_type TEXT NOT NULL,
            school_type TEXT NOT NULL,
            school_code TEXT,
            school_name TEXT NOT NULL,
            school_attr TEXT,
            fee_type TEXT,
            major_code TEXT,
            major_name TEXT,
            junior_school TEXT,
            district TEXT,
            plan_type TEXT,
            min_score INTEGER,
            rank_order INTEGER,
            subject_grade_req TEXT,
            subject_grade_total_req TEXT,
            quality_eval_req TEXT,
            total_score_req INTEGER,
            source TEXT,
            policy_note TEXT,
            remark TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS quota (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER NOT NULL,
            batch TEXT,
            school_type TEXT,
            school_code TEXT,
            high_school TEXT NOT NULL,
            school_attr TEXT,
            fee_type TEXT,
            junior_school TEXT,
            district TEXT,
            min_score INTEGER,
            rank_order INTEGER,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def import_data(conn):
    c = conn.cursor()
    if not os.path.exists(DATA_FILE):
        print(f"Error: Data file not found at {DATA_FILE}")
        return
    
    df = pd.read_excel(DATA_FILE)
    count_scores = 0
    count_quota = 0
    
    for _, row in df.iterrows():
        year = int(row['年份']) if pd.notna(row['年份']) else None
        batch = clean_str(row['批次'])
        score_type = clean_str(row['计划类别'])
        school_type = clean_str(row['学校类别'])
        school_code = clean_str(row['学校代码'])
        school_name = clean_str(row['学校名称'])
        school_attr = clean_str(row['学校属性'])
        fee_type = clean_str(row['收费类型'])
        major_code = clean_str(row['专业代码'])
        major_name = clean_str(row['专业名称'])
        junior_school = clean_str(row['指标生初中学校'])
        plan_type = clean_str(row['计划属性'])
        min_score = clean_score(row['出档分数线'])
        rank_order = clean_score(row['最低同分位次'])
        subj_grade = clean_str(row['考查科目等级最低要求'])
        subj_total = clean_str(row['考查科目等级总分最低要求'])
        quality = clean_str(row['综合素质评价要求'])
        total_req = clean_score(row['中考总分最低要求'])
        source = clean_str(row['分数来源'])
        
        if not school_name or not year: continue
        if score_type == '指标生':
            c.execute('''
                INSERT INTO quota (year, batch, school_type, school_code, high_school, school_attr,
                fee_type, junior_school, district, min_score, rank_order, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (year, batch, school_type, school_code, school_name, school_attr, fee_type, junior_school, '/', min_score, rank_order, source))
            count_quota += 1
        else:
            c.execute('''
                INSERT INTO scores (year, batch, score_type, school_type, school_code, school_name,
                school_attr, fee_type, major_code, major_name, junior_school, district,
                plan_type, min_score, rank_order, subject_grade_req, subject_grade_total_req,
                quality_eval_req, total_score_req, source, policy_note, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (year, batch, score_type, school_type, school_code, school_name, school_attr, fee_type, major_code, major_name, junior_school, '/', plan_type, min_score, rank_order, subj_grade, subj_total, quality, total_req, source, '', ''))
            count_scores += 1
    conn.commit()
    print(f"Import complete: scores={count_scores}, quota={count_quota}")

if __name__ == '__main__':
    conn = init_db()
    import_data(conn)
    conn.close()
