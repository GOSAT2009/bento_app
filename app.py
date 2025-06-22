from flask import Flask, render_template, request, redirect, session, url_for, flash, send_file
from werkzeug.utils import secure_filename
import os, json, datetime, csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# パス設定
DATA_DIR = 'data'
ORDERS_DIR = os.path.join(DATA_DIR, 'orders')
MENU_FILE = os.path.join(DATA_DIR, 'products.json')
PASSWORD_FILE = os.path.join(DATA_DIR, 'admin_password.txt')
UPLOAD_FOLDER = os.path.join('static', 'uploads')

# 必要なフォルダ作成
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ORDERS_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初期データ
if not os.path.exists(MENU_FILE):
    with open(MENU_FILE, 'w', encoding='utf-8') as f:
        json.dump({"bento": [], "bread": []}, f, ensure_ascii=False, indent=2)

if not os.path.exists(PASSWORD_FILE):
    with open(PASSWORD_FILE, 'w', encoding='utf-8') as f:
        f.write('admin')

# ヘルパー関数
def get_today_str():
    return datetime.date.today().isoformat()

def load_products():
    with open(MENU_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_products(data):
    with open(MENU_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_orders(date_str):
    path = os.path.join(ORDERS_DIR, f'{date_str}.json')
    if not os.path.exists(path): return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_orders(date_str, orders):
    path = os.path.join(ORDERS_DIR, f'{date_str}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def save_image(file):
    if file and file.filename:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        return filename
    return None

def load_password():
    with open(PASSWORD_FILE, 'r', encoding='utf-8') as f:
        return f.read().strip()

def save_password(new_pw):
    with open(PASSWORD_FILE, 'w', encoding='utf-8') as f:
        f.write(new_pw)

# ------------------ 利用者向け ------------------

@app.route('/')
def index():
    return redirect(url_for('user_top'))

@app.route('/user_top')
def user_top():
    data = load_products()
    bento_menu = [b for b in data['bento'] if b.get('show_today')]
    bread_menu = [b for b in data['bread'] if b.get('show_today')]
    return render_template('user_top.html', bento_menu=bento_menu, bread_menu=bread_menu)

@app.route('/order', methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        date_str = get_today_str()
        orders = load_orders(date_str)
        new_order = {
            "id4": f"{int(request.form['grade'])}{int(request.form['class'])}{int(request.form['number']):02d}",
            "grade": int(request.form['grade']),
            "class": int(request.form['class']),
            "number": int(request.form['number']),
            "name": request.form['name'],
            "bento": request.form.getlist('bento'),
            "bread": request.form.getlist('bread'),
            "total_price": float(request.form['total_price'])
        }
        orders.append(new_order)
        save_orders(date_str, orders)
        session['last_order'] = new_order
        return redirect('/order_done')
    data = load_products()
    return render_template('order.html',
        bento_menu=[b for b in data['bento'] if b.get('show_today')],
        bread_menu=[b for b in data['bread'] if b.get('show_today')]
    )

@app.route('/order_confirm', methods=['POST'])
def order_confirm():
    return render_template('confirm.html', form=request.form)

@app.route('/order_done')
def order_done():
    order = session.get('last_order')
    if not order: return redirect('/user_top')
    return render_template('done.html', order=order)

# ------------------ 管理者向け ------------------

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == load_password():
            session['admin'] = True
            return redirect('/admin_top')
        flash('パスワードが間違っています', 'error')
    return render_template('admin_login.html')

@app.route('/admin_top')
def admin_top():
    if not session.get('admin'): return redirect('/admin_login')
    return render_template('admin_top.html', today=get_today_str())

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/admin_login')

@app.route('/bento_register', methods=['GET', 'POST'])
def bento_register():
    if not session.get('admin'): return redirect('/admin_login')
    data = load_products()
    if request.method == 'POST':
        idx = request.form.get('bento_index')
        name = request.form['name']
        price = float(request.form['price'])
        show_today = 'show_today' in request.form
        img_filename = save_image(request.files.get('image'))
        if idx:
            item = data['bento'][int(idx)]
            item.update({"name": name, "price": price, "show_today": show_today})
            if img_filename: item['image'] = img_filename
        else:
            new_item = {"name": name, "price": price, "show_today": show_today}
            if img_filename: new_item['image'] = img_filename
            data['bento'].append(new_item)
        save_products(data)
        return redirect('/bento_register')
    return render_template('bento_register.html', bento_list=data['bento'])

@app.route('/bread_register', methods=['GET', 'POST'])
def bread_register():
    if not session.get('admin'): return redirect('/admin_login')
    data = load_products()
    if request.method == 'POST':
        idx = request.form.get('bread_index')
        name = request.form['name']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        show_today = 'show_today' in request.form
        img_filename = save_image(request.files.get('image'))
        if idx:
            item = data['bread'][int(idx)]
            item.update({"name": name, "price": price, "quantity": quantity, "show_today": show_today})
            if img_filename: item['image'] = img_filename
        else:
            new_item = {"name": name, "price": price, "quantity": quantity, "show_today": show_today}
            if img_filename: new_item['image'] = img_filename
            data['bread'].append(new_item)
        save_products(data)
        return redirect('/bread_register')
    return render_template('bread_register.html', bread_list=data['bread'])

@app.route('/order_check', methods=['GET'])
def order_check():
    if not session.get('admin'): return redirect('/admin_login')
    date_str = request.args.get('date') or get_today_str()
    orders = load_orders(date_str)
    data = load_products()
    bento_counts = {b['name']: 0 for b in data['bento']}
    bread_counts = {b['name']: 0 for b in data['bread']}
    for o in orders:
        for b in o.get('bento', []): bento_counts[b] += 1
        for br in o.get('bread', []): bread_counts[br] += 1
    return render_template('order_check.html',
        date=date_str, orders=orders,
        bento_counts=bento_counts, bread_counts=bread_counts)

@app.route('/delete_order/<date_str>/<int:index>', methods=['POST'])
def delete_order(date_str, index):
    if not session.get('admin'): return redirect('/admin_login')
    orders = load_orders(date_str)
    if 0 <= index < len(orders):
        del orders[index]
        save_orders(date_str, orders)
    return redirect(url_for('order_check', date=date_str))

@app.route('/export_csv/<date_str>')
def export_csv(date_str):
    if not session.get('admin'): return redirect('/admin_login')
    orders = load_orders(date_str)
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['4桁ID', '学年', '組', '番号', '名前', '弁当(複数可)', 'パン(複数可)', '合計金額'])
    for o in orders:
        writer.writerow([
            o['id4'], o['grade'], o['class'], o['number'], o['name'],
            "|".join(o.get('bento', [])),
            "|".join(o.get('bread', [])),
            o.get('total_price', 0)
        ])
    si.seek(0)
    return send_file(si, mimetype='text/csv', as_attachment=True,
                     download_name=f'orders_{date_str}.csv')

@app.route('/password_change', methods=['GET', 'POST'])
def password_change():
    if not session.get('admin'): return redirect('/admin_login')
    if request.method == 'POST':
        if request.form['current_password'] == load_password():
            save_password(request.form['new_password'])
            flash('パスワードを変更しました', 'success')
            return redirect('/admin_top')
        flash('現在のパスワードが違います', 'error')
    return render_template('password_change.html')


