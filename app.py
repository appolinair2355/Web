from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from ruamel.yaml import YAML
from tablib import Dataset
import os
import io
from datetime import datetime

app = Flask(__name__)
app.secret_key = "kouame2025"

DATA_DIR = "data"
YAML_FILE = os.path.join(DATA_DIR, "inscriptions.yaml")
os.makedirs(DATA_DIR, exist_ok=True)

yaml = YAML(typ='safe')
yaml.default_flow_style = False

# ---------- helpers ----------
def load_yaml():
    if not os.path.exists(YAML_FILE):
        return {"eleves": []}
    with open(YAML_FILE, "r", encoding="utf-8") as f:
        data = yaml.load(f)
        return data if data else {"eleves": []}

def save_yaml(data):
    with open(YAML_FILE, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

# ---------- routes ----------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/inscription", methods=["GET", "POST"])
def inscription():
    if request.method == "POST":
        eleve = {
            "nom": request.form["nom"],
            "prenoms": request.form["prenoms"],
            "classe": request.form["classe"],
            "date_naissance": request.form["date_naissance"],
            "contact": request.form["contact"],
            "prix_scolarite": int(request.form["prix_scolarite"]),
            "enregistre_par": request.form["enregistre_par"],
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "paiements": [],
            "notes": {}
        }
        data = load_yaml()
        data["eleves"].append(eleve)
        save_yaml(data)
        flash("Inscription enregistrée avec succès.", "success")
        return redirect(url_for("inscription"))
    return render_template("inscription.html")

@app.route("/liste")
def liste():
    data = load_yaml()
    return render_template("liste.html", eleves=data["eleves"])

@app.route("/scolarite", methods=["GET", "POST"])
def scolarite():
    if request.method == "POST":
        if request.form.get("password") != "kouame":
            flash("Mot de passe incorrect.", "danger")
            return redirect(url_for("scolarite"))
        session["auth_scolarite"] = True
        return redirect(url_for("scolarite"))

    if not session.get("auth_scolarite"):
        return render_template("scolarite_login.html")

    data = load_yaml()
    return render_template("scolarite.html", eleves=data["eleves"])

@app.route("/payer/<int:index>", methods=["POST"])
def payer(index):
    if not session.get("auth_scolarite"):
        return redirect(url_for("scolarite"))
    montant = int(request.form["montant"])
    data = load_yaml()
    if 0 <= index < len(data["eleves"]):
        data["eleves"][index]["paiements"].append({
            "date": datetime.now().isoformat(timespec="seconds"),
            "montant": montant
        })
        save_yaml(data)
        flash("Paiement enregistré.", "success")
    return redirect(url_for("scolarite"))

@app.route("/note", methods=["GET", "POST"])
def note():
    data = load_yaml()
    if request.method == "POST":
        prof = request.form["prof"]
        matiere = request.form["matiere"]
        coeff = int(request.form["coefficient"])
        classe = request.form["classe"]

        eleves = [e for e in data["eleves"] if e["classe"] == classe]
        return render_template("note_list.html",
                               prof=prof,
                               matiere=matiere,
                               coefficient=coeff,
                               classe=classe,
                               eleves=eleves)

    classes = sorted(set(e["classe"] for e in data["eleves"]))
    return render_template("note.html", classes=classes)

@app.route("/save_note", methods=["POST"])
def save_note():
    data = load_yaml()
    classe = request.form["classe"]
    matiere = request.form["matiere"]
    prof = request.form["prof"]
    coeff = int(request.form["coefficient"])

    for key, val in request.form.items():
        if key.startswith("note_"):
            idx = int(key.split("_")[1])
            if idx < len(data["eleves"]) and data["eleves"][idx]["classe"] == classe:
                data["eleves"][idx].setdefault("notes", {})
                data["eleves"][idx]["notes"][matiere] = {
                    "coefficient": coeff,
                    "note": float(val),
                    "professeur": prof
                }
    save_yaml(data)
    flash("Notes enregistrées !", "success")
    return redirect(url_for("note"))

@app.route("/import_export")
def import_export():
    return render_template("import_export.html")

@app.route("/export")
def export_xlsx():
    data = load_yaml()
    ds = Dataset(headers=["Nom", "Prénoms", "Classe", "Date naissance",
                          "Téléphone tuteur", "Prix scolarité (FCFA)",
                          "Enregistré par", "Date création", "Paiements", "Notes"])
    for e in data["eleves"]:
        paiements = "; ".join([f"{p['montant']} FCFA le {p['date'][:10]}" for p in e.get("paiements", [])])
        notes = "; ".join([f"{k}({v['coefficient']}):{v['note']}" for k, v in e.get("notes", {}).items()])
        ds.append([e["nom"], e["prenoms"], e["classe"], e["date_naissance"],
                   e["contact"], e["prix_scolarite"], e["enregistre_par"],
                   e["created_at"], paiements, notes])
    blob = ds.export("xlsx")
    return send_file(io.BytesIO(blob),
                     download_name="montsion_complet.xlsx",
                     as_attachment=True)

@app.route("/import_xlsx", methods=["POST"])
def import_xlsx():
    file = request.files.get("file")
    if not file or not file.filename.endswith((".xlsx", ".xls")):
        flash("Fichier non valide.", "danger")
        return redirect(url_for("import_export"))

    try:
        df = pd.read_excel(file)
        data = load_yaml()
        for _, row in df.iterrows():
            eleve = {
                "nom": str(row.get("Nom", "")),
                "prenoms": str(row.get("Prénoms", "")),
                "classe": str(row.get("Classe", "")),
                "date_naissance": str(row.get("Date naissance", "")),
                "contact": str(row.get("Téléphone tuteur", "")),
                "prix_scolarite": int(row.get("Prix scolarité (FCFA)", 0)),
                "enregistre_par": str(row.get("Enregistré par", "")),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "paiements": [],
                "notes": {}
            }
            data["eleves"].append(eleve)
        save_yaml(data)
        flash("Importation réussie !", "success")
    except Exception as e:
        flash(f"Erreur : {e}", "danger")
    return redirect(url_for("import_export"))

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
