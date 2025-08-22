from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import yaml, uuid
import xlsxwriter, xlrd2
from io import BytesIO
from datetime import datetime
import os

app = Flask(__name__)
DATABASE_FILE = 'database.yaml'
PORT = int(os.environ.get('PORT', 10000))

# --- utilitaires ---
def init_database():
    if not os.path.exists(DATABASE_FILE):
        save_data({'primaire': [], 'secondaire': [], 'paiements': {}, 'notes': {}})

def load_data():
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_data(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True)

# --- 1. ACCUEIL ---
@app.route('/')
def index():
    return render_template('index.html')

# --- 2. INSCRIPTION ---
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
        save_data(data)
        return redirect(url_for('index'))
    return render_template('register.html')

# --- 3. LISTE PAR CLASSE ---
@app.route('/students')
def students():
    data = load_data()
    classes_primaire = ['MATERNELLE', 'CP', 'CE1', 'CE2', 'CM1', 'CM2']
    classes_secondaire = ['6ème', '5ème', '4ème', '3ème']
    grouped = {}
    for cls in classes_primaire + classes_secondaire:
        grouped[cls] = [s for s in data['primaire'] + data['secondaire'] if s['classe'] == cls]
    return render_template('students.html', grouped=grouped)

# --- 4. MODIFIER / SUPPRIMER ---
@app.route('/edit_delete')
def edit_delete():
    data = load_data()
    return render_template('edit_delete.html', students=data['primaire'] + data['secondaire'])

@app.route('/delete/<student_id>', methods=['POST'])
def delete_student(student_id):
    password = request.json.get('password')
    if password != 'arrow':
        return jsonify({'success': False, 'message': 'Mot de passe incorrect'})
    data = load_data()
    for group in ['primaire', 'secondaire']:
        data[group] = [s for s in data[group] if s['id'] != student_id]
    save_data(data)
    return jsonify({'success': True})

# --- 5. SCOLARITÉ / PAIEMENT ---
@app.route('/scolarite')
def scolarite():
    data = load_data()
    return render_template('scolarite.html', students=data['primaire'] + data['secondaire'])

@app.route('/pay/<student_id>', methods=['POST'])
def pay(student_id):
    data = request.get_json()
    if data.get('password') != 'kouame':
        return jsonify({'success': False, 'message': 'Mot de passe incorrect'})
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Montant invalide'})
    data = load_data()
    for s in data['primaire'] + data['secondaire']:
        if s['id'] == student_id:
            s['frais_scolarite'] = max(0, s['frais_scolarite'] - amount)
            save_data(data)
            return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Élève introuvable'})

# --- 6. NOTES ---
@app.route('/notes', methods=['GET', 'POST'])
def notes():
    if request.method == 'POST':
        prof = request.form['professeur']
        matiere = request.form['matiere']
        classe = request.form['classe']
        data = load_data()
        eleves = [s for s in data['primaire'] + data['secondaire'] if s['classe'] == classe]
        return render_template('notes_list.html', prof=prof, matiere=matiere, classe=classe, eleves=eleves)
    return render_template('notes_form.html')

@app.route('/add_note', methods=['POST'])
def add_note():
    data = request.get_json()
    student_id = data['student_id']
    matiere = data['matiere']
    note = float(data['note'])
    data = load_data()
    for s in data['primaire'] + data['secondaire']:
        if s['id'] == student_id:
            s.setdefault('notes', {})
            s['notes'][matiere] = note
            save_data(data)
            return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/edit_note', methods=['POST'])
def edit_note():
    if request.json.get('password') != 'Kouamé':
        return jsonify({'success': False, 'message': 'Mot de passe incorrect'})
    student_id = request.json['student_id']
    matiere = request.json['matiere']
    note = float(request.json['note'])
    data = load_data()
    for s in data['primaire'] + data['secondaire']:
        if s['id'] == student_id:
            s['notes'][matiere] = note
            save_data(data)
            return jsonify({'success': True})
    return jsonify({'success': False})

# --- 7. RECAPITULATIF ---
@app.route('/recap')
def recap():
    data = load_data()
    return render_template('recap.html', students=data['primaire'] + data['secondaire'])

# --- 8. EXPORT / IMPORT EXCEL ---
@app.route('/export_excel')
def export_excel():
    data = load_data()
    all_students = data['primaire'] + data['secondaire']
    buffer = BytesIO()
    wb = xlsxwriter.Workbook(buffer, {'in_memory': True})
    ws = wb.add_worksheet('Global')
    headers = ['Nom', 'Prénoms', 'Classe', 'Frais', 'Matières_Notes', 'Professeur', 'Directrice']
    for col, h in enumerate(headers):
        ws.write(0, col, h)
    row = 1
    for s in all_students:
        notes = ', '.join([f"{m}:{n}" for m, n in s.get('notes', {}).items()])
        ws.write(row, 0, s['nom'])
        ws.write(row, 1, s['prenoms'])
        ws.write(row, 2, s['classe'])
        ws.write(row, 3, s['frais_scolarite'])
        ws.write(row, 4, notes)
        ws.write(row, 5, s['utilisateur'].get('professeur', ''))
        ws.write(row, 6, s['utilisateur'].get('directrice', ''))
        row += 1
    wb.close()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='inscriptions.xlsx')

@app.route('/import_excel', methods=['GET', 'POST'])
def import_excel():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            import xlrd2
            wb = xlrd2.open_workbook(file_contents=file.read())
            ws = wb.sheet_by_index(0)
            data = load_data()
            classes_primaire = ['MATERNELLE', 'CP', 'CE1', 'CE2', 'CM1', 'CM2']
            for row_idx in range(1, ws.nrows):
                row = ws.row(row_idx)
                student = {
                    'id': str(uuid.uuid4()),
                    'nom': str(row[0].value).upper(),
                    'prenoms': str(row[1].value).title(),
                    'classe': str(row[2].value),
                    'date_naissance': str(row[3].value),
                    'parent_phone': str(row[4].value),
                    'frais_scolarite': float(row[5].value),
                    'utilisateur': {
                        'maitre': str(row[6].value) if len(row) > 6 else '',
                        'professeur': str(row[7].value) if len(row) > 7 else '',
                        'directrice': str(row[8].value) if len(row) > 8 else ''
                    },
                    'date_inscription': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                group = 'primaire' if student['classe'].upper() in classes_primaire else 'secondaire'
                data.setdefault(group, [])
                data[group].append(student)
            save_data(data)
            return redirect(url_for('index'))
    return render_template('import_excel.html')

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=PORT, debug=True)
