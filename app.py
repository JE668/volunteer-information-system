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

# --- 等级分计算逻辑 ---
def grade_to_score(grade):
    mapping = {'A+': 5, 'A': 4, 'B+': 3, 'B': 2, 'C': 1}
    return mapping.get(grade, 0)

def check_detailed_grade_req(user_grades, req_str, total_req_str, plan_type='A'):
    """
    plan_type: 'A' (公费: 生地历道), 'B' (自费: 生地物化)
    """
    result = {'pass': True, 'reason': ''}
    grade_subjects = {
        'A': ['生物', '地理', '历史', '道法'],
        'B': ['生物', '地理', '物理', '化学']
    }.get(plan_type, ['生物', '地理', '历史', '道法'])
    
    filtered_grades = {k: v for k, v in user_grades.items() if k in grade_subjects}
    
    if req_str:
        try:
            req_label = 'C'
            if 'A+' in req_str: req_label = 'A+'
            elif 'A' in req_str: req_label = 'A'
            elif 'B+' in req_str: req_label = 'B+'
            elif 'B' in req_str: req_label = 'B'
            
            grade_order = {'A+': 5, 'A': 4, 'B+': 3, 'B': 2, 'C': 1}
            for sub in grade_subjects:
                user_val = filtered_grades.get(sub, 'C')
                if grade_order.get(user_val, 0) < grade_order.get(req_label, 0):
                    result['pass'] = False
                    result['reason'] = f'{sub}需{req_label}及以上'
                    break
        except: pass

    if total_req_str:
        try:
            user_total = sum(grade_to_score(filtered_grades.get(sub, 'C')) for sub in grade_subjects)
            req_total = int(''.join(filter(str.isdigit, total_req_str)))
            if user_total < req_total:
                result['pass'] = False
                if result['reason']: result['reason'] += f'; 等级总分不足({user_total}/{req_total})'
                else: result['reason'] = f'等级总分不足：需{req_total}分'
        except: pass
    return result

# --- 路由定义 ---
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

# --- API 接口 ---
@app.route('/api/enrollment')
def api_enrollment():
    year = request.args.get('year', 2025, type=int)
    high_school = request.args.get('high_school', '')
    junior_school = request.args.get('junior_school', '')
    sql = '''
        SELECT q.high_school as school_name, q.school_attr, q.fee_type, q.junior_school, 
               q.min_score as quota_score, q.rank_order, q.source, s.min_score as regular_score
        FROM quota q 
        LEFT JOIN scores s ON q.high_school = s.school_name AND s.year = q.year 
            AND s.batch = "第一批" AND s.score_type = "普通高中" 
        WHERE q.year = ? 
    '''
    params = [year]
    if high_school:
        sql += ' AND q.high_school LIKE ?'
        params.append(f'%{high_school}%')
    if junior_school:
        sql += ' AND q.junior_school LIKE ?'
        params.append(f'%{junior_school}%')
    sql += ' GROUP BY q.high_school ORDER BY q.min_score DESC'
    rows = query_all(sql, params)
    result = []
    for r in rows:
        quota_s, reg_s = r['quota_score'], r['regular_score']
        result.append({
            'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'],
            'junior_school': r['junior_school'], 'min_score': quota_s, 'regular_min_score': reg_s,
            'diff': (reg_s - quota_s) if (quota_s and reg_s) else None, 'rank_order': r['rank_order'], 'source': r['source']
        })
    return jsonify(result)

@app.route('/api/schools')
def api_schools():
    year = request.args.get('year', 2025, type=int)
    school_type = request.args.get('type', 'pg')
    attr = request.args.get('attr', '')
    fee = request.args.get('fee', '')
    batch = request.args.get('batch', '')
    
    result = []
    where_clauses = ['year=?', 'min_score IS NOT NULL']
    params = [year]
    
    if attr: where_clauses.append('school_attr = ?'); params.append(attr)
    if fee: where_clauses.append('fee_type = ?'); params.append(fee)
    if batch: where_clauses.append('batch = ?'); params.append(batch)
    
    if school_type in ('pg', 'all'):
        where_pg = where_clauses + ['school_type = "普通高中"']
        sql = f'SELECT school_name, major_name, school_attr, fee_type, batch, score_type, min_score FROM scores WHERE {" AND ".join(where_pg)} ORDER BY batch ASC, min_score DESC'
        rows = query_all(sql, params)
        for r in rows: result.append({'school_name': r['school_name'], 'major_name': r['major_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'score_type': r['score_type'], 'min_score': r['min_score'], 'type': 'pg'})
    
    if school_type in ('voc', 'all'):
        where_voc = where_clauses + ['school_type = "中职学校"']
        sql = f'SELECT school_name, major_name, school_attr, fee_type, batch, min_score FROM scores WHERE {" AND ".join(where_voc)} ORDER BY batch ASC, min_score DESC'
        rows = query_all(sql, params)
        for r in rows: result.append({'school_name': r['school_name'], 'major_name': r['major_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'min_score': r['min_score'], 'type': 'voc'})
        
    return jsonify(result)
    return jsonify(result)

@app.route('/api/schools_by_batch')
def api_schools_by_batch():
    year = request.args.get('year', 2025, type=int)
    sport = get_sport_score(year)
    result = {'提前批_学科特长': [], '提前批_指标生': [], '提前批_港澳台班': [], '第一批_A类': [], '第一批_B类': [], '第一批_中职试点': [], '第二批_本市中职': [], '第三批_外市中职': []}
    # 1. 学科特长
    rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, score_type, MIN(min_score) as min_score FROM scores WHERE year=? AND score_type IN ("学科类自主招生", "外国语班", "艺术生") AND min_score IS NOT NULL GROUP BY school_name, score_type ORDER BY min_score DESC', [year])
    for r in rows: result['提前批_学科特长'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': r['score_type'], 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    # 2. 指标生
    rows = query_all('SELECT DISTINCT high_school as school_name, school_attr, fee_type, MIN(min_score) as min_score FROM quota WHERE year=? AND min_score IS NOT NULL GROUP BY high_school ORDER BY min_score DESC', [year])
    for r in rows: result['提前批_指标生'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': '指标生', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    # 3. 港澳台
def get_matches_inner(score, grades, plan_type='A', sport=50):
    if not score: return {'rush': [], 'stable': [], 'backup': []}
    score_5subj = score - sport
    
    # 完全解绑：不再根据 A/B 类过滤 fee_type
    # 只筛选：普通高中 + 有分数线
    sql = f'''
        SELECT school_name, school_attr, fee_type, batch, min_score, subject_grade_req, subject_grade_total_req 
        FROM scores 
        WHERE year=? AND school_type = "普通高中" AND score_type = "普通高中" 
        AND min_score IS NOT NULL 
        GROUP BY school_name 
        ORDER BY min_score DESC
    '''
    # 注意：这里使用 g.db 或通过参数传递，为了简单，我们在路由中调用 query_all
    # 但 get_matches_inner 是全局函数，需要能够访问 query_all
    rows = query_all(sql, [year]) # 假设 year 是全局或从某个地方获取，更好的做法是传参
    
    results = []
    for r in rows:
        # 分数计算：(用户总分 - 体育) - (学校线 - 体育) = 用户总分 - 学校线
        diff = score - r['min_score'] 
        grade_check = check_detailed_grade_req(grades, r.get('subject_grade_req'), r.get('subject_grade_total_req'), plan_type)
        
        results.append({
            'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 
            'batch': r['batch'], 'min_score': r['min_score'], 'diff': diff, 
            'grade_pass': grade_check['pass'], 'grade_reason': grade_check['reason']
        })
    
    rush = [r for r in results if -10 <= r['diff'] <= 10 and r['grade_pass']]
    stable = [r for r in results if 10 < r['diff'] <= 30 and r['grade_pass']]
    backup = [r for r in results if r['diff'] > 30 and r['grade_pass']]
    
    rush.sort(key=lambda x: x['diff'])
    stable.sort(key=lambda x: x['diff'])
    backup.sort(key=lambda x: -x['min_score']) 
    return {'rush': rush, 'stable': stable, 'backup': backup}

@app.route('/api/match')
def api_match():
    year = request.args.get('year', 2025, type=int)
    school_type = request.args.get('type', 'pg')
    score_a = request.args.get('score_a', type=int)
    grades_a = {'生物': request.args.get('bio_a'), '地理': request.args.get('geo_a'), '历史': request.args.get('his_a'), '道法': request.args.get('pol_a')}
    score_b = request.args.get('score_b', type=int)
    grades_b = {'生物': request.args.get('bio_b'), '地理': request.args.get('geo_b'), '物理': request.args.get('phy_b'), '化学': request.args.get('che_b')}

    if not score_a and not score_b: return jsonify({'error': '请至少填写一项总分'}), 400
    sport = get_sport_score(year)
    
    def calc_total(grades):
        return sum(grade_to_score(v) for v in grades.values() if v)

    # 定义内部函数，直接闭包使用 year 和 sport，避免作用域问题
    def do_match(score, grades, p_type):
        if not score: return {'rush': [], 'stable': [], 'backup': []}
        
        # 1. 确定体育分权重
        # 当前考生是 2026 年的，体育分是 80
        sport_current = 80 
        # 对比的年份（2023-2025）体育分是 50
        sport_line = get_sport_score(year) # 根据选定的对比年份获取 (50)
        
        # SQL: 只查普通高中
        sql = 'SELECT school_name, school_attr, fee_type, batch, min_score, subject_grade_req, subject_grade_total_req FROM scores WHERE year=? AND school_type = "普通高中" AND score_type = "普通高中" AND min_score IS NOT NULL GROUP BY school_name ORDER BY min_score DESC'
        rows = query_all(sql, [year])
        
        results = []
        for r in rows:
            # 核心计算：纯学术分对比
            # Diff = (用户总分 - 80) - (学校分数线 - 50)
            diff = score - r['min_score'] - (sport_current - sport_line)
            
            # 等级校验（硬性要求）
            grade_check = check_detailed_grade_req(grades, r.get('subject_grade_req'), r.get('subject_grade_total_req'), p_type)
            
            if grade_check['pass']:
                results.append({
                    'school_name': r['school_name'], 
                    'school_attr': r['school_attr'], 
                    'fee_type': r['fee_type'], 
                    'batch': r['batch'], 
                    'min_score': r['min_score'], 
                    'diff': diff, 
                    'grade_pass': True, 
                    'grade_reason': ''
                })
        
        # 根据纯学术分差值分档
        rush = [r for r in results if -10 <= r['diff'] <= 10]
        stable = [r for r in results if 10 < r['diff'] <= 30]
        backup = [r for r in results if r['diff'] > 30]
        
        rush.sort(key=lambda x: x['diff'])
        stable.sort(key=lambda x: x['diff'])
        backup.sort(key=lambda x: -x['min_score'])
        return {'rush': rush, 'stable': stable, 'backup': backup}

    if school_type == 'pg':
        return jsonify({
            'score_a': score_a, 'score_b': score_b, 
            'user_total_a': calc_total(grades_a), 'user_total_b': calc_total(grades_b),
            'res_a': do_match(score_a, grades_a, 'A'), 
            'res_b': do_match(score_b, grades_b, 'B'), 
            'year': year
        })
    elif school_type == 'voc':
        rows = query_all('SELECT school_name, major_name, school_attr, fee_type, batch, min_score FROM scores WHERE year=? AND school_type = "中职学校" AND min_score IS NOT NULL GROUP BY school_name, major_name ORDER BY min_score DESC', [year])
        score_5subj = (score_a or 0) - sport
        results = [{'school_name': r['school_name'], 'major_name': r['major_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'min_score': r['min_score'], 'diff': score_5subj - (r['min_score'] - sport)} for r in rows]
        return jsonify({'score': score_a, 'rush': [r for r in results if -10 <= r['diff'] <= 10], 'stable': [r for r in results if 10 < r['diff'] <= 30], 'backup': [r for r in results if r['diff'] > 30], 'year': year, 'type': 'voc'})
    return jsonify({'error': 'Invalid school type'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
