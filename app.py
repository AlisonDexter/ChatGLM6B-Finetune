# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
import requests
from wtforms.validators import DataRequired, Length, EqualTo, Email
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, session, request, jsonify, render_template, redirect, url_for
import re
#from ChatGLM3_main.cli_demo_thirteen import main as chat  # gpu友好
#from ChatGLM3_main.cli_demo_thirteen_test import main as chat  #对显存要求高的
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
import datetime
from flask_mysqldb import MySQL
import json
import logging
from flask_cors import CORS
from flask import Flask, request, send_file, jsonify,send_from_directory
import os
from io import BytesIO

import uuid
import jieba
import fitz 
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import faiss
import numpy as np
import win32com.client
from flask_wtf.csrf import CSRFProtect



app = Flask(__name__)
csrf = CSRFProtect(app)
CORS(app)
logging.basicConfig(level=logging.DEBUG)


# 使用Flask-MySQLdb进行MySQL连接配置
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '3436068li'
app.config['MYSQL_DB'] = 'flask_login'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_CHARSET'] = 'utf8mb4'


# 配置数据库连接
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SECRET_KEY'] = '1234'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:3436068li@localhost/flask_login?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800
}
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
mysql = MySQL(app)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    session_id = db.Column(db.String(36), nullable=False, default=lambda: str(uuid.uuid4()))  # 默认生成 session_id
    user = db.relationship('User', backref=db.backref('chat_history', lazy=True))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    age = db.Column(db.Integer, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # 确保长度足够存储哈希后的密码

class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    password = PasswordField('密码', validators=[DataRequired()])
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    name = StringField('用户名', validators=[DataRequired()])
    email = StringField('邮箱', validators=[DataRequired(), Email()])
    age = IntegerField('年龄', validators=[DataRequired()])
    password = PasswordField('密码', validators=[
        DataRequired(),
        Length(min=6, message='密码至少需要6个字符'),
        EqualTo('confirm_password', message='两次输入的密码必须一致')
    ])
    confirm_password = PasswordField('确认密码', validators=[DataRequired()])

    submit = SubmitField('注册')

    def validate_password(self, field):
        if not re.match("^[A-Za-z0-9]*$", field.data):
            raise ValidationError('密码只能包含英文字符和数字。')

class ChatForm(FlaskForm):
    question = StringField('Question', validators=[DataRequired()])
    submit = SubmitField('发送')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 确认 CSRF 令牌名称
from flask_wtf.csrf import generate_csrf

@app.route('/get_csrf_token', methods=['GET'])
def get_csrf_token():
    token = generate_csrf()
    return jsonify({'csrf_token': token})


# 首页
@app.route('/home')
@app.route('/')
def home():
    return render_template('home1.html')
   

    
# 介绍
@app.route('/introduct')
def about_us():
    return render_template("introduct.html")



from pydub import AudioSegment
# ASR 服务的 URL
ASR_API_URL = "http://127.0.0.1:9000/api/v1/asr"

def convert_audio_to_wav(audio_data):
    """
    将音频数据转换为 16KHz 的 WAV 格式
    :param audio_data: 原始音频数据
    :return: 转换后的 WAV 格式音频数据
    """
    try:
        # 将音频数据加载为 pydub 的 AudioSegment 对象
        audio = AudioSegment.from_file(BytesIO(audio_data))

        # 如果采样率不是 16KHz，进行重采样
        if audio.frame_rate != 16000:
            audio = audio.set_frame_rate(16000)

        # 如果音频不是单声道，转换为单声道
        if audio.channels > 1:
            audio = audio.set_channels(1)

        # 将处理后的音频数据保存为 WAV 格式
        buffer = BytesIO()
        audio.export(buffer, format="wav")
        buffer.seek(0)
        return buffer.read()
    except Exception as e:
        raise Exception(f"音频格式转换失败: {str(e)}")
    
def get_asr_response(wav_file):
    """
    调用外部 ASR 服务的函数
    :param wav_file: 音频文件路径
    :return: 识别结果文本
    """
    try:
        # 读取音频文件
        with open(wav_file, "rb") as f:
            audio_data = f.read()

        # 转换音频格式为 16KHz WAV
        converted_audio_data = convert_audio_to_wav(audio_data)

        # 发送请求到 ASR 服务
        files = {"files": (os.path.basename(wav_file), converted_audio_data, "audio/wav")}
        data = {"keys": "test_audio", "lang": "auto"}  # 语言参数可以根据需要调整

        response = requests.post(ASR_API_URL, files=files, data=data, timeout=20)

        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            return result["result"][0]["text"]  # 返回识别结果
        else:
            raise Exception(f"ASR 服务请求失败: {response.status_code}, 详情: {response.text}")
    except Exception as e:
        raise Exception(f"调用 ASR 服务时出错: {str(e)}")

# 联系我们
@app.route('/contact')
def contrast():
    return render_template("contact.html")





def clean_text(text):
    try:
        # 移除或替换不兼容的字符
        cleaned_text = ''.join(char for char in text if ord(char) < 65536)
        return cleaned_text
    except Exception as e:
        print(f"Error cleaning text: {e}")
        return text


# Login status check endpoint
@app.route('/check_login_status')
def check_login_status():
    return jsonify({'isLoggedIn': current_user.is_authenticated})

@app.route('/check_auth')
def check_auth():
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'username': current_user.name if current_user.is_authenticated else None
    })

@app.route('/check_')
def check_login():
    if current_user.is_authenticated:
        return jsonify({'logged_in': True})
    else:
        return jsonify({'logged_in': False})

# 聊天机器人问答
# @app.route('/chatrobot', methods=['GET', 'POST'])
# @login_required
# def chatrobot():
 
#     if 'user_id' not in session:
#         flash('请先登录', 'warning')
#         return redirect(url_for('home'))

#     # 确保每次对话都有唯一的 session_id
#     if 'current_session_id' not in session:
#         session['current_session_id'] = str(uuid.uuid4())  # 生成新的 session_id

#     # 处理POST请求
#     if request.method == 'POST':
#         if request.is_json:
#             data = request.get_json()
#             question = data.get('question')
#             user_id = current_user.id
#             result = str(chat(question, user_id))  # 调用 chat 函数获取回复，传入 user_id
#             logging.debug(f"Question: {question}")
#             logging.debug(f"Result: {result}")
#             result_clean = clean_text(result)

#             # 将问题和答案保存到数据库，确保 session_id 被赋值
#             cur = mysql.connection.cursor()
#             try:
#                 cur.execute("INSERT INTO chat_history(user_id, question, response, session_id) VALUES(%s, %s, %s, %s)", 
#                             (user_id, question, result_clean, session['current_session_id']))
#                 mysql.connection.commit()
#             except Exception as e:
#                 print(f"Database error: {e}")
#                 mysql.connection.rollback()
#             finally:
#                 cur.close()

#             # 返回JSON格式的响应
#             return jsonify({'response': result_clean})
#         else:
#             return jsonify({'error': 'Unsupported Media Type'}), 415
#     else:
#         # GET 请求时加载聊天记录，按 session_id 加载当前对话记录
#         user_id = current_user.id
#         session_id = session.get('current_session_id')  # 获取当前 session_id
#         cur = mysql.connection.cursor()
#         cur.execute("SELECT id, question, response FROM chat_history WHERE user_id = %s AND session_id = %s ORDER BY timestamp DESC", 
#                     (user_id, session_id))
#         chat_history = cur.fetchall()
#         cur.close()

#         # 渲染模板并显示聊天记录
#         return render_template('chatrobot.html', 
#                                chat_history=chat_history, 
#                                username=current_user.name)



    

@app.route('/chatrobot', methods=['GET', 'POST'])
@login_required
def chatrobot():
    # Create a form object (assuming you have a form class)
    form = ChatForm()  # Replace with your actual form class
    
    if 'user_id' not in session:
        flash('请先登录', 'warning')
        return redirect(url_for('home'))

    # Ensure unique session_id
    if 'current_session_id' not in session:
        session['current_session_id'] = str(uuid.uuid4())

    # Handle POST request
    if request.method == 'POST':
        if request.is_json:
            # For JSON requests, you need to include the CSRF token in the request headers
            data = request.get_json()
            question = data.get('question')
            user_id = current_user.id
            result = str(chat(question, user_id))
            logging.debug(f"Question: {question}")
            logging.debug(f"Result: {result}")
            result_clean = clean_text(result)

            # Save to database
            cur = mysql.connection.cursor()
            try:
                cur.execute("INSERT INTO chat_history(user_id, question, response, session_id) VALUES(%s, %s, %s, %s)", 
                            (user_id, question, result_clean, session['current_session_id']))
                mysql.connection.commit()
            except Exception as e:
                print(f"Database error: {e}")
                mysql.connection.rollback()
            finally:
                cur.close()

            return jsonify({'response': result_clean})
        else:
            # For form submissions, validate the form with CSRF protection
            if form.validate_on_submit():
                question = form.question.data
                user_id = current_user.id
                result = str(chat(question, user_id))
                result_clean = clean_text(result)

                # Save to database
                cur = mysql.connection.cursor()
                try:
                    cur.execute("INSERT INTO chat_history(user_id, question, response, session_id) VALUES(%s, %s, %s, %s)", 
                                (user_id, question, result_clean, session['current_session_id']))
                    mysql.connection.commit()
                except Exception as e:
                    print(f"Database error: {e}")
                    mysql.connection.rollback()
                finally:
                    cur.close()

                # Redirect to avoid form resubmission
                return redirect(url_for('chatrobot'))
            else:
                # If form validation fails, log the errors
                print(f"Form errors: {form.errors}")
                return render_template('chatrobot.html', form=form, chat_history=[], username=current_user.name)
    else:
        # GET request - load chat history
        user_id = current_user.id
        session_id = session.get('current_session_id')
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, question, response FROM chat_history WHERE user_id = %s AND session_id = %s ORDER BY timestamp DESC", 
                    (user_id, session_id))
        chat_history = cur.fetchall()
        cur.close()

        # Render template with chat history and form
        return render_template('chatrobot.html', 
                               form=form,
                               chat_history=chat_history, 
                               username=current_user.name)



@app.route('/start_new_chat', methods=['POST'])
def start_new_chat():
    user_id = current_user.id  # 获取当前用户的 ID
    try:
        # 获取当前对话内容
        chat_data = request.json.get('chat_history')
        if not chat_data:
            return jsonify({"error": "聊天记录不能为空"}), 400

        # 保存每条聊天记录到数据库
        for chat in chat_data:
            new_chat = ChatHistory(
                user_id=user_id,
                question=chat.get('question'),
                response=chat.get('response')
            )
            db.session.add(new_chat)
        
        db.session.commit()
        return jsonify({"success": True, "message": "聊天记录已保存"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/get_user_chat_history', methods=['GET'])
def get_user_chat_history():
    user_id = current_user.id  # 获取当前用户 ID
    
    # 获取今天的日期
    today = datetime.datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # 查询各个时间段的聊天记录，添加用户ID过滤和时间排序（降序）
    today_chats = ChatHistory.query.filter(
        ChatHistory.timestamp >= today,
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.timestamp.desc()).all()  # 添加降序排序
    
    yesterday_chats = ChatHistory.query.filter(
        ChatHistory.timestamp >= yesterday,
        ChatHistory.timestamp < today,
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.timestamp.desc()).all()  # 添加降序排序
    
    last_week_chats = ChatHistory.query.filter(
        ChatHistory.timestamp >= last_week,
        ChatHistory.timestamp < yesterday,
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.timestamp.desc()).all()  # 添加降序排序
    
    last_month_chats = ChatHistory.query.filter(
        ChatHistory.timestamp >= last_month,
        ChatHistory.timestamp < last_week,
        ChatHistory.user_id == user_id
    ).order_by(ChatHistory.timestamp.desc()).all()  # 添加降序排序

    # 将按时间段整理的数据返回
    today_data = [{"id": chat.id, "question": chat.question} for chat in today_chats]
    yesterday_data = [{"id": chat.id, "question": chat.question} for chat in yesterday_chats]
    last_week_data = [{"id": chat.id, "question": chat.question} for chat in last_week_chats]
    last_month_data = [{"id": chat.id, "question": chat.question} for chat in last_month_chats]

    return jsonify({
        "today": today_data,
        "yesterday": yesterday_data,
        "last_week": last_week_data,
        "last_month": last_month_data
    })



@app.route('/get_chat_history/<int:chat_id>', methods=['GET'])
def get_chat_history(chat_id):
    user_id = current_user.id  # 获取当前用户的 ID

    # 打印调试信息
    print(f"查询 chat_id: {chat_id}, 当前用户: {user_id}")

    # 查询指定 chat_id 的聊天记录
    chat = ChatHistory.query.get(chat_id)

    # 验证记录是否存在且属于当前用户
    if not chat:
        print(f"未找到 chat_id: {chat_id}")
        return jsonify({"error": "未找到聊天记录"}), 404
    
    if chat.user_id != user_id:
        print(f"用户 {user_id} 尝试访问用户 {chat.user_id} 的聊天记录")
        return jsonify({"error": "无权访问该聊天记录"}), 403

    # 如果是当前用户的记录，返回详细内容
    return jsonify({
        "history": [{
            "question": chat.question,
            "response": chat.response,
            "timestamp": chat.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(chat, 'timestamp') else None
        }]
    })

# 添加一个新的路由用于获取当前用户信息
@app.route('/get_current_user', methods=['GET'])
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({"user_id": current_user.id})
    return jsonify({"error": "未登录"}), 401


@app.route('/switch_session/<session_id>', methods=['POST'])
@login_required
def switch_session(session_id):
    user_id = current_user.id

    # 获取当前 session_id 下的聊天记录
    chat_histories = db.session.query(ChatHistory).filter_by(user_id=user_id, session_id=session_id).all()

    # 渲染页面并显示相应的聊天记录
    return render_template('chatrobot.html', chat_histories=chat_histories, username=current_user.name)



@app.route('/clear_history', methods=['POST'])
@login_required
def clear_history():
    print("===== 清除历史记录函数被调用 =====")
    user_id = current_user.id
    session_id = session.get('current_session_id')
    
    print(f"用户ID: {user_id}")
    print(f"尝试清除会话ID: {session_id}")
    
    try:
        # 查询用户的所有会话记录
        existing_sessions = db.session.query(ChatHistory.session_id).filter_by(user_id=user_id).distinct().all()
        session_ids = [s[0] for s in existing_sessions]
        print(f"用户现有会话IDs: {session_ids}")
        
        if session_id and session_id in session_ids:
            # 清除指定会话ID的记录
            print(f"正在清除指定会话ID: {session_id}")
            deleted_count = ChatHistory.query.filter_by(user_id=user_id, session_id=session_id).delete()
        else:
            # 如果没有指定会话ID或会话ID不存在，清除当前显示的会话记录
            # 这里假设当前显示的是最新的会话记录
            print("无有效会话ID，清除最新会话")
            
            # 获取最新的会话记录ID
            latest_chat = ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).first()
            
            if latest_chat:
                latest_session_id = latest_chat.session_id
                print(f"最新会话ID: {latest_session_id}")
                deleted_count = ChatHistory.query.filter_by(user_id=user_id, session_id=latest_session_id).delete()
            else:
                print("未找到任何会话记录")
                deleted_count = 0
        
        # 提交更改
        db.session.commit()
        print(f"成功删除 {deleted_count} 条记录")
        
        # 生成新的会话ID
        new_session_id = str(uuid.uuid4())
        session['current_session_id'] = new_session_id
        print(f"已生成新会话ID: {new_session_id}")
        
        flash('聊天记录已清除，已开启新对话。', 'success')
        
        # 使用重定向而不是render_template
        return redirect(url_for('chatrobot'))  # 假设聊天页面的路由函数名为'chatrobot'
    except Exception as e:
        db.session.rollback()
        print(f"清除历史记录时出错: {str(e)}")
        flash('清除聊天记录失败，请稍后再试。', 'danger')
        return redirect(url_for('chatrobot'))



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



# 登录视图
@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()  # 清理旧session
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
        #if user and user.password == form.password.data:
            login_user(user)
            session['user_id'] = user.id
            flash('登录成功', 'success')
            return redirect(url_for('chatrobot'))
        else:
            flash('邮箱或密码错误', 'danger')
    return render_template('login.html', form=form)





@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            flash('密码和确认密码不匹配，请重新输入。', 'danger')
            return render_template('register.html', form=form)

        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('该邮箱已经被注册，请使用其他邮箱。', 'danger')
            return render_template('register.html', form=form)

        hashed_password = generate_password_hash(form.password.data)
        new_user = User(name=form.name.data, email=form.email.data, age=form.age.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('注册成功！请登录。', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录。', 'success')
    return redirect(url_for('home'))

@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    """
    上传音频文件并保存到本地
    """
    if 'audio' not in request.files:
        return jsonify({'error': '未提供音频文件'}), 400

    audio_file = request.files['audio']
    save_path = os.path.join('dataset', 'test.wav')

    try:
        # 保存音频文件
        audio_file.save(save_path)
        return jsonify({'message': '音频文件保存成功', 'path': save_path}), 200
    except Exception as e:
        return jsonify({'error': f'保存音频文件失败: {str(e)}'}), 500

@app.route('/process_audio', methods=['POST'])
def process_audio():
    """
    处理音频文件并调用 ASR 服务
    """
    if 'audio' not in request.files:
        return jsonify({'error': '未提供音频文件'}), 400

    audio_file = request.files['audio']
    save_path = os.path.join('dataset', 'test.wav')

    try:
        # 保存音频文件
        audio_file.save(save_path)

        # 调用 ASR 服务
        recognized_text = get_asr_response(save_path)
        print(recognized_text)
        return jsonify({'text': recognized_text}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    # 获取请求数据
    data = request.get_json()
    text = data.get('text', '')

    # 检查是否提供了文本
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    # FastAPI 服务的 URL
    url = "http://127.0.0.1:7000/v1/audio/speech"

    # 请求数据
    payload = {
        "input": text,           # 要合成的文本
        "voice": "8051",         # 说话人 ID
        "prompt": "开心",        # 情感提示
        "language": "zh_us",     # 语言
        "response_format": "wav",  # 输出格式（wav 或 mp3）
        "speed": 1.0             # 语速
    }

    # 设置请求头
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # 发送 POST 请求到 FastAPI 服务
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        # 检查响应状态
        if response.status_code == 200:
            # 保存音频文件
            audio_path = "dataset/response.wav"
            with open(audio_path, "wb") as f:
                f.write(response.content)

            # 返回音频文件
            return send_file(audio_path, mimetype='audio/wav')
        else:
            # 返回错误信息
            return jsonify({
                'error': f"Failed to generate audio: {response.status_code}",
                'message': response.text
            }), response.status_code
    except Exception as e:
        # 捕获并返回异常信息
        print(f"Error generating audio: {e}")
        return jsonify({'error': str(e)}), 500
    


model = SentenceTransformer("sensenova/piccolo-base-zh")
# 提取 .docx 文件内容
def extract_doc_text(file_path):
    try:
        print(f"尝试打开 DOC 文件: {file_path}")
        
        # 打开 Word 应用
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False  # 设置为不显示 Word 窗口
        doc = word.Documents.Open(file_path)
        
        # 获取文档文本
        text = doc.Content.Text
        doc.Close()
        word.Quit()
        
        #print(f"成功提取 DOC 文件文本，长度: {len(text)}")
        return text
    except Exception as e:
        #print(f"Error reading DOC file {file_path}: {e}")
        return ""


def extract_pdf_text(file_path):
    try:
        doc = fitz.open(file_path)
        print(f"成功打开 PDF 文件: {file_path}")
        text = "".join([page.get_text() for page in doc])
        print(f"提取的文本内容长度: {len(text)}")
        return text
    except Exception as e:
        print(f"Error reading PDF file {file_path}: {e}")
        return ""
    
# 加载文档
def load_documents():
    DOCUMENTS_FOLDER = r"D:/Age_copy/law_doc"
    #print(f"文件路径: {DOCUMENTS_FOLDER}")
    documents = {}
    doc_vectors = []
    doc_keys = []

    # 确保文档目录存在
    if not os.path.exists(DOCUMENTS_FOLDER):
        os.makedirs(DOCUMENTS_FOLDER)
        print(f"创建文档目录: {DOCUMENTS_FOLDER}")
        return {}, [], []

    # 打印目录中的文件列表，用于调试
    files = os.listdir(DOCUMENTS_FOLDER)
    #print(f"目录中包含 {len(files)} 个文件: {files}")

    for filename in os.listdir(DOCUMENTS_FOLDER):
        file_path = os.path.join(DOCUMENTS_FOLDER, filename)
        
        # 添加.doc到支持的文件类型中
        if filename.endswith((".doc", ".docx", ".pdf")):
            text = ""
            if filename.endswith(".doc"):
                text = extract_doc_text(file_path)
            elif filename.endswith(".docx"):
                text = extract_doc_text(file_path)  # 或使用专门的docx提取函数
            elif filename.endswith(".pdf"):
                text = extract_pdf_text(file_path)
                
            #print(f"提取的文本内容前100字符: {text[:100]}...") 

            if text and text.strip():
                print(f"文档 {filename} 提取内容成功，长度: {len(text)}")
                documents[filename] = text
                doc_keys.append(filename)
                try:
                    vector = model.encode(text)
                    doc_vectors.append(vector)
                except Exception as e:
                    print(f"Error encoding {filename}: {e}")
            else:
                print(f"文档 {filename} 提取内容为空或仅含空格")
        else:
            print(f"跳过不支持的文件类型: {filename}")
    
    print(f"已加载 {len(documents)} 个文档")
    return documents, doc_vectors, doc_keys

# 初始化搜索索引
def init_search_indices(documents, doc_vectors):
    # 初始化 FAISS 索引（如果有向量）
    faiss_index = None
    if doc_vectors and len(doc_vectors) > 0:
        doc_vectors_np = np.array(doc_vectors)
        faiss_index = faiss.IndexFlatL2(doc_vectors_np.shape[1])
        faiss_index.add(doc_vectors_np)
        print(f"FAISS 索引已创建，包含 {len(doc_vectors)} 个向量")
        # 保存 FAISS 索引到文件
        faiss.write_index(faiss_index, "faiss_law_case.index")
        print("FAISS 索引已保存到 faiss_law_case.index")
    
    # 只有在有文档时初始化 BM25
    bm25 = None
    if documents and len(documents) > 0:
        tokenized_docs = [jieba.lcut(doc) for doc in documents.values()]
        if tokenized_docs:
            bm25 = BM25Okapi(tokenized_docs)
            print("BM25 索引创建成功")
    
    return faiss_index, bm25

# 加载文档并创建索引
documents, doc_vectors, doc_keys = load_documents()
faiss_index, bm25 = init_search_indices(documents, doc_vectors)



# 搜索路由 - 确保路径和方法正确
@app.route("/search", methods=["POST"])
def search():
    print("收到搜索请求")
    try:
        query = request.json.get("query", "").strip()
        if not query:
            return jsonify({"error": "请输入搜索内容！"})

        # 检查是否有文档可搜索
        if not documents:
            return jsonify({"error": "无文档可搜索，请先添加文档！", "results": []})

        results = []
        
        # BM25 搜索
        if bm25:
            query_tokens = jieba.lcut(query)
            try:
                bm25_scores = bm25.get_scores(query_tokens)
                bm25_results = [(doc_keys[i], bm25_scores[i]) for i in range(len(bm25_scores)) if bm25_scores[i] > 0]
                bm25_results.sort(key=lambda x: x[1], reverse=True)
                results.extend(bm25_results)
            except Exception as e:
                print(f"BM25 搜索错误: {e}")
        
        # FAISS 语义搜索
        if faiss_index and len(doc_keys) > 0:
            try:
                query_vector = model.encode([query])
                D, I = faiss_index.search(np.array(query_vector), k=min(10, len(doc_keys)))
                faiss_results = [(doc_keys[idx], 1/(1+D[0][i])) for i, idx in enumerate(I[0])]  # 将距离转换为得分
                results.extend(faiss_results)
            except Exception as e:
                print(f"FAISS 搜索错误: {e}")
        
        # 合并并去重结果
        seen = set()
        unique_results = []
        for doc_name, score in sorted(results, key=lambda x: x[1], reverse=True):
            if doc_name not in seen:
                seen.add(doc_name)
                unique_results.append(doc_name)
        
        print(f"搜索结果: {len(unique_results)} 个文档")
        return jsonify({"results": unique_results[:10]})
    
    except Exception as e:
        print(f"搜索处理错误: {str(e)}")
        return jsonify({"error": f"搜索处理失败: {str(e)}", "results": []})

@app.route("/download/<filename>")
def download(filename):
    # 检查文件是否存在
    DOCUMENTS_FOLDER = r"D:/Age_copy/law_docs"
    file_path = os.path.join(DOCUMENTS_FOLDER, filename)
    
    if os.path.exists(file_path) and filename.endswith((".doc", ".docx", ".pdf")):
        try:
            return send_from_directory(DOCUMENTS_FOLDER, filename, as_attachment=True)
        except Exception as e:
            print(f"下载文件时发生错误: {e}")
            return jsonify({"error": f"下载文件失败: {str(e)}"}), 500
    else:
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
        else:
            print(f"不支持的文件格式: {filename}")
        return jsonify({"error": "文件不存在或格式不支持"}), 404




if __name__ == "__main__":
    app.run(debug=False)