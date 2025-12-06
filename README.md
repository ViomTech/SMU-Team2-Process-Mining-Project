# TripleThreatx2 - Process Mining & BPMN Analysis Platform

A full-stack application for process mining, BPMN diagram analysis, and process optimization recommendations using AI

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architectural Design](#architectural-design)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Building for Production](#building-for-production)
- [Production Deployment](#production-deployment)

---

## 📖 Project Overview

This Business Process Optimisation System (BPOS) is an intelligent process mining platform that:
- Uploads and analyzes event logs
- Generates and visualizes BPMN diagrams
- Identifies bottlenecks and performance issues
- Provides AI-powered process improvement recommendations
- Manages multiple projects with version control
- Tracks approvals and recommendations

---


## Project Sample Workflow and Set up
Process Creation, Upload, Generation and Approval: 
1. Admin and BPO both register their own accounts
2. Admin logs into account
3. Creates new process and assigns BPO to it
4. Uploads Txt/CSV event log (with case_id, activity and timestamp) and Mines Process
5. Backend will conduct normalisation and map raw messages into standardised activity labels
6. PM4PY will discover process models and generate BPMN diagram 
6. Admin submits request to BPO for approval

7. BPO logs into account
8. Clicks into process assigned by Admin
9. Able to approve/reject Admin's change request with comment
10. All approve / reject decisions are logged in a history tab

---

## 🏗️ Architectural Design

**System Context (Level 1)**
The Business Process Optimization System (BPOS) interacts with two main user types: Admins and Business Process Owners (BPO).

- Admins can upload logs, perform process mining, view BPMN diagrams, create comments, generate AI recommendations, optimize diagrams, export diagrams, and submit changes for approval.

- BPOs possess all Admin functionalities plus the ability to approve and reject change requests, restore versions, and clone versions.

**Container Model (Level 2)**

The application is architected as a set of loosely coupled containers behind a reverse proxy, and deployed across two primary platforms: AWS EC2 for the application API/DB, and GitHub Pages for the static frontend client.

- Reverse Proxy: Handled by Nginx and Certbot to manage HTTPS traffic on port 443.

- Backend App Container (Python): Deployed on AWS EC2, this container provides core services like Login, Upload Logs, Process Mining (via pm4py), and AI Recommendations (via Hugging Face API).

- Database Container (PostgreSQL): Also hosted on AWS EC2, storing application data (diagrams, user info, etc.) and is accessed via TCP 5432.

- Frontend (React/bpmn-js): The client application, responsible for the UI and diagram visualization/editing, is hosted on GitHub Pages and accessed via HTTPS.


## 🛠 Tech Stack

### Frontend
- **React 19** with TypeScript
- **Vite** for fast development and optimized builds
- **React Router** for navigation
- **React Hook Form** for form management
- **TanStack Query** for server state management
- **Tailwind CSS** for styling
- **BPMN.js** for BPMN diagram visualization
- **Radix UI** for accessible UI components
- **Axios** for HTTP requests

### Backend
- **Python 3.x** with Flask web framework
- **Flask-SQLAlchemy** for ORM
- **PostgreSQL** for database
- **pm4py** for process mining
- **Hugging Face API** for AI recommendations
- **boto3** for AWS S3 integration
- **Flask-Migrate** for database migrations

### Production Infrastructure
- **AWS EC2** for backend hosting
- **GitHub Pages** for frontend hosting
- **DuckDNS** for dynamic DNS
- **Certbot** for SSL/TLS certificates
---

## 📦 Prerequisites

### Local Development
- Node.js 18+, npm 9+
- Python 3.8+
- PostgreSQL 12+
- Git

### Accounts Required
- Gmail App Password (email notifications) (for reset / forgot password feature)
- Hugging Face API Key (ML models)
- GitHub Account (for GitHub Pages)
- DuckDNS Account (dynamic DNS)
- AWS Account (EC2 backend)

---

## 📁 Project Structure

```
TripleThreatx2/
├── frontend/                 # React + TypeScript application
│   ├── src/
│   │   ├── components/       # Reusable React components
│   │   ├── pages/            # Page components
│   │   ├── contexts/         # React contexts (auth)
│   │   ├── hooks/            # Custom React hooks
│   │   ├── lib/              # API and utility functions
│   │   └── types/            # TypeScript type definitions
│   ├── .env                  # Frontend dev environment variables
│   ├── .env.production       # Frontend production environment variables
│   └── package.json
│
└── backend/
    └── python_app/           # Flask application
        ├── routes/           # API endpoints
        ├── services/         # Business logic
        ├── migrations/       # Database migrations
        ├── tests/            # Unit tests
        ├── app.py            # Flask app entry point
        ├── config.py         # Configuration
        ├── requirements.txt  # Python dependencies
        └── .env              # Backend environment variables
```
---

## 🚀 Local Development

### Backend Setup

```bash
cd backend/python_app

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create PostgreSQL database
createdb <your_own_db_name>

# Configure .env file (see Configuration section)

# Initialize database
flask db upgrade

# Run backend
python app.py
```

Backend runs at `http://localhost:5000`

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure .env file (see Configuration section)

# Run development server
npm run dev
```

Frontend runs at `http://localhost:5173`

---

## ⚙️ Configuration

### Backend (.env)

```env
# API Keys
HF_API_KEY=your_hugging_face_api_key

# Flask Security
SECRET_KEY=dev_secret_key_change_in_production
SECURITY_PASSWORD_SALT=dev_salt_change_in_production

# Database
DB_NAME=your_own_db_name
DB_PASSWORD=your_password
DB_USER=postgres
DB_HOST=localhost
DB_PORT=5432

# Frontend
FRONTEND_ORIGIN=http://localhost:5173
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_SECURE=false

# Email
PASSWORD_RESET_URL=http://localhost:5173/reset-password
REMEMBER_ME_DAYS=7

# Gmail SMTP
MAIL_FROM="BPOS System <your_gmail_account>@gmail.com>"
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=<your_gmail_account>@gmail.com
MAIL_PASSWORD=your_gmail_app_password
MAIL_USE_TLS=true
MAIL_USE_SSL=false
```

**Getting Gmail App Password:**
1. Enable 2-Step Verification on Gmail
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Select Mail + your device
4. Copy the 16-character password

**Getting Hugging Face API Key:**
1. Sign up at [huggingface.co](https://huggingface.co)
2. Settings → Access Tokens
3. Create token and copy to `HF_API_KEY`

### Frontend (.env)

**Development:**
```env
VITE_API_URL=http://localhost:5000
```
---

**Production (.env.production):**
```env
VITE_API_URL=https://<your_own_domain_name>.duckdns.org
```

---

## 🏗️ Building for Production

### Backend
```bash
pip install -r requirements.txt
# No build step needed
```

### Frontend
```bash
cd frontend
npm run build
```

Output: `frontend/dist/`

---

## 🌐 Production Deployment

### Backend (AWS EC2)

1. **Launch EC2 Instance**
   - Ubuntu 22.04 LTS
   - Allow ports: 22, 80, 443, 5000
   - Allocate Elastic IP

2. **Install & Configure**
   - Install: Python, pip, PostgreSQL client, Nginx, Certbot
   - Clone repo and setup virtual environment
   - Configure `.env` with production values
   - Run migrations: `flask db upgrade`

3. **Setup Gunicorn**
   - Install: `pip install gunicorn`
   - Create systemd service for auto-restart
   - Test: `gunicorn --workers 4 --bind 0.0.0.0:5000 app:app`

4. **Configure Nginx**
   - Setup reverse proxy (port 80 → 5000)
   - Enable SSL with Certbot
   - Redirect HTTP to HTTPS

5. **Enable SSL**
   - Run: `certbot --nginx -d <your_own_domain_name>.duckdns.org`
   - Auto-renewal enabled via systemd timer

### Frontend (GitHub Pages + DuckDNS)

1. **Setup DuckDNS**
   - Register at [duckdns.org](https://www.duckdns.org)
   - Create subdomain: '<your_own_domain_name>'
   - Setup cron job on EC2 for auto-updates (every 5 min)

2. **Deploy to GitHub Pages**
   - Build: `npm run build`
   - Deploy: `npm run deploy`
   - GitHub creates CNAME automatically

3. **GitHub Pages Settings**
   - Set custom domain: `<your_own_domain_name>.duckdns.org`
   - Enable "Enforce HTTPS"

4. **SSL Certificate**
   - Certbot handles SSL on EC2 with Nginx redirect
   - GitHub Pages provides HTTPS for GitHub domain

---

## 📝 Key API Endpoints

- `POST /api/auth/register` - Register
- `POST /api/auth/login` - Login
- `POST /api/project/create-project` - Create project
- `POST /api/files/upload` - Upload event log
- `POST /api/process-mining/discover` - Discover process
- `GET /api/recommendation/library` - Get recommendations
- `POST /api/bpmn/submit-for-approval` - Submit for approval

---

## 🔐 Security

### Local Development
- Use simple credentials (local only)
- HTTP is fine for development

### Production
- Use strong `SECRET_KEY` (32+ random chars)
- Enable `SESSION_COOKIE_SECURE=true`
- Use HTTPS everywhere
- Set exact `FRONTEND_ORIGIN`
- Regularly rotate API keys
- Use AWS security groups to restrict access

---

## 📚 Resources

- [Flask Docs](https://flask.palletsprojects.com/)
- [React Docs](https://react.dev/)
- [Vite Docs](https://vitejs.dev/)
- [AWS EC2 Docs](https://docs.aws.amazon.com/ec2/)
- [Certbot Docs](https://certbot.eff.org/)
- [DuckDNS](https://www.duckdns.org/)
- [GitHub Pages](https://pages.github.com/)

---

## 📄 License

Final Year Project (FYP)

