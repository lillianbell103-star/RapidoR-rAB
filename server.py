#!/usr/bin/env python3
"""
Rapido Rör AB – Lead Capture API Server
Runs on port 5000. Accepts POST /api/lead and saves to leads.json.
Also serves the static website files (index.html, admin.html) on the same port.
"""

import json
import os
import re
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'leads.json')
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

def load_leads():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_leads(leads):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

def serve_static(path):
    """Serve static files from STATIC_DIR."""
    # Default to index.html
    if path == '' or path == '/':
        path = 'index.html'
    else:
        path = path.lstrip('/')
    
    # Security: only allow .html, .js, .css, .png, .jpg, .svg, .ico, .json
    allowed_ext = ('.html', '.js', '.css', '.png', '.jpg', '.jpeg', '.svg', '.ico', '.json', '.txt')
    if not any(path.endswith(ext) for ext in allowed_ext):
        return None, None
    
    filepath = os.path.join(STATIC_DIR, path)
    # Prevent directory traversal
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(STATIC_DIR)):
        return None, None
    
    if os.path.isfile(real_path):
        with open(real_path, 'rb') as f:
            content = f.read()
        ext_map = {
            '.html': 'text/html; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.json': 'application/json; charset=utf-8',
            '.txt': 'text/plain; charset=utf-8',
        }
        ext = os.path.splitext(path)[1].lower()
        content_type = ext_map.get(ext, 'application/octet-stream')
        return content, content_type
    
    return None, None


class LeadHandler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API health check
        if path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'leads_file': DATA_FILE,
                'leads_count': len(load_leads())
            }, ensure_ascii=False).encode('utf-8'))
            return
        
        # API: get leads (requires password)
        if path == '/api/leads':
            query = parsed.query
            params = {}
            if query:
                for part in query.split('&'):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        params[k] = v
            password = params.get('password', '')
            if password != 'rapido2025':
                self.send_response(401)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Unauthorized'}).encode())
                return
            
            leads = load_leads()
            # Reverse so newest first
            leads.reverse()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'leads': leads, 'total': len(leads)}, ensure_ascii=False).encode('utf-8'))
            return
        
        # Serve static files
        content, content_type = serve_static(path)
        if content is not None:
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b'<h1>404 Not Found</h1>')
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/api/lead':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(body)
            except:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'errors': ['Invalid JSON']}).encode())
                return
            
            # Validate
            errors = []
            name = (data.get('name') or '').strip()
            phone = (data.get('phone') or '').strip()
            email = (data.get('email') or '').strip()
            
            if not name:
                errors.append('name is required')
            if not phone:
                errors.append('phone is required')
            if not email:
                errors.append('email is required')
            elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                errors.append('email is invalid')
            
            if errors:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'errors': errors}).encode())
                return
            
            # Save lead
            leads = load_leads()
            lead = {
                'id': int(datetime.now().timestamp() * 1000),
                'name': name,
                'phone': phone,
                'email': email,
                'service': data.get('service', ''),
                'message': data.get('message', ''),
                'source': data.get('source', 'website'),
                'created_at': datetime.now().isoformat()
            }
            leads.append(lead)
            save_leads(leads)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'message': 'Tack! Din förfrågan har mottagits. Vi återkommer inom 30 minuter.'
            }, ensure_ascii=False).encode('utf-8'))
            return
        
        self.send_response(404)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps({'error': 'Not found'}).encode())
    
    def log_message(self, format, *args):
        """Silence default logging; use print for important messages."""
        if '/api/' in args[0]:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    port = 5000
    host = '0.0.0.0'
    
    # Ensure leads.json exists
    if not os.path.exists(DATA_FILE):
        save_leads([])
    
    print(f"🌸 Rapido Rör API Server")
    print(f"   Website:     http://localhost:{port}")
    print(f"   Admin:       http://localhost:{port}/admin.html")
    print(f"   API:         POST http://localhost:{port}/api/lead")
    print(f"   Leads file:  {DATA_FILE}")
    print(f"   Press Ctrl+C to stop.\n")
    
    server = HTTPServer((host, port), LeadHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == '__main__':
    main()