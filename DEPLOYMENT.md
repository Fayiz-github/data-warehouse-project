# Deployment Guide — Stock Market BI Dashboard

This guide details how to move the Stock Market Data Warehouse dashboard from a development environment to a production-ready state.

## 1. Prerequisites
- **PostgreSQL 18** instance (local or cloud-hosted).
- **Python 3.10+** installed on the server.
- Firewall access to the port (default `5000`).

---

## 2. Production Server Selection
The built-in Flask server (`app.run`) is for development only. For deployment, use a production WSGI server.

### Windows Deployment (Recommended)
Use **Waitress**, a production-grade WSGI server for Windows:
```bash
pip install waitress
```
Create a `run_production.py` file:
```python
from waitress import serve
from dashboard_app import app

if __name__ == "__main__":
    print("Dashboard serving on http://0.0.0.0:80")
    serve(app, host='0.0.0.0', port=80)
```

### Linux Deployment
Use **Gunicorn**:
```bash
pip install gunicorn
gunicorn --bind 0.0.0.0:80 dashboard_app:app
```

---

## 3. Environment Configuration
Ensure your `.env` file is properly configured for the production database:
```env
DB_HOST=your-production-db-host
DB_PORT=5432
DB_NAME=warehouse_db
DB_USER=dashboard_user  # Use the read-only user for security!
DB_PASSWORD=your_secure_password
```

---

## 4. Security Checklist (CRITICAL)
1. **Read-Only Access**: Ensure the app connects using the `dashboard_user` role created in `sql/bi_user.sql`. Never use the `postgres` superuser in production.
2. **CORS Policy**: If the frontend and backend are on different domains, update `CORS(app)` in `dashboard_app.py` to restrict origins.
3. **SSL/HTTPS**: Always serve the dashboard over HTTPS. Use a reverse proxy like **Nginx** with Let's Encrypt certificates.

---

## 5. Cloud Deployment Options
- **Render / Heroku**: Connect your GitHub repo. Add a `Procfile` with `web: gunicorn dashboard_app:app`.
- **AWS / Azure**: Deploy as a Container (Docker) or a Web App.
- **PythonAnywhere**: A great choice for simple Flask hosting.

---

## 6. Continuous Updates (ETL)
To keep the dashboard updated in production, set up a **Cron Job** (Linux) or **Task Scheduler** (Windows) to run the ETL pipeline daily:
```bash
# Example Windows Task command
C:\path\to\venv\Scripts\python.exe C:\path\to\project\etl\fetch_data.py
C:\path\to\venv\Scripts\python.exe C:\path\to\project\etl\load_facts.py
```
