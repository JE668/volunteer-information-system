import pandas as pd
import sqlite3

file_path = '/Users/je/Downloads/volunteer-information-system/data/分数线数据库.xlsx'
db_path = '/Users/je/Downloads/volunteer-information-system/data/zs_scores.db'

# 1. Read Excel
df = pd.read_excel(file_path)

# 2. Data Cleaning & Mapping
# Map Excel columns to DB columns
mapping = {
    '年份': 'year',
    '批次': 'batch',
    '计划类别': 'score_type',
    '计划属性': 'plan_type',
    '学校名称': 'school_name',
    '学校属性': 'school_attr',
    '专业代码': 'major_code',
    '专业名称': 'major_name',
    '收费类型': 'fee_type',
    '出档分数线': 'min_score',
    '考查科目等级最低要求': 'subject_grade_req',
    '考查科目等级总分最低要求': 'subject_grade_total_req'
}

# Only keep the columns we need and rename them
df_mapped = df[list(mapping.keys())].rename(columns=mapping)

# Data type conversion
df_mapped['min_score'] = pd.to_numeric(df_mapped['min_score'], errors='coerce').fillna(0).astype(int)
df_mapped['year'] = df_mapped['year'].fillna(0).astype(int)

# 3. Database Operations
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Clear existing data
cursor.execute("DELETE FROM scores")
print("Cleared old scores data.")

# Insert new data
df_mapped.to_sql('scores', conn, if_exists='append', index=False)
conn.commit()

print(f"Successfully imported {len(df_mapped)} records.")

# 4. Verification
res = cursor.execute("SELECT COUNT(*) FROM scores WHERE score_type = '艺术生'").fetchone()
print(f"Verification: '艺术生' count in DB = {res[0]}")

conn.close()
