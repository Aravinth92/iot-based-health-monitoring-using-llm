import smtplib
import datetime
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ─── CONFIGURATION ───────────────────────────────────────────────────────────
GROQ_API_KEY = "YOUR API KEY"
GROQ_MODEL   = "llama-3.1-8b-instant"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

config = {
    "alert_email":     "ALERT EMAIL",
    "sender_email":    "ADMIN EMAIL",
    "sender_password": "APP CODE",
}

readings = []
alerts   = []


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def send_alert_email(bpm, temp, bpm_status, temp_status):
    try:
        msg = MIMEMultipart()
        msg["From"]    = config["sender_email"]
        msg["To"]      = config["alert_email"]
        msg["Subject"] = "🚨 CRITICAL HEALTH ALERT – HealthSense AI"
        body = (
            f"Emergency Health Alert\n\n"
            f"Heart Rate : {bpm} BPM  ->  {bpm_status}\n"
            f"Temperature: {temp}C    ->  {temp_status}\n"
            f"Time       : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Please seek medical attention immediately if readings remain critical."
        )
        msg.attach(MIMEText(body, "plain"))
        srv = smtplib.SMTP("smtp.gmail.com", 587)
        srv.starttls()
        srv.login(config["sender_email"], config["sender_password"])
        srv.send_message(msg)
        srv.quit()
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def classify_health(bpm, temp):
    if   bpm > 120 or bpm < 40:  b_stat, b_col = "CRITICAL", "#ef4444"
    elif bpm > 100 or bpm < 60:  b_stat, b_col = "WARNING",  "#f59e0b"
    else:                         b_stat, b_col = "NORMAL",   "#10b981"

    if   temp >= 381.5:            t_stat, t_col = "CRITICAL", "#ef4444"
    elif temp < 35.0:             t_stat, t_col = "CRITICAL", "#ef4444"
    elif temp > 37.5:             t_stat, t_col = "ELEVATED", "#f59e0b"
    else:                         t_stat, t_col = "NORMAL",   "#10b981"

    return b_stat, b_col, t_stat, t_col


def groq_call(prompt, max_tokens=150):
    try:
        res = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
            },
            timeout=10,
        )
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        return "AI unavailable."


# ─── HTML ─────────────────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HealthSense AI</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg:      #0b0f19;
      --surface: #161b26;
      --deep:    #0f1422;
      --border:  #1e2740;
      --muted:   #64748b;
      --text:    #f1f5f9;
      --sub:     #94a3b8;
      --primary: #3b82f6;
      --red:     #ef4444;
      --amber:   #f59e0b;
      --green:   #10b981;
    }

    /* Lock page to viewport — no outer scroll */
    html, body {
      height: 100%;
      overflow: hidden;
    }
    body {
      font-family: 'Inter', system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      padding: 12px;
      gap: 10px;
    }

    /* Top bar */
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }
    .topbar h1 { font-size: 15px; font-weight: 700; color: var(--primary); }
    .topbar-right { display: flex; align-items: center; gap: 12px; font-size: 11px; color: var(--muted); }
    .live-pill {
      display: flex; align-items: center; gap: 5px;
      background: #10b98115; border: 1px solid #10b98130;
      border-radius: 20px; padding: 3px 10px;
      font-size: 11px; color: var(--green); font-weight: 600;
    }
    .live-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--green); animation: pulse 1.4s infinite;
    }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

    /* 3-column grid fills remaining height */
    .wrap {
      display: grid;
      grid-template-columns: 230px 1fr 260px;
      gap: 10px;
      flex: 1;
      min-height: 0;
    }

    /* Each column is a flex column, does NOT scroll itself */
    .col {
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-height: 0;
      overflow: hidden;
    }

    /* Regular card — fixed height, no scroll */
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
      flex-shrink: 0;
    }

    /* Grows to fill column; inner list scrolls */
    .card-grow {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
      flex: 1;
      min-height: 0;
      display: flex;
      flex-direction: column;
    }

    .sec-label {
      font-size: 10px; color: var(--muted);
      letter-spacing: .08em; text-transform: uppercase;
      font-weight: 600; margin-bottom: 6px;
    }
    .divider { border: none; border-top: 1px solid var(--border); margin: 8px 0; }

    /* Metric row */
    .split2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .metric {
      background: var(--deep); border: 1px solid var(--border);
      border-radius: 10px; padding: 12px;
    }
    .metric-num { font-size: 28px; font-weight: 800; line-height: 1; margin: 4px 0; }

    /* Badges */
    .badge {
      display: inline-flex; align-items: center; gap: 4px;
      font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
    }
    .b-ok   { background: #10b98118; color: var(--green); }
    .b-warn { background: #f59e0b18; color: var(--amber); }
    .b-crit { background: #ef444418; color: var(--red);   }
    .bdot   { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }

    /* Charts */
    .ct100 { position: relative; width: 100%; height: 100px; }
    .ct70  { position: relative; width: 100%; height: 70px;  }

    /* AI rec */
    .ai-rec-text { font-size: 12px; color: var(--sub); line-height: 1.6; min-height: 44px; }
    .ai-rec-footer {
      margin-top: 6px; font-size: 10px; color: var(--muted);
      display: flex; justify-content: space-between;
    }

    /* Alert scroll — the ONLY thing that scrolls in the left column */
    .notif-scroll {
      flex: 1;
      overflow-y: auto;
      min-height: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
      scrollbar-width: thin;
      scrollbar-color: var(--border) transparent;
    }
    .notif-item {
      border-left: 2px solid var(--red);
      padding: 7px 9px;
      background: var(--deep);
      border-radius: 0 7px 7px 0;
      flex-shrink: 0;     /* items don't shrink; list scrolls */
    }
    .notif-time   { font-size: 10px; color: var(--muted); }
    .notif-vals   { font-size: 12px; color: var(--text);  margin-top: 2px; }
    .notif-reason { font-size: 11px; color: var(--red);   margin-top: 2px; }
    .empty-notif  { font-size: 12px; color: var(--muted); text-align: center; padding: 16px 0; }

    .notif-cnt {
      display: inline-block; background: var(--red); color: white;
      border-radius: 20px; font-size: 10px; padding: 1px 7px;
      margin-left: 5px; font-weight: 700;
    }

    /* Toast — inside card-grow, above notif-scroll */
    .toast {
      background: #1a0e0e; border: 1px solid #7f1d1d; border-radius: 7px;
      padding: 7px 10px; font-size: 11px; color: #fca5a5; font-weight: 600;
      display: none; align-items: center; gap: 6px; margin-bottom: 6px;
      flex-shrink: 0;
    }
    .toast.show { display: flex; }

    /* Email input */
    .email-in {
      width: 100%; font-size: 11px; padding: 6px 8px;
      border-radius: 7px; border: 1px solid var(--border);
      background: var(--deep); color: var(--text);
      outline: none; margin-top: 4px;
    }
    .email-in:focus { border-color: var(--primary); }

    /* Chat */
    .chat-card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 12px;
      flex: 1; min-height: 0;
      display: flex; flex-direction: column;
    }
    .chat-body {
      flex: 1; overflow-y: auto; min-height: 0;
      display: flex; flex-direction: column; gap: 7px;
      padding-bottom: 4px;
      scrollbar-width: thin; scrollbar-color: var(--border) transparent;
    }
    .msg-ai {
      background: #1e2740; border-radius: 0 9px 9px 9px;
      padding: 8px 11px; font-size: 12px; line-height: 1.55;
      color: var(--sub); align-self: flex-start; max-width: 92%;
    }
    .msg-user {
      background: #1e3a5f; border-radius: 9px 0 9px 9px;
      padding: 8px 11px; font-size: 12px; line-height: 1.55;
      color: #93c5fd; align-self: flex-end; max-width: 92%;
    }
    .chat-input-row {
      display: flex; gap: 6px; margin-top: 8px; flex-shrink: 0;
    }
    .chat-input-row input {
      flex: 1; font-size: 12px; padding: 7px 10px;
      border-radius: 7px; border: 1px solid var(--border);
      background: var(--deep); color: var(--text); outline: none;
    }
    .chat-input-row input:focus { border-color: var(--primary); }
    .chat-input-row button {
      font-size: 12px; padding: 7px 13px; border-radius: 7px;
      border: none; background: var(--primary); color: white;
      cursor: pointer; font-weight: 600;
    }
    .chat-input-row button:hover { background: #2563eb; }
    .typing { opacity: .4; font-style: italic; }
  </style>
</head>
<body>

<!-- Top Bar -->
<div class="topbar">
  <h1>&#9829; HealthSense AI</h1>
  <div class="topbar-right">
    <div class="live-pill"><span class="live-dot"></span>Live</div>
    <span>Last sync: <span id="sync-time">--:--:--</span></span>
  </div>
</div>

<!-- Main 3-column grid -->
<div class="wrap">

  <!-- LEFT col: system card (fixed) + alert card (grows + scrolls inside) -->
  <div class="col">
    <div class="card">
      <div class="sec-label">system</div>
      <div style="font-size:12px;color:var(--sub)">Monitoring active</div>
      <hr class="divider">
      <div class="sec-label" style="margin-bottom:3px">recipient email</div>
      <input class="email-in" type="text" id="email-input" value="{{ alert_email }}">
    </div>

    <div class="card-grow">
      <div style="display:flex;align-items:center;margin-bottom:6px;flex-shrink:0">
        <span class="sec-label" style="margin:0">email alerts</span>
        <span class="notif-cnt" id="n-cnt">0</span>
      </div>
      <div id="toast-bar" class="toast">&#9888; Alert dispatched to recipient</div>
      <!-- This div scrolls; page does not grow -->
      <div id="notif-list" class="notif-scroll">
        <div class="empty-notif">No alerts sent yet</div>
      </div>
    </div>
  </div>

  <!-- CENTER col: metrics + charts + AI rec -->
  <div class="col">
    <div class="split2">
      <div class="metric">
        <div class="sec-label">heart rate</div>
        <div class="metric-num" id="v-bpm" style="color:var(--red)">--</div>
        <div style="font-size:11px;color:var(--muted)">BPM &nbsp;
          <span class="badge b-ok" id="s-bpm"><span class="bdot"></span>Normal</span>
        </div>
      </div>
      <div class="metric">
        <div class="sec-label">temperature</div>
        <div class="metric-num" id="v-temp" style="color:var(--primary)">--</div>
        <div style="font-size:11px;color:var(--muted)">°C &nbsp;
          <span class="badge b-ok" id="s-temp"><span class="bdot"></span>Normal</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="sec-label" style="margin-bottom:5px">heart rate — last 10 readings</div>
      <div class="ct100">
        <canvas id="bpm-chart" role="img" aria-label="Heart rate line chart">BPM over time.</canvas>
      </div>
    </div>

    <div class="card">
      <div class="sec-label" style="margin-bottom:5px">temperature — last 10 readings</div>
      <div class="ct70">
        <canvas id="temp-chart" role="img" aria-label="Temperature line chart">Temp over time.</canvas>
      </div>
    </div>

    <div class="card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:7px">
        <div class="sec-label" style="margin:0">AI recommendation</div>
        <span class="badge b-ok" id="rec-badge"><span class="bdot"></span>Normal</span>
      </div>
      <div class="ai-rec-text" id="ai-rec-text">Waiting for vitals data…</div>
      <div class="ai-rec-footer">
        <span id="ai-rec-time"></span>
        <span id="ai-rec-spin" style="display:none;color:var(--muted);font-size:10px">Analyzing…</span>
      </div>
    </div>
  </div>

  <!-- RIGHT col: chat (grows, messages scroll inside) -->
  <div class="col">
    <div class="chat-card">
      <div class="sec-label" style="margin-bottom:7px;flex-shrink:0">AI health assistant</div>
      <div class="chat-body" id="chat-msgs">
        <div class="msg-ai">Hello! I'm your AI health assistant. Ask me anything about your vitals.</div>
      </div>
      <div class="chat-input-row">
        <input type="text" id="chat-in" placeholder="Ask about your vitals…">
        <button id="chat-btn">Send</button>
      </div>
    </div>
  </div>

</div><!-- end .wrap -->

<script>
// ── State
let notifCount = 0;
let lastBpm = 0, lastTemp = 0, lastBs = 'NORMAL', lastTs = 'NORMAL';
const bpmLabels=[], bpmVals=[], tempLabels=[], tempVals=[];

// ── Charts
const bpmChart = new Chart(document.getElementById('bpm-chart'), {
  type: 'line',
  data: { labels: bpmLabels, datasets: [{ data: bpmVals, borderColor:'#ef4444',
    borderWidth:1.5, pointRadius:3, pointBackgroundColor:'#ef4444',
    tension:0.4, fill:true, backgroundColor:'rgba(239,68,68,0.06)' }] },
  options: { responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{display:false}, tooltip:{callbacks:{label:v=>v.raw+' bpm'}} },
    scales:{
      x:{ ticks:{font:{size:9},color:'#475569',maxTicksLimit:5}, grid:{display:false} },
      y:{ ticks:{font:{size:9},color:'#475569'}, grid:{color:'rgba(255,255,255,0.04)'},
          suggestedMin:40, suggestedMax:140 }
    }
  }
});

const tempChart = new Chart(document.getElementById('temp-chart'), {
  type: 'line',
  data: { labels: tempLabels, datasets: [{ data: tempVals, borderColor:'#3b82f6',
    borderWidth:1.5, pointRadius:3, pointBackgroundColor:'#3b82f6',
    tension:0.4, fill:true, backgroundColor:'rgba(59,130,246,0.06)' }] },
  options: { responsive:true, maintainAspectRatio:false,
    plugins:{ legend:{display:false}, tooltip:{callbacks:{label:v=>v.raw+'°C'}} },
    scales:{
      x:{ ticks:{font:{size:9},color:'#475569',maxTicksLimit:5}, grid:{display:false} },
      y:{ ticks:{font:{size:9},color:'#475569'}, grid:{color:'rgba(255,255,255,0.04)'},
          suggestedMin:34, suggestedMax:40 }
    }
  }
});

// ── Utils
function bc(s){ return s==='CRITICAL'?'b-crit': s==='WARNING'||s==='ELEVATED'?'b-warn':'b-ok'; }
function bl(s){ return s.charAt(0)+s.slice(1).toLowerCase(); }
function setBadge(id, status){
  const el = document.getElementById(id);
  el.className = 'badge ' + bc(status);
  el.innerHTML = '<span class="bdot"></span>' + bl(status);
}
function showToast(){
  const t = document.getElementById('toast-bar');
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'), 4000);
}

// ── Add notification — prepends so newest is on top; list scrolls, page stays fixed
function addNotif(bpm, temp, bs, ts, time){
  notifCount++;
  document.getElementById('n-cnt').textContent = notifCount;
  const list = document.getElementById('notif-list');
  const emp  = list.querySelector('.empty-notif');
  if(emp) emp.remove();
  const reasons = [];
  if(bs==='CRITICAL') reasons.push('Heart rate critical');
  if(ts==='CRITICAL') reasons.push('Temperature critical');
  const el = document.createElement('div');
  el.className = 'notif-item';
  el.innerHTML =
    `<div class="notif-time">${time}</div>
     <div class="notif-vals">BPM: ${bpm} &nbsp;|&nbsp; Temp: ${parseFloat(temp).toFixed(1)}°C</div>
     <div class="notif-reason">${reasons.join(' &amp; ')}</div>`;
  list.prepend(el);   // newest on top
  showToast();
}

function pushChart(labels, vals, chart, label, val){
  if(labels.length >= 10){ labels.shift(); vals.shift(); }
  labels.push(label); vals.push(val);
  chart.update('none');
}

// ── AI Recommendation (every 9 s)
let lastRecTime = 0;
async function fetchRec(bpm, temp, bs, ts){
  document.getElementById('ai-rec-spin').style.display = 'inline';
  try {
    const r = await fetch('/ai-recommendation',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ bpm, temp, bpm_status:bs, temp_status:ts })
    });
    const d = await r.json();
    document.getElementById('ai-rec-text').textContent = d.recommendation;
    document.getElementById('ai-rec-time').textContent = 'Updated ' + new Date().toLocaleTimeString();
    const sev = (bs==='CRITICAL'||ts==='CRITICAL')?'CRITICAL':
                (bs==='WARNING'||ts==='ELEVATED')?'WARNING':'NORMAL';
    setBadge('rec-badge', sev);
  } catch(e){
    document.getElementById('ai-rec-text').textContent = 'Could not fetch recommendation.';
  }
  document.getElementById('ai-rec-spin').style.display = 'none';
}

// ── Main refresh (every 3 s)
async function refresh(){
  try {
    const r    = await fetch('/api');
    const data = await r.json();
    if(!data.length) return;
    const last = data[data.length-1];
    lastBpm=last.bpm; lastTemp=last.temp; lastBs=last.bpm_status; lastTs=last.temp_status;

    document.getElementById('sync-time').textContent = last.time;
    document.getElementById('v-bpm').textContent     = last.bpm;
    document.getElementById('v-temp').textContent    = parseFloat(last.temp).toFixed(1);
    setBadge('s-bpm',  last.bpm_status);
    setBadge('s-temp', last.temp_status);

    const tick = last.time.slice(-8,-3);
    pushChart(bpmLabels,  bpmVals,  bpmChart,  tick, last.bpm);
    pushChart(tempLabels, tempVals, tempChart, tick, parseFloat(last.temp));

    if(last.email_sent)
      addNotif(last.bpm, last.temp, last.bpm_status, last.temp_status, last.time);

    const now = Date.now();
    if(now - lastRecTime > 9000){
      lastRecTime = now;
      fetchRec(last.bpm, last.temp, last.bpm_status, last.temp_status);
    }
  } catch(e){ console.error('Refresh:', e); }
}

setInterval(refresh, 3000);
refresh();

// ── Chat
const chatMsgs = document.getElementById('chat-msgs');
const chatIn   = document.getElementById('chat-in');

function appendMsg(text, role){
  const d = document.createElement('div');
  d.className = role==='user' ? 'msg-user' : 'msg-ai';
  d.textContent = text;
  chatMsgs.appendChild(d);
  chatMsgs.scrollTop = chatMsgs.scrollHeight;
  return d;
}

async function sendChat(){
  const q = chatIn.value.trim();
  if(!q) return;
  chatIn.value = '';
  appendMsg(q, 'user');
  const typing = appendMsg('Thinking…', 'ai');
  typing.classList.add('typing');
  try {
    const res = await fetch('/chat',{
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({question:q, bpm:lastBpm, temp:lastTemp,
                            bpm_status:lastBs, temp_status:lastTs})
    });
    const d = await res.json();
    typing.classList.remove('typing');
    typing.textContent = d.reply;
  } catch(e){
    typing.textContent = 'Could not reach AI.';
    typing.classList.remove('typing');
  }
  chatMsgs.scrollTop = chatMsgs.scrollHeight;
}

document.getElementById('chat-btn').addEventListener('click', sendChat);
chatIn.addEventListener('keydown', e=>{ if(e.key==='Enter') sendChat(); });
</script>
</body>
</html>"""


# ─── ROUTES ──────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template_string(HTML, alert_email=config["alert_email"])


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True)
        bpm  = int(data.get("hr", 0))
        temp = float(data.get("temp", 0.0))
        b_s, b_c, t_s, t_c = classify_health(bpm, temp)

        email_triggered = False
        if b_s == "CRITICAL" or t_s == "CRITICAL":
            email_triggered = send_alert_email(bpm, temp, b_s, t_s)
            if email_triggered:
                alerts.append({
                    "time":        datetime.datetime.now().strftime("%H:%M:%S"),
                    "bpm":         bpm,
                    "temp":        temp,
                    "bpm_status":  b_s,
                    "temp_status": t_s,
                })

        ai_tip = groq_call(
            f"One-sentence health tip for HR {bpm} BPM and temperature {temp}C.",
            max_tokens=60
        )

        readings.append({
            "time":        datetime.datetime.now().strftime("%H:%M:%S"),
            "bpm":         bpm,
            "temp":        temp,
            "ai":          ai_tip,
            "bpm_status":  b_s,
            "temp_status": t_s,
            "email_sent":  email_triggered,
        })
        return jsonify({"status": "Success"})
    except Exception as e:
        print(f"[PREDICT ERROR] {e}")
        return jsonify({"status": "Error", "detail": str(e)}), 400


@app.route("/api")
def api():
    return jsonify(readings)


@app.route("/alerts")
def get_alerts():
    return jsonify(alerts)


@app.route("/clear", methods=["POST"])
def clear():
    readings.clear()
    alerts.clear()
    return jsonify({"status": "cleared"})


@app.route("/ai-recommendation", methods=["POST"])
def ai_recommendation():
    try:
        data = request.get_json(force=True)
        bpm  = data.get("bpm")
        temp = data.get("temp")
        bs   = data.get("bpm_status")
        ts   = data.get("temp_status")
        prompt = (
            f"You are a clinical AI assistant in a real-time health monitor.\n"
            f"Patient vitals — Heart Rate: {bpm} BPM ({bs}), Temperature: {temp}C ({ts}).\n"
            f"Write a professional 3-sentence health recommendation. No bullet points."
        )
        return jsonify({"recommendation": groq_call(prompt, max_tokens=130)})
    except Exception as e:
        print(f"[REC ERROR] {e}")
        return jsonify({"recommendation": "Unable to generate recommendation."}), 500


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        q    = data.get("question", "")
        bpm  = data.get("bpm", "--")
        temp = data.get("temp", "--")
        bs   = data.get("bpm_status", "UNKNOWN")
        ts   = data.get("temp_status", "UNKNOWN")
        prompt = (
            f"You are a medical AI assistant in a health monitoring dashboard.\n"
            f"Current vitals: BPM={bpm} ({bs}), Temperature={temp}C ({ts}).\n"
            f"Answer in 2-3 sentences: {q}"
        )
        return jsonify({"reply": groq_call(prompt, max_tokens=150)})
    except Exception as e:
        print(f"[CHAT ERROR] {e}")
        return jsonify({"reply": "Unable to process your question."}), 500


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)