from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, UserNameChange, Chat, Message
from datetime import datetime, timedelta, timezone
from functools import wraps
import os
import hashlib
import logging
from logging.handlers import RotatingFileHandler
from init_db import init_database
from sqlalchemy.sql import func
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
PASSWORD_HASH = os.environ.get('PASSWORD_HASH')  # Store hashed password in env

# Configure logging
def setup_logging(app):
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Set up rotating file handler
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10,
        delay=True
    )
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Remove existing handlers
    app.logger.handlers = []
    
    # Add our handlers
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

setup_logging(app)

# Initialize database
engine, DBSession = init_database()

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('authenticated'):
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_db_session():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()

@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f'An error occurred: {str(error)}')
    return render_template('error.html', error=str(error)), 500

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/verify', methods=['POST'])
def verify():
    try:
        password = request.form.get('password', '')
        hashed = hashlib.sha256(password.encode()).hexdigest()
        
        if hashed == PASSWORD_HASH:
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        
        flash('Invalid password', 'error')
        return redirect(url_for('login'))
    except Exception as e:
        app.logger.error(f'Login error: {str(e)}')
        flash('An error occurred during login', 'error')
        return redirect(url_for('login'))

@app.route('/dashboard')
@requires_auth
def dashboard():
    try:
        days = request.args.get('days', 'today')
        view_type = request.args.get('view', 'users')
        
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        
        if days == 'today':
            # Set cutoff to start of current day in UTC
            cutoff_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            days_map = {
                '3days': 3,
                '7days': 7,
                'forever': 36500
            }
            cutoff_date = now - timedelta(days=days_map[days])
        
        db = next(get_db_session())
        
        if view_type == 'users':
            # First get all unique users with their messages
            results = (db.query(User, Message.message_text, Message.response_text, Message.timestamp)
                     .select_from(User)
                     .join(Message, User.id == Message.user_id)
                     .join(Chat, Message.chat_id == Chat.id)
                     .filter(Chat.chat_type == 'private')
                     .filter(Message.timestamp >= cutoff_date)
                     .order_by(User.user_id, Message.timestamp.desc())
                     .all())
            
            # Group messages by user
            data = {}
            for row in results:
                user = row[0]
                message = {
                    'message_text': row[1],
                    'response_text': row[2],
                    'timestamp': row[3]
                }
                if user.user_id not in data:
                    data[user.user_id] = {'user': user, 'messages': []}
                data[user.user_id]['messages'].append(message)
            data = list(data.values())
        elif view_type == 'groups':
            results = (db.query(Chat, Message.message_text, Message.response_text, Message.timestamp, User)
                     .select_from(Chat)
                     .join(Message, Chat.id == Message.chat_id)
                     .join(User, Message.user_id == User.id)
                     .filter(Chat.chat_type.in_(['supergroup', 'group']))
                     .filter(Message.timestamp >= cutoff_date)
                     .order_by(Chat.chat_id, Message.timestamp.desc())
                     .all())
            
            # Group messages by chat
            data = {}
            for row in results:
                chat = row[0]  # Use the full Chat object
                message = {
                    'message_text': row[1],
                    'response_text': row[2],
                    'timestamp': row[3],
                    'user': row[4]
                }
                if chat.chat_id not in data:
                    data[chat.chat_id] = {'chat': chat, 'messages': []}
                data[chat.chat_id]['messages'].append(message)
            data = list(data.values())
        else:  # total view
            # Get users with their message counts within the time period
            results = (db.query(User, func.count(Message.id).label('message_count'))
                     .join(Message, User.id == Message.user_id)
                     .filter(Message.timestamp >= cutoff_date)
                     .group_by(User)
                     .order_by(User.user_id)
                     .all())
            
            # Convert to list of users with message count
            data = []
            for user, count in results:
                user.message_count = count  # Add message count as attribute
                data.append(user)
        
        app.logger.info(f"Dashboard loaded successfully for view_type: {view_type}, days: {days}")
        return render_template('dashboard.html', 
                             data=data, 
                             days=days, 
                             view_type=view_type,
                             timezone=timezone,
                             timedelta=timedelta)
    except Exception as e:
        app.logger.error(f'Dashboard error: {str(e)}')
        flash('An error occurred while loading the dashboard', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/debug/chats')
@requires_auth
def debug_chats():
    try:
        db = next(get_db_session())
        # Get all chats
        chats = db.query(Chat).filter(
            Chat.chat_type.in_(['group', 'supergroup'])
        ).all()
        
        # Print chat details
        for chat in chats:
            app.logger.info(f"Chat ID: {chat.chat_id}, Type: {chat.chat_type}, Name: {chat.chat_name}")
        
        return jsonify([{
            'chat_id': chat.chat_id,
            'chat_type': chat.chat_type,
            'chat_name': chat.chat_name
        } for chat in chats])
    except Exception as e:
        app.logger.error(f"Debug error: {str(e)}")
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 