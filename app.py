"""
NEXUS — Flask Backend
Chạy file này để có Python Runner hoạt động:
  pip install flask flask-cors
  python app.py
Sau đó mở: http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess, sys, os, tempfile, json

app = Flask(__name__, static_folder='.')
CORS(app)

# Giới hạn bảo mật
MAX_CODE_LENGTH = 5000
TIMEOUT_SECONDS = 10

# Danh sách module bị cấm (bảo mật)
BLOCKED = [
    'os.system', 'subprocess', 'shutil.rmtree',
    '__import__("os")', 'open("/etc', 'open("/proc',
    'socket', 'requests.get("http://internal'
]


def is_safe(code: str) -> tuple[bool, str]:
    """Kiểm tra code có chứa lệnh nguy hiểm không."""
    code_lower = code.lower()
    danger_patterns = [
        ('import socket', 'Module socket bị hạn chế'),
        ('os.remove(', 'Xóa file bị hạn chế'),
        ('shutil.rmtree', 'Xóa thư mục bị hạn chế'),
        ('os.system(', 'Shell command bị hạn chế'),
        ('subprocess.', 'subprocess bị hạn chế'),
    ]
    for pattern, msg in danger_patterns:
        if pattern.lower() in code_lower:
            return False, f'⛔ Bị chặn: {msg}'
    return True, ''


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/admin.html')
def admin():
    return send_from_directory('.', 'admin.html')


@app.route('/run', methods=['POST'])
def run_code():
    """Nhận code Python, chạy an toàn và trả về output."""
    try:
        data = request.get_json(force=True)
        code = data.get('code', '').strip()

        if not code:
            return jsonify({'error': 'Không có code để chạy!'}), 400

        if len(code) > MAX_CODE_LENGTH:
            return jsonify({'error': f'Code quá dài! Tối đa {MAX_CODE_LENGTH} ký tự.'}), 400

        safe, msg = is_safe(code)
        if not safe:
            return jsonify({'error': msg}), 400

        # Tạo file tạm để chạy
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py',
            delete=False, encoding='utf-8'
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                encoding='utf-8',
                errors='replace'
            )
            output = result.stdout
            error  = result.stderr

            if error and not output:
                return jsonify({'error': error})
            elif error:
                return jsonify({'output': output, 'warning': error})
            else:
                return jsonify({'output': output or '(Chạy thành công, không có output)'})

        except subprocess.TimeoutExpired:
            return jsonify({'error': f'⏰ Timeout: Code chạy quá {TIMEOUT_SECONDS}s!'})
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except Exception as e:
        return jsonify({'error': f'Lỗi server: {str(e)}'}), 500


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'python': sys.version,
        'server': 'NEXUS Flask Backend v1.0'
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"""
╔══════════════════════════════════════╗
║        NEXUS Backend Server          ║
╠══════════════════════════════════════╣
║  Trang chủ:  http://localhost:{port}   ║
║  Admin:      http://localhost:{port}/admin.html ║
║  Health:     http://localhost:{port}/health     ║
╚══════════════════════════════════════╝

Nhấn Ctrl+C để dừng server.
""")
    app.run(debug=True, host='0.0.0.0', port=port)
