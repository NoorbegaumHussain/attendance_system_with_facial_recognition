import datetime
import cv2
import face_recognition
import numpy as np
import sqlite3
import hashlib
from flask import Flask, redirect,render_template,request,session

conn = sqlite3.connect("attendancesystem.db")

conn.execute("CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY AUTOINCREMENT,username varchar(100),password varchar(100))")
if len(conn.execute(f"SELECT * FROM admins").fetchall())==0:
    conn.execute("INSERT INTO admins(username,password) VALUES('admin','acfcd1ad7f716fa5a3468740b4e6c89283788029a9d6a3aebf145cf1d63e55e2')")
conn.execute("CREATE TABLE IF NOT EXISTS departments(id INTEGER PRIMARY KEY AUTOINCREMENT,name varchar(100),years integer)")
conn.execute("CREATE TABLE IF NOT EXISTS semesters(id INTEGER PRIMARY KEY AUTOINCREMENT, departmentid INTEGER FORIEGN KEY REFERENCES departments(id),name varchar(100))")
conn.execute("CREATE TABLE IF NOT EXISTS divisions(id INTEGER PRIMARY KEY AUTOINCREMENT, departmentid INTEGER FORIEGN KEY REFERENCES departments(id),name char(1))")
conn.execute("CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY AUTOINCREMENT,departmentid INTEGER FORIEGN KEY REFERENCES departments(id),semesterid INTEGER FORIEGN KEY REFERENCES semesters(id),divisionid INTEGER FORIEGN KEY REFERENCES divisions(id))")
conn.execute("CREATE TABLE IF NOT EXISTS class_subjects(id INTEGER PRIMARY KEY AUTOINCREMENT, classid INTEGER FORIEGN KEY REFERENCES classes(id),name varchar(100), type char(1))")
conn.execute("CREATE TABLE IF NOT EXISTS class_subject_teacher(id INTEGER PRIMARY KEY AUTOINCREMENT,teacherid INTEGER FORIEGN KEY REFERENCES teachers(id), subjectid INTEGER FORIEGN KEY REFERENCES subjects(id))")
conn.execute("CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,usn char(10) unique,name varchar(100),password varchar(100),mobile varchar(100) unique,email varchar(100) unique,image varchar(100),classid INTEGER FORIEGN KEY REFERENCES classes(id),professionalsubjectid INTEGER NULL,opensubjectid INTEGER NULL,isVerified bool default 0)")
conn.execute("CREATE TABLE IF NOT EXISTS teachers(id INTEGER PRIMARY KEY AUTOINCREMENT,faculityid INTEGER unique,name varchar(100),password varchar(100))")
conn.execute("CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, studentid INTEGER FORIEGN KEY REFERENCES students(id), classsubjectid INTEGER FORIEGN KEY REFERENCES class_subjects(id),day date,isPresent boolean)")
conn.execute("CREATE TABLE IF NOT EXISTS registrationdate(registrationdate date)")
if len(conn.execute(f"SELECT * FROM registrationdate").fetchall())==0:
    conn.execute("INSERT INTO registrationdate(registrationdate) VALUES('"+datetime.date.today().isoformat()+"')")

conn.commit()
conn.close()

app = Flask(__name__)

app.secret_key = "8y6ZZgYht2WHdMS5"

@app.route("/")
def index():
    return redirect("/login")

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method == "POST":
        conn = sqlite3.connect("attendancesystem.db")
        if datetime.date.today().isoformat() > conn.execute(f'SELECT * FROM registrationdate').fetchone()[0]:
            return redirect("/register")
        f = request.files["image"]
        filename = "static/studentimages/"+request.form.get("usn")+"."+f.filename.split(".")[-1]
        f.save(filename)
        usn = request.form.get("usn")
        name = request.form.get("name")
        departmentid = request.form.get("department")
        semester = request.form.get("semester")
        semesterid = conn.execute(f"SELECT * FROM semesters WHERE departmentid={departmentid} AND name='{semester}'").fetchone()[0]
        division = request.form.get("division")
        divisionid = conn.execute(f"SELECT * FROM divisions WHERE departmentid={departmentid} AND name='{division}'").fetchone()[0]
        password = hashlib.sha256(("123"+request.form.get("password")+"abc").encode()).hexdigest()
        mobile = request.form.get("mobile")
        email = request.form.get("email")
        classid = conn.execute(f"SELECT * FROM classes WHERE departmentid='{departmentid}' AND semesterid='{semesterid}' AND divisionid='{divisionid}'").fetchone()[0]
        conn.execute(f"INSERT INTO students (usn,name,password,mobile,email,image,classid) VALUES('{usn}','{name}','{password}','{mobile}','{email}','{filename}','{classid}')")
        conn.commit()
        conn.close()
        return redirect('/login')
    else:
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM departments").fetchall()
        lastdate = conn.execute(f'SELECT * FROM registrationdate').fetchone()[0]
        conn.close()
        return render_template("register.html",departments=result,lastdate=lastdate,todaydate=datetime.date.today().isoformat())

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method == "POST":
        usn = request.form.get("usn")
        password = request.form.get("password")
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM students WHERE usn='{usn}'").fetchall()
        conn.close()
        if len(result)==1:
            if result[0][10] == 0:
                return redirect("/login?error=Account not verified. Your account will be verified soon.")
            elif result[0][3] == hashlib.sha256(("123"+password+"abc").encode()).hexdigest():
                session["studentid"] = result[0][0]
                if not result[0][9] and not result[0][8]:
                    return redirect("/editsubject")
                else:
                    return redirect("/profile")
            else:
                return redirect("/login?error=Wrong utn or password.")
        else:
            return redirect("/login?error=Wrong utn or password.")
    else:
        return render_template("login.html")

@app.route("/profile")
def profile():
    if not "studentid" in session:
        return redirect("/login")
    conn = sqlite3.connect("attendancesystem.db")
    result = conn.execute("SELECT * FROM students WHERE id="+str(session["studentid"])).fetchone()
    class_ = conn.execute("SELECT * FROM classes WHERE id="+str(result[7])).fetchone()
    departmentname = conn.execute("SELECT * FROM departments WHERE id="+str(class_[1])).fetchone()[1]
    semestername = conn.execute(f"SELECT * FROM semesters WHERE departmentid='{class_[1]}' AND id="+str(class_[2])).fetchone()[2]
    divisionname = conn.execute(f"SELECT * FROM divisions WHERE departmentid='{class_[1]}' AND id="+str(class_[3])).fetchone()[2]
    conn.close()
    return render_template("profile.html",student=result,department=departmentname,semester=semestername,division=divisionname)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/editsubject",methods=["GET","POST"])
def editsubject():
    if request.method == "POST":
        conn = sqlite3.connect("attendancesystem.db")
        professionalsubjectid = request.form.get("professionalsubjectid")
        opensubjectid = request.form.get("opensubjectid")
        studentid = session.get("studentid")
        conn.execute(f"UPDATE students SET professionalsubjectid={professionalsubjectid},opensubjectid={opensubjectid} WHERE id='{studentid}'")
        conn.commit()
        conn.close()
        return redirect("/editsubject")
    else:
        if not "studentid" in session:
            return redirect("/login")
        conn = sqlite3.connect("attendancesystem.db")
        studentid = session.get("studentid")
        professionalresult = conn.execute(f"SELECT * FROM class_subjects WHERE classid=(SELECT classid FROM students WHERE id={studentid}) AND type='P'").fetchall()
        openresult = conn.execute(f"SELECT * FROM class_subjects WHERE classid=(SELECT classid FROM students WHERE id={studentid}) AND type='O'").fetchall()
        subjectid = conn.execute(f"SELECT subjectid FROM students WHERE id={studentid}").fetchone()[0]
        conn.close()
        return render_template("editsubject.html",professionalsubjects=professionalresult,opensubjects=openresult,subjectid=subjectid)


@app.route("/adminlogout")
def adminlogout():
    session.clear()
    return redirect("/adminlogin")

@app.route("/faculitylogout")
def faculitylogout():
    session.clear()
    return redirect("/faculitylogin")

@app.route("/dashboard")
def dashboard():
    if not "studentid" in session:
        return redirect("/login")
    conn = sqlite3.connect("attendancesystem.db")
    if request.args.get("month")==None:
        m = str(datetime.date.today().month)
        month = m if len(m)==2 else "0"+m
    else:
        month = request.args.get("month")
    studentid = session.get("studentid")
    subjectid = request.args.get("subject")
    present = conn.execute(f"SELECT count(id) FROM attendance WHERE studentid='{studentid}' and isPresent=1 and day like '____-{month}-__'"+("" if subjectid==None or subjectid=="all" else f" and classsubjectid={subjectid}")).fetchone()[0]
    total = conn.execute(f"SELECT count(id) FROM attendance WHERE studentid='{studentid}' and day like '____-{month}-__'"+("" if subjectid==None or subjectid=="all" else f" and classsubjectid={subjectid}")).fetchone()[0]
    absent = total - present
    try:
        percentage = present/total*100
    except:
        percentage = 0
    subjects = []
    subs = conn.execute(f"SELECT name,id FROM class_subjects WHERE classid=(SELECT classid FROM students WHERE id='{studentid}')"+("" if subjectid==None or subjectid=="all" else f" and id={subjectid}")).fetchall()
    details = {}
    for sub in subs:
        details[sub[0]] = {"present":conn.execute(f"SELECT count(id) FROM attendance WHERE studentid='{studentid}' and isPresent=1 and day like '____-{month}-__' and classsubjectid='{sub[1]}'").fetchone()[0],"total":conn.execute(f"SELECT count(id) FROM attendance WHERE studentid='{studentid}' and day like '____-{month}-__' and classsubjectid='{sub[1]}'").fetchone()[0]}
        subjects.append((sub[0],sub[1]))
    conn.close()
    return render_template("dashboard.html",percentage=percentage,present=present,total=total,absent=absent,subjects=subjects,details=details,month=month,subject=("all" if subjectid==None else subjectid))

@app.route("/edit",methods=["GET","POST"])
def edit():
    if not "studentid" in session:
        return redirect("/login")
    conn = sqlite3.connect("attendancesystem.db")
    if request.method == "GET":
        studentid = session.get("studentid")
        result = conn.execute(f"SELECT * FROM students WHERE id='{studentid}'").fetchone()
        class_ = conn.execute(f"SELECT * FROM classes WHERE id='{result[7]}'").fetchone()
        department = conn.execute(f"SELECT * FROM departments WHERE id='{class_[1]}'").fetchone()
        departmentid = department[0]
        semesters = ["I st","II nd","III rd","IV th","V th","VI th","VII th","VIII th"]
        departmentyears = department[2]
        semesterstosend = semesters[:departmentyears*2]
        semestername = conn.execute(f"SELECT * FROM semesters WHERE id='{class_[2]}'").fetchone()[2]
        divisionname = conn.execute(f"SELECT * FROM divisions WHERE id='{class_[3]}'").fetchone()[2]
        departments = conn.execute(f"SELECT * FROM departments").fetchall()
        conn.close()
        return render_template("edit.html",student=result,departmentid=departmentid,semestername=semestername,divisionname=divisionname,departments=departments,semesters=semesterstosend)
    else:
        f = request.files["image"]
        if f != None:
            filename = "static/studentimages/"+request.form.get("usn")+"."+f.filename.split(".")[-1]
            f.save(filename)
        conn = sqlite3.connect("attendancesystem.db")
        usn = request.form.get("usn")
        name = request.form.get("name")
        departmentid = request.form.get("department")
        semester = request.form.get("semester")
        semesterid = conn.execute(f"SELECT * FROM semesters WHERE departmentid={departmentid} AND name='{semester}'").fetchone()[0]
        division = request.form.get("division")
        divisionid = conn.execute(f"SELECT * FROM divisions WHERE departmentid={departmentid} AND name='{division}'").fetchone()[0]
        mobile = request.form.get("mobile")
        email = request.form.get("email")
        classid = conn.execute(f"SELECT * FROM classes WHERE departmentid='{departmentid}' AND semesterid='{semesterid}' AND divisionid='{divisionid}'").fetchone()[0]
        conn.execute(f"UPDATE students SET usn='{usn}',name='{name}',mobile='{mobile}',email='{email}',classid='{classid}'")
        return ""


@app.route("/faculitylogin",methods=["GET","POST"])
def faculitylogin():
    if request.method == "POST":
        faculityid = request.form.get("faculityid")
        password = request.form.get("password")
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM teachers WHERE faculityid='{faculityid}'").fetchall()
        conn.close()
        if len(result)==1:
            if result[0][3] == hashlib.sha256(("123"+password+"abc").encode()).hexdigest():
                session["faculityid"] = result[0][0]
                return redirect("/classes")
            else:
                return redirect("/faculitylogin")
        else:
            return redirect("/faculitylogin")
    else:
        return render_template("faculitylogin.html")

@app.route("/classes",methods=["GET","POST"])
def classes():
    if not "faculityid" in session:
        return redirect("/faculitylogin")
    conn = sqlite3.connect("attendancesystem.db")
    id = session.get("faculityid")
    teacherclassesresult = conn.execute(f"SELECT subjectid FROM class_subject_teacher WHERE teacherid='{id}'").fetchall()
    subjects = []
    for i in teacherclassesresult:
        for j in conn.execute(f"SELECT classid,name FROM class_subjects WHERE id='{i[0]}'").fetchall():
            subject = []
            ids = conn.execute(f"SELECT departmentid,semesterid,divisionid FROM classes WHERE id='{j[0]}'").fetchone()
            departmentname = conn.execute(f"SELECT name FROM departments WHERE id='{ids[0]}'").fetchone()[0]
            semestername = conn.execute(f"SELECT name FROM semesters WHERE id='{ids[1]}'").fetchone()[0]
            divisionname = conn.execute(f"SELECT name FROM divisions WHERE id='{ids[2]}'").fetchone()[0]
            subject.append(i[0])
            subject.append(j[1])
            subject.append(departmentname)
            subject.append(semestername)
            subject.append(divisionname)
            subjects.append(subject)
    conn.close()
    return render_template("classes.html",subjects=subjects)

@app.route("/showattendance")
def showattendance():
    if not "faculityid" in session:
        return redirect("/faculitylogin")
    conn = sqlite3.connect("attendancesystem.db")
    classsubjectid = request.args.get("id")
    if(request.args.get("day")==None):
        result = conn.execute(f"SELECT distinct(day) FROM attendance WHERE classsubjectid='{classsubjectid}'").fetchall()
        conn.close()
        return render_template("showdates.html",attendance=result,id=classsubjectid)
    else:
        day = request.args.get("day")
        result = conn.execute(f"SELECT studentid,isPresent FROM attendance WHERE classsubjectid='{classsubjectid}' and day='{day}'").fetchall()
        names = {}
        for i in result:
            names[i[0]] = conn.execute(f"SELECT name FROM students WHERE id='{i[0]}'").fetchone()[0]
        conn.close()
        return render_template("showattendance.html",attendance=result,names=names)

@app.route("/adminlogin",methods=["GET","POST"])
def adminlogin():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM admins WHERE username='{username}'").fetchall()
        conn.close()
        if len(result)==1:
            if result[0][2] == hashlib.sha256(("123"+password+"abc").encode()).hexdigest():
                session["adminid"] = result[0][0]
                return redirect("/adminteachers")
            else:
                return redirect("/adminlogin")
        else:
            return redirect("/adminlogin")
    else:
        return render_template("adminlogin.html")

@app.route("/adminstudents")
def adminstudents():
    if not "adminid" in session:
        return redirect("/adminlogin")
    conn = sqlite3.connect("attendancesystem.db")
    students = conn.execute(f"SELECT * FROM students ORDER BY id DESC").fetchall()
    departmentnames = []
    semesternames = []
    divisionnames = []
    for i in students:
        class_ = conn.execute(f"SELECT * FROM classes WHERE id='{i[7]}'").fetchone()
        departmentname = conn.execute(f"SELECT * FROM departments WHERE id='{class_[1]}'").fetchone()[1]
        semestername = conn.execute(f"SELECT * FROM semesters WHERE id='{class_[2]}'").fetchone()[2]
        divisionname = conn.execute(f"SELECT * FROM divisions WHERE id='{class_[3]}'").fetchone()[2]
        departmentnames.append(departmentname)
        semesternames.append(semestername)
        divisionnames.append(divisionname)
    result = []
    count = 0
    for i in students:
        temp = list(i)
        temp.extend([departmentnames[count],semesternames[count],divisionnames[count]])
        result.append(temp)
        count+=1
    conn.close()
    return render_template("adminstudents.html",students=result)

@app.route("/adminclasses")
def adminclasses():
    if not "adminid" in session:
        return redirect("/adminlogin")
    conn = sqlite3.connect("attendancesystem.db")
    departmentids = conn.execute(f"SELECT DISTINCT(departmentid) FROM classes").fetchall()
    departmentnames = {}
    for i in departmentids:
        departmentnames[i[0]] = conn.execute(f"SELECT * FROM departments WHERE id={i[0]}").fetchone()[1]
    semesterids = conn.execute(f"SELECT DISTINCT(semesterid) FROM classes").fetchall()
    semesternames = {}
    for i in semesterids:
        semesternames[i[0]] = conn.execute(f"SELECT * FROM semesters WHERE id={i[0]}").fetchone()[2]
    divisionids = conn.execute(f"SELECT DISTINCT(divisionid) FROM classes").fetchall()
    divisionnames = {}
    for i in divisionids:
        divisionnames[i[0]] = conn.execute(f"SELECT * FROM divisions WHERE id={i[0]}").fetchone()[2]
    classes = conn.execute(f"SELECT * FROM classes").fetchall()
    result = []
    for i in classes:
        result.append((i[0],departmentnames[i[1]],semesternames[i[2]],divisionnames[i[3]]))
    conn.close()
    return render_template("adminclasses.html",classes=result)

@app.route("/adminteachers")
def adminteachers():
    if not "adminid" in session:
        return redirect("/adminlogin")
    conn = sqlite3.connect("attendancesystem.db")
    result = conn.execute(f"SELECT * FROM teachers").fetchall()
    conn.close()
    return render_template("adminteachers.html",teachers=result)

@app.route("/adminaddteacher",methods=["GET","POST"])
def adminaddteacher():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        return render_template("adminaddteacher.html")
    else:
        conn = sqlite3.connect("attendancesystem.db")
        name = request.form.get("name")
        faculityid = request.form.get("faculityid")
        password = hashlib.sha256(("123"+request.form.get("password")+"abc").encode()).hexdigest()
        conn.execute(f"INSERT INTO teachers(name,faculityid,password) values('{name}','{faculityid}','{password}')")
        conn.commit()
        conn.close()
        return redirect("/adminteachers")

@app.route("/adminlastdate",methods=["GET","POST"])
def adminlastdate():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM registrationdate").fetchone()
        conn.close()
        return render_template("adminlastdate.html",date=result[0])
    else:
        conn = sqlite3.connect("attendancesystem.db")
        registrationdate = request.form.get("lastdate")
        conn.execute(f"UPDATE registrationdate SET registrationdate='{registrationdate}'")
        conn.commit()
        conn.close()
        return redirect("/adminlastdate")

@app.route("/admineditteacher",methods=["GET","POST"])
def admineditteacher():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM teachers WHERE id="+request.args.get("id")).fetchone()
        conn.close()
        return render_template("admineditteacher.html",teacher=result)
    else:
        conn = sqlite3.connect("attendancesystem.db")
        name = request.form.get("name")
        faculityid = request.form.get("faculityid")
        id = request.args.get("id")
        conn.execute(f"UPDATE teachers SET name='{name}',faculityid='{faculityid}' WHERE id={id}")
        conn.commit()
        conn.close()
        return redirect("/adminteachers")

@app.route("/adminsubjects")
def adminsubjects():
    if not "adminid" in session:
        return redirect("/adminlogin")
    id = request.args.get("id")
    conn = sqlite3.connect("attendancesystem.db")
    result = conn.execute(f"SELECT * FROM class_subjects WHERE classid={id}").fetchall()
    conn.close()
    return render_template("adminsubjects.html",subjects=result)

@app.route("/adminaddsubject",methods=["GET","POST"])
def adminaddsubject():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        return render_template("adminaddsubject.html")
    else:
        conn = sqlite3.connect("attendancesystem.db")
        classid = request.args.get("id")
        name = request.form.get("name")
        type = request.form.get("type")
        conn.execute(f"INSERT INTO class_subjects(classid,type,name) values('{classid}','{type}','{name}')")
        conn.commit()
        conn.close()
        return redirect(f"/adminsubjects?id={classid}")

@app.route("/admineditsubject",methods=["GET","POST"])
def admineditsubject():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM class_subjects WHERE id="+request.args.get("id")).fetchone()
        conn.close()
        return render_template("admineditsubject.html",subject=result)
    else:
        conn = sqlite3.connect("attendancesystem.db")
        name = request.form.get("name")
        id = request.args.get("id")
        isoptional = bool(request.form.get("isoptional"))
        conn.execute(f"UPDATE class_subjects SET name='{name}', isoptional='{isoptional}' WHERE id={id}")
        conn.commit()
        conn.close()
        return redirect("/adminsubjects?id="+request.args.get("classid"))

@app.route("/admindepartments")
def admindepartments():
    if not "adminid" in session:
        return redirect("/adminlogin")
    conn = sqlite3.connect("attendancesystem.db")
    result = conn.execute(f"SELECT * FROM departments").fetchall()
    conn.close()
    return render_template("admindepartments.html",departments=result)

@app.route("/adminadddepartment",methods=["GET","POST"])
def adminadddepartment():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        return render_template("adminadddepartment.html")
    else:
        name = request.form.get("name")
        years = int(request.form.get("years"))
        conn = sqlite3.connect("attendancesystem.db")
        departmentid = conn.execute(f"INSERT INTO departments (name,years) values('{name}','{years}')").lastrowid
        semesters = ["I st","II nd","III rd","IV th","V th","VI th","VII th","VIII th"]
        semesterids = []
        for i in range(years*2):
            semesterid = conn.execute(f"INSERT INTO semesters (departmentid,name) values ('{departmentid}','{semesters[i]}')").lastrowid
            semesterids.append(semesterid)
        divisionids = []
        divisionid = conn.execute(f"INSERT INTO divisions (departmentid,name) values ('{departmentid}','A')").lastrowid
        divisionids.append(divisionid)
        divisionid = conn.execute(f"INSERT INTO divisions (departmentid,name) values ('{departmentid}','B')").lastrowid
        divisionids.append(divisionid)
        for i in semesterids:
            for j in divisionids:
                conn.execute(f"INSERT INTO classes (departmentid,semesterid,divisionid) values ('{departmentid}','{i}','{j}')").lastrowid
        conn.commit()
        conn.close()
        return redirect("/admindepartments")

@app.route("/admineditdepartment",methods=["GET","POST"])
def admineditdepartment():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        conn = sqlite3.connect("attendancesystem.db")
        result = conn.execute(f"SELECT * FROM departments WHERE id="+request.args.get("id")).fetchone()
        conn.close()
        return render_template("admineditdepartment.html",department=result)
    else:
        name = request.form.get("name")
        id = request.args.get("id")
        conn = sqlite3.connect("attendancesystem.db")
        conn.execute(f"UPDATE departments SET name='{name}' WHERE id={id}")
        conn.commit()
        conn.close()
        return redirect("/admindepartments")

@app.route("/adminteacherclasses",methods=["GET","POST"])
def adminteacherclasses():
    if not "adminid" in session:
        return redirect("/adminlogin")
    if request.method != "POST":
        conn = sqlite3.connect("attendancesystem.db")
        departmentids = conn.execute(f"SELECT DISTINCT(departmentid) FROM classes").fetchall()
        departmentnames = {}
        for i in departmentids:
            departmentnames[i[0]] = conn.execute(f"SELECT * FROM departments WHERE id={i[0]}").fetchone()[1]
        semesterids = conn.execute(f"SELECT DISTINCT(semesterid) FROM classes").fetchall()
        semesternames = {}
        for i in semesterids:
            semesternames[i[0]] = conn.execute(f"SELECT * FROM semesters WHERE id={i[0]}").fetchone()[2]
        divisionids = conn.execute(f"SELECT DISTINCT(divisionid) FROM classes").fetchall()
        divisionnames = {}
        for i in divisionids:
            divisionnames[i[0]] = conn.execute(f"SELECT * FROM divisions WHERE id={i[0]}").fetchone()[2]
        classes = conn.execute(f"SELECT * FROM classes").fetchall()
        result = []
        for i in classes:
            subjects = conn.execute(f"SELECT * FROM class_subjects WHERE classid={i[0]}").fetchall()
            for j in subjects:
                result.append((j[0],j[2],departmentnames[i[1]],semesternames[i[2]],divisionnames[i[3]]))
        id = request.args.get("id")
        teacherclassesresult = conn.execute(f"SELECT subjectid FROM class_subject_teacher WHERE teacherid='{id}'").fetchall()
        teacherclasses = []
        for i in teacherclassesresult:
            teacherclasses.append(i[0])
        conn.close()
        return render_template("adminteacherclasses.html",classes=result,teachersclasses=teacherclasses)
    else:
        id = request.args.get("id")
        conn = sqlite3.connect("attendancesystem.db")
        conn.execute(f"DELETE FROM class_subject_teacher WHERE teacherid='{id}'")
        for i in request.form:
            conn.execute(f"INSERT INTO class_subject_teacher (teacherid,subjectid) values('{id}','{i}')")
        conn.commit()
        conn.close()
        return redirect("/adminteachers")

@app.route("/students")
def students():
    if not "faculityid" in session:
        return redirect("/faculitylogin")
    conn = sqlite3.connect("attendancesystem.db")
    classsubjectid = request.args.get("id")
    classid = conn.execute(f"SELECT classid FROM class_subjects WHERE id = '{classsubjectid}'").fetchone()[0]
    result = conn.execute(f"SELECT * FROM students WHERE classid='{classid}'").fetchall()
    conn.close()
    return render_template("students.html",students=result)

@app.route("/activate")
def activate():
    conn = sqlite3.connect("attendancesystem.db")
    id = request.args.get('id')
    conn.execute(f"UPDATE students SET isverified = 1 WHERE id='{id}'")
    conn.commit()
    conn.close()
    return redirect("/adminstudents")
    
@app.route("/takeattendance")
def takeattendance():
    if not "faculityid" in session:
        return redirect("/faculitylogin")
    conn = sqlite3.connect("attendancesystem.db")
    classsubjectid = request.args.get("id")
    date = str(datetime.date.today())
    if len(conn.execute(f"SELECT * FROM attendance WHERE classsubjectid='{classsubjectid}' and day='{date}'").fetchall())!=0:
        return redirect(f"/showattendance?id={classsubjectid}")
    classid = conn.execute(f"SELECT classid FROM class_subjects WHERE id = '{classsubjectid}'").fetchone()[0]
    students = conn.execute(f"SELECT * FROM students WHERE classid='{classid}'").fetchall()
    images = []
    studentids = []
    for i in students:
        image = cv2.imread(i[6])
        images.append(image)
        studentids.append(i[0])
    def face_encodings(images):
        encode_list = []
        for image in images:
            image = cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
            encode = face_recognition.face_encodings(image)[0]
            encode_list.append(encode)
        return encode_list
    encoding_list = face_encodings(images)
    cap = cv2.VideoCapture(0)
    capturedids = []
    count = 0
    while count<500:
        ret, frame = cap.read()
        faces = cv2.resize(frame, (0,0), None, 0.25,0.25)
        faces = cv2.cvtColor(faces, cv2.COLOR_BGR2RGB)
        faces_current_frame = face_recognition.face_locations(faces)
        encodes_current_frame = face_recognition.face_encodings(faces,faces_current_frame)
        for encode_face, face_loc in zip(encodes_current_frame, faces_current_frame):
            matches = face_recognition.compare_faces(encoding_list, encode_face)
            face_dis = face_recognition.face_distance(encoding_list, encode_face)
            match_index = np.argmin(face_dis)
            if matches[match_index]:
                id = studentids[match_index]
                if id not in capturedids: 
                    capturedids.append(id)
        count+=1
    for i in studentids:
        conn.execute(f"INSERT INTO attendance (studentid,classsubjectid,day,isPresent) VALUES('{i}','{classsubjectid}','{date}','"+str(1 if i in capturedids else 0)+"')")
    conn.commit()
    conn.close()
    return redirect("/showattendance?id="+request.args.get("id"))
app.run(debug=True)