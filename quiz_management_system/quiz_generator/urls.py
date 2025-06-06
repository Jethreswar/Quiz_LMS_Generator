from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name='login'),
    path("logout/", views.logout_view, name='logout'),
    path("admin/", views.admin_view, name='admin_view'),
    path("modify_question/<int:question_id>/", views.modify_question, name='modify_question'),
    path("delete_question/<int:question_id>/", views.delete_question, name='delete_question'),
    path('add_user/', views.add_user, name='add_user'),
    path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('create_quiz/', views.create_quiz, name='create_quiz'),
    path('delete_quiz/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    path("user/", views.user_view, name='user_view'),
    path('take_quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path("submit_quiz/<int:quiz_id_active>/", views.submit_quiz, name='submit_quiz'),
    #path('signup/<str:role>/', views.signup, name='signup'),
    path('admin_signup/', views.admin_signup, name='admin_signup'),  # Use underscore, not hyphen
    path('test-questions/', views.create_test_questions, name='create_test_questions'),
]