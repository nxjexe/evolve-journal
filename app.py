from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import logging
import os
import speech_recognition as sr

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
    tags = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_entry():
    content = request.form['content']
    tags = request.form.get('tags', '')
    if not content.strip():
        flash("Fehler: Textfeld leer!", "error")
        return redirect(url_for('index'))
    try:
        app.logger.debug(f"Versuche, Eintrag zu speichern: {content}, Tags: {tags}")
        entry = Entry(content=content, tags=tags)
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
        tag_filter = request.args.get('tag')
        if tag_filter:
            all_entries = Entry.query.filter(Entry.tags.contains(tag_filter)).order_by(Entry.timestamp.desc()).all()
            app.logger.debug(f"Geladene Einträge mit Tag '{tag_filter}': {len(all_entries)}")
        else:
            all_entries = Entry.query.order_by(Entry.timestamp.desc()).all()
            app.logger.debug(f"Geladene Einträge: {len(all_entries)}")
        return render_template('entries.html', entries=all_entries, current_tag=tag_filter)
    except Exception as e:
        app.logger.error(f"Fehler beim Laden der Einträge: {str(e)}")
        flash(f"Fehler beim Laden der Einträge: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/voice', methods=['POST'])
def voice_entry():
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            app.logger.debug("Warte auf Spracheingabe...")
            audio = r.listen(source, timeout=5)
        app.logger.debug("Verarbeite Spracheingabe...")
        text = r.recognize_google(audio, language='de-DE')
        tags = request.form.get('tags') or 'voice'  # Default-Tag 'voice'
        entry = Entry(content=text, tags=tags)
        db.session.add(entry)
        db.session.commit()
        app.logger.debug(f"Spracheintrag gespeichert: {text}")
        flash("Spracheintrag gespeichert!", "success")
    except sr.UnknownValueError:
        app.logger.error("Sprache konnte nicht verstanden werden")
        flash("Fehler: Sprache konnte nicht verstanden werden", "error")
    except sr.RequestError as e:
        app.logger.error(f"Fehler bei der Spracherkennung: {str(e)}")
        flash(f"Fehler bei der Spracherkennung: {str(e)}", "error")
    except Exception as e:
        app.logger.error(f"Fehler beim Speichern: {str(e)}")
        flash(f"Fehler beim Speichern: {str(e)}", "error")
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        app.logger.debug(f"DB-Pfad: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        app.logger.debug("DB und Tabellen erstellt")
    app.run(debug=True)