from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import yaml, uuid, pandas as pd
from io import BytesIO
from datetime import datetime
import os

app = Flask(__name__)
DATABASE_FILE = 'database.yaml'
PORT = int(os.environ.get('PORT', 10000))

def init_database():
    if not os.path.exists(DATABASE_FILE):
        save_data({'primaire': [], 'secondaire': [], 'paiements': {}})

def load_data():
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_data(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    classes_primaire = ['MATERNELLE', 'CP', 'CE1', 'CE2', 'CM1', 'CM2']
    if request.method == 'POST':
        data = load_data()
        student = {
            'id': str(uuid.uuid4()),
            'nom': request.form['nom'].upper(),
            'prenoms': request.form['prenoms'].title(),
            'classe': request.form['classe'],
            'date_naissance': request.form['date_naissance'],
            'parent_phone': request.form['parent_phone'],
            'frais_scolarite': float(request.form['frais_scolarite']),
            'utilisateur': {
                'maitre': request.form.get('maitre', ''),
                'professeur': request.form.get('professeur', ''),
                'directrice': request.form.get('directrice', '')
            },
            'date_inscription': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        group = 'primaire' if student['classe'].upper() in classes_primaire else 'secondaire'
        data.setdefault(group, [])
        data[group].append(student)
        data.setdefault('paiements', {})
        data['paiements'][student['id']] = []
        save_data(data)
        return redirect(url_for('students', saved='ok'))
    return render_template('register.html')

@app.route('/students')
def students():
    data = load_data()
    classes_primaire = ['MATERNELLE', 'CP', 'CE1', 'CE2', 'CM1', 'CM2']
    classes_secondaire = ['6ème', '5ème', '4ème', '3ème']
    grouped = {}
    for cls in classes_primaire + classes_secondaire:
        grouped[cls] = [s for s in data['primaire'] + data['secondaire'] if s['classe'] == cls]
    return render_template('students.html', grouped=grouped)

@app.route('/export')
def export_excel():
    data = load_data()
    all_students = data['primaire'] + data['secondaire']
    df = pd.json_normalize(all_students)
    df_fees = pd.json_normalize(df['frais_scolarite'])
    df = pd.concat([df.drop('frais_scolarite', axis=1), df_fees], axis=1)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inscriptions')
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='inscriptions.xlsx')

@app.route('/import', methods=['GET', 'POST'])
def import_excel():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
            data = {'primaire': [], 'secondaire': [], 'paiements': {}}
            for _, row in df.iterrows():
                student = {
                    'id': str(uuid.uuid4()),
                    'nom': str(row.get('nom', '')).upper(),
                    'prenoms': str(row.get('prenoms', '')).title(),
                    'classe': str(row.get('classe', '')),
                    'date_naissance': str(row.get('date_naissance', '')),
                    'parent_phone': str(row.get('parent_phone', '')),
                    'frais_scolarite': float(row.get('frais_scolarite', 0)),
                    'utilisateur': {
                        'maitre': str(row.get('maitre', '')),
                        'professeur': str(row.get('professeur', '')),
                        'directrice': str(row.get('directrice', ''))
                    },
                    'date_inscription': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                group = 'primaire' if student['classe'].upper() in ['MATERNELLE','CP','CE1','CE2','CM1','CM2'] else 'secondaire'
                data[group].append(student)
                data['paiements'][student['id']] = []
            save_data(data)
            return redirect(url_for('students'))
    return render_template('import.html')

@app.route('/delete/<student_id>', methods=['POST'])
def delete_student(student_id):
    password = request.json.get('password')
    if password != 'arrow':
        return jsonify({'success': False, 'message': 'Vous n\'êtes pas autorisé à supprimer.'})
    data = load_data()
    deleted = False
    for group in ['primaire', 'secondaire']:
        original = len(data[group])
        data[group] = [s for s in data[group] if s['id'] != student_id]
        if len(data[group]) < original:
            deleted = True
    if deleted:
        data['paiements'].pop(student_id, None)
        save_data(data)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Élève introuvable.'})

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=PORT, debug=True)
