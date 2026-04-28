import pandas as pd
import sqlite3

file_path = '/Users/je/Downloads/volunteer-information-system/data/分数线数据库.xlsx'
db_path = '/Users/je/Downloads/volunteer-information-system/data/zs_scores.db'

# 1. Read Excel
df = pd.read_excel(file_path)

# 2. Mapping
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

df_mapped = df[list(mapping.keys())].rename(columns=mapping)
df_mapped['min_score'] = pd.to_numeric(df_mapped['min_score'], errors='coerce')
df_mapped['year'] = pd.to_numeric(df_mapped['year'], errors='coerce').fillna(0).astype(int)

# 3. Correct school_type logic to match app.py API
def determine_school_type(score_type):
    if score_type == '中职学校':
        return '中职学校' # Changed from 'VOC'
    return '普通高中'     # Changed from 'PG'

df_mapped['school_type'] = df_mapped['score_type'].apply(determine_school_type)

# 4. Database Operations
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("DELETE FROM scores")
print("Cleared old scores data.")

df_mapped.to_sql('scores', conn, if_exists='append', index=False)
conn.commit()

print(f"Successfully imported {len(df_mapped)} records.")
conn.close()
