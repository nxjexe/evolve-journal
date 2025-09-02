from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import logging
import os

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "evolve.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
db = SQLAlchemy(app)

logging.basicConfig(level=logging.DEBUG)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_entry():
    content = request.form['content']
    if not content.strip():
        flash("Fehler: Textfeld leer!", "error")
        return redirect(url_for('index'))
    try:
        app.logger.debug(f"Versuche, Eintrag zu speichern: {content}")
        entry = Entry(content=content)
        db.session.add(entry)
        db.session.commit()
        app.logger.debug("Eintrag erfolgreich gespeichert")
        flash("Eintrag gespeichert!", "success")
    except Exception as e:
        app.logger.error(f"Fehler beim Speichern: {str(e)}")
        flash(f"Fehler beim Speichern: {str(e)}", "error")
    return redirect(url_for('index'))

@app.route('/entries')
def entries():
    try:
        all_entries = Entry.query.order_by(Entry.timestamp.desc()).all()
        app.logger.debug(f"Geladene Einträge: {len(all_entries)}")
        return render_template('entries.html', entries=all_entries)
    except Exception as e:
        app.logger.error(f"Fehler beim Laden der Einträge: {str(e)}")
        flash(f"Fehler beim Laden der Einträge: {str(e)}", "error")
        return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        app.logger.debug(f"DB-Pfad: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        app.logger.debug("DB und Tabellen erstellt")
    app.run(debug=True)