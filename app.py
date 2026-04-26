#!/usr/bin/env python3
import os, sqlite3
from flask import Flask, render_template, request, jsonify, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'app', 'templates'),
            static_folder=os.path.join(BASE_DIR, 'app', 'static'))
app.config['DATABASE'] = os.path.join(BASE_DIR, 'data', 'zs_scores.db')

SPORT_SCORE = {2023: 50, 2024: 50, 2025: 50, 2026: 80}
TOTAL_SCORE = {2023: 600, 2024: 600, 2025: 600, 2026: 630}

def get_sport_score(year): return SPORT_SCORE.get(year, 50)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None: db.close()

def query_all(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    return [dict(zip(r.keys(), r)) for r in cur.fetchall()]

def grade_level_label(score, year=2026):
    if score is None: return None
    if score >= 527: return 'A+'
    if score >= 482: return 'A'
    if score >= 420: return 'B+'
    if score >= 343: return 'B'
    return 'C'

def grade_level_score(grade_label):
    mapping = {'A+': 5, 'A': 4, 'B+': 3, 'B': 2, 'C': 1, 'C及以下': 0}
    return mapping.get(grade_label, 0)

def check_grade_req(user_grade, grade_req_str, grade_total_req_str):
    result = {'pass': True, 'grade_ok': True, 'grade_total_ok': True, 'reason': ''}
    if not grade_req_str and not grade_total_req_str: return result
    if grade_req_str:
        req = 'C'
        if 'A+' in grade_req_str: req = 'A+'
        elif 'A' in grade_req_str: req = 'A'
        elif 'B+' in grade_req_str: req = 'B+'
        elif 'B' in grade_req_str: req = 'B'
        grade_order = {'A+': 5, 'A': 4, 'B+': 3, 'B': 2, 'C': 1}
        if grade_order.get(user_grade, 0) < grade_order.get(req, 0):
            result['pass'], result['grade_ok'] = False, False
            result['reason'] = f'等级不足：需{req}及以上，当前{user_grade}'
    if grade_total_req_str:
        try:
            req_total = int(''.join(filter(str.isdigit, grade_total_req_str)))
            user_total = grade_level_score(user_grade) * 5
            if user_total < req_total:
                result['pass'], result['grade_total_ok'] = False, False
                if result['reason']: result['reason'] += f'; 等级总分不足({user_total}/{req_total})'
                else: result['reason'] = f'等级总分不足：需{req_total}分'
        except: pass
    return result

@app.route('/')
def index(): return render_template('index.html')

@app.route('/search')
def page_search(): return render_template('search.html')

@app.route('/compare')
def page_compare(): return render_template('compare.html')

@app.route('/quota')
def page_quota(): return render_template('quota.html')

@app.route('/enrollment')
def page_enrollment(): return render_template('enrollment.html')

@app.route('/simulate')
def page_simulate(): return render_template('simulate.html')

@app.route('/about')
def page_about(): return render_template('about.html')

@app.route('/api/schools')
def api_schools():
    year = request.args.get('year', 2025, type=int)
    school_type = request.args.get('type', 'pg')
    result = []
    if school_type in ('pg', 'all'):
        rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, batch, score_type, MIN(min_score) as min_score FROM scores WHERE year=? AND school_type = "普通高中" AND min_score IS NOT NULL GROUP BY school_name, score_type ORDER BY school_name', [year])
        for r in rows: result.append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'score_type': r['score_type'], 'min_score': r['min_score'], 'type': 'pg'})
    if school_type in ('voc', 'all'):
        rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, batch, MIN(min_score) as min_score FROM scores WHERE year=? AND school_type = "中职学校" AND min_score IS NOT NULL GROUP BY school_name ORDER BY school_name', [year])
        for r in rows: result.append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'min_score': r['min_score'], 'type': 'voc'})
    return jsonify(result)

@app.route('/api/schools_by_batch')
def api_schools_by_batch():
    year = request.args.get('year', 2025, type=int)
    sport = get_sport_score(year)
    result = {'提前批_学科特长': [], '提前批_指标生': [], '提前批_港澳台班': [], '第一批_A类': [], '第一批_B类': [], '第一批_中职试点': [], '第二批_本市中职': [], '第三批_外市中职': []}
    
    # simplified logic for brevity in regeneration, mirroring original flow
    # 1. 学科特长
    rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, score_type, MIN(min_score) as min_score FROM scores WHERE year=? AND score_type IN ("学科类自主招生", "外国语班", "艺术生") AND min_score IS NOT NULL GROUP BY school_name, score_type ORDER BY min_score DESC', [year])
    for r in rows: result['提前批_学科特长'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': r['score_type'], 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    # 2. 指标生
    rows = query_all('SELECT DISTINCT high_school as school_name, school_attr, fee_type, MIN(min_score) as min_score FROM quota WHERE year=? AND min_score IS NOT NULL GROUP BY high_school ORDER BY min_score DESC', [year])
    for r in rows: result['提前批_指标生'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': '指标生', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    # 3. 港澳台
    rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, MIN(min_score) as min_score FROM scores WHERE year=? AND score_type = "港澳台班" AND min_score IS NOT NULL GROUP BY school_name ORDER BY min_score DESC', [year])
    for r in rows: result['提前批_港澳台班'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': '港澳台班', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    # 4. 第一批 A类
    rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, MIN(min_score) as min_score FROM scores WHERE year=? AND batch="第一批" AND score_type="普通高中" AND fee_type = "公费" AND min_score IS NOT NULL GROUP BY school_name ORDER BY min_score DESC', [year])
    for r in rows: result['第一批_A类'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': 'A类计划', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    # 5. 第一批 B类
    rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, MIN(min_score) as min_score FROM scores WHERE year=? AND batch="第一批" AND score_type="普通高中" AND fee_type IN ("自费", "参公") AND min_score IS NOT NULL GROUP BY school_name ORDER BY min_score DESC', [year])
    for r in rows: result['第一批_B类'].append({'school_name': r['school_name'], 'school_attr': r['fee_type'], 'admission_type': 'B类计划', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    # 6. 中职试点
    rows = query_all('SELECT DISTINCT school_name, major_name, school_attr, fee_type, MIN(min_score) as min_score FROM scores WHERE year=? AND batch="第一批" AND score_type LIKE "%试点%" AND min_score IS NOT NULL GROUP BY school_name, major_name ORDER BY min_score DESC', [year])
    for r in rows: result['第一批_中职试点'].append({'school_name': r['school_name'], 'major_name': r['major_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': '中职试点专业', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    # 7. 本市中职
    rows = query_all('SELECT DISTINCT school_name, major_name, school_attr, fee_type, MIN(min_score) as min_score FROM scores WHERE year=? AND batch="第二批" AND score_type LIKE "%本市中职%" AND min_score IS NOT NULL GROUP BY school_name, major_name ORDER BY min_score DESC', [year])
    for r in rows: result['第二批_本市中职'].append({'school_name': r['school_name'], 'major_name': r['major_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': '本市中职', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    # 8. 外市中职
    rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, MIN(min_score) as min_score FROM scores WHERE year=? AND (batch="第三批" OR score_type LIKE "%外市%") AND score_type NOT LIKE "%试点%" AND min_score IS NOT NULL GROUP BY school_name ORDER BY min_score DESC', [year])
    for r in rows: result['第三批_外市中职'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': '外市中s中职', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    
    return jsonify(result)

@app.route('/api/match')
def api_match():
    score = request.args.get('score', type=int)
    year = request.args.get('year', 2025, type=int)
    school_type = request.args.get('type', 'pg')
    use_five_subjects = request.args.get('five', 'true') == 'true'
    if not score or score < 100 or score > 700: return jsonify({'error': '分数范围异常'}), 400
    sport = get_sport_score(year)
    score_5subj = score - sport if use_five_subjects else score
    grade_label = grade_level_label(score, year)
    
    if school_type == 'pg':
        rows = query_all('SELECT school_name, school_attr, fee_type, batch, min_score, subject_grade_req, subject_grade_total_req FROM scores WHERE year=? AND school_type = "普通高中" AND score_type = "普通高中" AND min_score IS NOT NULL GROUP BY school_name ORDER BY min_score DESC', [year])
        results = []
        for r in rows:
            min_score_5subj = r['min_score'] - sport
            diff = score_5subj - min_score_5subj
            grade_check = check_grade_req(grade_label, r.get('subject_grade_req'), r.get('subject_grade_total_req'))
            results.append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'min_score': r['min_score'], 'min_score_5subj': min_score_5subj, 'diff': diff, 'grade_req': r.get('subject_grade_req'), 'grade_total_req': r.get('subject_grade_total_req'), 'grade_pass': grade_check['pass'], 'grade_reason': grade_check['reason']})
        rush = [r for r in results if 0 <= r['diff'] <= 15]
        stable = [r for r in results if 15 < r['diff'] <= 40]
        backup = [r for r in results if r['diff'] > 40]
        rush.sort(key=lambda x: x['diff'])
        stable.sort(key=lambda x: x['diff'])
        backup.sort(key=lambda x: -x['diff'])
        return jsonify({'score': score, 'grade': grade_label, 'rush': rush, 'stable': stable, 'backup': backup, 'year': year})
    elif school_type == 'voc':
        rows = query_all('SELECT school_name, major_name, school_attr, fee_type, batch, min_score FROM scores WHERE year=? AND school_type = "中职学校" AND min_score IS NOT NULL GROUP BY school_name, major_name ORDER BY min_score DESC', [year])
        results = []
        for r in rows:
            min_score_5subj = r['min_score'] - sport
            diff = score_5subj - min_score_5subj
            results.append({'school_name': r['school_name'], 'major_name': r['major_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'min_score': r['min_score'], 'min_score_5subj': min_score_5subj, 'diff': diff})
        rush = [r for r in results if 0 <= r['diff'] <= 15]
        stable = [r for r in results if 15 < r['diff'] <= 40]
        backup = [r for r in results if r['diff'] > 40]
        rush.sort(key=lambda x: x['diff'])
        stable.sort(key=lambda x: x['diff'])
        backup.sort(key=lambda x: -x['diff'])
        return jsonify({'score': score, 'grade': grade_label, 'rush': rush, 'stable': stable, 'backup': backup, 'year': year})
    return jsonify({'error': 'Invalid school type'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
