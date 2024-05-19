from flask import *
import bcrypt
import psycopg2
import urllib


app = Flask(__name__)

# PostgreSQL configuration
username = "postgres.dnwjgeuyjcopiwjpbygs"
password = "3,dq5?C%pZJ,vX9"  # Your Supabase password
hostname = "aws-0-ap-southeast-1.pooler.supabase.com"
port = "5432"
database_name = "postgres"

# Properly encode the password
encoded_password = urllib.parse.quote(password, safe='')

# Construct the connection string
supabase_connection_string = f"postgres://{username}:{encoded_password}@{hostname}:{port}/{database_name}"


def create_tables():
    # Opening a connection to our database
    connection = psycopg2.connect(supabase_connection_string)

    cursor = connection.cursor()

    # SQL queries for creating tables
    create_account_table = """
    CREATE TABLE IF NOT EXISTS ACCOUNT (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        firstname VARCHAR(50) NOT NULL,
        middlename VARCHAR(50),
        lastname VARCHAR(100) NOT NULL,
        email VARCHAR(50) NOT NULL UNIQUE,
        user_type VARCHAR(10) NOT NULL CHECK (user_type IN ('customer', 'owner')),
        password_ VARCHAR(255) NOT NULL
    )
    """

    create_establishment_table = """
    CREATE TABLE IF NOT EXISTS ESTABLISHMENT (
        establishment_id SERIAL PRIMARY KEY,
        address_location VARCHAR(100) NOT NULL UNIQUE,
        establishment_name VARCHAR(50) NOT NULL UNIQUE,
        average_rating DECIMAL(3,2)
    )
    """

    create_food_table = """
    CREATE TABLE IF NOT EXISTS FOOD (
        food_id SERIAL PRIMARY KEY,
        foodname VARCHAR(80) NOT NULL UNIQUE,
        price DECIMAL(10,2) NOT NULL,
        food_type VARCHAR(20) NOT NULL CHECK (food_type IN ('meat','vegetable','seafood','dessert','beverage')),
        average_rating DECIMAL(3,2),
        establishment_id INT NOT NULL,
        CONSTRAINT food_establishment_fk FOREIGN KEY (establishment_id) 
            REFERENCES ESTABLISHMENT(establishment_id)
    )
    """

    create_establishment_review_table = """
    CREATE TABLE IF NOT EXISTS ESTABLISHMENT_REVIEW (
        review_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        establishment_id INT NOT NULL,
        rating DECIMAL(3,2) NOT NULL,
        establishment_review VARCHAR(255),
        review_datetime TIMESTAMP NOT NULL,
        CONSTRAINT est_review_user_fk FOREIGN KEY (user_id) 
            REFERENCES ACCOUNT(user_id),
        CONSTRAINT est_review_establishment_fk FOREIGN KEY (establishment_id) 
            REFERENCES ESTABLISHMENT(establishment_id)
    )
    """

    create_food_review_table = """
    CREATE TABLE IF NOT EXISTS FOOD_REVIEW (
        review_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        food_id INT NOT NULL,
        rating DECIMAL(3,2) NOT NULL,
        food_review VARCHAR(255),
        review_datetime TIMESTAMP NOT NULL,
        CONSTRAINT fd_review_user_fk FOREIGN KEY (user_id)
            REFERENCES ACCOUNT(user_id),
        CONSTRAINT fd_review_food_fk FOREIGN KEY (food_id)
            REFERENCES FOOD(food_id)
    )
    """

    # Execute the SQL queries
    cursor.execute(create_account_table)
    cursor.execute(create_establishment_table)
    cursor.execute(create_food_table)
    cursor.execute(create_establishment_review_table)
    cursor.execute(create_food_review_table)

    # Commit changes and close connection
    connection.commit()
    connection.close()

# Call the function to create tables
create_tables()

# Sign up user account (Create)
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template("SignUp.html")
    elif request.method == 'POST':
        # Get data from form in signup.html
        username = request.form.get("username")
        password = request.form.get("password")
        firstname = request.form.get("firstname")
        middlename = request.form.get("middlename")
        lastname = request.form.get("lastname")
        email = request.form.get("email")
        user_type = request.form.get("usertype")

        # Check if any required field is empty
        if not username or not password or not firstname or not lastname or not email or not user_type:
            return "All fields are required."
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Convert the hashed password bytes to string for storage in the database
        hashed_password_str = hashed_password.decode('utf-8')

        # Open a connection to project database
        connection = psycopg2.connect(supabase_connection_string)
        cursor = connection.cursor()

        # Check if the account already exists
        check_user_sql = "SELECT * FROM ACCOUNT WHERE username = %s OR email = %s"
        cursor.execute(check_user_sql, (username, email))
        existing_user = cursor.fetchone()

        # If username or email already exists, close connection
        if existing_user:
            connection.close()
            return "Account already exists."
        # Else add new user
        else: 
            add_user_sql = "INSERT INTO ACCOUNT (username, firstname, middlename, lastname, email, user_type, password_) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(add_user_sql, (username, firstname, middlename, lastname, email, user_type, hashed_password_str))
            connection.commit()
            connection.close()
            return "New account created."

# Login user account (Read)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("Login.html")
    elif request.method == 'POST':
        # Get data from form in login.html
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return "All fields are required."
        
        # Open a connection to project database
        connection = psycopg2.connect(supabase_connection_string)
        cursor = connection.cursor()

        # Check if the account exists
        check_user_sql = "SELECT * FROM ACCOUNT WHERE username = %s"
        cursor.execute(check_user_sql, (username,))
        existing_user = cursor.fetchone()

        # If account does not exist, close connection
        if not existing_user:
            connection.close()
            return "Account does not exist."
        # Else verify password
        else:
            stored_password = existing_user[6] # Index 6 corresponds to the password_ field
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                connection.close()
                return "Login Success."
            else:
                connection.close()
                return "Login Failed."

# See all user accounts (Read)
@app.route('/admin/user-list', methods=['GET'])
def see_users():
    connection = psycopg2.connect(supabase_connection_string)
    cursor = connection.cursor()
    cursor.execute("SELECT user_id, username, email, user_type, firstname, middlename, lastname FROM ACCOUNT")
    users = cursor.fetchall()
    connection.close()
    return render_template("UserList.html", users=users)

# Update user account
@app.route('/admin/edit-user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    if request.method == 'GET':
        connection = psycopg2.connect(supabase_connection_string)
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, username, email, user_type, firstname, middlename, lastname FROM ACCOUNT WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        connection.close()
        return render_template('EditUser.html', user=user)
    elif request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        user_type = request.form['user_type']
        firstname = request.form['firstname']
        middlename = request.form['middlename']
        lastname = request.form['lastname']
        
        connection = psycopg2.connect(supabase_connection_string)
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE ACCOUNT
            SET username = %s, email = %s, user_type = %s, firstname = %s, middlename = %s, lastname = %s
            WHERE user_id = %s
        """, (username, email, user_type, firstname, middlename, lastname, user_id))
        connection.commit()
        connection.close()
        return redirect(url_for('see_users'))

# Delete user account
@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    connection = psycopg2.connect(supabase_connection_string)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM ACCOUNT WHERE user_id = %s", (user_id,))
    connection.commit()
    connection.close()
    return redirect(url_for('see_users'))

# Create food establishment
@app.route('/admin/add-establishment', methods=['GET', 'POST'])
def add_est():
    if request.method == 'GET':
        return render_template("AddEst.html")
    elif request.method == 'POST':
        # Get data from form in AddEst.html
        est_name = request.form.get("est_name")
        ave_rating = 0.0
        addr_loc = request.form.get("addr_loc")
        
        # Check if any required field is empty
        if not est_name or not addr_loc:
            return "All fields are required."
        
        # Open a connection to project database
        connection = psycopg2.connect(supabase_connection_string)
        cursor = connection.cursor()

        # Check if the establishment already exists
        check_est_sql = "SELECT * FROM ESTABLISHMENT WHERE establishment_name = %s OR address_location = %s"
        cursor.execute(check_est_sql, (est_name, addr_loc))
        existing_est = cursor.fetchone()

        # If establishment already exists, close connection
        if existing_est:
            connection.close()
            return "Establishment already exists."
        # Else add new establishment
        else:
            add_est_sql = "INSERT INTO ESTABLISHMENT (address_location, establishment_name, average_rating) VALUES (%s, %s, %s)"        
            cursor.execute(add_est_sql, (addr_loc, est_name, ave_rating))
            connection.commit()
            connection.close()
            return redirect(url_for('see_est'))

# Read food establishment
@app.route('/admin/establishment-list', methods=['GET'])
def see_est():
    connection = psycopg2.connect(supabase_connection_string)
    cursor = connection.cursor()
    cursor.execute("SELECT establishment_id, establishment_name, address_location, average_rating FROM ESTABLISHMENT")
    establishments = cursor.fetchall()
    connection.close()
    return render_template("EstList.html", establishments=establishments)

# Update food establishment
@app.route('/admin/edit-establishment/<int:establishment_id>', methods=['GET', 'POST'])
def edit_est(establishment_id):
    if request.method == 'GET':
        connection = psycopg2.connect(supabase_connection_string)
        cursor = connection.cursor()
        cursor.execute("SELECT establishment_id, establishment_name, address_location, average_rating FROM ESTABLISHMENT WHERE establishment_id = %s", (establishment_id,))
        establishment = cursor.fetchone()
        connection.close()
        return render_template('EditEst.html', establishment=establishment)
    elif request.method == 'POST':
        est_name = request.form['est_name']
        addr_loc = request.form['addr_loc']
        ave_rating = request.form['ave_rating']
        
        connection = psycopg2.connect(supabase_connection_string)
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE ESTABLISHMENT
            SET establishment_name = %s, address_location = %s, average_rating = %s
            WHERE establishment_id = %s
        """, (est_name, addr_loc, ave_rating, establishment_id))
        connection.commit()
        connection.close()
        return redirect(url_for('see_est'))

# Delete food establishment
@app.route('/admin/delete-establishment/<int:establishment_id>', methods=['POST'])
def delete_est(establishment_id):
    connection = psycopg2.connect(supabase_connection_string)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM ESTABLISHMENT WHERE establishment_id = %s", (establishment_id,))
    connection.commit()
    connection.close()
    return redirect(url_for('see_est'))

# Create food item 

# Read food item

# Update food item

# Delete food item

if __name__ == "__main__":
    app.run(debug=True, port=3002)