from random import randint
import re  
import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
from datetime import datetime, timedelta

# App Configuration
app = Flask(__name__) 

app.secret_key = 'abcdefgh'
  
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'cs353hw4db'
mysql = MySQL(app)

@app.route('/')

# Login Page
@app.route('/login', methods =['GET', 'POST'])
def login():
    message = ''
    
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s AND password = % s', (username, password, ))
        user = cursor.fetchone()
        
        if user:              
            session['loggedin'] = True
            session['userid'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']
            message = 'Logged in successfully!'
            return redirect(url_for('tasks'))
        else:
            message = 'Please enter correct email / password !'
            
    return render_template('login.html', message = message)

@app.route('/logout-login', methods =['GET', 'POST'])
def logout():
    session['loggedin'] = False
    session['userid'] = None
    session['username'] = None
    session['email'] = None
    message = 'Logged out successfully!'
    
    return render_template('login.html', message = message)

# Register Page
@app.route('/register', methods =['GET', 'POST'])
def register():
    message = ''
    
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE username = % s', (username, ))
        account = cursor.fetchone()
        
        if account:
            message = 'Choose a different username!'
  
        elif not username or not password or not email:
            message = 'Please fill out the form!'

        else:
            # Select an ID for the new user which is (max_id + 1)
            cursor.execute("SELECT MAX(id) AS max_id FROM User")
            max = cursor.fetchone()
            max_id = max['max_id'] 
            new_id = max_id + 1
            
            # Add the user
            cursor.execute('INSERT INTO User (id, username, email, password) VALUES (% s, % s, % s, % s)', (new_id, username, email, password,))
            mysql.connection.commit()
            message = 'User successfully created!'

    elif request.method == 'POST':
        message = 'Please fill all the fields!'
        
    return render_template('register.html', message = message)

@app.route('/tasks', methods =['GET', 'POST'])
def tasks():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the tasks of the user
    cursor.execute("SELECT * FROM Task WHERE user_id = % s ORDER BY deadline", (session['userid'], ))
    tasks = cursor.fetchall()
    
    # Headers of the tasks table
    headers = ['ID', 'Title', 'Description', 'Status', 'Deadline', 'Creation Time', 'Done Time', 'Task Type']
    
    # Fetch the completed tasks of the user
    cursor.execute("SELECT * FROM Task WHERE user_id = % s AND status = % s ORDER BY done_time", (session['userid'], "Done"))
    completed_tasks = cursor.fetchall()
    
    return render_template('tasks.html', tasks = tasks, headers = headers, completed_tasks = completed_tasks)

@app.route('/analysis', methods =['GET', 'POST'])
def analysis():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Query and headers of analysis 1
    cursor.execute("SELECT title, TIMEDIFF(done_time, deadline) AS latency FROM Task WHERE status = 'Done' AND done_time > deadline AND user_id = % s", (session['userid'], ))
    analysis1 = cursor.fetchall() 
    headers1 = ['Title', 'Latency']
    
    # Query and headers of analysis 2
    cursor.execute("SELECT ROUND(AVG(TIMEDIFF(done_time, creation_time)) / 10000, 0) AS avg FROM Task WHERE status = 'Done' AND user_id = % s", (session['userid'], ))
    analysis2 = cursor.fetchall()
    headers2 = ['Avg']
    
    # Query and headers of analysis 3
    cursor.execute("SELECT task_type, COUNT(*) AS num FROM Task WHERE status = 'Done' AND user_id = % s GROUP BY task_type ORDER BY num DESC", (session['userid'], ))
    analysis3 = cursor.fetchall()
    headers3 = ['Task Type', 'Count']
    
    # Query and headers of analysis 4
    cursor.execute("SELECT title, deadline FROM Task WHERE status = 'Todo' AND user_id = % s ORDER BY deadline", (session['userid'], ))
    analysis4 = cursor.fetchall()
    headers4 = ['Title', 'Deadline']
    
    # Query and headers of analysis 5
    cursor.execute("SELECT title, TIMEDIFF(done_time, creation_time) AS completion_time FROM Task WHERE status = 'Done' AND user_id = % s ORDER BY completion_time DESC LIMIT 2", (session['userid'], ))
    analysis5 = cursor.fetchall()
    headers5 = ['Title', 'Completion Time']
     
    return render_template('analysis.html', analysis1 = analysis1, headers1 = headers1,
                                            analysis2 = analysis2, headers2 = headers2,
                                            analysis3 = analysis3, headers3 = headers3,
                                            analysis4 = analysis4, headers4 = headers4,
                                            analysis5 = analysis5, headers5 = headers5)

@app.route('/add', methods =['GET', 'POST'])
def add():
    message = ''
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the task types
    cursor.execute("SELECT * FROM TaskType")
    task_types = cursor.fetchall()
    
    
    if request.method == 'POST' and 'title' in request.form and 'description' in request.form and 'deadline' in request.form and 'tasktype' in request.form:
        # Get the input field values
        title = request.form['title']
        description = request.form['description']
        deadline = request.form['deadline']
        task_type = request.form['tasktype']
        
        if not title or not description or not deadline or not task_type:
            message = 'Please fill all the fields!'
        else:
            # Select an ID for the new task which is (max_id + 1)
            cursor.execute("SELECT MAX(id) AS max_id FROM Task")
            max = cursor.fetchone()
            max_id = max['max_id'] 
            new_id = max_id + 1
            
            # Get and format the current datetime to be used as creation_time
            current_datetime = datetime.now()
            current_datetime = current_datetime + timedelta(hours=3)
            creation_time = current_datetime.strftime("%Y/%m/%d %H:%M:%S")
           
            # Add the task
            cursor.execute("INSERT INTO Task (id, title, description, status, deadline, creation_time, done_time, user_id, task_type) VALUES (% s, % s, % s, % s, % s, % s, % s, % s, % s)", 
                          (new_id, title, description, "Todo", deadline, creation_time, None, session['userid'], task_type, ))
            mysql.connection.commit()
            message = 'Task successfully added!'
        
    return render_template('add.html', message = message, types = task_types)

@app.route('/delete', methods =['GET', 'POST'])
def delete():
    message = ''

    if request.method == 'POST' and 'id' in request.form:
        # Get the input field value
        id = request.form['id']
         
        # Input field check
        if not id:
            message = 'Please enter an ID!'
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Check if the task exists
            cursor.execute('SELECT * FROM Task WHERE id = % s AND user_id = % s', (id, session['userid'], ))
            task = cursor.fetchone()
            
            if not task:
                message = 'Task does not exist!'
            else: 
                # Delete the task if it exists
                cursor.execute("DELETE FROM Task WHERE id = % s", (id, ))
                mysql.connection.commit()
                message = 'Task successfully deleted!'
    
    return render_template('delete.html', message = message)

@app.route('/edit', methods =['GET', 'POST'])
def edit():
    message = ''
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Fetch the task types
    cursor.execute("SELECT * FROM TaskType")
    task_types = cursor.fetchall()

    if request.method == 'POST' and 'id' in request.form:
        # Get input field value
        id = request.form['id']
        
        # Input field check
        if not id:
            message = 'Please enter an ID!'
        else:
            # Check if the task exists
            cursor.execute('SELECT * FROM Task WHERE id = % s AND user_id = % s', (id, session['userid'], ))
            task = cursor.fetchone()
            
            if not task:
                message = 'Task does not exist!'
            else:
                # Edit the task -> get input field values
                message = 'Task found!'
                new_title = request.form['title']
                new_description = request.form['description']
                new_deadline = request.form['deadline']
                new_task_type = request.form['tasktype']
                
                # Update the database according to the edit            
                cursor.execute("UPDATE Task SET title = % s, description = % s, deadline = % s, task_type = % s WHERE id = % s", (new_title, new_description, new_deadline, new_task_type, id, ))
                mysql.connection.commit()
                message = 'Changes are successfully saved!'

    return render_template('edit.html', message = message, types = task_types)

@app.route('/finish', methods =['GET', 'POST'])
def finish():
    message = ''

    if request.method == 'POST' and 'id' in request.form:
        # Get input field value
        id = request.form['id']
         
        if not id:
            message = 'Please enter an ID!'
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # Check if the task exists
            cursor.execute('SELECT * FROM Task WHERE id = % s AND user_id = % s', (id, session['userid'], ))
            task = cursor.fetchone()
            
            if not task:
                message = 'Task does not exist!'
            else: 
                status = task['status']
                
                # Mark the task 'Done' if its status is 'Todo'
                if status == 'Todo':
                    # Get and format the current time to be used as done_time
                    current_datetime = datetime.now()
                    current_datetime = current_datetime + timedelta(hours=3)
                    done_time = current_datetime.strftime("%Y/%m/%d %H:%M:%S")
                    
                    # Update the task accordingly
                    cursor.execute("UPDATE Task SET status = % s, done_time = % s WHERE id = % s", ("Done", done_time, id, ))
                    mysql.connection.commit()
                    message = 'Task successfully marked as done!'
                else:
                    message = 'This task is already finished!'
    
    return render_template('finish.html', message = message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
