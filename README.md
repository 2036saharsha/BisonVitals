# Hospital CRM

A hospital CRM system supporting doctors and patients.

## Setup Instructions

1. Create a virtual environment:
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Migrate
```bash
python manage.py migrate
```

4. Start the server:
```bash
python manage.py runserver
```

The application will be available at:
- Main site: http://127.0.0.1:8000/