from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from sqlalchemy import and_



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dental.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dental'
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(255))
    emergency_contact_name = db.Column(db.String(150))
    emergency_contact_phone = db.Column(db.String(50))
    medical_history = db.Column(db.Text)
    appointments = db.relationship('Appointment', backref='patient')
    records = db.relationship('DentalRecord', backref='patient')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class Dentist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150))
    last_name = db.Column(db.String(150))
    specialization = db.Column(db.String(150))
    email = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    appointments = db.relationship('Appointment', backref='dentist')
    availabilities = db.relationship('DentistAvailability', backref='dentist')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class DentalService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_name = db.Column(db.String(150))
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)
    appointments = db.relationship('Appointment', backref='service')
    records = db.relationship('DentalRecord', backref='service')


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    dentist_id = db.Column(db.Integer, db.ForeignKey('dentist.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('dental_service.id'))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50))
    notes = db.Column(db.Text)
    creation_date = db.Column(db.DateTime)


class DentistAvailability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dentist_id = db.Column(db.Integer, db.ForeignKey('dentist.id'))
    day_of_week = db.Column(db.String(50))
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    date = db.Column(db.Date)


class DentalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    visit_date = db.Column(db.Date)
    service_id = db.Column(db.Integer, db.ForeignKey('dental_service.id'))
    notes = db.Column(db.Text)
    x_rays = db.Column(db.String(255))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    role = db.Column(db.String(50))
    patients = db.relationship('Patient', backref='user')
    dentists = db.relationship('Dentist', backref='user')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def check_availability(dentist_id, selected_date, selected_time, duration_of_appointment=60):
    appointment_start_time = datetime.combine(selected_date, datetime.strptime(selected_time, '%H:%M').time())
    appointment_end_time = appointment_start_time + timedelta(minutes=duration_of_appointment)

    overlapping_appointment = Appointment.query.filter(
        and_(
            Appointment.dentist_id == dentist_id,
            Appointment.start_time < appointment_end_time,
            Appointment.end_time > appointment_start_time,
            Appointment.start_time >= datetime.now(),
            Appointment.start_time <= datetime.now() + timedelta(days=7)
        )
    ).first()

    return overlapping_appointment is None

def edit_user(user_id):
    if request.method == 'POST':
        user = User.query.get(user_id)

        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('edit_user', user_id=user_id))
        user.username = request.form['username']
        user.email = request.form['email']
        if 'password' in request.form:
            user.password = generate_password_hash(request.form['password'])
        db.session.commit()

        flash('User information updated successfully.', 'success')
        return redirect(url_for('edit_user', user_id=user_id))
    user = User.query.get(user_id)

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('index'))

    return render_template('edit_user.html', user=user)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        user = User(
            username=username,
            password=hashed_password,
            email=email,
            role=role)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/register_dentist', methods=['GET', 'POST'])
def register_dentist():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        specialization = request.form['specialization']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        hashed_password = generate_password_hash(password)
        user = User(
            username=email,
            password=hashed_password,
            email=email,
            role='Dentist'
        )

        try:
            db.session.add(user)
            db.session.commit()

            dentist = Dentist(
                first_name=first_name,
                last_name=last_name,
                specialization=specialization,
                email=email,
                phone=phone,
                user_id=user.id  
            )

            db.session.add(dentist)
            db.session.commit()

            flash('Dentist registered successfully.', 'success')

            return redirect(url_for('dentist_dashboard'))

        except IntegrityError:
            db.session.rollback()
            flash('Email address is already in use. Please choose a different one.', 'danger')
            return redirect(url_for('register_dentist'))

    return render_template('register_dentist.html')


@app.route('/schedule_appointment', methods=['GET', 'POST'])
@login_required
def schedule_appointment():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    appointment_id = session.get('appointment_id')
    appointment = Appointment.get(appointment_id)

    if request.method == 'POST':
        date_of_birth_str = request.form['date_of_birth']
        if date_of_birth_str:
            date_of_birth = datetime.strptime(date_of_birth_str, '%Y-%m-%d').date()
        else:
            flash('Invalid date of birth.', 'danger')
            return redirect(url_for('schedule_appointment'))

        patient = Patient(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            date_of_birth=date_of_birth,
            gender=request.form['gender'],
            email=request.form['email'],
            phone=request.form['phone'],
            address=request.form['address'],
            emergency_contact_name=request.form['emergency_contact_name'],
            emergency_contact_phone=request.form['emergency_contact_phone'],
            medical_history=request.form['medical_history'],
            user_id=user.id
        )

        duration_of_appointment = 60
        db.session.add(patient)
        db.session.commit()

        dentist_id = request.form['dentist_id']
        selected_dentist = Dentist.query.get(dentist_id)

        selected_date_str = request.form['selected_date']
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()

        selected_time = request.form['selected_time']
        is_available = check_availability(dentist_id, selected_date, selected_time)
        print("Is available:", is_available)

        if not is_available:
            flash('The selected time slot is not available. Please choose a different time.', 'danger')
            return redirect(url_for('schedule_appointment'))
        appointment_start_time = datetime.combine(selected_date, datetime.strptime(selected_time, '%H:%M').time())
        appointment_end_time = appointment_start_time + timedelta(minutes=duration_of_appointment)

        

        appointment = Appointment(
            patient_id=patient.id,
            dentist_id=dentist_id,
            service_id=request.form['service_id'],
            start_time=appointment_start_time,
            end_time=appointment_end_time,
            status='Scheduled',
            notes='', 
            creation_date=datetime.now()
        )

        if appointment == (appointment)

        db.session.add(appointment)
        db.session.commit()

        flash('Appointment scheduled successfully.', 'success')
        return redirect(url_for('patient_dashboard'))

    dentists = Dentist.query.all()
    services = DentalService.query.all()

    return render_template('schedule_appointment.html', dentists=dentists, services=services)


@app.route('/create_service', methods=['GET', 'POST'])
@login_required
def create_service():
    if request.method == 'POST':
        service_name = request.form['service_name']
        description = request.form['description']
        duration = int(request.form['duration'])

        service = DentalService(
            service_name=service_name,
            description=description,
            duration=duration
        )

        db.session.add(service)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('create_service.html')


@app.route('/view_appointments')
@login_required
def view_appointments():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user.role == 'Dentist':
        dentist = Dentist.query.filter_by(user_id=user.id).first()
        appointments = Appointment.query.filter_by(dentist_id=dentist.id).all()
        return render_template('view_appointments.html', appointments=appointments)
    else:
        flash('Access denied. You are not a dentist.', 'danger')
        return redirect(url_for('login'))


@app.route('/cancel_appointment/<int:appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if appointment:
        appointment.status = 'Cancelled'
        db.session.commit()
    return redirect(url_for('view_appointments'))


@app.route('/patient_dashboard')
def patient_dashboard():
    user = User.query.filter_by(id=session['user_id']).first()
    return render_template('patient_dashboard.html', user=user)


@app.route('/dentist_dashboard')
def dentist_dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user and user.role == 'Dentist':
        dentist = Dentist.query.filter_by(user_id=user.id).first()

        if dentist:
            pending_appointments = Appointment.query.filter_by(dentist_id=dentist.id, status='Scheduled').all()

            return render_template('dentist_dashboard.html', user=dentist, pending_appointments=pending_appointments)
        else:
            flash('No associated dentist record found.', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Access denied. You are not a dentist or user not found.', 'danger')
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'Patient':
            return redirect(url_for('patient_dashboard'))
        elif user.role == 'Dentist':
            return redirect(url_for('dentist_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role

            if user.role == 'Patient':
                return redirect(url_for('patient_dashboard'))
            elif user.role == 'Dentist':
                return redirect(url_for('dentist_dashboard'))

        flash('Login failed. Please check your credentials.', 'danger')

    return render_template('login.html')
    
@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user_route(user_id):
    return edit_user(user_id)



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
    with app.app_context():
        db.create_all()
