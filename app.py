from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
import logging
import os
import speech_recognition as sr
import time
import spacy
from threading import Thread, Event

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "evolve.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dein-geheimer-schluessel'
db = SQLAlchemy(app)
socketio = SocketIO(app)
nlp = spacy.load('de_core_news_md')

logging.basicConfig(level=logging.DEBUG)

class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

recording_event = Event()

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

@socketio.on('start_recording')
def start_recording(data):
    global recording_event
    recording_event.set()
    def record():
        with app.app_context():
            try:
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    app.logger.debug("Warte auf Spracheingabe...")
                    r.adjust_for_ambient_noise(source, duration=1)
                    start_time = time.time()
                    audio_data = []
                    while recording_event.is_set():
                        try:
                            audio = r.listen(source, timeout=1, phrase_time_limit=None)
                            audio_data.append(audio)
                        except sr.WaitTimeoutError:
                            continue
                    duration = time.time() - start_time
                app.logger.debug("Verarbeite Spracheingabe...")
                text = ''
                for audio in audio_data:
                    try:
                        text += r.recognize_google(audio, language='de-DE') + ' '
                    except sr.UnknownValueError:
                        continue
                if not text.strip():
                    app.logger.error("Keine Sprache erkannt")
                    socketio.emit('recording_error', {'message': "Fehler: Keine Sprache erkannt"})
                    return
                doc = nlp(text.strip())
                punctuated_text = ''
                for sent in doc.sents:
                    sent_text = ''.join(token.text + (token.whitespace_ or '') for token in sent)
                    if sent_text.strip():
                        punctuated_text += sent_text.rstrip() + '. '
                tags = data.get('tags', 'voice')
                entry = Entry(content=punctuated_text.rstrip(), tags=tags)
                db.session.add(entry)
                db.session.commit()
                app.logger.debug(f"Spracheintrag gespeichert: {punctuated_text}")
                socketio.emit('recording_success', {'message': f"Spracheintrag ({duration:.1f}s) gespeichert!", 'duration': duration})
            except Exception as e:
                app.logger.error(f"Fehler beim Speichern: {str(e)}")
                socketio.emit('recording_error', {'message': f"Fehler beim Speichern: {str(e)}"})
    Thread(target=record).start()

@socketio.on('stop_recording')
def stop_recording():
    global recording_event
    recording_event.clear()
    app.logger.debug("Aufnahme gestoppt")
    socketio.emit('recording_stopped', {'message': "Aufnahme gestoppt"})

if __name__ == '__main__':
    with app.app_context():
        app.logger.debug(f"DB-Pfad: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        app.logger.debug("DB und Tabellen erstellt")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)