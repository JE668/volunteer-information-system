import pandas as pd

file_path = '/Users/je/Downloads/volunteer-information-system/data/分数线数据库.xlsx'
df = pd.read_excel(file_path)

print("--- Unique values in '计划类别' ---")
print(df['计划类别'].unique())

print("\n--- Unique values in '计划属性' ---")
print(df['计划属性'].unique())

# Also check if "艺术生" appears anywhere in the dataframe to be sure
mask = df.apply(lambda row: row.astype(str).str.contains('艺术生').any(), axis=1)
art_rows = df[mask]
print(f"\n--- Rows containing '艺术生': {len(art_rows)} ---")
if len(art_rows) > 0:
    print(art_rows[['计划类别', '计划属性', '专业名称']].head())
