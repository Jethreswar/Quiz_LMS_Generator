# 🎓 Quiz Management System

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2.7-green.svg)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive, full-featured Quiz Management System built with Django that enables professors to create and manage quizzes while providing students with an intuitive interface to take assessments. The system features role-based authentication, real-time quiz functionality, automated grading, and detailed performance analytics.

![Quiz Management System Dashboard](screenshots/dashboard.png)

## 📋 Table of Contents

- [Features](#-features)
- [Technology Stack](#️-technology-stack)
- [System Architecture](#-system-architecture)
- [Installation](#️-installation)
- [Configuration](#️-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

### 🔐 User Management & Authentication
- **Role-based Access Control**: Distinct interfaces and permissions for students and administrators/professors
- **Custom User Registration**: Seamless sign-up process with role selection
- **Secure Authentication**: Django's built-in authentication with session management
- **User Profiles**: Customizable user profiles with course assignments
- **Password Management**: Secure password reset and change functionality

### 👨‍🏫 Quiz Management (Admin/Professor)
- **Intuitive Quiz Builder**: Create quizzes with flexible configuration options
  - Customizable question count (1-50 questions)
  - Flexible time duration (5 minutes to 5 hours)
  - Quiz expiry date management
  - Randomized question order
- **Advanced Question Bank**: Comprehensive question management system
  - Multiple choice questions with 4 customizable options
  - Rich text support for questions and answers
  - Question categorization and tagging
  - Bulk import/export functionality
- **Course-based Organization**: Hierarchical quiz organization by courses and subjects
- **Student Assignment**: Granular control over quiz accessibility
- **Quiz Templates**: Save and reuse quiz configurations

### 🎯 Quiz Taking Experience (Students)
- **Responsive Interface**: Mobile-friendly, accessible quiz interface
- **Real-time Features**:
  - Live countdown timer with visual indicators
  - Auto-save functionality for answers
  - Progress tracking with completion percentage
  - Warning notifications for time constraints
- **Navigation System**: 
  - Question-by-question navigation
  - Question overview panel
  - Mark for review functionality
  - Quick jump to specific questions
- **Smart Submission**: 
  - Manual submission with confirmation
  - Automatic submission on time expiry
  - Draft saving for interrupted sessions

### 📊 Analytics & Performance Tracking
- **Comprehensive Scoring System**: 
  - Automatic grading with instant results
  - Percentage and grade-based scoring
  - Pass/fail status determination
- **Visual Analytics Dashboard**: 
  - Interactive charts using Chart.js
  - Performance trends over time
  - Subject-wise performance breakdown
  - Class average comparisons
- **Detailed Reporting**:
  - Individual quiz reports
  - Class performance summaries
  - Question-wise analysis
  - Time spent analytics

### 🔧 Administrative Features
- **User Management**: Add, modify, and manage student accounts
- **Quiz Monitoring**: Real-time quiz attempt monitoring
- **Data Export**: Export results to CSV/PDF formats
- **System Logs**: Comprehensive audit trail
- **Backup & Restore**: Database backup functionality

## 🛠️ Technology Stack

### Backend Technologies
- **Framework**: Django 4.2.7 (Python web framework)
- **Database**: PostgreSQL 13+ (Primary database)
- **ORM**: Django ORM with custom model relationships
- **Authentication**: Django's built-in authentication system
- **Session Management**: Database-backed sessions
- **Task Queue**: Django-RQ for background tasks (optional)

### Frontend Technologies
- **Template Engine**: Django Templates with Jinja2-style syntax
- **CSS Framework**: Bootstrap 5.3.0 (Responsive design)
- **JavaScript Libraries**:
  - Chart.js 3.9.1 (Data visualization)
  - jQuery 3.6.0 (DOM manipulation)
  - Popper.js (Tooltips and modals)
- **Icons**: Font Awesome 6.4.0 (Icon library)
- **Fonts**: Google Fonts (Typography)

### Development Tools
- **Version Control**: Git
- **Package Management**: pip with requirements.txt
- **Environment Management**: Python venv
- **Code Quality**: 
  - Black (Code formatting)
  - Flake8 (Linting)
  - isort (Import sorting)
- **Testing**: Django's built-in testing framework

### Data & Storage
- **Data Serialization**: JSON fields for flexible data storage
- **File Handling**: Django's file upload system
- **Static Files**: Django's collectstatic for production
- **Media Files**: Configurable media storage

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database      │
│                 │    │                 │    │                 │
│ • Bootstrap UI  │◄──►│ • Django Views  │◄──►│ • PostgreSQL    │
│ • JavaScript    │    │ • URL Routing   │    │ • User Data     │
│ • Chart.js      │    │ • Models/ORM    │    │ • Quiz Data     │
│ • AJAX Calls    │    │ • Authentication│    │ • Results       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Key Components
- **Models**: User, Quiz, Question, QuizAttempt, Course
- **Views**: Function-based and class-based views
- **Templates**: Reusable HTML templates with template inheritance
- **Static Files**: CSS, JavaScript, and image assets
- **URL Configuration**: RESTful URL patterns

## ⚙️ Installation

### Prerequisites
Ensure you have the following installed:
- **Python 3.8+** ([Download](https://python.org/downloads/))
- **PostgreSQL 13+** ([Download](https://postgresql.org/download/))
- **Git** ([Download](https://git-scm.com/downloads))
- **pip** (Python package manager)

### Step-by-Step Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/quiz-management-system.git
   cd quiz-management-system
   ```

2. **Create Virtual Environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Database Setup**
   ```sql
   -- Connect to PostgreSQL and create database
   CREATE DATABASE quizDb;
   CREATE USER quiz_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE quizDb TO quiz_user;
   ```

5. **Environment Configuration**
   ```bash
   # Create .env file
   cp .env.example .env
   # Edit .env with your database credentials
   ```

6. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create Superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Collect Static Files**
   ```bash
   python manage.py collectstatic
   ```

9. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

10. **Access Application**
    - Main Application: http://127.0.0.1:8000/
    - Admin Panel: http://127.0.0.1:8000/admin/
    - Quiz Login: http://127.0.0.1:8000/quiz/login/

## 🔧 Configuration

### Database Configuration
Update `quiz_management_system/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'quizDb',
        'USER': 'quiz_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Environment Variables
Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://quiz_user:password@localhost:5432/quizDb
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Production Settings
For production deployment:

```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

## 📖 Usage

### Admin/Professor Workflow

1. **Initial Setup**
   ```bash
   # Access admin dashboard
   http://localhost:8000/admin/
   ```

2. **User Management**
   - Register as administrator through signup page
   - Add students manually or via bulk import
   - Assign students to specific courses

3. **Quiz Creation Process**
   - Navigate to Quiz Management section
   - Create new quiz with parameters:
     - Quiz title and description
     - Course assignment
     - Time duration (5 min - 5 hours)
     - Number of questions
     - Expiry date and time
   - Add questions to question bank
   - Assign quiz to students

4. **Monitoring & Analytics**
   - View real-time quiz attempts
   - Analyze student performance
   - Generate reports and export data

### Student Workflow

1. **Registration & Login**
   ```bash
   # Student registration
   http://localhost:8000/quiz/signup/
   ```

2. **Dashboard Navigation**
   - View assigned quizzes
   - Check quiz deadlines
   - Review past attempts and scores

3. **Taking Quizzes**
   - Click on available quiz
   - Read instructions carefully
   - Navigate through questions using controls
   - Submit before time expires

4. **Results & History**
   - View immediate results after submission
   - Access detailed performance analytics
   - Track progress over time

### Key Workflows

#### Quiz Creation Workflow
```
Admin Login → Dashboard → Create Quiz → Add Questions → Set Parameters → Assign Students → Publish
```

#### Quiz Taking Workflow
```
Student Login → View Available Quizzes → Start Quiz → Answer Questions → Submit → View Results
```

## 📚 API Documentation

### Core Models

```python
# User Model (Extended)
class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    course = models.CharField(max_length=100, blank=True)
    
# Quiz Model
class Quiz(models.Model):
    title = models.CharField(max_length=200)
    course = models.CharField(max_length=100)
    num_questions = models.IntegerField()
    duration = models.IntegerField()  # in minutes
    expiry_date = models.DateTimeField()
    
# Question Model
class Question(models.Model):
    question_text = models.TextField()
    options = models.JSONField()  # Store 4 options as JSON
    correct_answer = models.CharField(max_length=1)
    
# Quiz Attempt Model
class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    answers = models.JSONField()
    score = models.FloatField()
    completed_at = models.DateTimeField()
```

### Key URLs

```python
# URL Patterns
urlpatterns = [
    path('admin/', admin.site.urls),
    path('quiz/login/', views.login_view, name='login'),
    path('quiz/signup/', views.signup_view, name='signup'),
    path('quiz/dashboard/', views.dashboard_view, name='dashboard'),
    path('quiz/take/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('quiz/results/<int:attempt_id>/', views.quiz_results, name='results'),
    path('quiz/create/', views.create_quiz, name='create_quiz'),
]
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test quiz_generator

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Test Categories
- **Unit Tests**: Model and form validation
- **Integration Tests**: View and template testing
- **Functional Tests**: End-to-end user workflows
- **Performance Tests**: Load testing for concurrent users

### Sample Test Case
```python
class QuizModelTest(TestCase):
    def test_quiz_creation(self):
        quiz = Quiz.objects.create(
            title="Sample Quiz",
            course="Computer Science",
            num_questions=10,
            duration=30
        )
        self.assertEqual(quiz.title, "Sample Quiz")
        self.assertEqual(quiz.num_questions, 10)
```

## 🚀 Deployment

### Production Deployment Options

#### 1. Heroku Deployment
```bash
# Install Heroku CLI
npm install -g heroku

# Login and create app
heroku login
heroku create your-quiz-app

# Configure environment
heroku config:set SECRET_KEY=your-secret-key
heroku config:set DEBUG=False

# Deploy
git push heroku main
heroku run python manage.py migrate
```

#### 2. DigitalOcean/AWS Deployment
```bash
# Install Gunicorn
pip install gunicorn

# Create Gunicorn configuration
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 3
```

#### 3. Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "quiz_management_system.wsgi:application"]
```

### Production Checklist
- [ ] Set `DEBUG = False`
- [ ] Configure proper `SECRET_KEY`
- [ ] Set up SSL/TLS certificates
- [ ] Configure database connection pooling
- [ ] Set up static file serving (Nginx/Apache)
- [ ] Configure logging and monitoring
- [ ] Set up automated backups
- [ ] Implement rate limiting
- [ ] Configure email settings

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Development Process
1. **Fork the Repository**
   ```bash
   git fork https://github.com/yourusername/quiz-management-system.git
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Development Standards**
   - Follow PEP 8 coding standards
   - Write comprehensive tests
   - Update documentation
   - Use meaningful commit messages

4. **Code Quality Checks**
   ```bash
   # Format code
   black .
   
   # Check linting
   flake8 .
   
   # Sort imports
   isort .
   
   # Run tests
   python manage.py test
   ```

5. **Submit Pull Request**
   - Provide clear description
   - Reference related issues
   - Ensure all tests pass

### Contribution Areas
- 🐛 Bug fixes and improvements
- ✨ New features and enhancements
- 📚 Documentation improvements
- 🧪 Test coverage expansion
- 🎨 UI/UX enhancements
- 🔧 Performance optimizations

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Quiz Management System

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

## 🙏 Acknowledgments

- **Django Community** - For the robust web framework
- **Bootstrap Team** - For responsive design components
- **Chart.js Contributors** - For beautiful data visualization
- **Font Awesome** - For comprehensive icon library
- **PostgreSQL Team** - For reliable database management
- **Open Source Community** - For continuous inspiration and support

---

**Made with ❤️ by [Jethreswar](https://github.com/Jethreswar)**

⭐ **If you find this project helpful, please give it a star!** ⭐