from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_entry():
    content = request.form['content']  # Text aus dem Textfeld holen
    print(f"Eingetragen: {content}")  # Vorerst nur ausgeben
    return redirect(url_for('index'))  # Zurück zur Hauptseite

if __name__ == '__main__':
    app.run(debug=True)