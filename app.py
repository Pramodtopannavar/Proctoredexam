from flask import Flask, request, render_template, flash, redirect, url_for,session, logging, send_file, jsonify, Response, render_template_string
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, DateTimeField, BooleanField, IntegerField, DecimalField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_mail import Mail, Message
from functools import wraps
from werkzeug.utils import secure_filename
from coolname import generate_slug
from datetime import timedelta, datetime


from deepface import DeepFace
import pandas as pd

import operator
import functools
import math, random
import csv
import cv2
import numpy as nppip
import json
import base64
from wtforms_components import TimeField
from wtforms_components import DateField
from wtforms.validators import ValidationError, NumberRange
from flask_session import Session
from flask_cors import CORS, cross_origin
# import camera
from objective import ObjectiveTest
from subjective import SubjectiveTest


app = Flask(__name__)

app.config['SECRET_KEY'] = 'b1f5b8a5e59e63f2e9578a6dcb9dce3b'

# Configure MySQL (update with your MySQL database configuration)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'quizapp'

mysql = MySQL(app)

# Configure Flask-Mail (update with your email configuration)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'pramodtopannavar843@gmail.com'
app.config['MAIL_PASSWORD'] = 'oqyn qcme pqss qyvg'

mail = Mail(app)

def user_role_professor(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			if session['user_role']=="teacher":
				return f(*args, **kwargs)
			else:
				flash('You dont have privilege to access this page!','danger')
				return render_template("404.html") 
		else:
			flash('Unauthorized, Please login!','danger')
			return redirect(url_for('login'))
	return wrap

def user_role_student(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			if session['user_role']=="student":
				return f(*args, **kwargs)
			else:
				flash('You dont have privilege to access this page!','danger')
				return render_template("404.html") 
		else:
			flash('Unauthorized, Please login!','danger')
			return redirect(url_for('login'))
	return wrap

@app.route("/config")
@user_role_professor
def get_publishable_key():
    stripe_config = {"publicKey": stripe_keys["publishable_key"]}
    return jsonify(stripe_config)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        cur = mysql.connection.cursor()

        # Check if the email already exists
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Email already exists. Please use a different email or try logging in.')
            return redirect(url_for('login'))

        # Insert the new user
        cur.execute('INSERT INTO users(name, email, password, user_type, user_login) VALUES (%s, %s, %s, %s, 0)',
                    (name, email, password, user_type))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_candidate = request.form['password']
        user_type = request.form['user_type']

        cur = mysql.connection.cursor()
        results = cur.execute('SELECT uid, name, email, password, user_type FROM users WHERE email = %s AND user_type = %s AND user_login = 0', (email, user_type))

        if results > 0:
            user_data = cur.fetchone()  # Fetch the first row

            stored_password = user_data[3]  # Assuming 'password' is the fourth column in your query
            if password_candidate == stored_password:
                # Set session variables
                session['logged_in'] = True
                session['email'] = email
                session['name'] = user_data[1]  # Accessing 'name' which is the second column
                session['user_role'] = user_type
                session['uid'] = user_data[0]  # Accessing 'uid' which is the first column

                # Update user_login status in database
                cur.execute('UPDATE users SET user_login = 1 WHERE email = %s', [email])
                mysql.connection.commit()

                cur.close()

                if user_type == "student":
                    return redirect(url_for('student_index'))
                else:
                    return redirect(url_for('professor_index'))
            else:
                error = 'Invalid password'
                return render_template('login.html', error=error)
        else:
            error = 'User not found or already logged in'
            return render_template('login.html', error=error)

    return render_template('login.html')


@app.route('/faq')
def faq():
	return render_template('faq.html')

@app.route('/report_student')
@user_role_student
def report_student():
	return render_template('report_student.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        sender = "pramodtopannavar33@gmail.com"  # Define the sender email here
        careEmail = "pramodtopannavar843@gmail.com"
        cname = request.form['cname']
        cemail = request.form['cemail']
        cquery = request.form['cquery']
        
        msg1 = Message('Hello', sender=sender, recipients=[cemail])
        msg1.body = "YOUR QUERY WILL BE PROCESSED WITHIN 24 HOURS"
        
        msg2 = Message('Hello', sender=sender, recipients=[careEmail])
        msg2.body = " ".join(["NAME:", cname, "EMAIL:", cemail, "QUERY:", cquery])
        
        mail.send(msg1)
        mail.send(msg2)
        
        flash('Your Query has been recorded.', 'success')
    
    return render_template('contact.html')


@app.route('/logout', methods=["GET", "POST"])
def logout():
	cur = mysql.connection.cursor()
	lbr = cur.execute('UPDATE users set user_login = 0 where email = %s and uid = %s',(session['email'],session['uid']))
	mysql.connection.commit()
	if lbr > 0:
		session.clear()
		return render_template('index.html')
	else:
		return "error"


@app.route('/generate_test')
@user_role_professor
def generate_test():
	return render_template('generatetest.html')

@app.route('/changepassword_professor')
@user_role_professor
def changepassword_professor():
	return render_template('changepassword_professor.html')

@app.route('/changepassword_student')
@user_role_student
def changepassword_student():
	return render_template('changepassword_student.html')

def examcreditscheck():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT examcredits from users where examcredits >= 1 and email = %s and uid = %s', (session['email'], session['uid']))
	if results > 0:
		return True

class QAUploadForm(FlaskForm):
	subject = StringField('Subject')
	topic = StringField('Topic')
	doc = FileField('CSV Upload', validators=[FileRequired()])
	start_date = DateField('Start Date')
	start_time = TimeField('Start Time', default=datetime.utcnow()+timedelta(hours=5.5))
	end_date = DateField('End Date')
	end_time = TimeField('End Time', default=datetime.utcnow()+timedelta(hours=5.5))
	duration = IntegerField('Duration(in min)')
	password = PasswordField('Exam Password', [validators.Length(min=3, max=6)])
	proctor_type = RadioField('Proctoring Type', choices=[('0','Automatic Monitoring'),('1','Live Monitoring')])

	def validate_end_date(form, field):
		if field.data < form.start_date.data:
			raise ValidationError("End date must not be earlier than start date.")
	
	def validate_end_time(form, field):
		start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		end_date_time = datetime.strptime(str(form.end_date.data) + " " + str(field.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		if start_date_time >= end_date_time:
			raise ValidationError("End date time must not be earlier/equal than start date time")
	
	def validate_start_date(form, field):
		if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S") < datetime.now():
			raise ValidationError("Start date and time must not be earlier than current")


class UploadForm(FlaskForm):
	subject = StringField('Subject')
	topic = StringField('Topic')
	doc = FileField('CSV Upload', validators=[FileRequired()])
	start_date = DateField('Start Date')
	start_time = TimeField('Start Time', default=datetime.utcnow()+timedelta(hours=5.5))
	end_date = DateField('End Date')
	end_time = TimeField('End Time', default=datetime.utcnow()+timedelta(hours=5.5))
	calc = BooleanField('Enable Calculator')
	neg_mark = DecimalField('Enable negative marking in % ', validators=[NumberRange(min=0, max=100)])
	duration = IntegerField('Duration(in min)')
	password = PasswordField('Exam Password', [validators.Length(min=3, max=6)])
	proctor_type = RadioField('Proctoring Type', choices=[('0','Automatic Monitoring'),('1','Live Monitoring')])

	def validate_end_date(form, field):
		if field.data < form.start_date.data:
			raise ValidationError("End date must not be earlier than start date.")
	
	def validate_end_time(form, field):
		start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		end_date_time = datetime.strptime(str(form.end_date.data) + " " + str(field.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		if start_date_time >= end_date_time:
			raise ValidationError("End date time must not be earlier/equal than start date time")
	
	def validate_start_date(form, field):
		if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S") < datetime.now():
			raise ValidationError("Start date and time must not be earlier than current")

class TestForm(Form):
	test_id = StringField('Exam ID')
	password = PasswordField('Exam Password')
	img_hidden_form = HiddenField(label=(''))

@app.route('/create-test', methods = ['GET', 'POST'])
@user_role_professor
def create_test():
	form = UploadForm()
	if request.method == 'POST' and form.validate_on_submit():
		test_id = generate_slug(2)
		filename = secure_filename(form.doc.data.filename)
		filestream = form.doc.data
		filestream.seek(0)
		ef = pd.read_csv(filestream)
		fields = ['qid','q','a','b','c','d','ans','marks']
		df = pd.DataFrame(ef, columns = fields)
		cur = mysql.connection.cursor()
		ecc = examcreditscheck()
		if ecc:
			for row in df.index:
				cur.execute('INSERT INTO questions(test_id,qid,q,a,b,c,d,ans,marks,uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (test_id, df['qid'][row], df['q'][row], df['a'][row], df['b'][row], df['c'][row], df['d'][row], df['ans'][row], df['marks'][row], session['uid']))
				cur.connection.commit()

			start_date = form.start_date.data
			end_date = form.end_date.data
			start_time = form.start_time.data
			end_time = form.end_time.data
			start_date_time = str(start_date) + " " + str(start_time)
			end_date_time = str(end_date) + " " + str(end_time)
			neg_mark = int(form.neg_mark.data)
			calc = int(form.calc.data)
			duration = int(form.duration.data)*60
			password = form.password.data
			subject = form.subject.data
			topic = form.topic.data
			proctor_type = form.proctor_type.data
			cur.execute('INSERT INTO teachers (email, test_id, test_type, start, end, duration, show_ans, password, subject, topic, neg_marks, calc,proctoring_type, uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
				(dict(session)['email'], test_id, "objective", start_date_time, end_date_time, duration, 1, password, subject, topic, neg_mark, calc, proctor_type, session['uid']))
			mysql.connection.commit()
			cur.execute('UPDATE users SET examcredits = examcredits-1 where email = %s and uid = %s', (session['email'],session['uid']))
			mysql.connection.commit()
			cur.close()
			flash(f'Exam ID: {test_id}', 'success')
			return redirect(url_for('professor_index'))
		else:
			flash("No exam credits points are found! Please pay it!")
			return redirect(url_for('professor_index'))
	return render_template('create_test.html' , form = form)

class PracUploadForm(FlaskForm):
	subject = StringField('Subject')
	topic = StringField('Topic')
	questionprac = StringField('Question')
	marksprac = IntegerField('Marks')
	start_date = DateField('Start Date')
	start_time = TimeField('Start Time', default=datetime.utcnow()+timedelta(hours=5.5))
	end_date = DateField('End Date')
	end_time = TimeField('End Time', default=datetime.utcnow()+timedelta(hours=5.5))
	duration = IntegerField('Duration(in min)')
	compiler = SelectField(u'Compiler/Interpreter', choices=[('11', 'C'), ('27', 'C#'), ('1', 'C++'),('114', 'Go'),('10', 'Java'),('47', 'Kotlin'),('56', 'Node.js'),
	('43', 'Objective-C'),('29', 'PHP'),('54', 'Perl-6'),('116', 'Python 3x'),('117', 'R'),('17', 'Ruby'),('93', 'Rust'),('52', 'SQLite-queries'),('40', 'SQLite-schema'),
	('39', 'Scala'),('85', 'Swift'),('57', 'TypeScript')])
	password = PasswordField('Exam Password', [validators.Length(min=3, max=10)])
	proctor_type = RadioField('Proctoring Type', choices=[('0','Automatic Monitoring'),('1','Live Monitoring')])

	def validate_end_date(form, field):
		if field.data < form.start_date.data:
			raise ValidationError("End date must not be earlier than start date.")
	
	def validate_end_time(form, field):
		start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		end_date_time = datetime.strptime(str(form.end_date.data) + " " + str(field.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		if start_date_time >= end_date_time:
			raise ValidationError("End date time must not be earlier/equal than start date time")
	
	def validate_start_date(form, field):
		if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S") < datetime.now():
			raise ValidationError("Start date and time must not be earlier than current")

@app.route('/create_test_pqa', methods = ['GET', 'POST'])
@user_role_professor
def create_test_pqa():
	form = PracUploadForm()
	if request.method == 'POST' and form.validate_on_submit():
		test_id = generate_slug(2)
		ecc = examcreditscheck()
		print(ecc)
		if ecc:
			test_id = generate_slug(2)
			compiler = form.compiler.data
			questionprac = form.questionprac.data
			marksprac = int(form.marksprac.data)
			cur = mysql.connection.cursor()
			cur.execute('INSERT INTO practicalqa(test_id,qid,q,compiler,marks,uid) values(%s,%s,%s,%s,%s,%s)', (test_id, 1, questionprac, compiler, marksprac, session['uid']))
			mysql.connection.commit()
			start_date = form.start_date.data
			end_date = form.end_date.data
			start_time = form.start_time.data
			end_time = form.end_time.data
			start_date_time = str(start_date) + " " + str(start_time)
			end_date_time = str(end_date) + " " + str(end_time)
			duration = int(form.duration.data)*60
			password = form.password.data
			subject = form.subject.data
			topic = form.topic.data
			proctor_type = form.proctor_type.data
			cur.execute('INSERT INTO teachers (email, test_id, test_type, start, end, duration, show_ans, password, subject, topic, neg_marks, calc, proctoring_type, uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
				(dict(session)['email'], test_id, "practical", start_date_time, end_date_time, duration, 0, password, subject, topic, 0, 0, proctor_type, session['uid']))
			mysql.connection.commit()
			cur.execute('UPDATE users SET examcredits = examcredits-1 where email = %s and uid = %s', (session['email'],session['uid']))
			mysql.connection.commit()
			cur.close()
			flash(f'Exam ID: {test_id}', 'success')
			return redirect(url_for('professor_index'))
		else:
			flash("No exam credits points are found! Please pay it!")
			return redirect(url_for('professor_index'))	
	return render_template('create_prac_qa.html' , form = form)

@app.route('/deltidlist', methods=['GET'])
@user_role_professor
def deltidlist():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s', (session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['start']),"%Y-%m-%d %H:%M:%S") > now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("deltidlist.html", cresults = testids)
	else:
		return render_template("deltidlist.html", cresults = None)

@app.route('/deldispques', methods=['GET','POST'])
@user_role_professor
def deldispques():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "objective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispques.html", callresults = callresults, tid = tidoption)
		elif et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from longqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispquesLQA.html", callresults = callresults, tid = tidoption)
		elif et['test_type'] == "practical":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from practicalqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispquesPQA.html", callresults = callresults, tid = tidoption)
		else:
			flash("Some Error Occured!")
			return redirect(url_for('/deltidlist'))

@app.route('/delete_questions/<testid>', methods=['GET', 'POST'])
@user_role_professor
def delete_questions(testid):
	et = examtypecheck(testid)
	if et['test_type'] == "objective":
		cur = mysql.connection.cursor()
		msg = '' 
		if request.method == 'POST':
			testqdel = request.json['qids']
			if testqdel:
				if ',' in testqdel:
					testqdel = testqdel.split(',')
					for getid in testqdel:
						cur.execute('DELETE FROM questions WHERE test_id = %s and qid =%s and uid = %s', (testid,getid,session['uid']))
						mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
				else:
					cur.execute('DELETE FROM questions WHERE test_id = %s and qid =%s and uid = %s', (testid,testqdel,session['uid']))
					mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
	elif et['test_type'] == "subjective":
		cur = mysql.connection.cursor()
		msg = '' 
		if request.method == 'POST':
			testqdel = request.json['qids']
			if testqdel:
				if ',' in testqdel:
					testqdel = testqdel.split(',')
					for getid in testqdel:
						cur.execute('DELETE FROM longqa WHERE test_id = %s and qid =%s and uid = %s', (testid,getid,session['uid']))
						mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
				else:
					cur.execute('DELETE FROM longqa WHERE test_id = %s and qid =%s and uid = %s', (testid,testqdel,session['uid']))
					mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
	elif et['test_type'] == "practical":
		cur = mysql.connection.cursor()
		msg = '' 
		if request.method == 'POST':
			testqdel = request.json['qids']
			if testqdel:
				if ',' in testqdel:
					testqdel = testqdel.split(',')
					for getid in testqdel:
						cur.execute('DELETE FROM practicalqa WHERE test_id = %s and qid =%s and uid = %s', (testid,getid,session['uid']))
						mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
			else:
				cur.execute('DELETE FROM questions WHERE test_id = %s and qid =%s and uid = %s', (testid,testqdel,session['uid']))
				mysql.connection.commit()
				resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
				resp.status_code = 200
				return resp
	else:
		flash("Some Error Occured!")
		return redirect(url_for('/deltidlist'))

@app.route('/<testid>/<qid>')
@user_role_professor
def del_qid(testid, qid):
	cur = mysql.connection.cursor()
	results = cur.execute('DELETE FROM questions where test_id = %s and qid = %s and uid = %s', (testid,qid,session['uid']))
	mysql.connection.commit()
	if results>0:
		msg="Deleted successfully"
		flash('Deleted successfully.', 'success')
		cur.close()
		return render_template("deldispques.html", success=msg)
	else:
		return redirect(url_for('/deldispques'))

@app.route('/updatetidlist', methods=['GET'])
@user_role_professor
def updatetidlist():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s', (session['email'],session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['start']),"%Y-%m-%d %H:%M:%S") > now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("updatetidlist.html", cresults = testids)
	else:
		return render_template("updatetidlist.html", cresults = None)

@app.route('/updatedispques', methods=['GET','POST'])
@user_role_professor
def updatedispques():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "objective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("updatedispques.html", callresults = callresults)
		elif et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from longqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("updatedispquesLQA.html", callresults = callresults)
		elif et['test_type'] == "practical":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from practicalqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("updatedispquesPQA.html", callresults = callresults)
		else:
			flash('Error Occured!')
			return redirect(url_for('updatetidlist'))

@app.route('/update/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_quiz(testid, qid):
	if request.method == 'GET':
		cur = mysql.connection.cursor()
		cur.execute('SELECT * FROM questions where test_id = %s and qid =%s and uid = %s', (testid,qid,session['uid']))
		uresults = cur.fetchall()
		mysql.connection.commit()
		return render_template("updateQuestions.html", uresults=uresults)
	if request.method == 'POST':
		ques = request.form['ques']
		ao = request.form['ao']
		bo = request.form['bo']
		co = request.form['co']
		do = request.form['do']
		anso = request.form['anso']
		markso = request.form['mko']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE questions SET q = %s, a = %s, b = %s, c = %s, d = %s, ans = %s, marks = %s where test_id = %s and qid = %s and uid = %s', (ques,ao,bo,co,do,anso,markso,testid,qid,session['uid']))
		cur.connection.commit()
		flash('Updated successfully.', 'success')
		cur.close()
		return redirect(url_for('updatetidlist'))
	else:
		flash('ERROR  OCCURED.', 'error')
		return redirect(url_for('updatetidlist'))

@app.route('/updateLQA/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_lqa(testid, qid):
	if request.method == 'GET':
		cur = mysql.connection.cursor()
		cur.execute('SELECT * FROM longqa where test_id = %s and qid =%s and uid = %s', (testid,qid,session['uid']))
		uresults = cur.fetchall()
		mysql.connection.commit()
		return render_template("updateQuestionsLQA.html", uresults=uresults)
	if request.method == 'POST':
		ques = request.form['ques']
		markso = request.form['mko']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE longqa SET q = %s, marks = %s where test_id = %s and qid = %s and uid = %s', (ques,markso,testid,qid,session['uid']))
		cur.connection.commit()
		flash('Updated successfully.', 'success')
		cur.close()
		return redirect(url_for('updatetidlist'))
	else:
		flash('ERROR  OCCURED.', 'error')
		return redirect(url_for('updatetidlist'))

@app.route('/updatePQA/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_PQA(testid, qid):
	if request.method == 'GET':
		cur = mysql.connection.cursor()
		cur.execute('SELECT * FROM practicalqa where test_id = %s and qid =%s and uid = %s', (testid,qid,session['uid']))
		uresults = cur.fetchall()
		mysql.connection.commit()
		return render_template("updateQuestionsPQA.html", uresults=uresults)
	if request.method == 'POST':
		ques = request.form['ques']
		markso = request.form['mko']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE practicalqa SET q = %s, marks = %s where test_id = %s and qid = %s and uid = %s', (ques,markso,testid,qid,session['uid']))
		cur.connection.commit()
		flash('Updated successfully.', 'success')
		cur.close()
		return redirect(url_for('updatetidlist'))
	else:
		flash('ERROR  OCCURED.', 'error')
		return redirect(url_for('updatetidlist'))

@app.route('/viewquestions', methods=['GET'])
@user_role_professor
def viewquestions():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT test_id from teachers where email = %s and uid = %s', (session['email'],session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		cur.close()
		return render_template("viewquestions.html", cresults = cresults)
	else:
		return render_template("viewquestions.html", cresults = None)

def examtypecheck(tidoption):
	cur = mysql.connection.cursor()
	cur.execute('SELECT test_type from teachers where test_id = %s and email = %s and uid = %s', (tidoption,session['email'],session['uid']))
	callresults = cur.fetchone()
	cur.close()
	return callresults

@app.route('/displayquestions', methods=['GET','POST'])
@user_role_professor
def displayquestions():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "objective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("displayquestions.html", callresults = callresults)
		elif et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from longqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("displayquestionslong.html", callresults = callresults)
		elif et['test_type'] == "practical":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from practicalqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("displayquestionspractical.html", callresults = callresults)

@app.route('/viewstudentslogs', methods=['GET'])
@user_role_professor
def viewstudentslogs():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT test_id from teachers where email = %s and uid = %s and proctoring_type = 0', (session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		cur.close()
		return render_template("viewstudentslogs.html", cresults = cresults)
	else:
		return render_template("viewstudentslogs.html", cresults = None)

@app.route('/insertmarkstid', methods=['GET'])
@user_role_professor
def insertmarkstid():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where show_ans = 0 and email = %s and uid = %s and (test_type = %s or test_type = %s)', (session['email'], session['uid'],"subjective","practical"))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['end']),"%Y-%m-%d %H:%M:%S") < now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("insertmarkstid.html", cresults = testids)
	else:
		return render_template("insertmarkstid.html", cresults = None)

@app.route('/displaystudentsdetails', methods=['GET','POST'])
@user_role_professor
def displaystudentsdetails():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		cur = mysql.connection.cursor()
		cur.execute('SELECT DISTINCT email,test_id from proctoring_log where test_id = %s', [tidoption])
		callresults = cur.fetchall()
		cur.close()
		return render_template("displaystudentsdetails.html", callresults = callresults)

@app.route('/insertmarksdetails', methods=['GET','POST'])
@user_role_professor
def insertmarksdetails():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT DISTINCT email,test_id from longtest where test_id = %s', [tidoption])
			callresults = cur.fetchall()
			cur.close()
			return render_template("subdispstudentsdetails.html", callresults = callresults)
		elif et['test_type'] == "practical":
			cur = mysql.connection.cursor()
			cur.execute('SELECT DISTINCT email,test_id from practicaltest where test_id = %s', [tidoption])
			callresults = cur.fetchall()
			cur.close()
			return render_template("pracdispstudentsdetails.html", callresults = callresults)
		else:
			flash("Some Error was occured!",'error')
			return redirect(url_for('insertmarkstid'))

@app.route('/insertsubmarks/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def insertsubmarks(testid,email):
	if request.method == "GET":
		cur = mysql.connection.cursor()
		cur.execute('SELECT l.email as email, l.marks as inputmarks, l.test_id as test_id, l.qid as qid, l.ans as ans, lqa.marks as marks, l.uid as uid, lqa.q as q  from longtest l, longqa lqa where l.test_id = %s and l.email = %s and l.test_id = lqa.test_id and l.qid = lqa.qid ORDER BY qid ASC', (testid, email))
		callresults = cur.fetchall()
		cur.close()
		return render_template("insertsubmarks.html", callresults = callresults)
	if request.method == "POST":
		cur = mysql.connection.cursor()
		results1 = cur.execute('SELECT COUNT(qid) from longtest where test_id = %s and email = %s',(testid, email))
		results1 = cur.fetchone()
		cur.close()
		for sa in range(1,results1['COUNT(qid)']+1):
			marksByProfessor = request.form[str(sa)]
			cur = mysql.connection.cursor()
			cur.execute('UPDATE longtest SET marks = %s WHERE test_id = %s and email = %s and qid = %s', (marksByProfessor, testid, email, sa))
			mysql.connection.commit()
		cur.close()
		flash('Marks Entered Sucessfully!', 'success')
		return redirect(url_for('insertmarkstid'))

@app.route('/insertpracmarks/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def insertpracmarks(testid,email):
	if request.method == "GET":
		cur = mysql.connection.cursor()
		cur.execute('SELECT l.email as email, l.marks as inputmarks, l.test_id as test_id, l.qid as qid, l.code as code, l.input as input, l.executed as executed, lqa.marks as marks, l.uid as uid, lqa.q as q  from practicaltest l, practicalqa lqa where l.test_id = %s and l.email = %s and l.test_id = lqa.test_id and l.qid = lqa.qid ORDER BY qid ASC', (testid, email))
		callresults = cur.fetchall()
		cur.close()
		return render_template("insertpracmarks.html", callresults = callresults)
	if request.method == "POST":
		cur = mysql.connection.cursor()
		results1 = cur.execute('SELECT COUNT(qid) from practicaltest where test_id = %s and email = %s',(testid, email))
		results1 = cur.fetchone()
		cur.close()
		for sa in range(1,results1['COUNT(qid)']+1):
			marksByProfessor = request.form[str(sa)]
			cur = mysql.connection.cursor()
			cur.execute('UPDATE practicaltest SET marks = %s WHERE test_id = %s and email = %s and qid = %s', (marksByProfessor, testid, email, sa))
			mysql.connection.commit()
		cur.close()
		flash('Marks Entered Sucessfully!', 'success')
		return redirect(url_for('insertmarkstid'))

def displaywinstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from window_estimation_log where test_id = %s and email = %s and window_event = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return callresults

def countwinstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as wincount from window_estimation_log where test_id = %s and email = %s and window_event = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	winc = [i['wincount'] for i in callresults]
	return winc

def countMobStudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as mobcount from proctoring_log where test_id = %s and email = %s and phone_detection = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	mobc = [i['mobcount'] for i in callresults]
	return mobc

def countMTOPstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as percount from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	perc = [i['percount'] for i in callresults]
	return perc

def countMTOPstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as percount from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	perc = [i['percount'] for i in callresults]
	return perc

def countTotalstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as total from proctoring_log where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	tot = [i['total'] for i in callresults]
	return tot

@app.route('/studentmonitoringstats/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def studentmonitoringstats(testid,email):
	return render_template("stat_student_monitoring.html", testid = testid, email = email)

@app.route('/ajaxstudentmonitoringstats/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def ajaxstudentmonitoringstats(testid,email):
	win = countwinstudentslogs(testid,email)
	mob = countMobStudentslogs(testid,email)
	per = countMTOPstudentslogs(testid,email)
	tot = countTotalstudentslogs(testid,email)
	return jsonify({"win":win,"mob":mob,"per":per,"tot":tot})

@app.route('/displaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def displaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("displaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/mobdisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def mobdisplaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s and phone_detection = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("mobdisplaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/persondisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def persondisplaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("persondisplaystudentslogs.html",testid = testid, email = email, callresults = callresults)

@app.route('/audiodisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def audiodisplaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("audiodisplaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/wineventstudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def wineventstudentslogs(testid,email):
	callresults = displaywinstudentslogs(testid,email)
	return render_template("wineventstudentlog.html", testid = testid, email = email, callresults = callresults)

@app.route('/<email>/<testid>/share_details', methods=['GET','POST'])
@user_role_professor
def share_details(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from teachers where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("share_details.html", callresults = callresults)

@app.route('/share_details_emails', methods=['GET','POST'])
@user_role_professor
def share_details_emails():
	if request.method == 'POST':
		tid = request.form['tid']
		subject = request.form['subject']
		topic = request.form['topic']
		duration = request.form['duration']
		start = request.form['start']
		end = request.form['end']
		password = request.form['password']
		neg_marks = request.form['neg_marks']
		calc = request.form['calc']
		emailssharelist = request.form['emailssharelist']
		msg1 = Message('EXAM DETAILS - MyProctor.ai', sender = sender, recipients = [emailssharelist])
		msg1.body = " ".join(["EXAM-ID:", tid, "SUBJECT:", subject, "TOPIC:", topic, "DURATION:", duration, "START", start, "END", end, "PASSWORD", password, "NEGATIVE MARKS in %:", neg_marks,"CALCULATOR ALLOWED:",calc ]) 
		mail.send(msg1)
		flash('Emails sended sucessfully!', 'success')
	return render_template('share_details.html')

@app.route("/publish-results-testid", methods=['GET','POST'])
@user_role_professor
def publish_results_testid():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where test_type != %s AND show_ans = 0 AND email = %s AND uid = %s', ("objectve", session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['end']),"%Y-%m-%d %H:%M:%S") < now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("publish_results_testid.html", cresults = testids)
	else:
		return render_template("publish_results_testid.html", cresults = None)

@app.route('/viewresults', methods=['GET','POST'])
@user_role_professor
def viewresults():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT SUM(marks) as marks, email from longtest where test_id = %s group by email', ([tidoption]))
			callresults = cur.fetchall()
			cur.close()
			return render_template("publish_viewresults.html", callresults = callresults, tid = tidoption)
		elif et['test_type'] == "practical":
			cur = mysql.connection.cursor()
			cur.execute('SELECT SUM(marks) as marks, email from practicaltest where test_id = %s group by email', ([tidoption]))
			callresults = cur.fetchall()
			cur.close()
			return render_template("publish_viewresults.html", callresults = callresults, tid = tidoption)
		else:
			flash("Some Error Occured!")
			return redirect(url_for('publish-results-testid'))

@app.route('/publish_results', methods=['GET','POST'])
@user_role_professor
def publish_results():
	if request.method == 'POST':
		tidoption = request.form['testidsp']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE teachers set show_ans = 1 where test_id = %s', ([tidoption]))
		mysql.connection.commit()
		cur.close()
		flash("Results published sucessfully!")
		return redirect(url_for('professor_index'))

@app.route('/test_update_time', methods=['GET','POST'])
@user_role_student
def test_update_time():
	if request.method == 'POST':
		cur = mysql.connection.cursor()
		time_left = request.form['time']
		testid = request.form['testid']
		cur.execute('UPDATE studentTestInfo set time_left=SEC_TO_TIME(%s) where test_id = %s and email = %s and uid = %s and completed=0', (time_left, testid, session['email'], session['uid']))
		mysql.connection.commit()
		t1 = cur.rowcount
		cur.close()
		if t1 > 0:
			return "time recorded updated"
		else:
			cur = mysql.connection.cursor()
			cur.execute('INSERT into studentTestInfo (email, test_id,time_left,uid) values(%s,%s,SEC_TO_TIME(%s),%s)', (session['email'], testid, time_left, session['uid']))
			t2 = mysql.connection.commit()
			t2 = cur.rowcount
			cur.close()
			if t2 > 0:
				return "time recorded inserted"
			else:
				return "time error"

@app.route("/give-test", methods = ['GET', 'POST'])
@user_role_student
def give_test():
    global duration, marked_ans, calc, subject, topic, proctortype
    form = TestForm(request.form)
    
    if request.method == 'POST' and form.validate():
        test_id = form.test_id.data
        password_candidate = form.password.data
        
        cur = mysql.connection.cursor()
        
        # Verify user's image against stored image (if required)
        # This part is commented out since camera functionality is removed
        """
        imgdata1 = form.img_hidden_form.data
        results1 = cur.execute('SELECT user_image FROM users WHERE email = %s AND user_type = %s', (session['email'], 'student'))
        
        if results1 > 0:
            cresults = cur.fetchone()
            imgdata2 = cresults['user_image']
            
            nparr1 = np.frombuffer(base64.b64decode(imgdata1), np.uint8)
            nparr2 = np.frombuffer(base64.b64decode(imgdata2), np.uint8)
            image1 = cv2.imdecode(nparr1, cv2.COLOR_BGR2GRAY)
            image2 = cv2.imdecode(nparr2, cv2.COLOR_BGR2GRAY)
            
            img_result = DeepFace.verify(image1, image2, enforce_detection=False)
            
            if not img_result["verified"]:
                flash('Image not verified', 'danger')
                return redirect(url_for('give_test'))
        else:
            flash('User image not found', 'danger')
            return redirect(url_for('give_test'))
        """
        
        results = cur.execute('SELECT * FROM teachers WHERE test_id = %s', [test_id])
        
        if results > 0:
            data = cur.fetchone()
            password = data[8]
            duration = data[6]
            calc = data[12]
            subject = data[9]
            topic = data[10]
            start = data[4]
            end = data[5]
            proctortype = data[13]
            
            if password == password_candidate:
                now = datetime.now()
                
                if start < now < end:
                    cur.execute('SELECT time_to_sec(time_left) AS time_left, completed FROM studentTestInfo WHERE email = %s AND test_id = %s', (session['email'], test_id))
                    results = cur.fetchone()
                    
                    if results:
                        is_completed = results[0]
                        time_left = results[1]
                        
                        if not is_completed and time_left <= duration:
                            duration = time_left
                            cur.execute('SELECT qid, ans FROM students WHERE email = %s AND test_id = %s AND uid = %s', (session['email'], test_id, session['uid']))
                            marked_ans = {row['qid']: row['ans'] for row in cur.fetchall()}
                            marked_ans = json.dumps(marked_ans)
                    else:
                        cur.execute('INSERT INTO studentTestInfo (email, test_id, time_left, uid) VALUES (%s, %s, SEC_TO_TIME(%s), %s)', (session['email'], test_id, duration, session['uid']))
                        mysql.connection.commit()
                        
                        cur.execute('SELECT time_to_sec(time_left) AS time_left, completed FROM studentTestInfo WHERE email = %s AND test_id = %s AND uid = %s', (session['email'], test_id, session['uid']))
                        results = cur.fetchone()
                        
                        if results:
                            is_completed = results[0]
                            time_left = results[1]
                            
                            if not is_completed and time_left <= duration:
                                duration = time_left
                                cur.execute('SELECT * FROM students WHERE email = %s AND test_id = %s AND uid = %s', (session['email'], test_id, session['uid']))
                                marked_ans = {row['qid']: row['ans'] for row in cur.fetchall()}
                                marked_ans = json.dumps(marked_ans)
                else:
                    if now < start:
                        flash(f'Exam start time is {start}', 'danger')
                    else:
                        flash(f'Exam has ended', 'danger')
                    return redirect(url_for('give_test'))
                
                cur.close()
                return redirect(url_for('test', testid=test_id))
            else:
                flash('Invalid password', 'danger')
        else:
            flash('Invalid test id', 'danger')
    
    return render_template('give_test.html', form=form)

@app.route('/give-test/<testid>', methods=['GET','POST'])
@user_role_student
def test(testid):
	cur = mysql.connection.cursor()
	cur.execute('SELECT test_type from teachers where test_id = %s ', [testid])
	callresults = cur.fetchone()
	cur.close()
	if callresults['test_type'] == "objective":
		global duration, marked_ans, calc, subject, topic, proctortype
		if request.method == 'GET':
			try:
				data = {'duration': duration, 'marks': '', 'q': '', 'a': '', 'b':'','c':'','d':'' }
				return render_template('testquiz.html' ,**data, answers=marked_ans, calc=calc, subject=subject, topic=topic, tid=testid, proctortype=proctortype)
			except:
				return redirect(url_for('give_test'))
		else:
			cur = mysql.connection.cursor()
			flag = request.form['flag']
			if flag == 'get':
				num = request.form['no']
				results = cur.execute('SELECT test_id,qid,q,a,b,c,d,ans,marks from questions where test_id = %s and qid =%s',(testid, num))
				if results > 0:
					data = cur.fetchone()
					del data['ans']
					cur.close()
					return json.dumps(data)
			elif flag=='mark':
				qid = request.form['qid']
				ans = request.form['ans']
				cur = mysql.connection.cursor()
				results = cur.execute('SELECT * from students where test_id =%s and qid = %s and email = %s', (testid, qid, session['email']))
				if results > 0:
					cur.execute('UPDATE students set ans = %s where test_id = %s and qid = %s and email = %s', (testid, qid, session['email']))
					mysql.connection.commit()
					cur.close()
				else:
					cur.execute('INSERT INTO students(email,test_id,qid,ans,uid) values(%s,%s,%s,%s,%s)', (session['email'], testid, qid, ans, session['uid']))
					mysql.connection.commit()
					cur.close()
			elif flag=='time':
				cur = mysql.connection.cursor()
				time_left = request.form['time']
				try:
					cur.execute('UPDATE studentTestInfo set time_left=SEC_TO_TIME(%s) where test_id = %s and email = %s and uid = %s and completed=0', (time_left, testid, session['email'], session['uid']))
					mysql.connection.commit()
					cur.close()
					return json.dumps({'time':'fired'})
				except:
					pass
			else:
				cur = mysql.connection.cursor()
				cur.execute('UPDATE studentTestInfo set completed=1,time_left=sec_to_time(0) where test_id = %s and email = %s and uid = %s', (testid, session['email'],session['uid']))
				mysql.connection.commit()
				cur.close()
				flash("Exam submitted successfully", 'info')
				return json.dumps({'sql':'fired'})

	elif callresults['test_type'] == "subjective":
		if request.method == 'GET':
			cur = mysql.connection.cursor()
			cur.execute('SELECT test_id, qid, q, marks from longqa where test_id = %s ORDER BY RAND()',[testid])
			callresults1 = cur.fetchall()
			cur.execute('SELECT time_to_sec(time_left) as duration from studentTestInfo where completed = 0 and test_id = %s and email = %s and uid = %s', (testid, session['email'], session['uid']))
			studentTestInfo = cur.fetchone()
			if studentTestInfo != None:
				duration = studentTestInfo['duration']
				cur.execute('SELECT test_id, subject, topic, proctoring_type from teachers where test_id = %s',[testid])
				testDetails = cur.fetchone()
				subject = testDetails['subject']
				test_id = testDetails['test_id']
				topic = testDetails['topic']
				proctortypes = testDetails['proctoring_type']
				cur.close()
				return render_template("testsubjective.html", callresults = callresults1, subject = subject, duration = duration, test_id = test_id, topic = topic, proctortypes = proctortypes )
			else:
				cur = mysql.connection.cursor()
				cur.execute('SELECT test_id, duration, subject, topic from teachers where test_id = %s',[testid])
				testDetails = cur.fetchone()
				subject = testDetails['subject']
				duration = testDetails['duration']
				test_id = testDetails['test_id']
				topic = testDetails['topic']
				cur.close()
				return render_template("testsubjective.html", callresults = callresults1, subject = subject, duration = duration, test_id = test_id, topic = topic )
		elif request.method == 'POST':
			cur = mysql.connection.cursor()
			test_id = request.form["test_id"]
			cur = mysql.connection.cursor()
			results1 = cur.execute('SELECT COUNT(qid) from longqa where test_id = %s',[testid])
			results1 = cur.fetchone()
			cur.close()
			insertStudentData = None
			for sa in range(1,results1['COUNT(qid)']+1):
				answerByStudent = request.form[str(sa)]
				cur = mysql.connection.cursor()
				insertStudentData = cur.execute('INSERT INTO longtest(email,test_id,qid,ans,uid) values(%s,%s,%s,%s,%s)', (session['email'], testid, sa, answerByStudent, session['uid']))
				mysql.connection.commit()
			else:
				if insertStudentData > 0:
					insertStudentTestInfoData = cur.execute('UPDATE studentTestInfo set completed = 1 where test_id = %s and email = %s and uid = %s', (test_id, session['email'], session['uid']))
					mysql.connection.commit()
					cur.close()
					if insertStudentTestInfoData > 0:
						flash('Successfully Exam Submitted', 'success')
						return redirect(url_for('student_index'))
					else:
						cur.close()
						flash('Some Error was occured!', 'error')
						return redirect(url_for('student_index'))	
				else:
					cur.close()
					flash('Some Error was occured!', 'error')
					return redirect(url_for('student_index'))

	elif callresults['test_type'] == "practical":
		if request.method == 'GET':
			cur = mysql.connection.cursor()
			cur.execute('SELECT test_id, qid, q, marks, compiler from practicalqa where test_id = %s ORDER BY RAND()',[testid])
			callresults1 = cur.fetchall()
			cur.execute('SELECT time_to_sec(time_left) as duration from studentTestInfo where completed = 0 and test_id = %s and email = %s and uid = %s', (testid, session['email'], session['uid']))
			studentTestInfo = cur.fetchone()
			if studentTestInfo != None:
				duration = studentTestInfo['duration']
				cur.execute('SELECT test_id, subject, topic, proctoring_type from teachers where test_id = %s',[testid])
				testDetails = cur.fetchone()
				subject = testDetails['subject']
				test_id = testDetails['test_id']
				topic = testDetails['topic']
				proctortypep = testDetails['proctoring_type']
				cur.close()
				return render_template("testpractical.html", callresults = callresults1, subject = subject, duration = duration, test_id = test_id, topic = topic, proctortypep = proctortypep )
			else:
				cur = mysql.connection.cursor()
				cur.execute('SELECT test_id, duration, subject, topic from teachers where test_id = %s',[testid])
				testDetails = cur.fetchone()
				subject = testDetails['subject']
				duration = testDetails['duration']
				test_id = testDetails['test_id']
				topic = testDetails['topic']
				cur.close()
				return render_template("testpractical.html", callresults = callresults1, subject = subject, duration = duration, test_id = test_id, topic = topic )
		elif request.method == 'POST':
			test_id = request.form["test_id"]
			codeByStudent = request.form["codeByStudent"]
			inputByStudent = request.form["inputByStudent"]
			executedByStudent = request.form["executedByStudent"]
			cur = mysql.connection.cursor()
			insertStudentData = cur.execute('INSERT INTO practicaltest(email,test_id,qid,code,input,executed,uid) values(%s,%s,%s,%s,%s,%s,%s)', (session['email'], testid, "1", codeByStudent, inputByStudent, executedByStudent, session['uid']))
			mysql.connection.commit()
			if insertStudentData > 0:
				insertStudentTestInfoData = cur.execute('UPDATE studentTestInfo set completed = 1 where test_id = %s and email = %s and uid = %s', (test_id, session['email'], session['uid']))
				mysql.connection.commit()
				cur.close()
				if insertStudentTestInfoData > 0:
					flash('Successfully Exam Submitted', 'success')
					return redirect(url_for('student_index'))
				else:
					cur.close()
					flash('Some Error was occured!', 'error')
					return redirect(url_for('student_index'))	
			else:
				cur.close()
				flash('Some Error was occured!', 'error')
				return redirect(url_for('student_index'))

@app.route('/randomize', methods = ['POST'])
def random_gen():
	if request.method == "POST":
		id = request.form['id']
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT count(*) from questions where test_id = %s', [id])
		if results > 0:
			data = cur.fetchone()
			total = data['count(*)']
			nos = list(range(1,int(total)+1))
			random.Random(id).shuffle(nos)
			cur.close()
			return json.dumps(nos)

@app.route('/<email>/<testid>')
@user_role_student
def check_result(email, testid):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT * FROM teachers where test_id = %s', [testid])
		if results>0:
			results = cur.fetchone()
			check = results['show_ans']
			if check == 1:
				results = cur.execute('select q,a,b,c,d,marks,q.qid as qid, \
					q.ans as correct, ifnull(s.ans,0) as marked from questions q left join \
					students s on  s.test_id = q.test_id and s.test_id = %s \
					and s.email = %s and s.uid = %s and s.qid = q.qid group by q.qid \
					order by LPAD(lower(q.qid),10,0) asc', (testid, email, session['uid']))
				if results > 0:
					results = cur.fetchall()
					return render_template('tests_result.html', results= results)
			else:
				flash('You are not authorized to check the result', 'danger')
				return redirect(url_for('tests_given',email = email))
	else:
		return redirect(url_for('student_index'))

def neg_marks(email,testid,negm):
	cur=mysql.connection.cursor()
	results = cur.execute("select marks,q.qid as qid, \
				q.ans as correct, ifnull(s.ans,0) as marked from questions q inner join \
				students s on  s.test_id = q.test_id and s.test_id = %s \
				and s.email = %s and s.qid = q.qid group by q.qid \
				order by q.qid asc", (testid, email))
	data=cur.fetchall()

	sum=0.0
	for i in range(results):
		if(str(data[i]['marked']).upper() != '0'):
			if(str(data[i]['marked']).upper() != str(data[i]['correct']).upper()):
				sum=sum - (negm/100) * int(data[i]['marks'])
			elif(str(data[i]['marked']).upper() == str(data[i]['correct']).upper()):
				sum+=int(data[i]['marks'])
	return sum

def totmarks(email,tests): 
	cur = mysql.connection.cursor()
	for test in tests:
		testid = test['test_id']
		results=cur.execute("select neg_marks from teachers where test_id=%s",[testid])
		results=cur.fetchone()
		negm = results['neg_marks']
		data = neg_marks(email,testid,negm)
		return data

def marks_calc(email,testid):
		cur = mysql.connection.cursor()
		results=cur.execute("select neg_marks from teachers where test_id=%s",[testid])
		results=cur.fetchone()
		negm = results['neg_marks']
		return neg_marks(email,testid,negm) 
		
@app.route('/<email>/tests-given', methods = ['POST','GET'])
@user_role_student
def tests_given(email):
	if request.method == "GET":
		if email == session['email']:
			cur = mysql.connection.cursor()
			resultsTestids = cur.execute('select studenttestinfo.test_id as test_id from studenttestinfo,teachers where studenttestinfo.email = %s and studenttestinfo.uid = %s and studenttestinfo.completed=1 and teachers.test_id = studenttestinfo.test_id and teachers.show_ans = 1 ', (session['email'], session['uid']))
			resultsTestids = cur.fetchall()
			cur.close()
			return render_template('tests_given.html', cresults = resultsTestids)
		else:
			flash('You are not authorized', 'danger')
			return redirect(url_for('student_index'))
	if request.method == "POST":
		tidoption = request.form['choosetid']
		cur = mysql.connection.cursor()
		cur.execute('SELECT test_type from teachers where test_id = %s',[tidoption])
		callresults = cur.fetchone()
		cur.close()
		if callresults['test_type'] == "objective":
			cur = mysql.connection.cursor()
			results = cur.execute('select distinct(students.test_id) as test_id, students.email as email, subject,topic,neg_marks from students,studenttestinfo,teachers where students.email = %s and teachers.test_type = %s and students.test_id = %s and students.test_id=teachers.test_id and students.test_id=studenttestinfo.test_id and studenttestinfo.completed=1', (email, "objective", tidoption))
			results = cur.fetchall()
			cur.close()
			results1 = []
			studentResults = None
			for a in results:
				results1.append(neg_marks(a['email'],a['test_id'],a['neg_marks']))
				studentResults = zip(results,results1)
			return render_template('obj_result_student.html', tests=studentResults)
		elif callresults['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			studentResults = cur.execute('select SUM(longtest.marks) as marks, longtest.test_id as test_id, teachers.subject as subject, teachers.topic as topic from longtest,teachers,studenttestinfo where longtest.email = %s and longtest.test_id = %s and longtest.test_id=teachers.test_id and studenttestinfo.test_id=teachers.test_id and longtest.email = studenttestinfo.email and studenttestinfo.completed = 1 and teachers.show_ans=1 group by longtest.test_id', (email, tidoption))
			studentResults = cur.fetchall()
			cur.close()
			return render_template('sub_result_student.html', tests=studentResults)
		elif callresults['test_type'] == "practical":
			cur = mysql.connection.cursor()
			studentResults = cur.execute('select SUM(practicaltest.marks) as marks, practicaltest.test_id as test_id, teachers.subject as subject, teachers.topic as topic from practicaltest,teachers,studenttestinfo where practicaltest.email = %s and practicaltest.test_id = %s and practicaltest.test_id=teachers.test_id and studenttestinfo.test_id=teachers.test_id and practicaltest.email = studenttestinfo.email and studenttestinfo.completed = 1 and teachers.show_ans=1 group by practicaltest.test_id', (email, tidoption))
			studentResults = cur.fetchall()
			cur.close()
			return render_template('prac_result_student.html', tests=studentResults)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('student_index'))

@app.route('/<email>/tests-created')
@user_role_professor
def tests_created(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('select * from teachers where email = %s and uid = %s and show_ans = 1', (email,session['uid']))
		results = cur.fetchall()
		return render_template('tests_created.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('professor_index'))

@app.route('/<email>/tests-created/<testid>', methods = ['POST','GET'])
@user_role_professor
def student_results(email, testid):
	if email == session['email']:
		et = examtypecheck(testid)
		if request.method =='GET':
			if et['test_type'] == "objective":
				cur = mysql.connection.cursor()
				results = cur.execute('select users.name as name,users.email as email, studentTestInfo.test_id as test_id from studentTestInfo, users where test_id = %s and completed = 1 and  users.user_type = %s and studentTestInfo.email=users.email ', (testid,'student'))
				results = cur.fetchall()
				cur.close()
				final = []
				names = []
				scores = []
				count = 1
				for user in results:
					score = marks_calc(user['email'], user['test_id'])
					user['srno'] = count
					user['marks'] = score
					final.append([count, user['name'], score])
					names.append(user['name'])
					scores.append(score)
					count+=1
				return render_template('student_results.html', data=final, labels=names, values=scores)
			elif et['test_type'] == "subjective":
				cur = mysql.connection.cursor()
				results = cur.execute('select users.name as name,users.email as email, longtest.test_id as test_id, SUM(longtest.marks) AS marks from longtest, users where longtest.test_id = %s  and  users.user_type = %s and longtest.email=users.email', (testid,'student'))
				results = cur.fetchall()
				cur.close()
				names = []
				scores = []
				for user in results:
					names.append(user['name'])
					scores.append(user['marks'])
				return render_template('student_results_lqa.html', data=results, labels=names, values=scores)
			elif et['test_type'] == "practical":
				cur = mysql.connection.cursor()
				results = cur.execute('select users.name as name,users.email as email, practicaltest.test_id as test_id, SUM(practicaltest.marks) AS marks from practicaltest, users where practicaltest.test_id = %s  and  users.user_type = %s and practicaltest.email=users.email', (testid,'student'))
				results = cur.fetchall()
				cur.close()
				names = []
				scores = []
				for user in results:
					names.append(user['name'])
					scores.append(user['marks'])
				return render_template('student_results_pqa.html', data=results, labels=names, values=scores)

@app.route('/<email>/disptests')
@user_role_professor
def disptests(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('select * from teachers where email = %s and uid = %s', (email,session['uid']))
		results = cur.fetchall()
		return render_template('disptests.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('professor_index'))

@app.route('/<email>/student_test_history')
@user_role_student
def student_test_history(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT a.test_id, b.subject, b.topic \
			from studenttestinfo a, teachers b where a.test_id = b.test_id and a.email=%s  \
			and a.completed=1', [email])
		results = cur.fetchall()
		return render_template('student_test_history.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('student_index'))

@app.route('/test_generate', methods=["GET", "POST"])
@user_role_professor
def test_generate():
	if request.method == "POST":
		inputText = request.form["itext"]
		testType = request.form["test_type"]
		noOfQues = request.form["noq"]
		if testType == "objective":
			objective_generator = ObjectiveTest(inputText,noOfQues)
			question_list, answer_list = objective_generator.generate_test()
			testgenerate = zip(question_list, answer_list)
			return render_template('generatedtestdata.html', cresults = testgenerate)
		elif testType == "subjective":
			subjective_generator = SubjectiveTest(inputText,noOfQues)
			question_list, answer_list = subjective_generator.generate_test()
			testgenerate = zip(question_list, answer_list)
			return render_template('generatedtestdata.html', cresults = testgenerate)
		else:
			return None

@app.route('/student_index')
@user_role_student
def student_index():
	return render_template('student_index.html')

@app.route('/professor_index')
@user_role_professor
def professor_index():
	return render_template('professor_index.html')




if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
