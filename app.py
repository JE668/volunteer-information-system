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
        # Use URI mode for read-only access to prevent journal file creation issues on read-only filesystems (like Vercel)
        db_path = app.config['DATABASE']
        db_uri = f'file:{db_path}?mode=ro' if not db_path.startswith('file:') else db_path
        g.db = sqlite3.connect(db_uri, uri=True)
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
            req_total = int(''.join(filter(str.isdigit, total_req_str)) )
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
@app.route('/api/filters')
def api_filters():
    year = request.args.get('year', 2025, type=int)
    db = get_db()
    batches = [r['batch'] for r in db.execute('SELECT DISTINCT batch FROM scores WHERE year=? AND batch IS NOT NULL ORDER BY batch', [year]).fetchall()]
    score_types = [r['score_type'] for r in db.execute('SELECT DISTINCT score_type FROM scores WHERE year=? AND score_type IS NOT NULL ORDER BY score_type', [year]).fetchall()]
    return jsonify({'batches': batches, 'score_types': score_types})

@app.route('/api/filters/types')
def api_filter_types():
    year = request.args.get('year', 2025, type=int)
    batch = request.args.get('batch', '')
    db = get_db()
    sql = 'SELECT DISTINCT score_type FROM scores WHERE year=? AND score_type IS NOT NULL'
    params = [year]
    if batch:
        sql += ' AND batch = ?'
        params.append(batch)
    sql += ' ORDER BY score_type'
    score_types = [r['score_type'] for r in db.execute(sql, params).fetchall()]
    return jsonify({'score_types': score_types})

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
    score_type = request.args.get('score_type', '')
    sub_category = request.args.get('sub_category', '')

    result = []
    where_clauses = ['year=?', 'min_score IS NOT NULL']
    params = [year]

    if attr: where_clauses.append('school_attr = ?'); params.append(attr)
    if fee: where_clauses.append('fee_type = ?'); params.append(fee)
    if batch: where_clauses.append('batch = ?'); params.append(batch)
    if score_type: where_clauses.append('score_type = ?'); params.append(score_type)
    if sub_category: where_clauses.append('major_name LIKE ?'); params.append(f'%{sub_category}%')

    if school_type in ('pg', 'all'):
        # 普高：排除 3+4中本贯通 (将其交给 voc 逻辑处理)
        where_pg = where_clauses + ['school_type = "普通高中" AND score_type != "3+4中本贯通"']
        sql = f'SELECT school_name, major_name, major_code, school_attr, fee_type, batch, score_type, plan_type, min_score, subject_grade_req, subject_grade_total_req, junior_school FROM scores WHERE {" AND ".join(where_pg)} ORDER BY batch ASC, min_score DESC'
        rows = query_all(sql, params)
        for r in rows: result.append({'year': year, 'school_name': r['school_name'], 'major_name': r['major_name'], 'major_code': r.get('major_code', ''), 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'score_type': r['score_type'], 'plan_type': r.get('plan_type', ''), 'min_score': r['min_score'], 'subject_grade_req': r['subject_grade_req'], 'subject_grade_total_req': r['subject_grade_total_req'], 'junior_school': r.get('junior_school', ''), 'type': 'pg'})

    if school_type in ('voc', 'all'):
        # 中职：包含 school_type="中职学校" OR score_type="3+4中本贯通"
        where_voc_base = where_clauses + ['(school_type = "中职学校" OR score_type = "3+4中本贯通")']
        sql = f'SELECT school_name, major_name, major_code, school_attr, fee_type, batch, score_type, plan_type, min_score, junior_school FROM scores WHERE {" AND ".join(where_voc_base)} ORDER BY batch ASC, min_score DESC'
        rows = query_all(sql, params)
        for r in rows: result.append({'year': year, 'school_name': r['school_name'], 'major_name': r['major_name'], 'major_code': r.get('major_code', ''), 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'score_type': r['score_type'], 'plan_type': r.get('plan_type', ''), 'min_score': r['min_score'], 'junior_school': r.get('junior_school', ''), 'type': 'voc'})

    return jsonify(result)

@app.route('/api/schools_by_batch')
def api_schools_by_batch():
    year = request.args.get('year', 2025, type=int)
    sport = get_sport_score(year)
    result = {'提前批_学科特长': [], '提前批_指标生': [], '提前批_港澳台班': [], '第一批_A类': [], '第一批_B类': [], '第一批_中职试点': [], '第二批_本市中职': [], '第三批_外市中职': []}
    rows = query_all('SELECT DISTINCT school_name, school_attr, fee_type, score_type, MIN(min_score) as min_score FROM scores WHERE year=? AND score_type IN ("学科类自主招生", "外国语班", "艺术生") AND min_score IS NOT NULL GROUP BY school_name, score_type ORDER BY min_score DESC', [year])
    for r in rows: result['提前批_学科特长'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': r['score_type'], 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    rows = query_all('SELECT DISTINCT high_school as school_name, school_attr, fee_type, MIN(min_score) as min_score FROM quota WHERE year=? AND min_score IS NOT NULL GROUP BY high_school ORDER by min_score DESC', [year])
    for r in rows: result['提前批_指标生'].append({'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'admission_type': '指标生', 'min_score': r['min_score'], 'min_score_5subj': r['min_score'] - sport})
    return jsonify(result)

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

    def do_match(score, grades, p_type):
        if not score: return {'rush': [], 'stable': [], 'backup': [], 'grade_failed': [], 'has_c_grade': False, 'c_grade_note': ''}
        grade_subjects = {'A': ['生物', '地理', '历史', '道法'], 'B': ['生物', '地理', '物理', '化学']}.get(p_type, [])
        has_c = any(grades.get(sub, 'C') == 'C' for sub in grade_subjects)
        if p_type == 'B' and has_c:
            return {'rush': [], 'stable': [], 'backup': [], 'has_c_grade': True, 'c_grade_note': 'B 类等级含 C，无法报考任何学校（B 类只有普通高中计划）'}
        if p_type == 'A' and has_c:
            return {'rush': [], 'stable': [], 'backup': [], 'has_c_grade': True, 'c_grade_note': 'A 类等级含 C，无法报考普通高中（公费/自费/参公），但可以报考中职学校', 'can_apply_zhi_zhong': True}
        sport_current = 80
        sport_line = get_sport_score(year)
        target_plan = 'A 类计划' if p_type == 'A' else 'B 类计划'
        sql = 'SELECT school_name, school_attr, fee_type, batch, plan_type, min_score, subject_grade_req, subject_grade_total_req FROM scores WHERE year=? AND school_type = "普通高中" AND score_type = "普通高中" AND substr(plan_type, 1, 1) = ? AND min_score IS NOT NULL ORDER BY min_score DESC'
        rows = query_all(sql, [year, target_plan[0]])
        results = []
        grade_failed = []
        for r in rows:
            grade_check = check_detailed_grade_req(grades, r.get('subject_grade_req'), r.get('subject_grade_total_req'), p_type)
            diff = score - r['min_score'] - (sport_current - sport_line)
            entry = {'school_name': r['school_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'plan_type': r['plan_type'], 'min_score': r['min_score'], 'min_score_2026': r['min_score'] + 30 if r['min_score'] else None, 'diff': diff, 'grade_pass': grade_check['pass'], 'grade_reason': grade_check.get('reason', '')}
            if grade_check['pass']:
                results.append(entry)
            else:
                grade_failed.append(entry)
        rush = [r for r in results if -10 <= r['diff'] <= 10]
        stable = [r for r in results if 10 < r['diff'] <= 30]
        backup = [r for r in results if r['diff'] > 30]
        rush.sort(key=lambda x: x['diff'])
        stable.sort(key=lambda x: x['diff'])
        backup.sort(key=lambda x: -x['min_score'])
        grade_failed.sort(key=lambda x: x['grade_reason'])
        result = {'rush': rush, 'stable': stable, 'backup': backup, 'grade_failed': grade_failed, 'has_c_grade': False, 'c_grade_note': ''}
        if p_type == 'A':
            result['can_apply_zhi_zhong'] = True
        return result

    if school_type == 'pg':
        return jsonify({
            'score_a': score_a, 'score_b': score_b,
            'user_total_a': calc_total(grades_a), 'user_total_b': calc_total(grades_b),
            'res_a': do_match(score_a, grades_a, 'A'),
            'res_b': do_match(score_b, grades_b, 'B'),
            'year': year
        })
    elif school_type == 'voc':
        rows = query_all('SELECT school_name, major_name, school_attr, fee_type, batch, plan_type, min_score FROM scores WHERE year=? AND school_type = "中职学校" AND min_score IS NOT NULL GROUP BY school_name, major_name ORDER BY min_score DESC', [year])
        score_5subj = (score_a or 0) - sport
        results = [{'school_name': r['school_name'], 'major_name': r['major_name'], 'school_attr': r['school_attr'], 'fee_type': r['fee_type'], 'batch': r['batch'], 'plan_type': r['plan_type'], 'min_score': r['min_score'], 'min_score_2026': r['min_score'] + 30 if r['min_score'] else None, 'diff': score_5subj - (r['min_score'] - sport)} for r in rows]
        return jsonify({'score': score_a, 'zhizhong': results, 'year': year, 'type': 'voc'})
    return jsonify({'error': 'Invalid school type'}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)