import pandas as pd
df = pd.read_excel('data/分数线数据库.xlsx')

# 检查纪念中学2025年的A类和B类计划分数
jinian = df[(df['学校名称'].str.contains('纪念', na=False)) & (df['年份'] == 2025)]
print('纪念中学2025年数据:')
print(jinian[['批次', '计划类别', '计划属性', '学校名称', '专业名称', '出档分数线']].head(20).to_string())

print('\n\n华侨中学2025年数据:')
hucqiao = df[(df['学校名称'].str.contains('华侨', na=False)) & (df['年份'] == 2025)]
print(hucqiao[['批次', '计划类别', '计划属性', '学校名称', '专业名称', '出档分数线']].head(20).to_string())