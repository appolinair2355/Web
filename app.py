from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import yaml, io, xlsxwriter, xlrd2, os, uuid, re
from datetime import datetime
from decimal import Decimal

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ecole-mont-sion-secret-key')
PORT = int(os.environ.get('PORT', 10000))
DATABASE = 'database.yaml'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

SMS_SENDER = '+2290167924076'
MATIERES = ['Mathématiques', 'Français', 'Anglais', 'Histoire', 'Géographie',
            'Sciences', 'SVT', 'Physique', 'Chimie', 'Philosophie']
TRIMESTRES = ['T1', 'T2', 'T3']

class SMSService:
    def send_sms(self, to, msg):
        to = re.sub(r'\D', '', str(to))
        if len(to) >= 8:
            print(f"SMS envoyé à {to}: {msg}")
            return True
        return False
sms_service = SMSService()

# ── BASE DE DONNÉES  -------------------------------------------------
def load_data():
    try:
        with open(DATABASE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {'primaire': [], 'secondaire': []}
        for niv in ['primaire', 'secondaire']:
            for s in data.get(niv, []):
                s.setdefault('notes', {m: {t: None for t in TRIMESTRES} for m in MATIERES})
                s.setdefault('paiements', [])
        return data
    except FileNotFoundError:
        return {'primaire': [], 'secondaire': []}

def save_data(data):
    with open(DATABASE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

# ── ROUTAGE  ---------------------------------------------------------
@app.context_processor
def inject_today():
    return {'today': datetime.now().strftime('%Y-%m-%d')}

@app.route('/')
def index():
    return render_template('index.html')

# ---------------------------- INSCRIPTION ----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = load_data()
        nom = request.form.get('nom', '').strip()
        prenoms = request.form.get('prenoms', '').strip()
        classe = request.form.get('classe', '').strip()
        sexe = request.form.get('sexe', '').strip()
        date_naissance = request.form.get('date_naissance', '').strip()
        parent = request.form.get('parent', '').strip()
        parent_phone = re.sub(r'\D', '', request.form.get('parent_phone', '').strip())
        frais_total = int(request.form.get('frais', '0'))
        niveau = request.form.get('niveau', '').strip()
        utilisateur = request.form.get('utilisateur', '').strip()

        if not all([nom, prenoms, classe, sexe, date_naissance, parent, parent_phone, frais_total, niveau, utilisateur]):
            flash('Tous les champs sont obligatoires', 'error')
            return render_template('register.html')

        eleve = {
            'id': str(uuid.uuid4()),
            'nom': nom.upper(),
            'prenoms': prenoms.title(),
            'classe': classe,
            'sexe': sexe.upper(),
            'date_naissance': date_naissance,
            'parent': parent.title(),
            'parent_phone': parent_phone,
            'frais_total': frais_total,
            'notes': {m: {t: None for t in TRIMESTRES} for m in MATIERES},
            'paiements': [],
            'date_inscription': datetime.now().strftime('%d/%m/%Y')
        }
        data.setdefault(niveau, []).append(eleve)
        save_data(data)
        flash('Élève inscrit avec succès', 'success')
        return redirect(url_for('students'))
    return render_template('register.html')

# ---------------------------- LISTE ---------------------------------
@app.route('/students')
def students():
    data = load_data()
    students = data.get('primaire', []) + data.get('secondaire', [])
    classes = sorted(set(s.get('classe', 'Sans classe') for s in students))
    grouped = {cls: [s for s in students if s.get('classe') == cls] for cls in classes}
    return render_template('students.html', grouped=grouped)

# ---------------------------- NOTES ---------------------------------
@app.route('/notes', methods=['GET', 'POST'])
def notes():
    data = load_data()
    students = data.get('primaire', []) + data.get('secondaire', [])
    if request.method == 'POST':
        # Enregistrer les notes
        for student in students:
            for m in MATIERES:
                for t in TRIMESTRES:
                    key = f"{student['id']}_{m}_{t}"
                    val = request.form.get(key, '').strip()
                    student['notes'][m][t] = float(val) if val else None
        save_data(data)
        flash('Notes enregistrées', 'success')
        return redirect(url_for('notes'))

    return render_template('notes.html', students=students, matieres=MATIERES, trimestres=TRIMESTRES)

# ---------------------------- PAIEMENT ------------------------------
@app.route('/scolarite')
def scolarite():
    data = load_data()
    students = data.get('primaire', []) + data.get('secondaire', [])
    return render_template('scolarite.html', students=students)

@app.route('/pay', methods=['POST'])
def pay():
    if request.form.get('password') != 'kouame':
        flash('Mot de passe incorrect', 'error')
        return redirect(url_for('scolarite'))

    student_id = request.form.get('student_id')
    amount = int(request.form.get('amount', 0))
    data = load_data()
    for niv in ['primaire', 'secondaire']:
        for s in data[niv]:
            if s['id'] == student_id:
                s['paiements'].append({
                    'date': datetime.now().strftime('%d/%m/%Y'),
                    'montant': amount,
                    'mode': 'Espèces'
                })
                save_data(data)
                sms_service.send_sms(s['parent_phone'],
                                     f"Paiement {amount} FCFA reçu. Restant: {sum([p['montant'] for p in s['paiements']])} / {s['frais_total']} FCFA")
                flash('Paiement enregistré', 'success')
                return redirect(url_for('scolarite'))
    flash('Élève introuvable', 'error')
    return redirect(url_for('scolarite'))

# ---------------------------- IMPORT / EXPORT -----------------------
@app.route('/import_excel', methods=['GET', 'POST'])
def import_excel():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.xlsx'):
            wb = xlrd2.open_workbook(file_contents=file.read())
            ws = wb.sheet_by_index(0)
            headers = [ws.cell_value(0, c) for c in range(ws.ncols)]
            data = load_data()
            for r in range(1, ws.nrows):
                row = ws.row_values(r)
                eleve = {
                    'id': str(uuid.uuid4()),
                    'nom': str(row[headers.index('Nom')]).upper(),
                    'prenoms': str(row[headers.index('Prénoms')]).title(),
                    'classe': str(row[headers.index('Classe')]),
                    'sexe': str(row[headers.index('Sexe')]).upper(),
                    'date_naissance': str(row[headers.index('DateNaissance')]),
                    'parent': str(row[headers.index('Parent')]).title(),
                    'parent_phone': re.sub(r'\D', '', str(row[headers.index('Téléphone')])),
                    'frais_total': int(row[headers.index('FraisTotal')]),
                    'notes': {m: {t: None for t in TRIMESTRES} for m in MATIERES},
                    'paiements': []
                }
                # Notes
                for m in MATIERES:
                    for t in TRIMESTRES:
                        val = row[headers.index(f'{m}{t}')]
                        eleve['notes'][m][t] = float(val) if val else None
                # Paiements
                idx = 1
                while f'Paiement{idx}' in headers:
                    val = row[headers.index(f'Paiement{idx}')]
                    if val:
                        eleve['paiements'].append({'date': '', 'montant': int(val), 'mode': 'Import'})
                    idx += 1
                niveau = 'primaire' if eleve['classe'] in {'CI', 'CP', 'CE1', 'CE2', 'CM1', 'CM2'} else 'secondaire'
                data[niveau].append(eleve)
            save_data(data)
            flash('Import terminé', 'success')
        else:
            flash('Fichier .xlsx requis', 'error')
        return redirect(url_for('students'))
    return render_template('import_excel.html')

@app.route('/export_excel')
def export_excel():
    data = load_data()
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = wb.add_worksheet('Élèves')

    # En-têtes fixes
    headers = ['Nom', 'Prénoms', 'Classe', 'Sexe', 'DateNaissance', 'Parent', 'Téléphone', 'FraisTotal']
    # Notes
    for m in MATIERES:
        for t in TRIMESTRES:
            headers.append(f'{m}{t}')
    # Paiements dynamiques
    max_paiements = max([len(s.get('paiements', [])) for s in data['primaire'] + data['secondaire']], default=0)
    for i in range(1, max_paiements + 1):
        headers.append(f'Paiement{i}')
    headers.append('ResteAPayer')

    # Écriture
    for col, h in enumerate(headers):
        ws.write(0, col, h)
    row = 1
    students = data.get('primaire', []) + data.get('secondaire', [])
    for s in students:
        ws.write(row, 0, s['nom'])
        ws.write(row, 1, s['prenoms'])
        ws.write(row, 2, s['classe'])
        ws.write(row, 3, s['sexe'])
        ws.write(row, 4, s['date_naissance'])
        ws.write(row, 5, s['parent'])
        ws.write(row, 6, s['parent_phone'])
        ws.write(row, 7, s['frais_total'])
        col = 8
        # Notes
        for m in MATIERES:
            for t in TRIMESTRES:
                ws.write(row, col, s['notes'][m][t])
                col += 1
        # Paiements
        for idx, p in enumerate(s['paiements'], start=1):
            ws.write(row, col, p['montant'])
            col += 1
        # Reste
        reste = s['frais_total'] - sum([p['montant'] for p in s['paiements']])
        ws.write(row, col, reste)
        row += 1

    wb.close()
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue()),
                     as_attachment=True,
                     download_name=f"export_complet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

# ---------------------------- EDIT / DELETE -------------------------
@app.route('/edit/<sid>', methods=['GET', 'POST'])
def edit(sid):
    data = load_data()
    student = None
    niveau = None
    for n in ['primaire', 'secondaire']:
        for s in data[n]:
            if s['id'] == sid:
                student, niveau = s, n
    if not student:
        flash('Élève introuvable', 'error')
        return redirect(url_for('edit_delete'))

    if request.method == 'POST':
        student['nom'] = request.form['nom'].upper()
        student['prenoms'] = request.form['prenoms'].title()
        student['classe'] = request.form['classe']
        student['sexe'] = request.form['sexe'].upper()
        student['date_naissance'] = request.form['date_naissance']
        student['parent'] = request.form['parent'].title()
        student['parent_phone'] = re.sub(r'\D', '', request.form['parent_phone'])
        student['frais_total'] = int(request.form['frais_total'])
        save_data(data)
        flash('Modifications enregistrées', 'success')
        return redirect(url_for('students'))
    return render_template('edit.html', student=student)

@app.route('/delete/<sid>', methods=['POST'])
def delete(sid):
    data = load_data()
    for n in ['primaire', 'secondaire']:
        data[n] = [s for s in data[n] if s['id'] != sid]
    save_data(data)
    flash('Élève supprimé', 'success')
    return redirect(url_for('students'))

@app.route('/edit_delete')
def edit_delete():
    data = load_data()
    students = data['primaire'] + data['secondaire']
    return render_template('edit_delete.html', students=students)

# ---------------------------- ERREURS -------------------------------
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
