from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import os
import sqlite3
import random
import string
import json
import bcrypt

app = Flask(__name__, static_url_path='/static')
app.secret_key = 'BAD_SECRET_KEY'
#''.join(random.choice(string.ascii_letters) for i in range(30))

app.config['PERMANENT_SESSION_LIFETIME'] = 900 # session expiry time
app.config['SESSION_REFRESH_EACH_REQUEST'] = True # reloads expiry time after every request
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif'] # specifies file extensions for uploads

def get_db_connection():
    return sqlite3.connect("app.db", check_same_thread=False) 

def check_uploaded_file(file):
    if file.filename != '':
        file_ext = os.path.splitext(file.filename)[1]
        if file_ext not in app.config['UPLOAD_EXTENSIONS']:
            return ''
        else:
            fnlength = 16
            counter=1
            new_filename = ''.join(random.choice(string.ascii_lowercase) for i in range(fnlength)) + file_ext
            while os.path.exists(os.path.join('static/uploads'), new_filename):
                new_filename = os.path.join(f"{os.path.split(new_filename)[0]}_{counter}{file_ext}")
                counter += 1
            file.save(os.path.join('static/uploads', new_filename))
            return new_filename
        
def get_total_cost():
    conn = get_db_connection()
    cursor = conn.cursor()

    totalcost = 0

    for item in session['basket'].items():
        cursor.execute(f"SELECT price FROM products WHERE itemid = {item[0]} LIMIT 1;")
        resp = cursor.fetchone()
        totalcost += (int(resp[0]) * item[1])
    
    return totalcost



@app.before_request
def initialize_session():
    if "basket" not in session:
        session["basket"] = {}

@app.after_request
def add_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' cdn.jsdelivr.net 'unsafe-inline';"
        "style-src 'self' cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "frame-ancestors 'none';"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.context_processor
def inject_session():
    return dict(session=session)

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/admin/uploadShopItem', methods=['GET','POST'])
def uploadItem():
    # check if admin

    if request.method == 'POST':

        name = request.form.get('name')
        description = request.form.get('description')
        price = int(request.form.get('price'))
        stock = int(request.form.get('stock'))
        image_data = request.files.get('image')

        imagename = check_uploaded_file(image_data)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO products(name, description, price, stock, image) VALUES (?, ?, ?, ?, ?);", (name, description, price, stock, imagename))
            conn.commit()
        except sqlite3.Error as e:
            print("Database Error:", e)
        finally:
            conn.close()

    return render_template('addProduct.html')

@app.route('/api/products', methods=['GET'])
def getProducts():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT itemid, name, price, image FROM products;")
        products = [
            {"itemid": row[0], "name": row[1], "price": row[2], "image": row[3]}
            for row in cursor.fetchall()
        ]
        products.reverse()
        return jsonify(products)
    except sqlite3.Error as e:
        print("Database Error:", e)
    finally:
        conn.close()
    
    return None

@app.route('/product', methods=['GET'])
def displayProduct():
    id = request.args.get('id')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(f"SELECT * FROM products WHERE itemid = ? LIMIT 1;", (id,))
        resp = cursor.fetchone()
        if resp:
            return render_template('product.html',
                                id=resp[0],
                                name=resp[1],
                                description=resp[2],
                                price="{:0.2f}".format(resp[3]/100),
                                stock=resp[4],
                                image=resp[5])
        else:
            return redirect('/')
    except sqlite3.Error as e:
        print("Database Error:", e)
        return redirect('/')
    finally:
        conn.close()



@app.route('/basket', methods=["GET", "POST"])
def basket():
    if request.method == "POST":
        itemid = request.form.get('itemid')
        quantity = request.form.get('quantity', None)
        if not quantity:
            new_quantity = request.form.get('new_quantity', None)
            if new_quantity:
                session['basket'][itemid] = int(new_quantity)
        else:
            session['basket'][itemid] = session['basket'].get(itemid, 0) + int(quantity)

        session.modified = True


    conn = get_db_connection()
    cursor = conn.cursor()

    basketItems = []
    currentBasket = session['basket'].copy() # allows for deletion in the method below
    
    try:
        for item in currentBasket.items():
            if int(item[1]) < 1:
                session['basket'].pop(item[0])
            else:
                cursor.execute(f"SELECT name, price, image, itemid, stock FROM products WHERE itemid={item[0]} LIMIT 1;")
                resp = cursor.fetchone()
                if int(item[1]) > resp[4]:
                    final = resp[4]
                    session['basket'][item[0]] = final
                else:
                    final = int(item[1])
                basketItems.append((*resp, final))
    except sqlite3.Error as e:
        print("Database Error:", e)
    finally:
        conn.close()

    cost = get_total_cost()

    return render_template('basket.html', items=json.dumps(basketItems), cost=cost)

@app.route('/login', methods=["GET", "POST"])
def login():
    if 'username' in session and 'privilege' in session:
        return redirect('/')
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT hash, privilege FROM users WHERE username = ?;", (username,))
            resp = cursor.fetchone()
            if not resp:
                return render_template('login.html', msg="Error: incorrect username or password")
            pswdBytes = password.encode('utf-8')
            result = bcrypt.checkpw(pswdBytes, resp[0])
            if not result:
                return render_template('login.html', msg="Error: Incorrect Username or Password")
            else:
                session['privilege'] = resp[1]
                session['username'] = username
                return redirect('/')
        except sqlite3.Error as e:
            print("Database Error:", e)
            return render_template('login.html', msg="Error: incorrect username or password")
        finally:
            conn.close()

    return render_template('login.html')

@app.route('/register', methods=["POST", "GET"])
def register():
    if 'username' in session and 'privilege' in session:
        return redirect('/')
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        cpassword = request.form.get('cpassword')
        if password != cpassword:
            return render_template('register.html', msg="Error: passwords do not match")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(f"SELECT 1 FROM users WHERE username = ? LIMIT 1;", (username,))
                resp = cursor.fetchone()
                if resp:
                    return render_template('register.html', msg="Error: username already exists")
                else:
                    pswdBytes = password.encode('utf-8')
                    salt = bcrypt.gensalt()
                    hash = bcrypt.hashpw(pswdBytes, salt) 
                    cursor.execute(f"INSERT INTO users (username, hash, privilege) VALUES (?, ?, ?);", (username, hash, "user"))
                    conn.commit()
                    conn.close()
                    return render_template('register.html', msg="Account successfully created! Please log in")
            except sqlite3.Error as e:
                print("Database Error:", e)
                conn.close()
                return render_template('register.html', msg="Error: incorrect username or password")
    return render_template('register.html')  

@app.route('/logout', methods=["GET"])
def logout():
    session.pop('username', None)
    session.pop('privilege', None)
    return redirect('/')

@app.route('/checkout', methods=["GET", "POST"])
def checkout():
    if 'username' not in session or 'privilege' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        addr_l1 = request.form.get("addr_l1", "")
        addr_l2 = request.form.get("addr_l2", "")
        addr_l3 = request.form.get("addr_l3", "")
        addr_city = request.form.get("addr_city", "")
        addr_county = request.form.get("addr_county", "")
        addr_postcode = request.form.get("addr_postcode", "")
        payment_num = request.form.get("payment_num", "")
        payment_exp = request.form.get("payment_exp", "")
        payment_exp = request.form.get("payment_exp", "")
        payment_cvv = request.form.get("payment_cvv", "")

        conn = get_db_connection()
        cursor = conn.cursor()

        if request.form.get('save_address') == "on":
            addr_save = 1
            cursor.execute("UPDATE users SET addr_l1 = ?, addr_l2 = ?, addr_l3 = ?, addr_city = ?, addr_county = ?, addr_postcode = ?, addr_save = 1 WHERE username = ?;", (addr_l1, addr_l2, addr_l3, addr_city, addr_county, addr_postcode, session['username']))
            # save address

        if request.form.get('save_payment') == "on":
            payment_save = 1
            cursor.execute("UPDATE users SET payment_num = ?, payment_exp = ?, payment_save = 1 WHERE username = ?;", (payment_num, payment_exp, session['username']))
            # save payment details, except cvv


        # this is where you would process the payment on an actual e-commerce store

        # add to orders database
        cursor.execute("SELECT userid FROM users WHERE username = ? LIMIT 1;", (session['username'],))
        
        resp = cursor.fetchone()
        userid = resp[0]

        cost = get_total_cost()

        address_parts = [value for key, value in request.form.items() if key.startswith("addr_") and value.strip()]
        address =  ", ".join(address_parts)

        cursor.execute("INSERT INTO orders (userid, address, cost, status) VALUES (?, ?, ?, ?)", (userid, address, cost, "ORDERED"))
        resp = cursor.lastrowid


        # add to orderitems
        for item in session['basket'].items():
            cursor.execute("INSERT INTO orderitems (orderid, productid, quantity) VALUES (?, ?, ?)", (str(resp), item[0], item[1]))
            cursor.execute("UPDATE products SET stock = stock - ? WHERE itemid = ?;", (item[1], item[0]))

        conn.commit()

    basketItems = []


    for item in session['basket'].items():
        cursor.execute(f"SELECT itemid, name, price, image, stock FROM products WHERE itemid={item[0]} LIMIT 1;")
        row = cursor.fetchone()

        basketItems.append({"itemid": row[0], "name": row[1], "price": row[2], "image": row[3], "stock": row[4], "quantity": item[1]})

    cursor.execute(f"SELECT addr_l1, addr_l2, addr_l3, addr_city, addr_county, addr_postcode, addr_save, payment_num, payment_exp, payment_save FROM users WHERE username = '{session['username']}' LIMIT 1;")
    resp = cursor.fetchone()
    resp = tuple("" if value is None else value for value in resp) if resp else None
    
    
    subtotal = "{:0.2f}".format(get_total_cost()/100)

    conn.close()

    if request.method == "POST":
        session['basket'] = {}
        state = "confirmed"
    else:
        state = "unconfirmed"

    return render_template('checkout.html', addr_l1=resp[0], addr_l2=resp[1], addr_l3=resp[2], addr_city=resp[3], addr_county=resp[4], addr_postcode=resp[5], addr_save=resp[6], payment_num=resp[7], payment_exp=resp[8], payment_save=resp[9], basketItems=basketItems, subtotal=subtotal, state=state)

@app.route('/account', methods=["GET"])
def account():
    
    conn = get_db_connection()
    cursor = conn.cursor()

    orders = [
            {"orderid": row[0], "placed_at": row[1], "address": row[2], "cost": row[3], "status": row[4], }
            for row in cursor.fetchall()
        ]


if __name__ == "__main__":
    app.run()