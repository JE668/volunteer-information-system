import pandas as pd

file_path = '/Users/je/Downloads/volunteer-information-system/data/分数线数据库.xlsx'
df = pd.read_excel(file_path)

print("--- Columns in Excel ---")
print(df.columns.tolist())
print("\n--- Sample Data (First 5 rows) ---")
print(df.head().to_string())

# Check for specific keyword "音乐" to verify update
art_music = df[df['分数线类型'].astype(str).str.contains('艺术生') & df['专业名称'].astype(str).str.contains('音乐')]
print(f"\n--- Art Music count: {len(art_music)} ---")
if len(art_music) > 0:
    print(art_music[['学校名称', '专业名称']].head())
