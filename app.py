from flask import Flask, render_template, request, redirect, url_for, jsonify
import yaml
import os
from datetime import datetime
import uuid

app = Flask(__name__)

# Configuration
DATABASE_FILE = 'database.yaml'
PORT = int(os.environ.get('PORT', 10000))

# Initialisation de la base de données YAML
def init_database():
    if not os.path.exists(DATABASE_FILE):
        data = {
            'primaire': [],
            'secondaire': [],
            'paiements': {}
        }
        save_data(data)

def load_data():
    with open(DATABASE_FILE, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def save_data(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as file:
        yaml.dump(data, file, allow_unicode=True, default_flow_style=False)

# Routes
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
        
        # Classification primaire/secondaire
        classes_primaire = ['MATERNELLE', 'CP', 'CE1', 'CE2', 'CM1', 'CM2']
        if student['classe'].upper() in classes_primaire:
            data['primaire'].append(student)
        else:
            data['secondaire'].append(student)
        
        # Initialisation des paiements
        data['paiements'][student['id']] = []
        
        save_data(data)
        return redirect(url_for('students'))
    
    return render_template('register.html')

@app.route('/students')
def students():
    data = load_data()
    return render_template('students.html', 
                         primaire=data['primaire'], 
                         secondaire=data['secondaire'])

@app.route('/search')
def search():
    query = request.args.get('q', '').lower()
    data = load_data()
    
    results = []
    for student in data['primaire'] + data['secondaire']:
        if query in student['nom'].lower() or query in student['prenoms'].lower():
            results.append(student)
    
    return jsonify(results)

@app.route('/edit/<student_id>')
def edit(student_id):
    data = load_data()
    
    student = None
    for s in data['primaire'] + data['secondaire']:
        if s['id'] == student_id:
            student = s
            break
    
    if not student:
        return "Élève non trouvé", 404
    
    return render_template('edit.html', student=student)

@app.route('/update/<student_id>', methods=['POST'])
def update(student_id):
    data = load_data()
    
    student = None
    for group in ['primaire', 'secondaire']:
        for i, s in enumerate(data[group]):
            if s['id'] == student_id:
                student = s
                student_index = i
                student_group = group
                break
    
    if not student:
        return "Élève non trouvé", 404
    
    # Mise à jour des informations
    student['nom'] = request.form['nom'].upper()
    student['prenoms'] = request.form['prenoms'].title()
    student['classe'] = request.form['classe']
    student['date_naissance'] = request.form['date_naissance']
    student['parent_phone'] = request.form['parent_phone']
    
    # Vérifier le changement de groupe (primaire/secondaire)
    classes_primaire = ['MATERNELLE', 'CP', 'CE1', 'CE2', 'CM1', 'CM2']
    new_group = 'primaire' if student['classe'].upper() in classes_primaire else 'secondaire'
    
    if new_group != student_group:
        data[student_group].pop(student_index)
        data[new_group].append(student)
    
    # Mise à jour des frais
    nouveau_frais = float(request.form['frais_scolarite'])
    ancien_total = student['frais_scolarite']['total']
    
    student['frais_scolarite']['total'] = nouveau_frais
    student['frais_scolarite']['reste'] = nouveau_frais - student['frais_scolarite']['paye']
    
    save_data(data)
    return redirect(url_for('students'))

@app.route('/pay/<student_id>', methods=['POST'])
def pay(student_id):
    data = load_data()
    
    student = None
    for s in data['primaire'] + data['secondaire']:
        if s['id'] == student_id:
            student = s
            break
    
    if not student:
        return "Élève non trouvé", 404
    
    montant = float(request.form['montant'])
    
    # Enregistrer le paiement
    paiement = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'montant': montant
    }
    
    data['paiements'][student_id].append(paiement)
    
    # Mettre à jour les frais
    student['frais_scolarite']['paye'] += montant
    student['frais_scolarite']['reste'] -= montant
    
    save_data(data)
    return redirect(url_for('students'))

if __name__ == '__main__':
    init_database()
    app.run(host='0.0.0.0', port=PORT, debug=True)
