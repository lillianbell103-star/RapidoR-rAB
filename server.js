const http = require('http');
const { execSync } = require('child_process');

const PORT = 3001;
const HOST = '0.0.0.0';

function escapeQuotes(val) {
  if (typeof val !== 'string') return '';
  return val.replace(/'/g, "''");
}

function insertLead(data) {
  const { name, phone, email, service, message, source } = data;
  const nameEsc = escapeQuotes(name || '');
  const phoneEsc = escapeQuotes(phone || '');
  const emailEsc = escapeQuotes(email || '');
  const serviceEsc = escapeQuotes(service || '');
  const msgEsc = escapeQuotes(message || '');
  const srcEsc = escapeQuotes(source || 'website');

  const sql = `INSERT INTO leads (name, phone, email, service, message, source) VALUES ('${nameEsc}', '${phoneEsc}', '${emailEsc}', '${serviceEsc}', '${msgEsc}', '${srcEsc}')`;
  
  try {
    const out = execSync(`team-db "${sql.replace(/"/g, '\\"')}"`, {
      encoding: 'utf8',
      timeout: 10000
    });
    return { success: true, output: out.trim() };
  } catch (err) {
    return { success: false, error: err.stderr || err.message };
  }
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        resolve(JSON.parse(body));
      } catch {
        // Also try URL-encoded
        const params = new URLSearchParams(body);
        const obj = {};
        for (const [k, v] of params) obj[k] = v;
        resolve(obj);
      }
    });
    req.on('error', reject);
  });
}

const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Health check
  if (req.method === 'GET' && req.url === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }));
    return;
  }

  // Lead capture endpoint
  if (req.method === 'POST' && req.url === '/api/lead') {
    try {
      const body = await parseBody(req);
      
      // Validate required fields
      const errors = [];
      if (!body.name || !body.name.trim()) errors.push('name is required');
      if (!body.phone || !body.phone.trim()) errors.push('phone is required');
      if (!body.email || !body.email.trim()) errors.push('email is required');
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email)) errors.push('email is invalid');

      if (errors.length > 0) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, errors }));
        return;
      }

      const result = insertLead({
        name: body.name.trim(),
        phone: body.phone.trim(),
        email: body.email.trim(),
        service: body.service || '',
        message: body.message || '',
        source: body.source || 'website'
      });

      if (result.success) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          message: 'Tack! Din förfrågan har mottagits. Vi återkommer inom 30 minuter.'
        }));
      } else {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: 'Database error', detail: result.error }));
      }
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
    return;
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, HOST, () => {
  console.log(`Rapido Rör API server running on http://${HOST}:${PORT}`);
});