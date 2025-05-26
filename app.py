from flask import Flask, render_template
import qrcode
import os
import socket

app = Flask(__name__)
QR_DIR = 'static/qrcodes'
os.makedirs(QR_DIR, exist_ok=True)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def generate_qr(table_num, ip):
    url = f"http://{ip}:5000/table/{table_num}"
    img = qrcode.make(url)
    path = os.path.join(QR_DIR, f"table_{table_num}.png")
    img.save(path)
    return f"/{path}"

# QR 코드 생성 (서버 시작 전에)
local_ip = get_local_ip()
for i in range(1, 13):
    generate_qr(i, local_ip)

@app.route('/table/<int:table_id>')
def table(table_id):
    return render_template('table.html', table_id=table_id)

@app.route('/')
def index():
    return render_template('index.html', tables=range(1, 13))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
