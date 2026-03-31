from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import requests
import threading
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quotes.db'
db = SQLAlchemy(app)

class Quote(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    text     = db.Column(db.String(300), nullable=False)
    author   = db.Column(db.String(100), nullable=False)
    likes    = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()

count     = 0
last_time = datetime.now()

def reset_if_needed():
    global count, last_time
    now = datetime.now()
    if now - last_time >= timedelta(minutes=1):
        count     = 0
        last_time = now

def get_quote():
    global count
    reset_if_needed()
    if count >= 3:
        return None, None
    try:
        response = requests.get(
            'https://zenquotes.io/api/random',
            timeout=5
        )
        data   = response.json()
        text   = data[0]['q']
        author = data[0]['a']
        if 'Too many requests' in text:
            return None, None
        count += 1
        return text, author
    except Exception as e:
        print("Error:", e)
        return None, None

def auto_fetch():
    while True:
        time.sleep(20)
        with app.app_context():
            text, author = get_quote()
            if text is not None:
                new_quote = Quote(text=text, author=author)
                db.session.add(new_quote)
                db.session.commit()

def start():
    t        = threading.Thread(target=auto_fetch)
    t.daemon = True
    t.start()

@app.route('/')
def index():
    text, author = get_quote()
    if text is None:
        quote = Quote.query.order_by(Quote.id.desc()).first()
        if quote is None:
            quote = Quote(text="Keep going!", author="Unknown")
        return render_template('index.html', quote=quote)
    new_quote = Quote(text=text, author=author)
    db.session.add(new_quote)
    db.session.commit()
    return render_template('index.html', quote=new_quote)

@app.route('/like/<int:id>')
def like(id):
    quote        = Quote.query.get_or_404(id)
    quote.likes += 1
    db.session.commit()
    return redirect(url_for('show_quote', id=id))

@app.route('/dislike/<int:id>')
def dislike(id):
    quote           = Quote.query.get_or_404(id)
    quote.dislikes += 1
    db.session.commit()
    return redirect(url_for('show_quote', id=id))

@app.route('/quote/<int:id>')
def show_quote(id):
    quote = Quote.query.get_or_404(id)
    return render_template('index.html', quote=quote)

@app.route('/next/<int:id>')
def next_quote(id):
    quote = Quote.query.filter(Quote.id > id).order_by(Quote.id.asc()).first()
    if quote is None:
        quote = Quote.query.get_or_404(id)
    return render_template('index.html', quote=quote)

@app.route('/prev/<int:id>')
def prev_quote(id):
    quote = Quote.query.filter(Quote.id < id).order_by(Quote.id.desc()).first()
    if quote is None:
        quote = Quote.query.get_or_404(id)
    return render_template('index.html', quote=quote)

@app.route('/all')
def all_quotes():
    quotes = Quote.query.order_by(Quote.id.desc()).all()
    return render_template('all_quotes.html', quotes=quotes)

if __name__ == '__main__':
    start()
    app.run(debug=True, use_reloader=False)