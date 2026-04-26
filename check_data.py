import pandas as pd
df = pd.read_excel('data/分数线数据库.xlsx', sheet_name='Sheet1')
pg_df = df[(df['学校类别'] == '普通高中') & (df['批次'] == '第一批')]
print('计划类别唯一值:', pg_df['计划类别'].unique())
print('计划属性唯一值:', pg_df['计划属性'].unique())
print('\n前 20 行:')
print(pg_df[['年份', '批次', '计划类别', '计划属性', '学校名称', '学校属性']].head(20).to_string())
pg_df.to_csv('/tmp/pg_first_batch.csv', index=False)
print('\n已保存到 /tmp/pg_first_batch.csv')
