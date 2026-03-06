"""
Flask Application — Job Skill Portal
Full-stack web app with BST visualization, Random Forest predictions, and job browsing.
"""

import os
import ast
import re
import sqlite3
import json
from flask import Flask, render_template, request, jsonify
import pandas as pd
from bst import BST
from ml_model import predict_category, get_metrics, get_feature_importance, load_and_preprocess

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'job_portal.db')
CSV_PATH = os.path.join(BASE_DIR, 'all_job_post.csv')

# Global BST instances
skill_tree = BST()
prediction_tree = BST()  # BST for prediction history (name -> prediction)
prediction_counter = 0   # Auto-increment prediction ID


# ─────────────────────────────────────────────
# Database Setup
# ─────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite database from CSV."""
    if os.path.exists(DB_PATH):
        conn = get_db()
        cursor = conn.execute("SELECT COUNT(*) FROM jobs")
        count = cursor.fetchone()[0]
        conn.close()
        if count > 0:
            print(f"Database already populated with {count} jobs.")
            return

    print("Initializing database from CSV...")
    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip().str.lower()

    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        category TEXT,
        job_title TEXT,
        job_description TEXT,
        job_skill_set TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS skills (
        skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name TEXT UNIQUE,
        frequency INTEGER DEFAULT 0
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS job_skills (
        job_id TEXT,
        skill_id INTEGER,
        FOREIGN KEY (job_id) REFERENCES jobs(job_id),
        FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_skills TEXT,
        predicted_category TEXT,
        confidence REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Insert jobs
    for _, row in df.iterrows():
        try:
            conn.execute(
                'INSERT OR IGNORE INTO jobs VALUES (?, ?, ?, ?, ?)',
                (str(row.get('job_id', '')), str(row.get('category', '')),
                 str(row.get('job_title', '')), str(row.get('job_description', '')),
                 str(row.get('job_skill_set', '')))
            )
        except Exception:
            continue

    # Extract and insert skills
    skill_freq = {}
    for _, row in df.iterrows():
        skills_str = str(row.get('job_skill_set', ''))
        skills = parse_skills(skills_str)
        for skill in skills:
            skill = skill.lower().strip()
            if skill and len(skill) > 1:
                skill_freq[skill] = skill_freq.get(skill, 0) + 1

    for skill_name, freq in skill_freq.items():
        try:
            conn.execute(
                'INSERT OR IGNORE INTO skills (skill_name, frequency) VALUES (?, ?)',
                (skill_name, freq)
            )
        except Exception:
            continue

    conn.commit()
    conn.close()
    print(f"Database initialized with {len(df)} jobs and {len(skill_freq)} unique skills.")


def parse_skills(skill_str):
    """Parse skill string into list."""
    if pd.isna(skill_str) or not skill_str or skill_str == 'nan':
        return []
    try:
        skills = ast.literal_eval(skill_str)
        if isinstance(skills, list):
            return [s.strip().lower() for s in skills if isinstance(s, str) and s.strip()]
    except (ValueError, SyntaxError):
        pass
    skill_str = re.sub(r"[\[\]']", '', str(skill_str))
    return [s.strip().lower() for s in skill_str.split(',') if s.strip()]


def build_bst():
    """Build BST from database skills."""
    global skill_tree
    skill_tree = BST()

    conn = get_db()
    rows = conn.execute('SELECT job_id, job_skill_set FROM jobs').fetchall()
    conn.close()

    count = 0
    for row in rows:
        skills = parse_skills(row['job_skill_set'])
        for skill in skills:
            skill = skill.lower().strip()
            if skill and len(skill) > 1 and len(skill) < 80:
                skill_tree.insert(skill, row['job_id'])
                count += 1

    print(f"BST built with {skill_tree.size} unique skill nodes from {count} skill-job associations.")


# ─────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    conn = get_db()
    total_jobs = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
    total_skills = conn.execute('SELECT COUNT(*) FROM skills').fetchone()[0]
    categories = conn.execute('SELECT DISTINCT category FROM jobs').fetchall()
    conn.close()

    metrics = get_metrics()
    accuracy = metrics['accuracy'] * 100 if metrics else 0

    return render_template('index.html',
                           total_jobs=total_jobs,
                           total_skills=total_skills,
                           num_categories=len(categories),
                           accuracy=accuracy,
                           bst_nodes=skill_tree.size,
                           bst_height=skill_tree.get_height())


@app.route('/predict')
def predict_page():
    conn = get_db()
    skills = conn.execute('SELECT skill_name FROM skills ORDER BY frequency DESC LIMIT 100').fetchall()
    conn.close()
    return render_template('predict.html', popular_skills=[s['skill_name'] for s in skills])


@app.route('/prediction-bst')
def prediction_bst_page():
    return render_template('prediction_bst.html', bst_stats=prediction_tree.get_stats())


@app.route('/browse')
def browse_page():
    conn = get_db()
    categories = conn.execute('SELECT DISTINCT category FROM jobs ORDER BY category').fetchall()
    conn.close()
    return render_template('browse.html', categories=[c['category'] for c in categories])


@app.route('/bst')
def bst_page():
    return render_template('bst.html', bst_stats=skill_tree.get_stats())


@app.route('/dashboard')
def dashboard_page():
    metrics = get_metrics()
    feature_imp = get_feature_importance(20)
    top_skills = skill_tree.get_top_skills(20)
    return render_template('dashboard.html',
                           metrics=metrics,
                           feature_importance=feature_imp,
                           top_skills=top_skills)


@app.route('/about')
def about_page():
    return render_template('about.html')


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

@app.route('/api/predict', methods=['POST'])
def api_predict():
    global prediction_counter
    data = request.get_json()
    skills = data.get('skills', '')
    name = data.get('name', '').strip()
    if not skills:
        return jsonify({'error': 'No skills provided'}), 400
    if not name:
        return jsonify({'error': 'No name provided'}), 400

    results = predict_category(skills)

    # Auto-increment prediction ID
    prediction_counter += 1
    pred_id = prediction_counter

    # Save prediction to database
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO predictions (input_skills, predicted_category, confidence) VALUES (?, ?, ?)',
            (skills, results[0]['category'], results[0]['confidence'])
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

    # Insert into prediction BST (key = name, stores prediction ID)
    prediction_tree.insert(name, str(pred_id))

    return jsonify({
        'predictions': results,
        'input_skills': skills,
        'name': name,
        'prediction_id': pred_id,
        'prediction_bst_stats': prediction_tree.get_stats()
    })


@app.route('/api/jobs')
def api_jobs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    conn = get_db()
    query = 'SELECT job_id, category, job_title, job_skill_set FROM jobs WHERE 1=1'
    params = []

    if category:
        query += ' AND UPPER(category) = ?'
        params.append(category.upper())
    if search:
        query += ' AND (LOWER(job_title) LIKE ? OR LOWER(job_skill_set) LIKE ?)'
        params.extend([f'%{search.lower()}%', f'%{search.lower()}%'])

    # Count total
    count_q = query.replace('SELECT job_id, category, job_title, job_skill_set', 'SELECT COUNT(*)')
    total = conn.execute(count_q, params).fetchone()[0]

    # Paginate
    query += f' LIMIT {per_page} OFFSET {(page - 1) * per_page}'
    rows = conn.execute(query, params).fetchall()
    conn.close()

    jobs = []
    for r in rows:
        skills = parse_skills(r['job_skill_set'])
        jobs.append({
            'job_id': r['job_id'],
            'category': r['category'],
            'job_title': r['job_title'],
            'skills': skills[:10]
        })

    return jsonify({
        'jobs': jobs,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })


@app.route('/api/job/<job_id>')
def api_job_detail(job_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM jobs WHERE job_id = ?', (job_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Job not found'}), 404

    skills = parse_skills(row['job_skill_set'])
    return jsonify({
        'job_id': row['job_id'],
        'category': row['category'],
        'job_title': row['job_title'],
        'job_description': row['job_description'][:2000],
        'skills': skills
    })


@app.route('/api/bst/tree')
def api_bst_tree():
    max_depth = request.args.get('max_depth', 6, type=int)
    tree_data = skill_tree.to_dict(max_depth=max_depth)
    return jsonify({
        'tree': tree_data,
        'stats': skill_tree.get_stats()
    })


@app.route('/api/bst/insert', methods=['POST'])
def api_bst_insert():
    data = request.get_json()
    skill = data.get('skill', '').strip()
    if not skill:
        return jsonify({'error': 'No skill provided'}), 400

    skill_tree.insert(skill)
    return jsonify({
        'message': f'Skill "{skill}" inserted successfully',
        'stats': skill_tree.get_stats()
    })


@app.route('/api/bst/search', methods=['POST'])
def api_bst_search():
    data = request.get_json()
    skill = data.get('skill', '').strip()
    if not skill:
        return jsonify({'error': 'No skill provided'}), 400

    path = skill_tree.search_path(skill)
    node = skill_tree.search(skill)

    result = {
        'found': node is not None,
        'skill': skill,
        'path': path,
        'path_length': len(path)
    }
    if node:
        result['frequency'] = node.frequency
        result['job_count'] = len(node.job_ids)

    return jsonify(result)


@app.route('/api/bst/delete', methods=['POST'])
def api_bst_delete():
    data = request.get_json()
    skill = data.get('skill', '').strip()
    if not skill:
        return jsonify({'error': 'No skill provided'}), 400

    node = skill_tree.search(skill)
    if not node:
        return jsonify({'error': f'Skill "{skill}" not found'}), 404

    skill_tree.delete(skill)
    return jsonify({
        'message': f'Skill "{skill}" deleted successfully',
        'stats': skill_tree.get_stats()
    })


@app.route('/api/bst/traverse', methods=['POST'])
def api_bst_traverse():
    data = request.get_json()
    traversal_type = data.get('type', 'inorder')
    limit = data.get('limit', 50)

    if traversal_type == 'inorder':
        result = skill_tree.inorder()
    elif traversal_type == 'preorder':
        result = skill_tree.preorder()
    elif traversal_type == 'postorder':
        result = skill_tree.postorder()
    else:
        return jsonify({'error': 'Invalid traversal type'}), 400

    return jsonify({
        'type': traversal_type,
        'result': result[:limit],
        'total': len(result)
    })


@app.route('/api/bst/top-skills')
def api_bst_top_skills():
    n = request.args.get('n', 20, type=int)
    return jsonify({'skills': skill_tree.get_top_skills(n)})


@app.route('/api/stats')
def api_stats():
    conn = get_db()
    total_jobs = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
    categories = conn.execute(
        'SELECT category, COUNT(*) as cnt FROM jobs GROUP BY category ORDER BY cnt DESC'
    ).fetchall()
    conn.close()

    metrics = get_metrics()

    return jsonify({
        'total_jobs': total_jobs,
        'categories': [{'name': c['category'], 'count': c['cnt']} for c in categories],
        'model_metrics': metrics,
        'bst_stats': skill_tree.get_stats()
    })


@app.route('/api/metrics')
def api_metrics():
    metrics = get_metrics()
    if not metrics:
        return jsonify({'error': 'No metrics found. Train the model first.'}), 404
    return jsonify(metrics)


# ─────────────────────────────────────────────
# Prediction BST API Routes
# ─────────────────────────────────────────────

@app.route('/api/prediction-bst/tree')
def api_prediction_bst_tree():
    max_depth = request.args.get('max_depth', 10, type=int)
    tree_data = prediction_tree.to_dict(max_depth=max_depth)
    return jsonify({
        'tree': tree_data,
        'stats': prediction_tree.get_stats()
    })


@app.route('/api/prediction-bst/search', methods=['POST'])
def api_prediction_bst_search():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'No name provided'}), 400

    path = prediction_tree.search_path(name)
    node = prediction_tree.search(name)

    result = {
        'found': node is not None,
        'name': name,
        'path': path,
        'path_length': len(path)
    }
    if node:
        result['prediction_ids'] = list(node.job_ids)
        result['prediction_count'] = len(node.job_ids)

    return jsonify(result)


@app.route('/api/prediction-bst/traverse', methods=['POST'])
def api_prediction_bst_traverse():
    data = request.get_json()
    traversal_type = data.get('type', 'inorder')
    limit = data.get('limit', 100)

    if traversal_type == 'inorder':
        result = prediction_tree.inorder()
    elif traversal_type == 'preorder':
        result = prediction_tree.preorder()
    elif traversal_type == 'postorder':
        result = prediction_tree.postorder()
    else:
        return jsonify({'error': 'Invalid traversal type'}), 400

    return jsonify({
        'type': traversal_type,
        'result': result[:limit],
        'total': len(result)
    })


@app.route('/api/prediction-bst/clear', methods=['POST'])
def api_prediction_bst_clear():
    global prediction_tree, prediction_counter
    prediction_tree = BST()
    prediction_counter = 0
    return jsonify({'message': 'Prediction BST cleared', 'stats': prediction_tree.get_stats()})


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    build_bst()
    app.run(debug=True, port=5000)
