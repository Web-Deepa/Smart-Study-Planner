from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response,send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import shutil
from datetime import date, datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from collections import defaultdict
from sqlalchemy.orm import joinedload
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
import random

KTM = ZoneInfo("Asia/Kathmandu")

def ktm_now():
    # Return a NAIVE datetime that represents the current wall-clock time
    # in Kathmandu. Mixing timezone-aware datetimes with SQLite (which has
    # no real datetime type) causes functions like SQLite's date()/time()
    # to silently reinterpret the offset and shift the calculated date,
    # which previously broke the "already sent today" reminder check
    # around midnight. Keeping everything naive-but-local keeps every
    # comparison (log_date, notif_date, created_at) consistent.
    return datetime.now(KTM).replace(tzinfo=None)

WEEK_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def upcoming_days():   
    today_name = ktm_now().strftime('%A')
    idx = WEEK_ORDER.index(today_name)
    return WEEK_ORDER[idx:]

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smart_study.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'deepapaneru220@gmail.com'
app.config['MAIL_PASSWORD'] = 'jloz moag qzha tvrg'   
app.config['MAIL_DEFAULT_SENDER'] = ('Smart Study Planner', 'deepapaneru220@gmail.com')

mail = Mail(app)

db = SQLAlchemy(app)

class Role(db.Model):
    __tablename__ = 'role'
    role_id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    remarks = db.Column(db.Text, nullable=True)

class College(db.Model):
    __tablename__ = 'college'
    col_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    PAN = db.Column(db.String(50), unique=True, nullable=True)
    Reg_no = db.Column(db.String(50), unique=True, nullable=True)
    longitude = db.Column(db.String(50), nullable=True)
    latitude = db.Column(db.String(50), nullable=True)
    url = db.Column(db.String(256), nullable=True)
    contact_person = db.Column(db.String(100), nullable=True)
    contact = db.Column(db.String(20), nullable=True)

class User(db.Model):
    __tablename__ = 'user'
    uid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)

    program = db.Column(db.String(100), nullable=True)
    sem = db.Column(db.String(50), nullable=True)
    profile_pic = db.Column(db.String(255), nullable=True)

    reset_otp = db.Column(db.String(6), nullable=True)
    reset_otp_expiry = db.Column(db.DateTime, nullable=True)

    col_id = db.Column(db.Integer, db.ForeignKey('college.col_id'))
    college = db.relationship("College" ,backref='user')

    # Foreign Keys
    role_id = db.Column(db.Integer, db.ForeignKey('role.role_id'), nullable=True)

    # soft delete
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships for easier querying
    notes = db.relationship('Note', backref='author', lazy=True)
    role = db.relationship("Role", backref='users') 
    plans = db.relationship('Weekly_plan', backref='user', lazy=True)


class Subject(db.Model):
    __tablename__ = 'subject'
    sid = db.Column(db.Integer, primary_key=True)
    sname = db.Column(db.String(100), nullable=False)
    scode = db.Column(db.String(50), unique=True, nullable=False)
    credit_hr = db.Column(db.Integer, nullable=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)

    # soft delete
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    notes = db.relationship(
        'Note',
        back_populates='subject',
        lazy=True
    )

class Note(db.Model):
    nid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: ktm_now())
    updated_at = db.Column(
        db.DateTime,
        default=lambda: ktm_now(),
        onupdate=lambda: ktm_now()
    )

    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    sid = db.Column(db.Integer, db.ForeignKey('subject.sid'), nullable=False)

    # soft delete
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    subject = db.relationship(
        'Subject',
        back_populates='notes'
    )


class Weekly_plan(db.Model):
    wid = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.String(20), nullable=False)
    hr = db.Column(db.Integer, nullable=False)
    # NOTE: previously `time` was `unique=True` on its own, which meant
    # no two users in the entire system could ever have a plan at the
    # same clock time (e.g. two different students both studying at
    # 6:00 PM would collide). The real constraint we want is "this user
    # can't have two plans on the same day at the same time" — enforced
    # below via a composite UniqueConstraint instead.
    time = db.Column(db.Time, nullable=False)
    # Foreign Keys
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    sid = db.Column(db.Integer, db.ForeignKey('subject.sid'), nullable=False)

    # soft delete
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)

    subject = db.relationship('Subject', backref='weekly_plans')

    __table_args__ = (
        UniqueConstraint('uid', 'day_of_week', 'time', name='uq_user_day_time'),
    )


class StudyLog(db.Model):
    __tablename__ = 'study_log'
    lid          = db.Column(db.Integer, primary_key=True)
    hours_spent  = db.Column(db.Float, nullable=False)
    log_date     = db.Column(db.Date, nullable=False,
                             default=lambda: ktm_now().date())
    uid          = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=False)
    sid          = db.Column(db.Integer, db.ForeignKey('subject.sid'), nullable=False)
    subject_rel  = db.relationship('Subject', backref='logs', lazy=True)

    user = db.relationship('User', backref='study_logs', lazy=True)
    subject = db.relationship('Subject', backref='study_logs', lazy=True)


class Notification(db.Model):
    __tablename__ = "notification"

    nid = db.Column(db.Integer, primary_key=True)

    uid = db.Column(db.Integer, db.ForeignKey("user.uid"), nullable=False)

    title = db.Column(db.String(200), nullable=False)

    message = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=lambda: ktm_now()
    )

    is_read = db.Column(db.Boolean, default=False)

    # Structured dedupe columns — replaces parsing a "[Plan #wid]" tag
    # out of the free-text message, which was fragile (any wording
    # change to the message broke the dedupe check silently).
    plan_id = db.Column(db.Integer, db.ForeignKey('weekly_plan.wid'), nullable=True)
    notif_date = db.Column(db.Date, nullable=True)

    user = db.relationship("User", backref="notifications")
    plan = db.relationship("Weekly_plan", backref="notifications")


#routes

@app.route("/")
def home():
    return render_template("home.html")


def get_or_create_role(prefix, name, remarks=None):
    
    role = Role.query.filter(Role.code.like(f"{prefix}_%")).first()
    if role:
        return role

  
    role = Role(code=f"{prefix}_temp", name=name, remarks=remarks)
    db.session.add(role)
    db.session.flush()   

   
    role.code = f"{prefix}_{role.role_id}"
    db.session.flush()

    return role

#signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get('name')
        program= request.form.get('faculty')
        sem = request.form.get('semester')
        email = request.form.get('email')
        college = request.form.get("college")

        college_record = College.query.filter_by(name=college).first()

        password = request.form.get('password')
        confirm_password= request.form.get('confirm_password')

        existing_user = User.query.filter((User.email == email)).first()
        if existing_user:
            flash(" Email already exists. Please choose another.", "danger")
            return redirect(url_for("signup"))

        if password!=confirm_password:
         flash ("password and confirm password must be same",'danger')
         return redirect(url_for('signup'))

        if not college_record:
         college_record = College(
            name=college,
            code=secure_filename(college).upper()
        )
         db.session.add(college_record)
         db.session.flush()

        enc_pass = generate_password_hash(password)

        student_role = get_or_create_role("student", "Student", "Regular user")
       
        db.session.add(student_role)
        
        new_user = User(
            name=name,
            program=program,
            sem=sem,
            email=email,
            col_id=college_record.col_id ,
            role_id=student_role.role_id,
            password=enc_pass
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('signup.html')

#login
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
      email = request.form.get('email')
      password = request.form.get('password')

      user = User.query.filter_by(email=email, is_deleted=False).first()

      if user and check_password_hash(user.password, password):
            session['user_id'] = user.uid
            return redirect(url_for('dashboard'))
      else:
            flash("Invalid username or password.","danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash("No account found with that email.", "danger")
            return redirect(url_for('forgot_password'))

        otp = str(random.randint(100000, 999999))
        user.reset_otp = otp
        user.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=1)
        db.session.commit()

        msg = Message("Your Password Reset OTP", recipients=[email])
        msg.body = (
            f"Your OTP for resetting your Smart Study Planner password is: {otp}\n"
            f"This code expires in 1 minutes.\n\n"
            f"If you didn't request this, you can ignore this email."
        )
        mail.send(msg)

        session['reset_email'] = email
        flash("An OTP has been sent to your email.", "success")
        return redirect(url_for('verify_otp'))

    return render_template('forgot_password.html')


@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        user = User.query.filter_by(email=email).first()

        if not user or not user.reset_otp:
            flash("Something went wrong. Please try again.", "danger")
            return redirect(url_for('forgot_password'))

        if user.reset_otp_expiry < datetime.utcnow():
            flash("OTP has expired. Please request a new one.", "danger")
            return redirect(url_for('forgot_password'))

        if str(entered_otp) != str(user.reset_otp):
         flash("Incorrect OTP. Please try again.", "danger")
         return redirect(url_for('verify_otp'))
        
        session['otp_verified'] = True
        flash("OTP verified. Please set a new password.", "success")
        return redirect(url_for('reset_password'))

    return render_template('verify_otp.html', email=email)

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')
    if not email or not session.get('otp_verified'):
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for('reset_password'))

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('reset_password'))

        user = User.query.filter_by(email=email).first()
        user.password = generate_password_hash(password)
        user.reset_otp = None
        user.reset_otp_expiry = None
        db.session.commit()

        session.pop('reset_email', None)
        session.pop('otp_verified', None)

        flash("Password reset successful. Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/resend-otp')
def resend_otp():
    email = session.get('reset_email')
    if not email:
        return redirect(url_for('forgot_password'))

    user = User.query.filter_by(email=email).first()
    if not user:
        return redirect(url_for('forgot_password'))

    otp = str(random.randint(100000, 999999))
    user.reset_otp = otp
    user.reset_otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    msg = Message("Your Password Reset OTP", recipients=[email])
    msg.body = f"Your new OTP is: {otp}\nThis code expires in 10 minutes."
    mail.send(msg)

    flash("A new OTP has been sent to your email.", "success")
    return redirect(url_for('verify_otp'))

@app.route("/logout",methods=['POST','GET'])
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user    = db.session.get(User, session['user_id'])
    if not user or user.is_deleted:
        session.clear()
        return redirect(url_for('login'))

    uid     = user.uid
    today   = ktm_now().date()

    # Notes stats
    user_notes         = Note.query.filter_by(uid=uid, is_deleted=False).all()
    notes_count        = len(user_notes)
    unique_subjects    = len(set(n.sid for n in user_notes))
    seven_days_ago     = ktm_now() - timedelta(days=7)
    recent_notes_count = Note.query.filter(
        Note.uid == uid,
        Note.is_deleted == False,
        Note.created_at >= seven_days_ago
    ).count()
    recent_notes       = (Note.query.filter_by(uid=uid, is_deleted=False)
                          .order_by(Note.created_at.desc()).limit(3).all())

    # Weekly plan
    weekly_plans  = Weekly_plan.query.filter_by(uid=uid, is_deleted=False).all()
    weekly_hours  = sum(p.hr for p in weekly_plans) if weekly_plans else 0
    subjects      = Subject.query.filter_by(uid=uid, is_deleted=False).all()

    # Study log hours this week
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week   = start_of_week + timedelta(days=6)
    logs_this_week = StudyLog.query.filter(
        StudyLog.uid      == uid,
        StudyLog.log_date >= start_of_week,
        StudyLog.log_date <= end_of_week
    ).all()
    studied_this_week = sum(l.hours_spent for l in logs_this_week)

    streak = 0
    check_date = today
    while True:
        log = StudyLog.query.filter(
            StudyLog.uid == uid,
            StudyLog.log_date == check_date
        ).first()
        if log:
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return render_template(
        'dashboard.html',
        user               = user,
        notes_count        = notes_count,
        unique_subjects    = unique_subjects,
        recent_notes_count = recent_notes_count,
        recent_notes       = recent_notes,
        weekly_hours       = weekly_hours,
        studied_this_week  = round(studied_this_week, 1),
        weekly_plans       = weekly_plans,
        subjects           = subjects,
        current_streak     = streak,
    )

@app.route("/about")
def about():
   if 'user_id' not in session:
           return redirect(url_for('login'))
   return render_template('about.html')

@app.route("/notes", methods=["GET"])
def notes():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    search = request.args.get('search', '').strip()

    query = Note.query.filter(
        Note.uid == user_id,
        Note.is_deleted == False
    )

    if search:
        query = query.filter(
            (Note.title.ilike(f"%{search}%")) |
            (Note.file_path.ilike(f"%{search}%"))
        )

    all_notes = query.order_by(Note.nid.desc()).all()

    if not all_notes:
        if search:
            flash("No notes found.", "warning")
        else:
            flash("No notes added yet.", "info")

    grouped_notes = defaultdict(list)

    for note in all_notes:
        subject = Subject.query.filter_by(
            sid=note.sid,
            is_deleted=False
        ).first()

        subject_name = subject.sname if subject else "Uncategorized"
        grouped_notes[subject_name].append(note)

    return render_template(
        "notes.html",
        grouped_notes=grouped_notes,
        search=search
    )

@app.route("/add_notes", methods=["GET", "POST"])
def add_notes():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":

        subject = request.form.get("subject", "").strip()
        title = request.form.get("title", "").strip()
        note_content = request.form.get("note_content", "").strip()
        files = request.files.getlist("note-file")

        has_files = any(f.filename for f in files)
        has_text = bool(note_content)

        if not subject:
            flash("Subject is compulsory.", "danger")
            return redirect(url_for("add_notes"))

        if not has_files and not has_text:
            flash("Upload a file or write a text note.", "danger")
            return redirect(url_for("add_notes"))

        if has_text and not title:
            flash("Title is compulsory for text notes.", "danger")
            return redirect(url_for("add_notes"))

        user_id = session["user_id"]

        subject_record = Subject.query.filter_by(
            sname=subject,
            uid=user_id,
            is_deleted=False
        ).first()

        if not subject_record:
            code = secure_filename(subject).lower() + f"_{user_id}"

            if Subject.query.filter_by(scode=code).first():
                code += str(random.randint(100, 999))

            subject_record = Subject(
                sname=subject,
                scode=code,
                uid=user_id
            )

            db.session.add(subject_record)
            db.session.commit()

        folder = secure_filename(subject)
        folder_path = os.path.join(app.config["UPLOAD_FOLDER"], folder)
        os.makedirs(folder_path, exist_ok=True)

        # ---------- SAVE FILE NOTES ----------
        if has_files:
            for file in files:

                if not file or file.filename == "":
                    continue

                filename = secure_filename(file.filename)

                duplicate = Note.query.filter_by(
                    uid=user_id,
                    sid=subject_record.sid,
                    title=filename,
                    is_deleted=False
                ).first()

                if duplicate:
                    flash(f"{filename} already exists.", "danger")
                    return redirect(url_for("add_notes"))

                save_path = os.path.join(folder_path, filename)
                file.save(save_path)

                db.session.add(
                    Note(
                        title=filename,
                        file_path=save_path,
                        uid=user_id,
                        sid=subject_record.sid,
                        is_deleted=False
                    )
                )

        if has_text:

            txt_filename = secure_filename(title).lower() + ".txt"

            duplicate = Note.query.filter_by(
                uid=user_id,
                sid=subject_record.sid,
                title=txt_filename,
                is_deleted=False
            ).first()

            if duplicate:
                flash("Text note already exists.", "danger")
                return redirect(url_for("add_notes"))

            txt_path = os.path.join(folder_path, txt_filename)

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(note_content)

            db.session.add(
                Note(
                    title=txt_filename,
                    file_path=txt_path,
                    uid=user_id,
                    sid=subject_record.sid,
                    is_deleted=False
                )
            )

        db.session.commit()

        flash("Note added successfully.", "success")
        return redirect(url_for("notes"))

    return render_template("add_notes.html")

@app.route("/edit_note/<int:nid>", methods=['GET', 'POST'])
def edit_note(nid):

    if 'user_id' not in session:
        return redirect(url_for('login'))

    note = Note.query.get_or_404(nid)

    if note.uid != session['user_id'] or note.is_deleted:
        flash("Permission denied.", "danger")
        return redirect(url_for('notes'))


    if not note.title.lower().endswith('.txt'):
        flash("Only generated text notes can be edited dynamically.", "danger")
        return redirect(url_for('notes'))

    if request.method == 'POST':

        updated_content = request.form.get('updated_content', '')

        try:

            with open(note.file_path, "w", encoding="utf-8") as txt_file:
                txt_file.write(updated_content)

            flash("Note updated successfully.", "success")
            return redirect(url_for('notes'))
        except Exception as e:
            flash(f"Failed to update file: {str(e)}", "danger")
            return redirect(url_for('notes'))

    current_text = ""
    if os.path.exists(note.file_path):
        with open(note.file_path, "r", encoding="utf-8") as txt_file:
            current_text = txt_file.read()
    else:
        flash("The underlying physical file could not be located.", "danger")
        return redirect(url_for('notes'))

    return render_template('edit_note.html', note=note, current_text=current_text)

@app.route("/search_subjects")
def search_subjects():
   query=request.args.get('q','')
   if len(query)<1:
      return jsonify([])

   matching_subjects=Subject.query.filter(Subject.sname.like(f"%{query}%"), Subject.is_deleted==False).all()
   results = [s.sname for s in matching_subjects]
   return jsonify(results)

#download note
@app.route("/download_note/<int:nid>")
def download_note(nid):

    if "user_id" not in session:
     
        return redirect(url_for("login"))

    # Get the note
    note = Note.query.get_or_404(nid)

    # Check ownership
    if note.uid != session["user_id"]:
        flash("You are not authorized to download this file.", "danger")
        return redirect(url_for("notes"))
    
    if not note.file_path:
        flash("No file is associated with this note.", "danger")
        return redirect(url_for("notes"))

    # Absolute path of the file
    file_path = os.path.abspath(note.file_path)

    # Check if file exists
    if not os.path.isfile(file_path):
        flash("File not found on the server.", "danger")
        return redirect(url_for("notes"))

    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    # Download the exact file
    return send_from_directory(
        directory=directory,
        path=filename,
        as_attachment=True,
        download_name=filename
    )

@app.route("/delete_notes/<int:nid>")
def delete_notes(nid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    note=Note.query.get_or_404(nid)

    if note.uid != session['user_id']:
        flash("Permission denied.", "danger")
        return redirect(url_for('notes'))

    note.is_deleted = True
    note.deleted_at = ktm_now()
    db.session.commit()

    flash("Note deleted successfully.", "success")
    return redirect(url_for('notes'))

@app.route("/delete_subject/<int:sid>", methods=['POST', 'GET'])
def delete_subject(sid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    subject = Subject.query.get_or_404(sid)

    if subject.uid != session['user_id']:
        flash("Permission denied.", "danger")
        return redirect(url_for('notes'))
   
    now = ktm_now()
    subject.is_deleted = True
    subject.deleted_at = now

    Note.query.filter_by(sid=subject.sid, is_deleted=False).update(
        {Note.is_deleted: True, Note.deleted_at: now}
    )
    Weekly_plan.query.filter_by(sid=subject.sid, is_deleted=False).update(
        {Weekly_plan.is_deleted: True, Weekly_plan.deleted_at: now}
    )

    db.session.commit()

    flash(f"Folder '{subject.sname}' successfully deleted.", "success")
    return redirect(url_for('notes'))



@app.route("/view_note/<int:nid>")
def view_note_file(nid):
   
    if 'user_id' not in session:
        flash("Please log in to view notes.", "danger")
        return redirect(url_for('login'))

    # 2. Fetch the Note record safely
    note = Note.query.get_or_404(nid)

    
    directory = os.path.dirname(note.file_path)
    filename = os.path.basename(note.file_path)

    return send_from_directory(directory, filename, as_attachment=False)


#weekplan
@app.route("/week_plan", methods=["GET", "POST"])
def week_plan():

    if 'user_id' not in session:
        return redirect(url_for('login'))


    user_id = session['user_id']

    subjects = Subject.query.filter_by(uid=user_id, is_deleted=False).all()

    search_query = request.args.get('search', '').strip()

    if  search_query:
       plans = Weekly_plan.query.filter_by(uid=user_id, is_deleted=False).filter(
            Weekly_plan.day_of_week.ilike(f"%{search_query}%")
        ).all()

       if not plans:
         flash("no plan added add first them")

    else:
        plans = Weekly_plan.query.filter_by(uid=user_id, is_deleted=False).all()
        if not plans:
            flash("No plans added yet. Add your first plan!")

    return render_template(
            "week_plan.html",
            subjects=subjects,
            plans=plans
        )

@app.route("/add_plan", methods=["GET", "POST"])
def add_plan():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    subjects = Subject.query.filter_by(uid=user_id, is_deleted=False).all()

    if request.method == "POST":
        subject_id = request.form.get("subject")
        day = request.form.get("day")
        hours = request.form.get("hours")
        time = request.form['time']

        if not subject_id or not day or not hours or not time:
            flash("Please fill all fields.", "danger")
            return render_template('add_plan.html', subjects=subjects)


        
        plan_time = datetime.strptime(time, "%H:%M").time()

        existing_plan = Weekly_plan.query.filter(
            Weekly_plan.uid == user_id,
            Weekly_plan.is_deleted == False,
            Weekly_plan.day_of_week.ilike(day.strip()),
            Weekly_plan.time == plan_time
        ).first()

        if existing_plan:
            flash("You already have a plan scheduled for this day and time!", "danger")
            return render_template('add_plan.html', subjects=subjects)

        new_plan = Weekly_plan(
            day_of_week=day,
            hr=hours,
            time=plan_time,
            uid=user_id,
            sid=int(subject_id)
        )
        db.session.add(new_plan)
        db.session.commit()
        flash("Weekly plan added successfully!", "success")
        return redirect(url_for("week_plan"))

    return render_template('add_plan.html', subjects=subjects)

@app.route("/edit_plan/<int:wid>",methods=['GET','POST'])
def edit_plan(wid):
     if 'user_id' not in session:
                return redirect(url_for('login'))

     user_id = session['user_id']

     plan=Weekly_plan.query.get_or_404(wid)
     if plan.uid != user_id:
        flash("Permission denied.", "danger")
        return redirect(url_for('week_plan'))

     if request.method == "POST":
         plan.sid=int(request.form['subject'])
         plan.day_of_week=request.form['day']

         if  plan.day_of_week not in upcoming_days():
             flash(f"{ plan.day_of_week} has already gone for this week.", "danger")
             subjects = Subject.query.filter_by(uid=user_id, is_deleted=False).all()
             return render_template('edit_plan.html', plan=plan, subjects=subjects)
         
         plan.hr=int(request.form['hours'])
         time_input=request.form['time']
         plan.time = datetime.strptime(time_input, "%H:%M").time()
         db.session.commit()
         return redirect(url_for('week_plan'))

     subjects = Subject.query.filter_by(uid=user_id, is_deleted=False).all()
     return render_template('edit_plan.html', plan=plan, subjects=subjects)


@app.route("/delete_plan/<int:wid>")
def delete_plan(wid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    plan = Weekly_plan.query.get_or_404(wid)

    if plan.uid != session['user_id']:
        flash("Permission denied.", "danger")
        return redirect(url_for('week_plan'))

    # soft delete
    plan.is_deleted = True
    plan.deleted_at = ktm_now()
    db.session.commit()

    flash("plan  successfully deleted.", "success")
    return redirect(url_for('week_plan'))

#studylog
@app.route("/log_study", methods=["GET", "POST"])
def log_study():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    uid = session['user_id']

    # Only subjects that have an active weekly plan
    planned_sids = {
        p.sid for p in Weekly_plan.query.filter_by(
            uid=uid,
            is_deleted=False
        ).all()
    }

    subjects = Subject.query.filter(
        Subject.uid == uid,
        Subject.is_deleted == False,
        Subject.sid.in_(planned_sids)
    ).all()

    if request.method == "POST":

        sid = request.form.get("subject_id")
        hours = request.form.get("hours_spent")
        log_date = request.form.get("log_date")

        if not sid or not hours:
            flash("Subject and hours are required.", "danger")
            return redirect(url_for("log_study"))

        sid = int(sid)
        new_hours = float(hours)

        # Rule 1: Subject must have a weekly plan
        subject_plans = Weekly_plan.query.filter_by(
            uid=uid,
            sid=sid,
            is_deleted=False
        ).all()

        if not subject_plans:
            flash("You must set a weekly plan for this subject before logging a session.", "danger")
            return redirect(url_for("log_study"))

        # Parse date
        parsed_date = (
            datetime.strptime(log_date, "%Y-%m-%d").date()
            if log_date else ktm_now().date()
        )

        today = ktm_now().date()

        # Rule 2: No future dates
        if parsed_date > today:
            flash("You can't log a study session for a future date.", "danger")
            return redirect(url_for("log_study"))

        # Rule 3: Date must be a planned day
        session_day_name = parsed_date.strftime("%A")

        planned_days = {p.day_of_week for p in subject_plans}

        if session_day_name not in planned_days:
            flash(
                f"No plan is scheduled for {session_day_name} for this subject.",
                "danger"
            )
            return redirect(url_for("log_study"))

        # Get the plan for this day
        plan = Weekly_plan.query.filter_by(
            uid=uid,
            sid=sid,
            day_of_week=session_day_name,
            is_deleted=False
        ).first()

        if not plan:
            flash("Weekly plan not found.", "danger")
            return redirect(url_for("log_study"))

        planned_hours = float(plan.hr)

        # Hours already logged on this date
        logged_hours = db.session.query(
            db.func.coalesce(db.func.sum(StudyLog.hours_spent), 0)
        ).filter(
            StudyLog.uid == uid,
            StudyLog.sid == sid,
            StudyLog.log_date == parsed_date
        ).scalar()

        # Rule 4: Cannot exceed planned hours
        if logged_hours + new_hours > planned_hours:
            remaining = max(planned_hours - logged_hours, 0)

            flash(
                f"You can only log {remaining:.1f} more hour(s) for {session_day_name}. "
                f"Planned hours: {planned_hours}.",
                "danger"
            )
            return redirect(url_for("log_study"))

        # Save study log
        new_log = StudyLog(
            hours_spent=new_hours,
            log_date=parsed_date,
            uid=uid,
            sid=sid
        )

        db.session.add(new_log)
        db.session.commit()

        flash(f"Logged {new_hours} hour(s) of study successfully!", "success")
        return redirect(url_for("progress"))

    today = ktm_now().date().strftime("%Y-%m-%d")
    return render_template(
        "log_study.html",
        subjects=subjects,
        today=today
    )

#progress
@app.route("/progress", methods=['GET'])
def progress():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    uid           = session['user_id']
    today         = ktm_now().date()
    start_of_week = today - timedelta(days=today.weekday())   # Monday
    end_of_week   = start_of_week + timedelta(days=6)          # Sunday

    subjects   = Subject.query.filter_by(uid=uid, is_deleted=False).all()
    plans      = Weekly_plan.query.filter_by(uid=uid, is_deleted=False).all()
    subject_map = {s.sid: s.sname for s in subjects}

    # Planned hours per subject from weekly plan
    planned_per_subject = {}
    for plan in plans:
        sname = subject_map.get(plan.sid, f"Subject #{plan.sid}")
        planned_per_subject[sname] = planned_per_subject.get(sname, 0) + int(plan.hr or 0)

    # Actual hours studied this week from StudyLog
    logs = StudyLog.query.filter(
        StudyLog.uid      == uid,
        StudyLog.log_date >= start_of_week,
        StudyLog.log_date <= end_of_week
    ).all()

    studied_per_subject = {}
    for log in logs:
        sname = subject_map.get(log.sid, f"Subject #{log.sid}")
        studied_per_subject[sname] = studied_per_subject.get(sname, 0) + log.hours_spent

    # Merge into subject_data
    all_subjects = set(list(planned_per_subject.keys()) + list(studied_per_subject.keys()))
    colors = ["#534AB7", "#1D9E75", "#EF27D1", "#378ADD", "#E24B4A", "#6D28D9", "#0891B2","#08B290","#3508B2","#B20865"]
    subject_data = {}
    for i, sname in enumerate(sorted(all_subjects)):
        planned = planned_per_subject.get(sname, 0)
        studied = studied_per_subject.get(sname, 0)
        pct     = min(round((studied / planned * 100) if planned > 0 else 0), 100)
        subject_data[sname] = {
            "planned_hours": planned,
            "studied_hours": round(studied, 1),
            "pct":           pct,
            "color":         colors[i % len(colors)],
        }

    # Totals
    total_planned = sum(d["planned_hours"] for d in subject_data.values())
    total_studied = round(sum(d["studied_hours"] for d in subject_data.values()), 1)
    global_pct    = min(round((total_studied / total_planned * 100) if total_planned > 0 else 0), 100)

    # For Chart.js
    chart_labels  = list(subject_data.keys())
    chart_planned = [subject_data[s]["planned_hours"] for s in chart_labels]
    chart_studied = [subject_data[s]["studied_hours"] for s in chart_labels]
    chart_colors  = [subject_data[s]["color"] for s in chart_labels]

    # Recent study logs for this week
    recent_logs = (StudyLog.query
                   .filter(StudyLog.uid == uid,
                           StudyLog.log_date >= start_of_week,
                           StudyLog.log_date <= end_of_week)
                   .order_by(StudyLog.log_date.desc()).all())

    return render_template(
        'progress.html',
        subject_data   = subject_data,
        total_planned  = total_planned,
        total_studied  = total_studied,
        global_pct     = global_pct,
        start_date     = start_of_week.strftime('%b %d'),
        end_date       = end_of_week.strftime('%b %d'),
        chart_labels   = chart_labels,
        chart_planned  = chart_planned,
        chart_studied  = chart_studied,
        chart_colors   = chart_colors,
        recent_logs    = recent_logs,
        subject_map    = subject_map,
    )

#profile
@app.context_processor
def inject_navbar_user():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:

            name_str = (user.name or '').strip()
            parts = name_str.split()
            if len(parts) >= 2:
                initials = parts[0][0].upper() + parts[-1][0].upper()
            elif len(parts) == 1:
                initials = parts[0][0].upper()
            else:
                initials = 'U'
            return dict(current_navbar_user=user, navbar_initials=initials)
    return dict(current_navbar_user=None, navbar_initials='')



@app.context_processor
def inject_sidebar_user():
    
    admin = None
    initials = 'A'

    if 'admin_uid' in session:
        admin = db.session.get(User, session['admin_uid'])
        if admin:
            name_str = (admin.name or '').strip()
            parts = name_str.split()
            if len(parts) >= 2:
                initials = (parts[0][0] + parts[-1][0]).upper()
            elif len(parts) == 1:
                initials = parts[0][0].upper()

    return dict(admin=admin, initials=initials)
 
@app.context_processor
def notification_count():

    if "user_id" not in session:
        return dict(unread_count=0)

    count = Notification.query.filter_by(
        uid=session["user_id"],
        is_read=False
    ).count()

    return dict(unread_count=count)

@app.route("/profile", methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        user = db.session.get(User, session['user_id'])
        if not user:
            return redirect(url_for('login'))

       
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        program = request.form.get('program', '').strip()
        sem     = request.form.get('sem', '').strip()

        if name:
            user.name = name
        if email:
            if email != user.email and User.query.filter_by(email=email).first():
                flash("That email is already in use by another account.", "danger")
                return redirect(url_for('profile'))
            user.email = email
        if program:
            user.program = program
        if sem:
            user.sem = sem

        college_name = request.form.get('college', '').strip()
        if college_name:
            college_record = College.query.filter_by(name=college_name).first()
            if not college_record:
                college_record = College(
                    name=college_name,
                    code=secure_filename(college_name).upper()
                )
                db.session.add(college_record)
                db.session.flush()
            user.col_id = college_record.col_id

        file = request.files.get('profile_picture')
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1].lower()
           
            clean_name = secure_filename(user.name.replace(' ', '_'))
            filename   = f"user_{user.uid}_{clean_name}{ext}"
            save_path = os.path.join('static', 'uploads', filename)
            os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
            file.save(save_path)
            user.profile_pic = filename

        new_password = request.form.get('new_password', '').strip()
        if new_password:
            user.password = generate_password_hash(new_password)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not update profile — that email may already be taken.", "danger")
            return redirect(url_for('profile'))

        session['name'] = user.name
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    user = db.session.get(User, session['user_id'])
    if not user or user.is_deleted:
        session.clear()
        return redirect(url_for('login'))

    name_str = (user.name or '').strip()
    parts    = name_str.split()
    if len(parts) >= 2:
        initials = parts[0][0].upper() + parts[-1][0].upper()
    elif len(parts) == 1:
        initials = parts[0][0].upper()
    else:
        initials = 'U'

    return render_template('profile.html', user=user, initials=initials)


@app.route('/profile/photo/<int:user_id>')
def view_profile_pic(user_id):
 if 'user_id' not in session:
    return redirect(url_for('login'))
 user = User.query.get_or_404(user_id)
 return render_template('view_photo.html', user=user)

#admin
@app.route("/admin")
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        admin = User.query.filter_by(email=email, is_deleted=False).first()

        is_admin = (
            admin is not None
            and admin.role_id is not None
            and Role.query.get(admin.role_id)
            and Role.query.get(admin.role_id).code == "admin"
        )
        if admin and check_password_hash(admin.password, password) and is_admin:
            session["admin"] = admin.email
            session["admin_uid"] = admin.uid
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials", "danger")

    return render_template('admin_login.html')

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    users = User.query.filter_by(is_deleted=False).all()

    user_count = User.query.filter_by(is_deleted=False).count()
    subject_count = Subject.query.filter_by(is_deleted=False).count()
    note_count = Note.query.filter_by(is_deleted=False).count()
    plan_count = Weekly_plan.query.filter_by(is_deleted=False).count()
    task_count = StudyLog.query.count()

    trash_count = (
        User.query.filter_by(is_deleted=True).count()
        + Subject.query.filter_by(is_deleted=True).count()
        + Note.query.filter_by(is_deleted=True).count()
        + Weekly_plan.query.filter_by(is_deleted=True).count()
    )

    return render_template(
        "admin_dashboard.html",
        users=users,
        user_count=user_count,
        subject_count=subject_count,
        task_count=task_count,
        note_count=note_count,
        plan_count=plan_count,
        trash_count=trash_count,
    )

@app.route("/admin/profile", methods=['GET', 'POST'])
def admin_profile():

    if 'admin' not in session or 'admin_uid' not in session:
        return redirect(url_for('admin_login'))

    if request.method == "POST":
        admin = db.session.get(User, session['admin_uid'])
        if not admin:
            session.clear()
            return redirect(url_for('admin_login'))

        name  = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()

        if name:
            admin.name = name
        if email:
            if email != admin.email and User.query.filter_by(email=email).first():
                flash("That email is already in use by another account.", "danger")
                return redirect(url_for('admin_profile'))
            admin.email = email
            session["admin"] = email  

        file = request.files.get('profile_picture')
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1].lower()
   
            clean_name = secure_filename(admin.name.replace(' ', '_'))
            filename   = f"admin_{admin.uid}_{clean_name}{ext}"
            save_path  = os.path.join('static', 'uploads', filename)
            os.makedirs(os.path.join('static', 'uploads'), exist_ok=True)
            file.save(save_path)
            admin.profile_pic = filename

        new_password = request.form.get('new_password', '').strip()
        if new_password:
            admin.password = generate_password_hash(new_password)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Could not update profile — that email may already be taken.", "danger")
            return redirect(url_for('admin_profile'))

        flash("Admin profile updated successfully!", "success")
        return redirect(url_for('admin_profile'))


    admin = db.session.get(User, session['admin_uid'])
    if not admin or admin.is_deleted:
        session.clear()
        return redirect(url_for('admin_login'))

    name_str = (admin.name or '').strip()
    parts    = name_str.split()
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1:
        initials = parts[0][0].upper()
    else:
        initials = 'A'

    return render_template('admin_profile.html', admin=admin, initials=initials)

@app.route("/admin/users")
def admin_users():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    users = User.query.filter_by( is_deleted=False).all()

    return render_template(
        "admin_user.html",
        users=users
    )

@app.route("/admin/users/delete/<int:uid>")
def admin_delete_user(uid):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    user = User.query.get_or_404(uid)

    if user.uid == session.get("admin_uid"):
        flash("You can't delete your own admin account.", "danger")
        return redirect(url_for("admin_users"))

    user.is_deleted = True
    user.deleted_at = ktm_now()
    db.session.commit()

    return redirect(url_for("admin_users"))


@app.route("/admin/subjects")
def admin_subjects():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    subjects = Subject.query.filter_by(is_deleted=False).all()
    return render_template("admin_subjects.html", subjects=subjects)

@app.route("/admin/notes")
def admin_notes():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    notes = Note.query.filter_by(is_deleted=False).all()
    return render_template("admin_notes.html", notes=notes)

@app.route("/admin/plans")
def admin_plans():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    plans = Weekly_plan.query.filter_by(is_deleted=False).all()
    return render_template("admin_plans.html", plans=plans)

@app.route("/admin/progress")
def admin_progress():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    progress = StudyLog.query.all()

    return render_template(
        "admin_progress.html",
        progress=progress
    )

@app.route("/admin/deadlines")
def admin_deadlines():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    today_date = date.today()
    current_day_name = today_date.strftime('%A')

    active_plans = Weekly_plan.query.options(
        joinedload(Weekly_plan.user),
        joinedload(Weekly_plan.subject)
    ).filter(
        Weekly_plan.day_of_week == current_day_name,
        Weekly_plan.is_deleted == False
    ).all()

    today_logs = StudyLog.query.filter(
        StudyLog.log_date == today_date
    ).all()

    log_lookup = {}
    for log in today_logs:
        key = (log.uid, log.sid)
        log_lookup[key] = log.hours_spent

    return render_template(
        "deadline.html",
        active_plans=active_plans,
        log_lookup=log_lookup,
        today_date=today_date
    )

@app.route("/admin/trash")
def admin_trash():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    deleted_users    = User.query.filter_by(is_deleted=True).all()
    deleted_subjects = Subject.query.filter_by(is_deleted=True).all()
    deleted_notes    = Note.query.filter_by(is_deleted=True).all()
    deleted_plans    = Weekly_plan.query.filter_by(is_deleted=True).all()

    return render_template(
        "admin_trash.html",
        deleted_users=deleted_users,
        deleted_subjects=deleted_subjects,
        deleted_notes=deleted_notes,
        deleted_plans=deleted_plans,
    )


@app.route("/admin/restore/<string:kind>/<int:item_id>")
def admin_restore(kind, item_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    model_map = {
        "user": (User, "uid"),
        "subject": (Subject, "sid"),
        "note": (Note, "nid"),
        "plan": (Weekly_plan, "wid"),
    }

    if kind not in model_map:
        flash("Unknown item type.", "danger")
        return redirect(url_for("admin_trash"))

    model, _ = model_map[kind]
    item = model.query.get_or_404(item_id)
    item.is_deleted = False
    item.deleted_at = None
    db.session.commit()

    flash(f"{kind.capitalize()} restored.", "success")
    return redirect(url_for("admin_trash"))


@app.route("/admin/permanent_delete/<string:kind>/<int:item_id>")
def admin_permanent_delete(kind, item_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    model_map = {
        "user": (User, "uid"),
        "subject": (Subject, "sid"),
        "note": (Note, "nid"),
        "plan": (Weekly_plan, "wid"),
    }

    if kind not in model_map:
        flash("Unknown item type.", "danger")
        return redirect(url_for("admin_trash"))

    model, _ = model_map[kind]
    item = model.query.get_or_404(item_id)

    if not item.is_deleted:
        flash("Only trashed items can be permanently deleted.", "danger")
        return redirect(url_for("admin_trash"))

    if kind == "note" and item.file_path and os.path.exists(item.file_path):
        try:
            os.remove(item.file_path)
        except OSError:
            pass

    if kind == "subject":
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(item.sname))
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)

    db.session.delete(item)
    db.session.commit()

    flash(f"{kind.capitalize()} permanently deleted.", "success")
    return redirect(url_for("admin_trash"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    session.pop("admin_uid", None)
    return redirect(url_for("admin_login"))


def create_notification(user, subject, plan, notif_date):

    notification = Notification(
        uid=user.uid,
        title="Study Reminder",
        message=f"It's time to study {subject.sname}. "
                f"Duration: {plan.hr} hour(s).",
        plan_id=plan.wid,
        notif_date=notif_date,
    )
    db.session.add(notification)

    db.session.commit()


def check_study_time():
  
    with app.app_context():

        now = ktm_now()
        today_date = now.date()
        day = now.strftime("%A")
        current_time_obj = now.time()

        plans = Weekly_plan.query.filter_by(
            day_of_week=day,
            is_deleted=False
        ).all()

        for plan in plans:
            if current_time_obj < plan.time:
                continue  # not due yet today

            already_sent = Notification.query.filter_by(
                uid=plan.uid,
                plan_id=plan.wid,
                notif_date=today_date
            ).first()

            if already_sent:
                continue

            create_notification(
                plan.user,
                plan.subject,
                plan,
                today_date
            )


@app.route("/notification/read/<int:id>")
def read_notification(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    notification = Notification.query.get_or_404(id)

    if notification.uid != session["user_id"]:
        flash("Permission denied.", "danger")
        return redirect(url_for("notifications"))

    notification.is_read = True
    db.session.commit()

    return redirect(url_for("notifications"))

@app.route("/notifications")
def notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])

    notifications = Notification.query.filter_by(
        uid=user.uid
    ).order_by(
        Notification.created_at.desc()
    ).all()

    unread_notifications = [n for n in notifications if not n.is_read]
    if unread_notifications:
        for n in unread_notifications:
            n.is_read = True
        db.session.commit() 

    return render_template(
        "notifications.html",
        notifications=notifications
    )



if __name__ =="__main__":
    with app.app_context():

        db.create_all()
        admin_role = Role.query.filter_by(code="admin").first()

        if not admin_role:
            admin_role = Role(code="admin", name="Admin", remarks="System Admin Access")
            db.session.add(admin_role)
            db.session.commit()

        admin_email = "deepapaneru220@gmail.com"
        admin_password = "admin"

        hashed_password = generate_password_hash(admin_password)

        admin = User.query.filter_by(email=admin_email).first()

        if admin:
            admin.password = hashed_password
            admin.role_id = admin_role.role_id
            print(f"Updated existing user {admin_email} with correct password hash and admin role.")
        else:
            admin = User(
                name=" Admin",
                email=admin_email,
                password=hashed_password,
                role_id=admin_role.role_id
            )
            db.session.add(admin)
        db.session.commit()
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN")=="true":
     scheduler = BackgroundScheduler(timezone=KTM)
     scheduler.add_job(check_study_time, 'interval', minutes=1, id='check_study_time')
    
     scheduler.start()
    app.run(debug=True)