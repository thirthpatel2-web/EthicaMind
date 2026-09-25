<div align="center">

# 🧠 EthicaMind

**A responsible AI wellness companion: a supportive chat that watches for crisis language first and answers with AI second.**

![Python](https://img.shields.io/badge/Python-Flask-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18-149ECA?logo=react&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-insights-FF6384?logo=chartdotjs&logoColor=white)

</div>

```
message ──► crisis check ──(risk)──► crisis screen with helpline options
                 │
                 └─(safe)──► Gemini (tries several models, with retries) ──► supportive reply
```

## ✨ Features

- 💬 **Chat** with an AI wellness assistant (React chat window)
- 🚨 **Safety first**: every message is screened for crisis language *before* any AI call, and a crisis gets a dedicated help screen instead of a generated reply
- 🔁 **Resilient AI calls**: tries a list of Gemini models in order and retries with back-off, so one unavailable model doesn't break the chat
- 📈 **Insights** page with a mood/trend chart (sample data for now)
- 🚀 **Deploy-ready**: a root `app.py` exposes the Flask app for Gunicorn (`gunicorn app:app`)

## 🚀 Quick start

**Backend** (Flask, port 5000):

```bash
git clone https://github.com/thirthpatel2-web/EthicaMind.git
cd EthicaMind
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

export ETHICAMIND_API_KEY=your_gemini_key   # Windows: set ETHICAMIND_API_KEY=...  (key from aistudio.google.com)
python backend/app.py
```

**Frontend** (React):

```bash
cd frontend
npm install
npm start          # ➜ http://localhost:3000
```

The frontend calls `http://localhost:5000` by default; set `REACT_APP_API_URL` to point it elsewhere.

## 🔌 API

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"I have had a stressful week"}'
```

## 📁 Project structure

```
EthicaMind/
├── app.py                 # Gunicorn entry point (wraps backend/app.py)
├── backend/app.py         # Flask API: /api/chat, crisis check, Gemini calls
└── frontend/src/
    ├── components/ChatWindow.js   # chat + crisis screen
    └── components/Dashboard.js    # insights chart
```

## 🧾 Honest notes

- EthicaMind is a **prototype, not a medical or therapy service**.
- The crisis check is a simple keyword list, a safety net rather than a clinical assessment.
- The Insights chart currently shows sample data.
- The crisis screen currently offers US options (call 911, text 741741). For users in India, the national mental-health helpline is **Tele-MANAS: 14416** (and **112** for emergencies).

## 👤 Author

Built by [Thirth Patel](https://github.com/thirthpatel2-web).
