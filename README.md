# 📚 STUDY_ANALYSER

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Gemini AI](https://img.shields.io/badge/Google_Gemini-AI?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

**STUDY_ANALYSER** is a comprehensive web application designed to empower students with AI-powered study management tools. Track study sessions with focus metrics, manage assignments and subjects with deadlines, and get intelligent assistance through integrated Google Gemini AI chat. Built with Django for robust backend, user authentication, and intuitive dashboards.

## ✨ Features
- **AI-Powered Chat Assistant**: Real-time conversation with Google Gemini AI for study tips, explanations, and productivity advice (local chat interface).
- **Study Session Tracking**: Log sessions with duration (hours) and focus level (0-100%), linked to subjects or assignments.
- **Assignment Management**: CRUD operations for assignments with titles, deadlines, estimated hours, and completion status.
- **Subject Organization**: User-specific subjects for categorizing studies.
- **User Dashboards**: Personalized admin/user dashboards, onboarding, login/register.
- **Responsive Templates**: Clean management interfaces for sessions, assignments, subjects (delete/edit/list).
- **Data Integrity**: Django models with constraints, indexes, migrations for production-ready DB.

## 🛠️ Tech Stack
| Category | Technologies |
|----------|--------------|
| **Backend** | Django 6.0.3, Python 3.x |
| **AI/ML** | Google Gemini (generativeai) |
| **Database** | Django ORM (SQLite/PostgreSQL compatible) |
| **Environment** | python-dotenv |
| **Frontend** | Django Templates, HTML/CSS/JS, Static files |
| **Deployment** | ASGI/WGSI ready |

## 📸 Screenshots
*(Add your screenshots here)*
```
- User Dashboard: ![Dashboard]()
- AI Chat Interface: ![Chat]()
- Assignment Manager: ![Assignments]()
- Study Sessions: ![Sessions]()
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Git

### Setup
```bash
# Clone the repo
git clone <your-repo-url>
cd STYDY_ANALYSER/STYDY_ANALYSER/studyanalyser

# Create virtual environment
python -m venv venv
# Windows: venv\\Scripts\\activate
# macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable (get free API key from https://aistudio.google.com/app/apikey)
echo GEMINI_API_KEY=your_api_key_here > .env

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Register/login to access dashboards.

## 🏗️ Project Structure
```
STYDY_ANALYSER/
├── README.md
├── STYDY_ANALYSER/studyanalyser/
│   ├── manage.py
│   ├── requirements.txt
│   ├── student/           # Main app
│   │   ├── models.py      # Subject, Assignment, StudySession
│   │   ├── views.py
│   │   ├── gemini_client.py # AI client
│   │   └── chat_local.py  # Chat views
│   ├── templates/student/ # Dashboards & management UIs
│   └── studyanalyser/     # Project settings
└── TODO.md
```

## 🔧 Environment Configuration
Create `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

## 🤝 Contributing
1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License
This project is open-source under MIT License - see [LICENSE](LICENSE) file (add if needed).

## 🙏 Acknowledgments
- [Django](https://www.djangoproject.com/)
- [Google Gemini API](https://ai.google.dev/)
- Django community templates & best practices

---

⭐ **Star this repo if it helps your studies!** 🚀
