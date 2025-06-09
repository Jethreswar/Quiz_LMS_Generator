from django.db import models

class User(models.Model):
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    user_role = models.CharField(max_length=10, choices=[('user', 'User'), ('admin', 'Admin')])
    user_type = models.CharField(max_length=20, choices=[('professor', 'Professor'), ('student', 'Student')])
    courses = models.JSONField(default=list)

    def is_admin(self):
        return self.user_role == 'admin' 

class Questions(models.Model):
    question = models.CharField(max_length=255)
    option1 = models.CharField(max_length=50)
    option2 = models.CharField(max_length=50)
    option3 = models.CharField(max_length=50)
    option4 = models.CharField(max_length=50)
    correct_answer = models.CharField(max_length=50)
    course = models.JSONField(max_length=20)

class Quiz(models.Model):
    course = models.CharField(max_length=255)
    num_questions = models.IntegerField()
    quiz_duration = models.IntegerField()
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz_expire_date = models.DateField()    

class QuizHistory(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    quiz_date = models.DateField(auto_now_add=True)
    score = models.FloatField(default=0)
    num_correct = models.IntegerField(default=0)
    num_wrong = models.IntegerField(default=0)
    
    def __str__(self):
        if hasattr(self.quiz, 'student') and hasattr(self.quiz.student, 'username'):
            return f"{self.quiz.student.username}'s {self.quiz.course} quiz on {self.quiz_date}"
        return f"Quiz {self.quiz.id} on {self.quiz_date}"