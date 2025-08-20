from flask import Flask, render_template, request, redirect, url_for, jsonify
import yaml
import os
from datetime import datetime
import uuid

app = Flask(__name__)

DATABASE_FILE = 'database.yaml'
PORT = int(os.environ.get('PORT', 10000))

def init_database():
    if not os.path.exists(DATABASE_FILE):
        data = {'primaire': [], 'secondaire': [], 'paiements': {}}
        save_data(data)

def load_data():
    with open(DATABASE_FILE, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def save_data(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as file:
        yaml.dump(data, file, allow_unicode=True, default_flow_style=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = load_data()
        student = {
            'id': str(uuid.uuid4()),
            'nom': request.form['nom'].upper(),
            'prenoms': request.form['prenoms'].title(),
            'classe': request.form['classe'],
            'date_naissance': request.form['date_naissance'],
            'parent_phone': request.form['parent_phone'],
            'date_inscription': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'frais_scolarite': {
                'total': float(request.form['frais_scolarite']),
                'paye': 0.0,
                'reste': float(request.form['frais_scolarite'])
            }
        }
        classes_primaire = ['MATERNELLE', 'CP', 'CE1', 'CE2', 'CM1', 'CM2']
        group = 'primaire' if student['classe'].upper() in classes_primaire else 'secondaire'
        data[group].append(student)
        data['paiements'][student['id']] = []
        save_data(data)
        return redirect(url_for('students'))
    return render_template('register.html')

@app.route('/students')
def students():
    data = load_data()
    return render_template('students.html', primaire=data['primaire'], secondaire=data['secondaire'])

@app.route('/scolarite')
def scolarite():
    data = load_data()
    return render_template('scolarite.html', primaire=data['primaire'], secondaire=data['secondaire'])

@app.route('/edit/<student_id>')
def edit(student_id):
    data = load_data()
    for group in ['primaire', 'secondaire']:
        for s in data[group]:
            if s['id'] == student_id:
                return render_template('edit.html', student=s)
    return "Élève non trouvé", 404

@app.route('/update/<student_id>', methods=['POST'])
def update(student_id):
    data = load_data()
    for group in ['primaire', 'secondaire']:
        for i, s in enumerate(data[group]):
            if s['id'] == student_id:
                s['nom'] = request.form['nom'].upper()
                s['prenoms'] = request.form['prenoms'].title()
                s['classe'] = request.form['classe']
                s['date_naissance'] = request.form['date_naissance']
                s['parent_phone'] = request.form['parent_phone']
                nouveau_frais = float(request.form['frais_scolarite'])
                s['frais_scolarite']['total'] = nouveau_frais
                s['frais_scolarite']['reste'] = nouveau_frais - s['frais_scolarite']['paye']
                save_data(data)
                return redirect(url_for('scolarite'))
    return "Élève non trouvé", 404

@app.route('/api/payer/<student_id>', methods=['POST'])
def api_payer(student_id):
    data = load_data()
    student = None
    for group in ['primaire', 'secondaire']:
        for s in data[group]:
            if s['id'] == student_id:
                student = s
                break
    if not student:
        return jsonify({'error': 'Élève non trouvé'}), 404

    montant = float(request.json.get('montant', 0))
    if montant <= 0:
        return jsonify({'error': 'Montant invalide'}), 400

    student['frais_scolarite']['paye'] += montant
    student['frais_scolarite']['reste'] -= montant
    data['paiements'][student_id].append({
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'montant': montant
    })
    save_data(data)

    return jsonify({
        'success': True,
        'paye': student['frais_scolarite']['paye'],
        'reste': student['frais_scolarite']['reste']
    })

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=PORT, debug=True)
        
