# -*- coding: utf-8 -*-


import requests
from wtforms.validators import DataRequired, Length, EqualTo, Email
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, session, request, jsonify, render_template, redirect, url_for,Response
import re
from ChatGLM3_main.cli_demo_thirteen import main as chat
#from GPT2.interact import main as chat
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask import render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
import datetime
from flask_mysqldb import MySQL
import json
import logging
from flask_cors import CORS
from flask import Flask, request, send_file, jsonify
import os
from io import BytesIO
import torchaudio


app = Flask(__name__)
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

# 首页
@app.route('/home')
@app.route('/')
def home():
    return render_template("home.html")


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


# 聊天机器人问答
@app.route('/chatrobot', methods=['GET', 'POST'])
@login_required
def chatrobot():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            question = data.get('question')
            user_id = current_user.id
            result = str(chat(question, user_id))  # 调用 chat 函数获取回复，传入 user_id
            logging.debug(f"Question: {question}")
            logging.debug(f"Result: {result}")
            result_clean = clean_text(result)
            
            # 将问题和答案保存到数据库
            cur = mysql.connection.cursor()
            try:
                cur.execute("INSERT INTO chat_history(user_id, question, response) VALUES(%s, %s, %s)", 
                            (user_id, question, result_clean))
                mysql.connection.commit()
            except Exception as e:
                print(f"Database error: {e}")
                mysql.connection.rollback()
            finally:
                cur.close()

            # 返回JSON格式的响应
            return jsonify({'response': result_clean})
        else:
            return jsonify({'error': 'Unsupported Media Type'}), 415
    else:
        # GET 请求时加载聊天记录
        user_id = current_user.id
        cur = mysql.connection.cursor()
        cur.execute("SELECT question, response FROM chat_history WHERE user_id = %s", [user_id])
        chat_history = cur.fetchall()
        cur.close()

        # 渲染模板并显示聊天记录
        return render_template('chatrobot_asr.html', chat_history=chat_history, username=current_user.name)

# 清除聊天记录
@app.route('/clear_history', methods=['POST'])
@login_required
def clear_history():
    user_id = current_user.id  # 使 current_user 获取 user_id
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM chat_history WHERE user_id=%s", [user_id])
    mysql.connection.commit()
    cur.close()

    flash('聊天记录已清除。', 'success')
    return redirect(url_for('chatrobot'))





@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




# 登录视图
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
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
    return redirect(url_for('login'))

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

if __name__ == '__main__':
    app.run(debug=False)
