import pandas as pd
df = pd.read_excel('data/分数线数据库.xlsx')

# 检查第一批普通高中中，计划类别为"普通高中"的行
batch1_pg = df[(df['年份'] == 2025) & 
               (df['批次'] == '第一批') & 
               (df['学校类别'] == '普通高中')]
print('第一批普通高中，计划类别分布:')
print(batch1_pg['计划类别'].value_counts())

print('\n计划类别为"普通高中"的行:')
pg_only = batch1_pg[batch1_pg['计划类别'] == '普通高中']
print(pg_only[['批次', '计划类别', '计划属性', '学校名称', '专业名称', '出档分数线']].head(20).to_string())

print('\n计划类别为"A 类计划"的行:')
a_plan = batch1_pg[batch1_pg['计划类别'] == 'A 类计划']
print(a_plan[['批次', '计划类别', '计划属性', '学校名称', '专业名称', '出档分数线']].head(20).to_string())

print('\n计划类别为"B 类计划"的行:')
b_plan = batch1_pg[batch1_pg['计划类别'] == 'B 类计划']
print(b_plan[['批次', '计划类别', '计划属性', '学校名称', '专业名称', '出档分数线']].head(20).to_string())