from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.uic import loadUi
import sys
import sqlite3
import re
import hashlib
import csv
import pandas as pd
import os
import random
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# hashing object
def hashira(passw):
    hash_obj = hashlib.new("SHA256")
    hash_obj.update(passw.encode())
    return hash_obj.hexdigest()



def message(self,prompt):
    msgbox = QMessageBox()
    msgbox.setFixedSize(800, 800)
    msgbox.setIcon(QMessageBox.Information)

    msgbox.setText(f"{prompt}")
    msgbox.exec_()
    self.hide()
    self.show()

# for user
userpass = "user"
userpass_hash = hashira(userpass)


# for admin
adminpass = "admin"
adminpass_hash = hashira(adminpass)



# database object
db = sqlite3.connect("playerdata.db")
cur = db.cursor()


cur.execute('''
CREATE TABLE IF NOT EXISTS Students (email TEXT PRIMARY KEY UNIQUE, 
FirstName TEXT NOT NULL, LastName TEXT NOT NULL, password TEXT);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS Admins (email TEXT PRIMARY KEY UNIQUE, 
FirstName TEXT NOT NULL, LastName TEXT NOT NULL, password TEXT);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS temp (email TEXT PRIMARY KEY UNIQUE,
FirstName TEXT NOT NULL, LastName TEXT NOT NULL, role TEXT NOT NULL);
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS testconfig (id TEXT PRIMARY KEY UNIQUE,testname TEXT UNIQUE NOT NULL, filepath TEXT NOT NULL, 
quesamt INTEGER NOT NULL, time TIME NOT NULL, shuffleq TEXT NOT NULL,
 shufflea TEXT NOT NULL);
''')

cur.execute('''
    CREATE TRIGGER IF NOT EXISTS configmanager
    AFTER INSERT ON testconfig
    BEGIN
        UPDATE testconfig SET id = (SELECT last_insert_rowid() FROM testconfig) WHERE rowid = new.rowid;
    END;
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS testresults (id TEXT PRIMARY KEY UNIQUE,testname TEXT NOT NULL, email TEXT NOT NULL, 
score INTEGER NOT NULL);
''')
# the score should be in percentage

cur.execute('''
    CREATE TRIGGER IF NOT EXISTS testmanager
    AFTER INSERT ON testresults
    BEGIN
        UPDATE testresults SET id = (SELECT last_insert_rowid() FROM testresults) WHERE rowid = new.rowid;
    END;
''')


query = cur.execute(f'Select * FROM Students WHERE email="user@gmail.com" and password = "{userpass_hash}"')
if query.fetchall() == []:
    cur.execute("INSERT INTO Students (email, FirstName, LastName, Password) VALUES(?,?,?,?)", ("user@gmail.com", "user","user", userpass_hash))

query = cur.execute(f'Select * FROM Admins WHERE email="admin@gmail.com" and password = "{adminpass_hash}"')
if query.fetchall() == []:
    cur.execute("INSERT INTO admins (email, FirstName, LastName, Password) VALUES(?,?,?,?)", ("admin@gmail.com", "admin","admin", adminpass_hash))

db.commit()


class quiz(QMainWindow):

    def __init__(self, parent=None, email=None, testname=None, filepath=None, quesamt=0, time="00:00:30", shufq=False,
                 shufa=False, mode="TEST"):
        super(quiz, self).__init__(parent)
        loadUi("UI_designs/quiz.ui", self)
        self.timing = time
        self.screen = 0
        self.quesamt = quesamt
        self.mode = mode
        self.tname = testname
        self.email = email
        self.goto = self.findChild(QSpinBox, "ques_spin")
        self.goto.setMaximum(quesamt)
        self.gotobtn = self.findChild(QPushButton, "pushButton_3")
        self.gotobtn.clicked.connect(self.jump)
        self.submit = self.findChild(QPushButton, "pushButton_4")
        self.submit.clicked.connect(self.submiter)
        self.time = self.findChild(QLabel, "label")
        self.number = self.findChild(QLabel, "label_4")
        self.quest = self.findChild(QTextEdit, "textEdit")
        self.opt1 = self.findChild(QRadioButton, "radioButton_3")
        self.opt1.clicked.connect(self.optclicked)
        self.opt2 = self.findChild(QRadioButton, "radioButton")
        self.opt2.clicked.connect(self.optclicked)
        self.opt3 = self.findChild(QRadioButton, "radioButton_4")
        self.opt3.clicked.connect(self.optclicked)
        self.opt4 = self.findChild(QRadioButton, "radioButton_2")
        self.opt4.clicked.connect(self.optclicked)
        self.prev = self.findChild(QPushButton, "pushButton_2")
        self.prev.clicked.connect(self.prevquestion)
        self.nxt = self.findChild(QPushButton, "pushButton")
        self.nxt.clicked.connect(self.nextquestion)


        # explanation part
        self.anslabel = self.findChild(QLabel, "label_3")
        self.ans = self.findChild(QLabel, "label_5")
        self.explanlabel = self.findChild(QLabel, "label_6")
        self.explan = self.findChild(QTextEdit, "textEdit_2")

        self.start_timer()

        df = pd.read_csv(f"{filepath}")

        # Check if the CSV file exists
        if not os.path.exists(filepath):
            message(self, "Test file doesn't Exist")
            # If the file doesn't exist, print out a file doesn't exist error

        # list that stores the questions and details
        self.questions_list = []

        for thing in range(quesamt):

            question = df['Question'].iloc[thing]
            options = df[['Option1', 'Option2', 'Option3', 'Option4']].values.tolist()[thing]
            if shufa:
                print("options shuffled")
                random.shuffle(options)
            correct_answer = df['CorrectOption'].iloc[thing]
            explanation = df['Explanation'].iloc[thing]

            # Append the extracted data to the questions_list
            self.questions_list.append([question, options, correct_answer, explanation])
            # append the correct answer to list

        self.picked_answer = []
        for thing in range(quesamt):
            self.picked_answer.insert(thing, "null")

        self.score = 0
        if shufq:
            print("questions shuffled")
            random.shuffle(self.questions_list)

        self.load(self.screen)


        if mode == "TEST":
            self.anslabel.setText(None)
            self.ans.setText(None)
            self.explanlabel.setText(None)
            self.explan.setText(None)


    def start_timer(self):
        # create qtimer object
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer_display)
        clock = self.timing
        self.time_object = QTime.fromString(clock, "hh:mm:ss")
        # Start the timer (for example, to update every second)
        self.timer.start(1000)  # Update every 1000 ms (1 second)


    def load(self, number):

        if self.screen < 0:
            self.message("This is the first question")
            self.screen = 0
            return

        if self.screen > self.quesamt - 1:
            self.submiter()
            self.screen = self.quesamt - 1
            return



        first = self.questions_list[number]
        self.number.setText(str(self.screen + 1))
        self.quest.setText(str(first[0]))
        opt = first[1]

        self.opt1.setText(opt[0])
        self.opt1.setChecked(True)
        self.opt2.setText(opt[1])
        self.opt3.setText(opt[2])
        self.opt4.setText(opt[3])

        self.picked = self.opt1.text()

        if self.mode == "REVISE":
            self.anslabel.setText("Correct Answer: ")
            self.ans.setText(first[2])
            self.explanlabel.setText("Explanation: ")
            self.explan.setText(first[3])

    def jump(self):
        try:
            self.picked_answer[self.screen] = self.picked
            self.screen = int(self.goto.text()) - 1
            self.load(int(self.goto.text()) - 1)
        except Exception as error:
            print(error)


    def scorer(self):
        first = self.questions_list
        count = 0
        quest = len(first)
        for thing in first:
            print("correct answer")
            print(f"{thing[2]}")
            print(f"{self.picked_answer[count]}")
            if thing[2] == self.picked_answer[count]:
                print("Correct")
                self.score += 1
            count += 1

        self.score = (self.score/quest) * 100

        try:
            cur.execute("INSERT INTO testresults (testname, email, score) VALUES(?,?,?)",
                        (str(self.tname), str(self.email), self.score))

            db.commit()
        except Exception as error:
            self.message(f"{error}")
            print(error)


    def nextquestion(self):
        try:
            print(self.screen)
            print(self.quesamt)
            if self.screen > (self.quesamt - 1):
                self.submiter()

            self.picked_answer[self.screen] = self.picked
            self.screen += 1
            self.load(self.screen)
        except Exception as err:
            print(err)
    def prevquestion(self):
        try:
            self.picked_answer[self.screen] = self.picked
            self.screen -= 1
            self.load(self.screen)
        except Exception as error:
            print(error)

    def update_timer_display(self):
        # Increment the time by one second
        self.time_object = self.time_object.addSecs(-1)
        # Update display or perform other actions based on the updated time
        self.time.setText(f"{QTime.toString(self.time_object, "hh:mm:ss")}")
        hour = self.time_object.hour()
        minutes = self.time_object.minute()
        second = self.time_object.second()

        second = (hour * 60 * 60) + (minutes * 60 ) + second

        if second < 60:
            self.time.setStyleSheet("color: red;")
        if second <= 0:
            self.timer.stop()
            message(self, "time is up")
            self.scorer()
            self.show_score_dialog()
            self.hide()
            new = userwin(self, email=self.email)
            new.show()

    def optclicked(self):
        sender = self.sender()
        self.picked = sender.text()
        print(self.picked)

    def submiter(self):
        # self.picked_answer[self.screen] = self.picked

        # Question message box with icon
        question_box = QMessageBox()
        question_box.setWindowTitle("Submit?")
        question_box.setText("Do you want to Submit")
        question_box.setIcon(QMessageBox.Question)
        question_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply = question_box.exec_()
        if reply == QMessageBox.Yes:
            print("User clicked Yes")
            # score the person
            self.timer.stop()
            self.scorer()
            print(self.picked_answer)
            print(f"scored{self.score} over {self.quesamt}")
            self.show_score_dialog()
            self.hide()
            new = userwin(self,email=self.email)
            new.show()
        else:
            print("User clicked No")
            self.hide()
            self.show()




    # score functions

    def show_score_dialog(self):
        # Function to create and show the score dialog
        dialog = QDialog()
        dialog.setWindowTitle("User Score")

        # Create layout
        layout = QVBoxLayout(dialog)

        # Add label to display score
        score_label = QLabel("Score: {}".format(self.score))
        layout.addWidget(score_label)

        # Add widget to embed matplotlib plot
        plot_widget = QWidget()
        layout.addWidget(plot_widget)

        # Generate and display initial plot
        self.update_plot(plot_widget)

        # Add OK button
        ok_button = QPushButton("OK", dialog)
        ok_button.clicked.connect(dialog.accept)
        layout.addWidget(ok_button)

        # Execute the dialog
        dialog.exec_()

    def update_plot(self, plot_widget):

        # Create bar chart for the score
        fig, ax = plt.subplots()
        ax.bar(["Score", "pass mark"], [self.score, 60], color=['green', 'blue'])
        ax.set_ylabel('Percentage')
        ax.set_title('User Score')
        ax.set_ylim(0, 100)  # Ensure the y-axis ranges from 0 to 100

        # Embed plot in PyQt widget
        canvas = FigureCanvas(fig)
        layout = QVBoxLayout(plot_widget)
        layout.addWidget(canvas)

    def message(self,prompt):
        msgbox = QMessageBox()
        msgbox.setFixedSize(800, 800)
        msgbox.setIcon(QMessageBox.Warning)

        msgbox.setText(f"{prompt}")
        msgbox.exec_()
        self.hide()
        self.show()


class userlogin(QDialog):
    def __init__(self, parent=None):
        super(userlogin, self).__init__(parent)
        loadUi("UI_designs/userlogin.ui", self)
        self.email = self.findChild(QLineEdit, "user_ent")
        self.password = self.findChild(QLineEdit, "pass_ent")
        self.error = self.findChild(QLabel, "userpass_err")
        self.login = self.findChild(QPushButton, "login_btn")
        self.admin = self.findChild(QPushButton, "admin_btn")

        self.login.clicked.connect(self.lgnpage)
        self.admin.clicked.connect(self.admpage)


        self.open()


    def lgnpage(self):
        email = self.email.text()
        email = email.lower()
        Password = self.password.text()
        Password = hashira(Password)
        # password_pattern = r"^[A-Za-z\d*@$]{6,}$"
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if re.match(email_pattern, email):
            db = sqlite3.connect("playerdata.db")
            cur = db.cursor()
            query = cur.execute(f'Select * FROM temp WHERE email="{email}" AND role = "Students"')
            if query.fetchall() != []:
                msgbox = QMessageBox()
                msgbox.setFixedSize(800, 800)
                msgbox.setIcon(QMessageBox.Information)

                msgbox.setText("New user detected")
                msgbox.exec_()

                try:
                    query = cur.execute(
                        f'Select Firstname FROM temp WHERE email="{email}"')
                    person = query.fetchone()
                    person = str(person)
                    print(person)
                    self.hide()
                    new = useradd(self, email, person)
                    new.show()
                except Exception as error:
                    print(error)
            else:
                query = cur.execute(f'Select * FROM Students WHERE email="{email}" and password = "{Password}"')
                if query.fetchall() != []:

                    msgbox = QMessageBox()
                    msgbox.setFixedSize(800, 800)
                    msgbox.setIcon(QMessageBox.Information)

                    msgbox.setText("Login Successful")
                    msgbox.exec_()

                    try:
                        query = cur.execute(f'Select Firstname FROM Students WHERE email="{email}" and password = "{Password}"')
                        person = query.fetchone()
                        person = list(person)
                        print(person[0])
                        self.hide()
                        new = userwin(self,person[0],email)
                        new.show()
                    except Exception as error:
                        print(error)


                else:
                    msgbox = QMessageBox()
                    msgbox.setFixedSize(800, 800)
                    msgbox.setIcon(QMessageBox.Warning)

                    msgbox.setText("Invalid Login Details")
                    msgbox.exec_()
                    self.hide()
                    self.show()

        else:
            message(self,"Email or password doesn't comply")



    def admpage(self):
        try:
            self.hide()
            new = admlogin_mail(self)
            new.show()
        except Exception as error:
            print(error)
class userwin(QMainWindow):

    def message(self,prompt):
        msgbox = QMessageBox()
        msgbox.setFixedSize(800, 800)
        msgbox.setIcon(QMessageBox.Warning)

        msgbox.setText(f"{prompt}")
        msgbox.exec_()
        self.hide()
        self.show()

    def exit(self):

        # Question message box with icon
        question_box = QMessageBox()
        question_box.setWindowTitle("Exit?")
        question_box.setText("Do you want to leave")
        question_box.setIcon(QMessageBox.Question)
        question_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply = question_box.exec_()
        if reply == QMessageBox.Yes:
            print("User clicked Yes")
            self.hide()
            new = userlogin(self)
            new.show()
        else:
            print("User clicked No")
            self.hide()
            self.show()

    def take(self, email):
        self.taken.clear()
        query = cur.execute(f"SELECT testname FROM testresults WHERE email='{self.email}' ORDER BY id DESC")
        result = query.fetchall()
        print("take clear")

        # Add each item to the QListWidget
        for row in result:
            item_text = row[0]  # Assuming name is the first column
            self.taken.addItem(item_text)

    def __init__(self, parent=None, person=None, email=None):
        super(userwin, self).__init__(parent)
        loadUi("UI_designs/user-win.ui", self)
        self.email = email
        print("i entered here")
        print(str(person))

        self.name = self.findChild(QLabel, "nam")
        self.name.setText(str(person))
        print("not my problem")
        self.logout = self.findChild(QPushButton, "logout_btn")
        self.logout.clicked.connect(self.exit)
        self.taken = self.findChild(QListWidget, "tests_taken")
        self.take(self.email)

        # # # # First tab elements (Customize Quiz)
        self.subject = self.findChild(QComboBox, "sub")
        self.subject.activated.connect(self.load)
        self.tname1 = self.findChild(QLineEdit, "tstname1")
        self.ques = self.findChild(QSpinBox, "ques1")
        self.time = self.findChild(QTimeEdit, "time1")
        self.shuffle_q = self.findChild(QCheckBox, "shuffq")
        self.shuffle_a = self.findChild(QCheckBox, "shuffa")

        # radiobuttons
        self.mode = "TEST"
        self.rad1 = self.findChild(QRadioButton, "radioButton1")
        self.rad1.clicked.connect(self.radioButtonClicked)
        self.rad2 = self.findChild(QRadioButton, "radioButton2")
        self.rad2.clicked.connect(self.radioButtonClicked)


        # start quiz button
        self.go1 = self.findChild(QPushButton, "go_btn1")
        self.go1.clicked.connect(self.start1)

        # # # # second tab elements (choose quiz file)
        self.subject2 = self.findChild(QComboBox, "sub_2")
        self.loadbtn = self.findChild(QPushButton, "load_btn")
        self.loadbtn.clicked.connect(self.loading)
        self.quesunt = self.findChild(QSpinBox, "ques2")
        self.time2 = self.findChild(QTimeEdit, "time2")
        self.go2 = self.findChild(QPushButton, "go_btn2")
        self.go2.clicked.connect(self.start2)

        self.load2()

    # functions
    def radioButtonClicked(self):
        sender = self.sender()
        if sender.isChecked():
            print(f'{sender.text()} is selected')
            self.mode = sender.text()

    def load(self):
        subject = self.subject.currentText()

        if subject == "English":
            file_path = "./question files/english.csv"
            print("English")
        elif subject == "Mathematics":
            file_path = "./question files/maths.csv"
            print("mathematics")
        elif subject == "Chemistry":
            file_path = "./question files/chemistry.csv"
            print("chemistry")
        elif subject == "Geography":
            file_path = "./question files/geography.csv"
            print("geography")
        else:
            message(self, "An error occured")

        # Check if the CSV file exists
        if not os.path.exists(file_path):
            message(self, "Test file doesn't Exist")
            # If the file doesn't exist, print out a file doesn't exist error



        with open(file_path, "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            # Use sum() to count the number of rows
            row_count = sum(1 for row in reader)
            if row_count < 2:
                self.message("Empty Question file")
        self.ques.setMaximum(row_count - 1)

        return file_path
    def load2(self):
        query = cur.execute("SELECT * FROM testconfig")
        result = query.fetchall()
        result = list(result)
        print(result)

        self.subject2.clear()
        # Add each item to the Qcombobox
        count = 0
        for row in result:
            item_text = row[1]  # Assuming name is the first column
            # self.subject2.addItem(item_text)
            self.subject2.insertItem(count,item_text)
            count =+ 1

    def loading(self):
        subject = self.subject2.currentText()
        print(subject)

        if subject:
            try:
                query = cur.execute(f"SELECT * FROM testconfig WHERE testname = '{subject}'")
                result = query.fetchone()
                print(f"hello boy {result}")

                self.quesunt.setValue(result[3])
                time_from_db = result[4]
                # Parse the time string into a QTime object
                time_object = QTime.fromString(time_from_db, "hh:mm:ss")
                self.time2.setTime(time_object)
            except Exception as error:
                print(error)
        else:
            self.message("No Test file selected")

    def start1(self):
        namereg = "^[a-zA-Z0-9-]{3,}$"
        filepath = self.load()
        tname = self.tname1.text()
        ques = self.ques.value()
        timev = self.time.time()
        timev = timev.toString("HH:mm:ss")
        shuffleq = self.shuffle_q.isChecked()
        shufflea = self.shuffle_a.isChecked()
        tmode = self.mode
        email = self.email

        if tname:
            if re.match(namereg, tname):
                self.hide()
                new = quiz(self,email,tname,filepath,ques,timev,shuffleq,shufflea,tmode)
                new.show()
            else:
                self.message("Please make sure the test name doesn't contain special characters and is at least 3 "
                             "characters long")
        else:
            self.message("please fill in the empty fields")

    def start2(self):
        tname = self.subject2.currentText()
        email = self.email
        tmode = self.mode

        self.loading()

        try:
            query = cur.execute(f"SELECT * FROM testconfig WHERE testname = '{tname}'")
            result = query.fetchone()
            result = list(result)

            self.hide()
            new = quiz(self, email, result[1], result[2], result[3], result[4], result[5], result[6], tmode)
            new.show()
        except Exception as error:
            print(error)
class useradd(QDialog):
    def __init__(self, parent=None, email=None, person=None):
        super(useradd, self).__init__(parent)
        self.user_email = email
        self.person = person
        loadUi("UI_designs/useradd.ui", self)

        self.password = self.findChild(QLineEdit, "pass_ent")
        self.conpassword = self.findChild(QLineEdit, "pass_ent2")
        self.login = self.findChild(QPushButton, "login_btn")

        self.login.clicked.connect(self.next)

    def next(self):
        password = self.password.text()
        con = self.conpassword.text()
        password_pattern = r"^[A-Za-z\d*@$]{6,}$"

        if password and con:
            if re.match(password_pattern, password):
                if password == con:
                    password = hashira(password)
                    query = cur.execute(f'Select email, FirstName, LastName FROM temp WHERE email="{self.user_email}"')
                    result = query.fetchone()
                    result = list(result)
                    print(result)
                    print(type(result))
                    try:
                        cur.execute("INSERT INTO Students (email, FirstName, LastName, Password) VALUES(?,?,?,?)",
                                    (str(result[0]),str(result[1]), str(result[2]), password))
                        cur.execute(f"DELETE FROM temp WHERE email = '{str(result[0])}'")
                        db.commit()
                        message(self, "success")

                        self.hide()
                        print(result[1])
                        print(result[0])
                        new = userwin(person=result[1],email=result[0])
                        new.show()
                    except Exception as error:
                        message(self, f"{error}")
                        print(f"{error}")
                else:
                    message(self,"Passwords don't match")
            else:
                message(self,"Please make sure the password follows standard")

        else:
            message(self,"Please fill in the empty fields")
class adminadd(QDialog):
    def __init__(self, parent=None, email=None):
        super(adminadd, self).__init__(parent)
        self.admin_email = email
        loadUi("UI_designs/adminadd.ui", self)

        self.password = self.findChild(QLineEdit, "pass_ent")
        self.conpassword = self.findChild(QLineEdit, "pass_ent2")
        self.login = self.findChild(QPushButton, "login_btn")

        self.login.clicked.connect(self.next)

    def next(self):
        password = self.password.text()
        con = self.conpassword.text()
        password_pattern = r"^[A-Za-z\d*@$]{6,}$"

        if password and con:
            if re.match(password_pattern, password):
                if password == con:
                    password = hashira(password)
                    query = cur.execute(f'Select email, FirstName, LastName FROM temp WHERE email="{self.admin_email}"')
                    result = query.fetchall()
                    thing = list(result[0])
                    print(thing)
                    try:
                        cur.execute("INSERT INTO Admins (email, FirstName, LastName, Password) VALUES(?,?,?,?)",
                                    (str(thing[0]),str(thing[1]), str(thing[2]), password))
                        cur.execute(f"DELETE FROM temp WHERE email = '{str(thing[0])}'")
                        db.commit()
                        message(self, "success")


                        self.hide()
                        new = admlogin_ui(self)
                        new.show()
                    except Exception as error:
                        message(self, f"{error}")



                else:
                    message(self,"Passwords don't match")
            else:
                message(self,"Please make sure the password follows standard")

        else:
            message(self,"Please fill in the empty fields")
class admlogin_mail(QDialog):

    def __init__(self, parent=None):
        super(admlogin_mail, self).__init__(parent)
        loadUi("UI_designs/adminlogin-email.ui", self)
        self.email = self.findChild(QLineEdit, "user_ent")
        self.login = self.findChild(QPushButton, "login_btn")
        self.user = self.findChild(QPushButton, "user_btn")
        self.password = self.findChild(QLineEdit, "pass_ent")

        self.login.clicked.connect(self.passpage)
        self.user.clicked.connect(self.userpage)
        self.open()


    def passpage(self):
        email = self.email.text()
        email = email.lower()
        password = self.password.text()
        password = hashira(password)

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if re.match(email_pattern, email):
            db = sqlite3.connect("playerdata.db")
            cur = db.cursor()
            query = cur.execute(f'Select * FROM temp WHERE email="{email}" AND role = "Admins"')
            if query.fetchall() != []:
                msgbox = QMessageBox()
                msgbox.setFixedSize(800, 800)
                msgbox.setIcon(QMessageBox.Information)

                msgbox.setText("New user detected")
                msgbox.exec_()

                try:
                    self.hide()
                    new = adminadd(self, email)
                    new.show()
                except Exception as error:
                    print(error)
            else:
                query = cur.execute(f'Select * FROM Admins WHERE email="{email}" and password = "{password}"')
                if query.fetchall() != []:

                    msgbox = QMessageBox()
                    msgbox.setFixedSize(800, 800)
                    msgbox.setIcon(QMessageBox.Information)

                    msgbox.setText("Login Successful")
                    msgbox.exec_()

                    try:
                        self.hide()
                        new = admlogin_ui(self)
                        new.show()
                    except Exception as error:
                        print(error)


                else:
                    msgbox = QMessageBox()
                    msgbox.setFixedSize(800, 800)
                    msgbox.setIcon(QMessageBox.Warning)

                    msgbox.setText("Invalid Login Details")
                    msgbox.exec_()
                    self.hide()
                    self.show()

        else:
            message(self, "Email or password doesn't comply")


    def userpage(self):
        try:
            self.hide()
            new = userlogin(self)
            new.show()
        except Exception as error:
            print(error)
class admlogin_ui(QMainWindow):

    def load(self):
        subject = self.subject.currentText()

        if subject == "English":
            file_path = "./question files/english.csv"
            print("English")
        elif subject == "Mathematics":
            file_path = "./question files/maths.csv"
            print("mathematics")
        elif subject == "Chemistry":
            file_path = "./question files/chemistry.csv"
            print("chemistry")
        elif subject == "Geography":
            file_path = "./question files/geography.csv"
            print("geography")
        else:
            self.message("an error occurred")

        # Check if the CSV file exists
        if not os.path.exists(file_path):
            # If the file doesn't exist, create it with headers
            with open(file_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                # Write headers
                writer.writerow(["Question", "Option1", "Option2", "Option3", "Option4", "CorrectOption", "Explanation"])

        with open(file_path, "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            # Use sum() to count the number of rows
            row_count = sum(1 for row in reader)
            if row_count < 2:
                self.message("Empty Question file")
        self.qamt.setMaximum(row_count - 1)

        return file_path

    def quit(self):

        # Question message box with icon
        question_box = QMessageBox()
        question_box.setWindowTitle("Exit?")
        question_box.setText("Do you want to leave")
        question_box.setIcon(QMessageBox.Question)
        question_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply = question_box.exec_()
        if reply == QMessageBox.Yes:
            print("User clicked Yes")
            self.hide()
            new = userlogin(self)
            new.show()
        else:
            print("User clicked No")
            self.hide()
            self.show()

    def message(self,prompt):
        msgbox = QMessageBox()
        msgbox.setFixedSize(800, 800)
        msgbox.setIcon(QMessageBox.Warning)

        msgbox.setText(f"{prompt}")
        msgbox.exec_()
        self.hide()
        self.show()


    def query(self, what, where):
        alphonse = cur.execute(f"SELECT {what} FROM {where}")
        result = alphonse.fetchall()
        return result

    def __init__(self, parent=None):
        super(admlogin_ui, self).__init__(parent)
        loadUi("UI_designs/admin.ui", self)

        # logout button

        self.logout = self.findChild(QPushButton, "logout_btn")
        self.logout.clicked.connect(self.quit)

        # user control tab elements
        self.tabc = self.findChild(QComboBox, "tab_combo")
        tab = self.tabc.currentText()
        self.email = self.findChild(QLineEdit, "email_ent")
        self.fname = self.findChild(QLineEdit, "first_name")
        self.lname = self.findChild(QLineEdit, "last_name")
        self.search = self.findChild(QComboBox, "search_combo")
        self.searchbtn = self.findChild(QPushButton, "search_btn")
        self.searchbtn.clicked.connect(self.searching)
        self.printall = self.findChild(QPushButton, "printall_btn")
        self.printall.clicked.connect(self.refreshtable)
        self.table = self.findChild(QTableWidget, "table_wid")
        self.delete = self.findChild(QPushButton, "delete_btn")
        self.delete.clicked.connect(self.deleteperson)
        self.edit = self.findChild(QPushButton, "edit_btn")
        self.edit.clicked.connect(self.editperson)
        self.add = self.findChild(QPushButton, "reg_admin")
        self.add.clicked.connect(self.addperson)

        # Create Quiz tab elements
        self.subject = self.findChild(QComboBox, "sub")
        self.subject.activated.connect(self.load)
        self.tname = self.findChild(QLineEdit, "tboy")
        self.qamt = self.findChild(QSpinBox, "ques")
        self.time = self.findChild(QTimeEdit, "tamt")
        self.shuffle_q = self.findChild(QCheckBox, "shuffq")
        self.shuffle_a = self.findChild(QCheckBox, "shuffa")
        self.start = self.findChild(QPushButton, "startbtn")
        self.start.clicked.connect(self.make)

        self.load()


        # insights part
        self.list = self.findChild(QListWidget, "listWidget")
        self.list.itemClicked.connect(self.clicked)
        self.frame = self.findChild(QWidget, "widget_2")
        self.bperf = self.findChild(QLabel, "label_13")
        self.wperf = self.findChild(QLabel, "label_14")
        self.take()


    def clicked(self, item):
        print("hello")
        print(item.text())
        try:
            query = cur.execute(f"SELECT score FROM testresults WHERE testname = '{item.text()}'")
            result = query.fetchall()
            total = len(result)
            query = cur.execute(f"SELECT score FROM testresults WHERE score >= 60 AND testname = '{item.text()}'")
            result = query.fetchall()
            passed = len(result)
            failed = total - passed
            query = cur.execute(f"SELECT email, MIN(score) FROM testresults WHERE testname = '{item.text()}'")
            result = query.fetchone()
            self.wperf.setText(result[0])
            query = cur.execute(f"SELECT email, MAX(score) FROM testresults WHERE testname = '{item.text()}'")
            result = query.fetchone()
            self.bperf.setText(result[0])

            print(f"{total}total")
            print(f"{passed}passed")
            print(f"{failed}failed")


            if total <= 0:
                self.message("NO DATA TO SHOW")



            # Create a Matplotlib figure and axis
            self.figure = Figure()
            self.canvas = FigureCanvas(self.figure)

            # Set a layout for the QWidget
            self.layout = QVBoxLayout(self.frame)
            self.layout.addWidget(self.canvas)

            # Create a pie chart
            self.ax = self.figure.add_subplot(111)
            labels = ['passed', 'failed']
            sizes = [passed, failed]
            self.ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            self.ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
            self.canvas.draw()

        except Exception as error:
            print(error)



    def take(self):
        self.list.clear()
        query = cur.execute(f"SELECT DISTINCT testname FROM testresults ORDER BY id DESC")
        result = query.fetchall()

        # Add each item to the QListWidget
        for row in result:
            item_text = row[0]  # Assuming name is the first column
            self.list.addItem(item_text)

    def searching(self):
        email_ent = self.email.text()
        email_ent = email_ent.lower()
        fname_ent = self.fname.text()
        lname_ent = self.lname.text()
        tab = self.tabc.currentText()
        searc = self.search.currentText()
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        name_pattern = r"^[a-zA-Z]+(?: [a-zA-Z]+)*$"

        if searc == "Email":
            searc = "email"

            if email_ent == "":
                self.message("empty field")

            if re.match(email_pattern, email_ent):
                scan = cur.execute(f'SELECT * FROM {tab} WHERE email = "{email_ent}"')
                scan = scan.fetchall()

                row = 0
                self.table.setRowCount(len(scan))

                for person in scan:
                    self.table.setItem(row, 0, QTableWidgetItem(str(person[0])))
                    self.table.setItem(row, 1, QTableWidgetItem(str(person[1])))
                    self.table.setItem(row, 2, QTableWidgetItem(str(person[2])))

                    row += 1
            else:
                self.message("Email field doesn't comply")

        if searc == "First Name":
            searc = "FirstName"

            if fname_ent == "":
                self.message("empty field")

            if re.match(name_pattern, fname_ent):
                scan = cur.execute(f'SELECT * FROM {tab} WHERE FirstName = "{fname_ent}"')
                scan = scan.fetchall()

                row = 0
                self.table.setRowCount(len(scan))

                for person in scan:
                    self.table.setItem(row, 0, QTableWidgetItem(str(person[0])))
                    self.table.setItem(row, 1, QTableWidgetItem(str(person[1])))
                    self.table.setItem(row, 2, QTableWidgetItem(str(person[2])))

                    row += 1
            else:
                self.message("firstname field doesn't comply")
        if searc == "Last name":
            searc = "LastName"

            if lname_ent == "":
                self.message("empty field")

            if re.match(name_pattern, lname_ent):
                scan = cur.execute(f'SELECT * FROM {tab} WHERE email = "{lname_ent}"')
                scan = scan.fetchall()

                row = 0
                self.table.setRowCount(len(scan))

                for person in scan:
                    self.table.setItem(row, 0, QTableWidgetItem(str(person[0])))
                    self.table.setItem(row, 1, QTableWidgetItem(str(person[1])))
                    self.table.setItem(row, 2, QTableWidgetItem(str(person[2])))

                    row += 1
            else:
                self.message("lastname field doesn't comply")
    def refreshtable(self):
        tab = self.tabc.currentText()
        row = 0
        result = self.query("*", f"{tab}")
        self.table.setRowCount(len(result))

        for person in result:
            self.table.setItem(row, 0, QTableWidgetItem(str(person[0])))
            self.table.setItem(row, 1, QTableWidgetItem(str(person[1])))
            self.table.setItem(row, 2, QTableWidgetItem(str(person[2])))

            row += 1
    def deleteperson(self):
        email_ent = self.email.text()
        email_ent = email_ent.lower()
        tab = self.tabc.currentText()
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if re.match(email_pattern, email_ent):

            # Question message box with icon
            question_box = QMessageBox()
            question_box.setWindowTitle("DELETE")
            question_box.setText("Do you want to continue?")
            question_box.setIcon(QMessageBox.Question)
            question_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            reply = question_box.exec_()
            if reply == QMessageBox.Yes:
                try:
                    scan = cur.execute(f'SELECT * FROM {tab} WHERE email = "{email_ent}"')
                    scan = scan.fetchall()
                    if len(scan) != 0:
                        cur.execute(f"DELETE FROM {tab} WHERE email = '{email_ent}'")

                        db.commit()

                        msgbox = QMessageBox()
                        msgbox.setFixedSize(800, 800)
                        msgbox.setIcon(QMessageBox.Information)

                        msgbox.setText(f"user removed successfully")
                        msgbox.exec_()
                        self.hide()
                        self.show()
                        self.email.setText(None)
                        self.fname.setText(None)
                        self.lname.setText(None)
                        self.refreshtable()
                    else:
                        self.message("email doesn't exists")

                except Exception as error:
                    print(error)
                    self.message(f"{error}")
            else:
                self.message("Reverted")


        else:
            self.message("one or more fields don't comply")
    def editperson(self):
        email_ent = self.email.text()
        email_ent = email_ent.lower()
        fname_ent = self.fname.text()
        lname_ent = self.lname.text()
        tab = self.tabc.currentText()
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        name_pattern = r"^[a-zA-Z]+(?: [a-zA-Z]+)*$"

        if re.match(email_pattern, email_ent) and re.match(name_pattern, fname_ent) and re.match(name_pattern,
                                                                                                 lname_ent):
            try:
                scan = cur.execute(f'SELECT * FROM {tab} WHERE email = "{email_ent}"')
                scan = scan.fetchall()
                if len(scan) != 0 :
                    cur.execute(f"UPDATE {tab} SET FirstName = '{fname_ent}', LastName = '{lname_ent}' WHERE email = '{email_ent}';")

                    db.commit()

                    msgbox = QMessageBox()
                    msgbox.setFixedSize(800, 800)
                    msgbox.setIcon(QMessageBox.Information)

                    msgbox.setText(f"user details updated successfully")
                    msgbox.exec_()
                    self.hide()
                    self.show()
                    self.email.setText(None)
                    self.fname.setText(None)
                    self.lname.setText(None)
                    self.refreshtable()
                else:
                    self.message("email doesn't exists")

            except Exception as error:
                print(error)
                self.message(f"{error}")
        else:
            self.message("one or more fields don't comply")
    def addperson(self):
        email_ent = self.email.text()
        email_ent = email_ent.lower()
        fname_ent = self.fname.text()
        lname_ent = self.lname.text()
        tab = self.tabc.currentText()
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        name_pattern = r"^[a-zA-Z]+(?: [a-zA-Z]+)*$"

        if re.match(email_pattern, email_ent) and re.match(name_pattern, fname_ent) and re.match(name_pattern, lname_ent):
            try:
                scan = cur.execute(f'SELECT * FROM {tab} WHERE email = "{email_ent}"')
                scan = scan.fetchall()
                new = cur.execute(f'SELECT * FROM temp WHERE email = "{email_ent}"')
                new = new.fetchall()

                if len(scan) == 0 & len(new) == 0:
                    cur.execute("INSERT INTO temp (email, FirstName, LastName, role) VALUES(?,?,?,?)",
                                (email_ent, fname_ent, lname_ent, tab))
                    db.commit()

                    msgbox = QMessageBox()
                    msgbox.setFixedSize(800, 800)
                    msgbox.setIcon(QMessageBox.Information)

                    msgbox.setText(f"user added successfully")
                    msgbox.exec_()
                    self.hide()
                    self.show()
                    self.email.setText(None)
                    self.fname.setText(None)
                    self.lname.setText(None)
                    self.refreshtable()
                else:
                    self.message("email already exists")
            except Exception as error:
                print(error)
                self.message(f"{error}")
        else:
            self.message("one or more fields don't comply")


    # Create quiz page functions

    def make(self):
        file_path = self.load()
        name = self.tname.text()
        print(name)
        ques = self.qamt.value()
        timev = self.time.time()
        timev = timev.toString("HH:mm:ss")
        shuffleq = self.shuffle_q.isChecked()
        shufflea = self.shuffle_a.isChecked()
        namereg = "^[a-zA-Z0-9-]{3,}$"


        if name:
            if re.match(namereg, name):
                try:
                    cur.execute("INSERT INTO testconfig (id, testname, filepath, quesamt, time, shuffleq, shufflea) VALUES (?,?,?,?,?,?,?);",
                                (0,f"{str(name)}", file_path, ques, timev, shuffleq, shufflea))
                    db.commit()
                    self.message("success")
                    self.tname.setText(None)

                except Exception as error:
                    self.message(f"{error}")

            else:
                self.message("Please make sure the test name doesn't"
                             " contain special characters and is at least 3 characters long")

        else:
            self.message("Please fill in the empty fields")


def main():
    ex = QApplication(sys.argv)
    exes = userlogin()
    exes.show()
    sys.exit(ex.exec_())


if __name__ == "__main__":
    main()
