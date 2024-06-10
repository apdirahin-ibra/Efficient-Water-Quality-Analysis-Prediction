from flask import Flask, render_template, request, session, redirect, url_for
import numpy as np
import os
import pickle
import mysql.connector

app = Flask(__name__)
app.secret_key = "xtay6UY&"

mysql_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "waterquality",
}

def connect_db():
    return mysql.connector.connect(**mysql_config)

@app.route('/index', methods=['GET', 'POST'])
def home():

    if request.method == "POST":
        # Request all the input fields
        ph = float(request.form['ph value'])
        Hardness = float(request.form['Hardness'])
        Solids = float(request.form['Solids'])
        Chloramines = float(request.form['Chloramines'])
        Sulfate = float(request.form['Sulfate'])
        Conductivity = float(request.form['Conductivity'])
        Organic_carbon = float(request.form['Organic carbon'])
        Trihalomethanes = float(request.form['Trihalomethanes'])
        Turbidity = float(request.form['Turbidity'])

        # Create numpy array for all the inputs
        val = np.array([ph, Hardness, Solids, Chloramines, Sulfate, Conductivity, Organic_carbon, Trihalomethanes, Turbidity])

        # Define save model and scaler path
        model_path = os.path.join('models', 'model_svm.pkl')
        scaler_path = os.path.join('models', 'scaler.sav')

        # Load the model and scaler
        model = pickle.load(open(model_path, 'rb'))
        scc = pickle.load(open(scaler_path, 'rb'))

        # Transform the input data using pre-fitted standard scaler
        data = scc.transform([val])

        # Make a prediction for the given data
        res = model.predict(data)

        # Weight Ratio For WQI Calculation
        ph_weight_rel = 0.19047619047619047619047619047619  # 4
        hardness_weight_rel = 0.0952380952380952380952380952381  # 2
        solids_weight_rel = 0.0952380952380952380952380952381  # 2
        chloramines_weight_rel = 0.14285714285714285714285714285714  # 3
        sulfate_weight_rel = 0.0952380952380952380952380952381  # 2
        conductivity_weight_rel = 0.0952380952380952380952380952381  # 2
        organic_carbon_weight_rel = 0.0952380952380952380952380952381  # 2
        trihalomethanes_weight_rel = 0.0952380952380952380952380952381  # 2
        turbidity_weight_rel = 0.0952380952380952380952380952381  # 2

        # Water quality rating calculation for each parameter
        quality_rating_ph = 100 - 5 * (ph - 7)
        quality_rating_hardness = 100 - 5 * (Hardness - 50) / (450 - 50)
        quality_rating_solids = 100 - 5 * (Solids - 500) / (2000 - 500)
        quality_rating_chloramines = 100 - 5 * (Chloramines - 0.6) / (4.0 - 0.6)
        quality_rating_sulfate = 100 - 5 * (Sulfate - 200) / (400 - 200)
        quality_rating_conductivity = 100 - 5 * (Conductivity - 150) / (1500 - 150)
        quality_rating_organic_carbon = 100 - 5 * (Organic_carbon - 5) / (30 - 5)
        quality_rating_trihalomethanes = 100 - 5 * (Trihalomethanes - 20) / (80 - 20)
        quality_rating_turbidity = 100 - 5 * (Turbidity - 1) / (5 - 1)

        # Sub Index Calculation
        ph_sub_index = quality_rating_ph * ph_weight_rel
        hardness_sub_index = quality_rating_hardness * hardness_weight_rel
        solids_sub_index = quality_rating_solids * solids_weight_rel
        chloramines_sub_index = quality_rating_chloramines * chloramines_weight_rel
        sulfate_sub_index = quality_rating_sulfate * sulfate_weight_rel
        conductivity_sub_index = quality_rating_conductivity * conductivity_weight_rel
        organic_carbon_sub_index = quality_rating_organic_carbon * organic_carbon_weight_rel
        trihalomethanes_sub_index = quality_rating_trihalomethanes * trihalomethanes_weight_rel
        turbidity_sub_index = quality_rating_turbidity * turbidity_weight_rel

        # WQI Calculation as per WHO
        WQI = ph_sub_index + hardness_sub_index + solids_sub_index + chloramines_sub_index + sulfate_sub_index + conductivity_sub_index + organic_carbon_sub_index + trihalomethanes_sub_index + turbidity_sub_index

        if res == 1:
            outcome = 'Drinkable'
        else:
            outcome = 'not Drinkable'
            WQI += 300

        if WQI >= 0 and WQI <= 50:
            wqi_class = "Excellent"
            template_name = 'goodwater.html'
        elif WQI > 50 and WQI <= 100:
            wqi_class = "Good"
            template_name = 'goodwater.html'
        elif WQI > 100 and WQI <= 200:
            wqi_class = "Fair"
            template_name = 'goodwater.html'
        elif WQI > 200 and WQI <= 300:
            wqi_class = "Poor"
            template_name = 'dirtywater.html'
        elif WQI > 300 and WQI <= 400:
            wqi_class = "Very Poor"
            template_name = 'dirtywater.html'
        else:
            wqi_class = "Unsatisfactory"
            template_name = 'dirtywater.html'

        r_value = f"Water is {outcome}. \nWQI Value: {WQI}, WQI Classification: {wqi_class}"
        
        # Save the prediction to the database
        conn = connect_db()
        cursor = conn.cursor()
        sql = """
        INSERT INTO predictions (
            ph, Hardness, Solids, Chloramines, Sulfate, Conductivity, Organic_carbon, 
            Trihalomethanes, Turbidity, WQI, outcome, wqi_class
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (ph, Hardness, Solids, Chloramines, Sulfate, Conductivity, Organic_carbon, 
                  Trihalomethanes, Turbidity, WQI, outcome, wqi_class)
        cursor.execute(sql, values)
        conn.commit()
        cursor.close()
        conn.close()

        return render_template(template_name, result=r_value)
    return render_template('index.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["name"] = user["name"]
            session["username"] = user["username"]
            session['user_id'] = user['id']
            return render_template('index.html')
        else:
            return render_template("login.html", error="Invalid username or password", username=username)
    return render_template("login.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        if not name or not username or not password:
            return render_template("signup.html", error="All fields must be filled")

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user:
            cursor.close()
            conn.close()
            return render_template("signup.html", error="Username already exists", username=username)

        cursor.execute("INSERT INTO user (name, username, password) VALUES (%s, %s, %s)", (name, username, password))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route('/logout')
def logout():
    session.pop('name', None)
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == 'POST':
        return redirect(url_for('home'))
    return render_template('home.html')

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
