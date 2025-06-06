from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User, Questions, Quiz, QuizHistory
import random
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth import logout
from django.utils import timezone
import json
from django.db.models import Count
import datetime
from django.http import HttpResponse

active_user = None

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            # Check if user exists and password is correct
            user = User.objects.get(username=username)
            
            # Add debugging information
            print(f"Login attempt for: {username}")
            print(f"Stored password: {user.password}")
            print(f"Entered password: {password}")
            
            if user.password == password:  # Using plain text comparison - consider using Django auth system
                # Set session variables
                request.session['user'] = username
                request.session['user_role'] = user.user_role
                request.session['user_type'] = user.user_type
                
                # Redirect based on role
                if user.user_role == 'admin':
                    return redirect('admin_view')
                else:
                    return redirect('user_view')
            else:
                messages.error(request, 'Invalid credentials')
        except User.DoesNotExist:
            messages.error(request, 'User does not exist')
    
    # For GET requests or failed login attempts
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def admin_view(request):
    active_user = request.session.get('user')
    users = User.objects.all()
    questions = Questions.objects.all()
    quizzes = Quiz.objects.all()
    all_quiz_history = QuizHistory.objects.all()
    
    # Clean up the course data display
    distinct_courses = set()
    for question in questions:
        # Extract courses as plain text
        if question.course:
            # Try to detect if it's a JSON string (from older data)
            if question.course.startswith('[') and question.course.endswith(']'):
                try:
                    import json
                    parsed_courses = json.loads(question.course)
                    if isinstance(parsed_courses, list):
                        for course in parsed_courses:
                            if course:  # Skip empty entries
                                distinct_courses.add(course.strip())
                    else:
                        distinct_courses.add(str(parsed_courses).strip())
                except:
                    # If JSON parsing fails, add as is
                    distinct_courses.add(question.course.strip())
            else:
                # It's already plain text
                distinct_courses.add(question.course.strip())
    
    # Convert to list and sort
    distinct_courses = sorted(list(distinct_courses))
    
    # Count questions per course
    course_question_counts = {}
    for course in distinct_courses:
        # Count questions with exact course match
        count = Questions.objects.filter(course=course).count()
        
        # Also try with JSON formatted courses for backwards compatibility
        if count == 0:
            count = Questions.objects.filter(course__icontains=f'"{course}"').count()
            
        course_question_counts[course] = count
    
    # Format for template
    courses_with_counts = [
        {'name': course, 'question_count': course_question_counts.get(course, 0)} 
        for course in distinct_courses
    ]
    
    # Prepare users data with properly formatted courses for JavaScript
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_role': user.user_role,
        }
        
        # Clean and parse courses to ensure it's always a properly formatted array
        clean_courses = []
        if user.courses is None:
            pass  # Keep empty list
        elif isinstance(user.courses, str):
            try:
                import json
                parsed_courses = json.loads(user.courses)
                if isinstance(parsed_courses, list):
                    for course in parsed_courses:
                        if isinstance(course, str):
                            # Clean up any poorly formatted course names
                            clean_course = course.replace('\n', '').replace('"', '').strip()
                            clean_courses.append(clean_course)
                        else:
                            clean_courses.append(str(course))
                else:
                    clean_course = str(parsed_courses).replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
            except:
                # If parsing fails, try to clean the string itself
                if user.courses:
                    clean_course = user.courses.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
        elif isinstance(user.courses, list):
            for course in user.courses:
                if isinstance(course, str):
                    clean_course = course.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
                else:
                    clean_courses.append(str(course))
        
        user_data['courses'] = clean_courses
        users_data.append(user_data)
    
    # Get today's date for the minimum date in the expiry date picker
    today_date = timezone.now()

    # Define choices for number of questions (for dropdowns etc.)
    num_questions_choices = list(range(1, 51))
    
    # Add a field to track which quiz is currently selected for adding questions
    active_quiz_id = None
    
    # Process POST request for adding questions
    if request.method == 'POST' and request.POST.get('form_type') == 'add_question':
        question_text = request.POST.get('question')
        course = request.POST.get('course')
        quiz_id = request.POST.get('quiz_id')  # Get the quiz ID
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        correct_answer = request.POST.get('correct_answer')
        
        # Store course as plain text - no JSON encoding
        
        # Create the question
        new_question = Questions.objects.create(
            question=question_text,
            course=course,  # Store as plain text
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_answer=correct_answer
        )
        
        # Associate the question with the quiz if provided
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                # Store quiz-question relationship (you might need to add a field to your Quiz model)
                # For example: quiz.questions.add(new_question)
                messages.success(request, f"Question added successfully and associated with quiz {quiz_id}!")
            except Quiz.DoesNotExist:
                messages.warning(request, "Quiz not found, question added but not associated with any quiz.")
        else:
            messages.success(request, f"Question for course {course} added successfully!")
            
        return redirect('admin_view')
        
    # Ensure users_data is properly JSON serialized for JavaScript
    import json
    users_json = json.dumps(users_data)
    
    # Fix course display formatting
    for question in questions:
        # Fix the course display format
        if isinstance(question.course, str):
            try:
                # Try to parse as JSON
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    # Join list elements into a readable string
                    question.display_course = ", ".join([str(c) for c in courses if c])
                else:
                    question.display_course = str(courses)
            except:
                # If parsing fails, use as is
                question.display_course = question.course
        elif isinstance(question.course, list):
            question.display_course = ", ".join([str(c) for c in question.course if c])
        else:
            question.display_course = str(question.course)
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    return render(request, 'admin_page.html', {
        'all_quiz_history': all_quiz_history,
        'quizzes': quizzes, 
        'users': users_data,  
        'users_json': users_json,  # Add this new variable for JavaScript
        'questions': questions, 
        'active_user': active_user,
        'num_questions_choices': num_questions_choices,
        'distinct_courses': courses_with_counts,
        'today_date': today_date
    })

def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses')
        
        # Process courses to ensure they're stored as plain text
        # If multiple courses are provided as comma-separated, store them as-is
        # No JSON encoding
        
        # Create the user
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses  # Store as plain text
        )
        
        return redirect('admin_view')
    
    return redirect('admin_view')

def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    user.delete()
    return redirect('admin_view')

def modify_question(request, question_id):
    question = Questions.objects.get(pk=question_id)
    
    if request.method == 'POST':
        # Handle modification logic here
        question.question = request.POST.get('question')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_answer = request.POST.get('correct_answer')
        question.course = request.POST.get('question_course')
        question.save()
        return redirect('admin_view')

    return render(request, 'modify_question.html', {'question': question})

def delete_question(request, question_id):
    quiz = Questions.objects.get(pk=question_id)
    quiz.delete()
    return redirect('admin_view')

def create_quiz(request):
    if request.method == 'POST':
        course = request.POST.get('course')
        student_id = request.POST.get('student_id')
        
        # Get num_questions as an integer
        try:
            num_questions = int(request.POST.get('num_questions', 10))
            # Enforce reasonable limits
            if num_questions < 1:
                num_questions = 1
            elif num_questions > 50:
                num_questions = 50
        except ValueError:
            # Default to 10 if conversion fails
            num_questions = 10
            
        quiz_duration = int(request.POST.get('quiz_duration', 30))
        quiz_expire_date = request.POST.get('quiz_expire_date')
        
        # Ensure the student exists
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            messages.error(request, "Invalid student selection")
            return redirect('admin_view')
        
        # Check if this course exists for the selected student
        student_courses = []
        if isinstance(student.courses, str):
            try:
                import json
                student_courses = json.loads(student.courses)
            except:
                student_courses = []
        else:
            student_courses = student.courses
            
        if course not in student_courses:
            messages.error(request, f"Course '{course}' is not assigned to student {student.username}")
            return redirect('admin_view')
            
        # Check how many questions are available for this course
        # First try exact match
        questions = Questions.objects.filter(course__exact=course)
        
        # If no questions found, try contains with quotes for JSON stored courses
        if questions.count() == 0:
            questions = Questions.objects.filter(course__icontains=f'"{course}"')
        
        # Third attempt: Try with more flexible approach for JSON array fields
        if questions.count() == 0:
            from django.db.models import Q
            questions = Questions.objects.filter(
                Q(course__icontains=course) | 
                Q(course__icontains=f'"{course}"')
            )
        
        available_question_count = questions.count()
        
        if available_question_count == 0:
            messages.error(request, f"No questions available for the course '{course}'")
            return redirect('admin_view')
            
        if available_question_count < num_questions:
            messages.warning(request, f"Only {available_question_count} questions available for this course. Quiz created with {available_question_count} questions.")
            num_questions = available_question_count
            
        # Create the quiz
        Quiz.objects.create(
            course=course,
            num_questions=num_questions,
            quiz_duration=quiz_duration,
            quiz_expire_date=quiz_expire_date,
            student=student
        )
        
        messages.success(request, f"Quiz created successfully for {student.username} with {num_questions} questions")
        return redirect('admin_view')
    
    # If not POST request, redirect to admin view
    return redirect('admin_view')

def delete_quiz(request, quiz_id):
    quiz = Quiz.objects.get(pk=quiz_id)
    quiz.delete()
    return redirect('admin_view')

def user_view(request):
    active_user = request.session.get('user')
    
    if not active_user:
        return redirect('login')
    
    try:
        user = User.objects.get(username=active_user)
    except User.DoesNotExist:
        return redirect('login')
    
    # Get current date - important for expiration comparison
    today = timezone.now().date()
    
    # Get quizzes assigned to this specific user that are not expired
    available_quizzes = Quiz.objects.filter(
        student=user,
        quiz_expire_date__gte=today  # Only get quizzes not expired
    ).order_by('quiz_expire_date')
    
    # Debug output
    print(f"DEBUG: Today: {today}")
    print(f"DEBUG: Available quizzes: {list(available_quizzes.values('id', 'course', 'quiz_expire_date'))}")
    
    # Get the user's course list
    user_courses = []
    if user.courses:
        if isinstance(user.courses, str):
            try:
                import json
                user_courses = json.loads(user.courses)
            except:
                user_courses = []
        else:
            user_courses = user.courses
    
    # Get quiz history
    quiz_history = QuizHistory.objects.filter(quiz__student=user).order_by('-quiz_date')
    
    return render(request, 'user_page.html', {
        'username': active_user,
        'user': user,
        'available_quizzes': available_quizzes,
        'user_courses': user_courses,
        'quiz_history': quiz_history,
        'today': today  # Pass current date to template
    })

def take_quiz(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')
    
    # Check if quiz is expired
    today = timezone.now().date()
    if quiz.quiz_expire_date < today:
        messages.error(request, f"This quiz expired on {quiz.quiz_expire_date}. Please contact your instructor.")
        return redirect('user_view')
    
    num_questions = quiz.num_questions
    course = quiz.course
    
    # Improved question filtering - try multiple methods to find questions
    # First attempt: Try exact match
    questions = Questions.objects.filter(course__exact=course)
    
    # Second attempt: Try contains with quotes (for JSON stored courses)
    if questions.count() == 0:
        questions = Questions.objects.filter(course__contains=course)
    
    # Third attempt: Try icontains to make it case insensitive
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=course)
    
    # Fourth attempt: Try with JSON formatting
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=f'"{course}"')
    
    # Fifth attempt: If course is stored as a list, try a more generic approach
    if questions.count() == 0:
        # Get all questions and filter manually
        all_questions = Questions.objects.all()
        filtered_questions = []
        
        for question in all_questions:
            # Try to parse the course field if it's a string
            question_courses = question.course
            if isinstance(question_courses, str):
                try:
                    import json
                    question_courses = json.loads(question_courses)
                except:
                    # If parsing fails, treat it as a single course
                    question_courses = [question_courses]
            
            # Check if the course exists in the list
            if course in question_courses:
                filtered_questions.append(question)
        
        # Convert the filtered list to a queryset if needed
        if filtered_questions:
            from django.db.models import Q
            question_ids = [q.id for q in filtered_questions]
            questions = Questions.objects.filter(id__in=question_ids)
    
    # Check if we have enough questions for this quiz
    available_question_count = questions.count()
    
    if available_question_count == 0:
        # Debug information to help troubleshoot
        print(f"DEBUG: No questions found for course {course}")
        print(f"DEBUG: Quiz ID: {quiz_id}")
        print(f"DEBUG: All questions: {list(Questions.objects.all().values_list('id', 'course'))}")
        
        messages.error(request, f"No questions are available for course {course}. Please contact your instructor.")
        return redirect('user_view')
    
    if available_question_count < num_questions:
        # Not enough questions available, adjust num_questions
        num_questions = available_question_count
        messages.warning(
            request, 
            f"This quiz was configured for {quiz.num_questions} questions, but only {num_questions} are available for course {course}."
        )
    
    # Now safely select random questions
    selected_questions = random.sample(list(questions), num_questions)
    
    # For POST method (submitting the quiz)
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        num_correct = 0
        num_wrong = 0
        
        for question in selected_questions:
            # Get user's answer for this question
            user_answer = request.POST.get(f'answer_{question.id}')
            
            # Check if answer is correct
            if user_answer == question.correct_answer:
                num_correct += 1
            else:
                num_wrong += 1
        
        # Calculate score
        total_questions = num_correct + num_wrong
        if total_questions > 0:
            score = (num_correct / total_questions) * 100
        
        # Save quiz history
        quiz_history = QuizHistory.objects.create(
            quiz=quiz,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,
            quiz_date=today
        )
        
        # Render results page
        return render(request, 'submit_quiz.html', {
            'score': score,
            'num_correct': num_correct,
            'num_wrong': num_wrong,
            'quiz_date': today
        })
    
    # For GET method (displaying the quiz)
    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': selected_questions,
        'quiz_duration': quiz.quiz_duration
    })

def submit_quiz(request, quiz_id_active):
    if request.method == 'POST':
        user_inputs = {key: request.POST[key] for key in request.POST.keys() if key.startswith('answer_')}
        quiz_ids = [int(key.replace('answer_', '')) for key in user_inputs.keys()]
        correct_answers = Questions.objects.filter(id__in=quiz_ids).values_list('id', 'correct_answer')

        num_correct = 0
        num_wrong = 0
        for quiz_id, correct_answer in correct_answers:
            user_input = user_inputs.get(f'answer_{quiz_id}')
            if user_input == correct_answer:
                num_correct += 1
            else:
                num_wrong += 1

        total_questions=num_correct+num_wrong
        if total_questions > 0:
            score = (num_correct/total_questions)*100
        else:
            score = 0  
        # Save quiz data to QuizHistory table
        quiz_date = timezone.now().date()
        quiz_instance = Quiz.objects.get(pk=quiz_id_active)
        
        QuizHistory.objects.create(
            quiz=quiz_instance,
            quiz_date=quiz_date,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,            
        )        
        # Display the results on submit_quiz.html
        return render(request, 'submit_quiz.html', {'score':round(score, 2), 'num_correct': num_correct, 'num_wrong': num_wrong, 'quiz_date':quiz_date})

def signup(request, role):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign user to appropriate group based on role
            if role == 'student':
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
            elif role == 'professor':
                professor_group, _ = Group.objects.get_or_create(name='Professor')
                user.groups.add(professor_group)
            
            return redirect('login')
    else:
        form = UserCreationForm()
    
    # Add Bootstrap classes to form fields
    form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
    form.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
    form.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    return render(request, 'signup.html', {
        'form': form,
        'role': role
    })

def admin_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'user')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses', '[]')
        
        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'admin_signup.html')
        
        # Create user using your custom User model
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses
        )
        
        # Add success message - this will be displayed on the signup page before redirecting
        success_message = f"{username}'s account is created successfully!"
        
        # Render the template with the success message
        context = {'success_message': success_message}
        return render(request, 'signup_success.html', context)
    
    return render(request, 'admin_signup.html')

def create_test_questions(request):
    """Create test questions for troubleshooting"""
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        num_to_create = int(request.POST.get('num_questions', 1))
        
        # Format course name properly
        import json
        course_json = json.dumps([course_name])
        
        # Create the specified number of questions
        questions_created = 0
        for i in range(1, num_to_create + 1):
            Questions.objects.create(
                question=f"Test question #{i} for {course_name}",
                course=course_json,
                option1=f"Option 1 for question {i}",
                option2=f"Option 2 for question {i}",
                option3=f"Option 3 for question {i}",
                option4=f"Option 4 for question {i}",
                correct_answer="option1"  # Make option1 always correct for test questions
            )
            questions_created += 1
        
        return HttpResponse(
            f"<h3>Created {questions_created} test questions for course {course_name}</h3>" +
            f"<p>Course stored as: {course_json}</p>" +
            f"<p><a href='/quiz/admin/'>Return to Admin Dashboard</a></p>"
        )
    
    # Display form for GET request
    return render(request, 'create_test_questions.html', {})

def admin_view(request):
    active_user = request.session.get('user')
    users = User.objects.all()
    questions = Questions.objects.all()
    quizzes = Quiz.objects.all()
    all_quiz_history = QuizHistory.objects.all()
    
    # Clean up the course data display
    distinct_courses = set()
    for question in questions:
        # Extract courses as plain text
        if question.course:
            # Try to detect if it's a JSON string (from older data)
            if question.course.startswith('[') and question.course.endswith(']'):
                try:
                    import json
                    parsed_courses = json.loads(question.course)
                    if isinstance(parsed_courses, list):
                        for course in parsed_courses:
                            if course:  # Skip empty entries
                                distinct_courses.add(course.strip())
                    else:
                        distinct_courses.add(str(parsed_courses).strip())
                except:
                    # If JSON parsing fails, add as is
                    distinct_courses.add(question.course.strip())
            else:
                # It's already plain text
                distinct_courses.add(question.course.strip())
    
    # Convert to list and sort
    distinct_courses = sorted(list(distinct_courses))
    
    # Count questions per course
    course_question_counts = {}
    for course in distinct_courses:
        # Count questions with exact course match
        count = Questions.objects.filter(course=course).count()
        
        # Also try with JSON formatted courses for backwards compatibility
        if count == 0:
            count = Questions.objects.filter(course__icontains=f'"{course}"').count()
            
        course_question_counts[course] = count
    
    # Format for template
    courses_with_counts = [
        {'name': course, 'question_count': course_question_counts.get(course, 0)} 
        for course in distinct_courses
    ]
    
    # Prepare users data with properly formatted courses for JavaScript
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_role': user.user_role,
        }
        
        # Clean and parse courses to ensure it's always a properly formatted array
        clean_courses = []
        if user.courses is None:
            pass  # Keep empty list
        elif isinstance(user.courses, str):
            try:
                import json
                parsed_courses = json.loads(user.courses)
                if isinstance(parsed_courses, list):
                    for course in parsed_courses:
                        if isinstance(course, str):
                            # Clean up any poorly formatted course names
                            clean_course = course.replace('\n', '').replace('"', '').strip()
                            clean_courses.append(clean_course)
                        else:
                            clean_courses.append(str(course))
                else:
                    clean_course = str(parsed_courses).replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
            except:
                # If parsing fails, try to clean the string itself
                if user.courses:
                    clean_course = user.courses.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
        elif isinstance(user.courses, list):
            for course in user.courses:
                if isinstance(course, str):
                    clean_course = course.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
                else:
                    clean_courses.append(str(course))
        
        user_data['courses'] = clean_courses
        users_data.append(user_data)
    
    # Get today's date for the minimum date in the expiry date picker
    today_date = timezone.now()

    # Define choices for number of questions (for dropdowns etc.)
    num_questions_choices = list(range(1, 51))
    
    # Add a field to track which quiz is currently selected for adding questions
    active_quiz_id = None
    
    # Process POST request for adding questions
    if request.method == 'POST' and request.POST.get('form_type') == 'add_question':
        question_text = request.POST.get('question')
        course = request.POST.get('course')
        quiz_id = request.POST.get('quiz_id')  # Get the quiz ID
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        correct_answer = request.POST.get('correct_answer')
        
        # Store course as plain text - no JSON encoding
        
        # Create the question
        new_question = Questions.objects.create(
            question=question_text,
            course=course,  # Store as plain text
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_answer=correct_answer
        )
        
        # Associate the question with the quiz if provided
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                # Store quiz-question relationship (you might need to add a field to your Quiz model)
                # For example: quiz.questions.add(new_question)
                messages.success(request, f"Question added successfully and associated with quiz {quiz_id}!")
            except Quiz.DoesNotExist:
                messages.warning(request, "Quiz not found, question added but not associated with any quiz.")
        else:
            messages.success(request, f"Question for course {course} added successfully!")
            
        return redirect('admin_view')
        
    # Ensure users_data is properly JSON serialized for JavaScript
    import json
    users_json = json.dumps(users_data)
    
    # Fix course display formatting
    for question in questions:
        # Fix the course display format
        if isinstance(question.course, str):
            try:
                # Try to parse as JSON
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    # Join list elements into a readable string
                    question.display_course = ", ".join([str(c) for c in courses if c])
                else:
                    question.display_course = str(courses)
            except:
                # If parsing fails, use as is
                question.display_course = question.course
        elif isinstance(question.course, list):
            question.display_course = ", ".join([str(c) for c in question.course if c])
        else:
            question.display_course = str(question.course)
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    return render(request, 'admin_page.html', {
        'all_quiz_history': all_quiz_history,
        'quizzes': quizzes, 
        'users': users_data,  
        'users_json': users_json,  # Add this new variable for JavaScript
        'questions': questions, 
        'active_user': active_user,
        'num_questions_choices': num_questions_choices,
        'distinct_courses': courses_with_counts,
        'today_date': today_date
    })

def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses')
        
        # Process courses to ensure they're stored as plain text
        # If multiple courses are provided as comma-separated, store them as-is
        # No JSON encoding
        
        # Create the user
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses  # Store as plain text
        )
        
        return redirect('admin_view')
    
    return redirect('admin_view')

def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    user.delete()
    return redirect('admin_view')

def modify_question(request, question_id):
    question = Questions.objects.get(pk=question_id)
    
    if request.method == 'POST':
        # Handle modification logic here
        question.question = request.POST.get('question')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_answer = request.POST.get('correct_answer')
        question.course = request.POST.get('question_course')
        question.save()
        return redirect('admin_view')

    return render(request, 'modify_question.html', {'question': question})

def delete_question(request, question_id):
    quiz = Questions.objects.get(pk=question_id)
    quiz.delete()
    return redirect('admin_view')

def create_quiz(request):
    if request.method == 'POST':
        course = request.POST.get('course')
        student_id = request.POST.get('student_id')
        
        # Get num_questions as an integer
        try:
            num_questions = int(request.POST.get('num_questions', 10))
            # Enforce reasonable limits
            if num_questions < 1:
                num_questions = 1
            elif num_questions > 50:
                num_questions = 50
        except ValueError:
            # Default to 10 if conversion fails
            num_questions = 10
            
        quiz_duration = int(request.POST.get('quiz_duration', 30))
        quiz_expire_date = request.POST.get('quiz_expire_date')
        
        # Ensure the student exists
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            messages.error(request, "Invalid student selection")
            return redirect('admin_view')
        
        # Check if this course exists for the selected student
        student_courses = []
        if isinstance(student.courses, str):
            try:
                import json
                student_courses = json.loads(student.courses)
            except:
                student_courses = []
        else:
            student_courses = student.courses
            
        if course not in student_courses:
            messages.error(request, f"Course '{course}' is not assigned to student {student.username}")
            return redirect('admin_view')
            
        # Check how many questions are available for this course
        # First try exact match
        questions = Questions.objects.filter(course__exact=course)
        
        # If no questions found, try contains with quotes for JSON stored courses
        if questions.count() == 0:
            questions = Questions.objects.filter(course__icontains=f'"{course}"')
        
        # Third attempt: Try with more flexible approach for JSON array fields
        if questions.count() == 0:
            from django.db.models import Q
            questions = Questions.objects.filter(
                Q(course__icontains=course) | 
                Q(course__icontains=f'"{course}"')
            )
        
        available_question_count = questions.count()
        
        if available_question_count == 0:
            messages.error(request, f"No questions available for the course '{course}'")
            return redirect('admin_view')
            
        if available_question_count < num_questions:
            messages.warning(request, f"Only {available_question_count} questions available for this course. Quiz created with {available_question_count} questions.")
            num_questions = available_question_count
            
        # Create the quiz
        Quiz.objects.create(
            course=course,
            num_questions=num_questions,
            quiz_duration=quiz_duration,
            quiz_expire_date=quiz_expire_date,
            student=student
        )
        
        messages.success(request, f"Quiz created successfully for {student.username} with {num_questions} questions")
        return redirect('admin_view')
    
    # If not POST request, redirect to admin view
    return redirect('admin_view')

def delete_quiz(request, quiz_id):
    quiz = Quiz.objects.get(pk=quiz_id)
    quiz.delete()
    return redirect('admin_view')

def user_view(request):
    active_user = request.session.get('user')
    
    if not active_user:
        return redirect('login')
    
    try:
        user = User.objects.get(username=active_user)
    except User.DoesNotExist:
        return redirect('login')
    
    # Get current date - important for expiration comparison
    today = timezone.now().date()
    
    # Get quizzes assigned to this specific user that are not expired
    available_quizzes = Quiz.objects.filter(
        student=user,
        quiz_expire_date__gte=today  # Only get quizzes not expired
    ).order_by('quiz_expire_date')
    
    # Debug output
    print(f"DEBUG: Today: {today}")
    print(f"DEBUG: Available quizzes: {list(available_quizzes.values('id', 'course', 'quiz_expire_date'))}")
    
    # Get the user's course list
    user_courses = []
    if user.courses:
        if isinstance(user.courses, str):
            try:
                import json
                user_courses = json.loads(user.courses)
            except:
                user_courses = []
        else:
            user_courses = user.courses
    
    # Get quiz history
    quiz_history = QuizHistory.objects.filter(quiz__student=user).order_by('-quiz_date')
    
    return render(request, 'user_page.html', {
        'username': active_user,
        'user': user,
        'available_quizzes': available_quizzes,
        'user_courses': user_courses,
        'quiz_history': quiz_history,
        'today': today  # Pass current date to template
    })

def take_quiz(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')
    
    # Check if quiz is expired
    today = timezone.now().date()
    if quiz.quiz_expire_date < today:
        messages.error(request, f"This quiz expired on {quiz.quiz_expire_date}. Please contact your instructor.")
        return redirect('user_view')
    
    num_questions = quiz.num_questions
    course = quiz.course
    
    # Improved question filtering - try multiple methods to find questions
    # First attempt: Try exact match
    questions = Questions.objects.filter(course__exact=course)
    
    # Second attempt: Try contains with quotes (for JSON stored courses)
    if questions.count() == 0:
        questions = Questions.objects.filter(course__contains=course)
    
    # Third attempt: Try icontains to make it case insensitive
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=course)
    
    # Fourth attempt: Try with JSON formatting
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=f'"{course}"')
    
    # Fifth attempt: If course is stored as a list, try a more generic approach
    if questions.count() == 0:
        # Get all questions and filter manually
        all_questions = Questions.objects.all()
        filtered_questions = []
        
        for question in all_questions:
            # Try to parse the course field if it's a string
            question_courses = question.course
            if isinstance(question_courses, str):
                try:
                    import json
                    question_courses = json.loads(question_courses)
                except:
                    # If parsing fails, treat it as a single course
                    question_courses = [question_courses]
            
            # Check if the course exists in the list
            if course in question_courses:
                filtered_questions.append(question)
        
        # Convert the filtered list to a queryset if needed
        if filtered_questions:
            from django.db.models import Q
            question_ids = [q.id for q in filtered_questions]
            questions = Questions.objects.filter(id__in=question_ids)
    
    # Check if we have enough questions for this quiz
    available_question_count = questions.count()
    
    if available_question_count == 0:
        # Debug information to help troubleshoot
        print(f"DEBUG: No questions found for course {course}")
        print(f"DEBUG: Quiz ID: {quiz_id}")
        print(f"DEBUG: All questions: {list(Questions.objects.all().values_list('id', 'course'))}")
        
        messages.error(request, f"No questions are available for course {course}. Please contact your instructor.")
        return redirect('user_view')
    
    if available_question_count < num_questions:
        # Not enough questions available, adjust num_questions
        num_questions = available_question_count
        messages.warning(
            request, 
            f"This quiz was configured for {quiz.num_questions} questions, but only {num_questions} are available for course {course}."
        )
    
    # Now safely select random questions
    selected_questions = random.sample(list(questions), num_questions)
    
    # For POST method (submitting the quiz)
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        num_correct = 0
        num_wrong = 0
        
        for question in selected_questions:
            # Get user's answer for this question
            user_answer = request.POST.get(f'answer_{question.id}')
            
            # Check if answer is correct
            if user_answer == question.correct_answer:
                num_correct += 1
            else:
                num_wrong += 1
        
        # Calculate score
        total_questions = num_correct + num_wrong
        if total_questions > 0:
            score = (num_correct / total_questions) * 100
        
        # Save quiz history
        quiz_history = QuizHistory.objects.create(
            quiz=quiz,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,
            quiz_date=today
        )
        
        # Render results page
        return render(request, 'submit_quiz.html', {
            'score': score,
            'num_correct': num_correct,
            'num_wrong': num_wrong,
            'quiz_date': today
        })
    
    # For GET method (displaying the quiz)
    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': selected_questions,
        'quiz_duration': quiz.quiz_duration
    })

def submit_quiz(request, quiz_id_active):
    if request.method == 'POST':
        user_inputs = {key: request.POST[key] for key in request.POST.keys() if key.startswith('answer_')}
        quiz_ids = [int(key.replace('answer_', '')) for key in user_inputs.keys()]
        correct_answers = Questions.objects.filter(id__in=quiz_ids).values_list('id', 'correct_answer')

        num_correct = 0
        num_wrong = 0
        for quiz_id, correct_answer in correct_answers:
            user_input = user_inputs.get(f'answer_{quiz_id}')
            if user_input == correct_answer:
                num_correct += 1
            else:
                num_wrong += 1

        total_questions=num_correct+num_wrong
        if total_questions > 0:
            score = (num_correct/total_questions)*100
        else:
            score = 0  
        # Save quiz data to QuizHistory table
        quiz_date = timezone.now().date()
        quiz_instance = Quiz.objects.get(pk=quiz_id_active)
        
        QuizHistory.objects.create(
            quiz=quiz_instance,
            quiz_date=quiz_date,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,            
        )        
        # Display the results on submit_quiz.html
        return render(request, 'submit_quiz.html', {'score':round(score, 2), 'num_correct': num_correct, 'num_wrong': num_wrong, 'quiz_date':quiz_date})

def signup(request, role):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign user to appropriate group based on role
            if role == 'student':
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
            elif role == 'professor':
                professor_group, _ = Group.objects.get_or_create(name='Professor')
                user.groups.add(professor_group)
            
            return redirect('login')
    else:
        form = UserCreationForm()
    
    # Add Bootstrap classes to form fields
    form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
    form.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
    form.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    return render(request, 'signup.html', {
        'form': form,
        'role': role
    })

def admin_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'user')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses', '[]')
        
        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'admin_signup.html')
        
        # Create user using your custom User model
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses
        )
        
        # Add success message - this will be displayed on the signup page before redirecting
        success_message = f"{username}'s account is created successfully!"
        
        # Render the template with the success message
        context = {'success_message': success_message}
        return render(request, 'signup_success.html', context)
    
    return render(request, 'admin_signup.html')

def create_test_questions(request):
    """Create test questions for troubleshooting"""
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        num_to_create = int(request.POST.get('num_questions', 1))
        
        # Format course name properly
        import json
        course_json = json.dumps([course_name])
        
        # Create the specified number of questions
        questions_created = 0
        for i in range(1, num_to_create + 1):
            Questions.objects.create(
                question=f"Test question #{i} for {course_name}",
                course=course_json,
                option1=f"Option 1 for question {i}",
                option2=f"Option 2 for question {i}",
                option3=f"Option 3 for question {i}",
                option4=f"Option 4 for question {i}",
                correct_answer="option1"  # Make option1 always correct for test questions
            )
            questions_created += 1
        
        return HttpResponse(
            f"<h3>Created {questions_created} test questions for course {course_name}</h3>" +
            f"<p>Course stored as: {course_json}</p>" +
            f"<p><a href='/quiz/admin/'>Return to Admin Dashboard</a></p>"
        )
    
    # Display form for GET request
    return render(request, 'create_test_questions.html', {})

def admin_view(request):
    active_user = request.session.get('user')
    users = User.objects.all()
    questions = Questions.objects.all()
    quizzes = Quiz.objects.all()
    all_quiz_history = QuizHistory.objects.all()
    
    # Clean up the course data display
    distinct_courses = set()
    for question in questions:
        # Extract courses as plain text
        if question.course:
            # Try to detect if it's a JSON string (from older data)
            if question.course.startswith('[') and question.course.endswith(']'):
                try:
                    import json
                    parsed_courses = json.loads(question.course)
                    if isinstance(parsed_courses, list):
                        for course in parsed_courses:
                            if course:  # Skip empty entries
                                distinct_courses.add(course.strip())
                    else:
                        distinct_courses.add(str(parsed_courses).strip())
                except:
                    # If JSON parsing fails, add as is
                    distinct_courses.add(question.course.strip())
            else:
                # It's already plain text
                distinct_courses.add(question.course.strip())
    
    # Convert to list and sort
    distinct_courses = sorted(list(distinct_courses))
    
    # Count questions per course
    course_question_counts = {}
    for course in distinct_courses:
        # Count questions with exact course match
        count = Questions.objects.filter(course=course).count()
        
        # Also try with JSON formatted courses for backwards compatibility
        if count == 0:
            count = Questions.objects.filter(course__icontains=f'"{course}"').count()
            
        course_question_counts[course] = count
    
    # Format for template
    courses_with_counts = [
        {'name': course, 'question_count': course_question_counts.get(course, 0)} 
        for course in distinct_courses
    ]
    
    # Prepare users data with properly formatted courses for JavaScript
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_role': user.user_role,
        }
        
        # Clean and parse courses to ensure it's always a properly formatted array
        clean_courses = []
        if user.courses is None:
            pass  # Keep empty list
        elif isinstance(user.courses, str):
            try:
                import json
                parsed_courses = json.loads(user.courses)
                if isinstance(parsed_courses, list):
                    for course in parsed_courses:
                        if isinstance(course, str):
                            # Clean up any poorly formatted course names
                            clean_course = course.replace('\n', '').replace('"', '').strip()
                            clean_courses.append(clean_course)
                        else:
                            clean_courses.append(str(course))
                else:
                    clean_course = str(parsed_courses).replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
            except:
                # If parsing fails, try to clean the string itself
                if user.courses:
                    clean_course = user.courses.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
        elif isinstance(user.courses, list):
            for course in user.courses:
                if isinstance(course, str):
                    clean_course = course.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
                else:
                    clean_courses.append(str(course))
        
        user_data['courses'] = clean_courses
        users_data.append(user_data)
    
    # Get today's date for the minimum date in the expiry date picker
    today_date = timezone.now()

    # Define choices for number of questions (for dropdowns etc.)
    num_questions_choices = list(range(1, 51))
    
    # Add a field to track which quiz is currently selected for adding questions
    active_quiz_id = None
    
    # Process POST request for adding questions
    if request.method == 'POST' and request.POST.get('form_type') == 'add_question':
        question_text = request.POST.get('question')
        course = request.POST.get('course')
        quiz_id = request.POST.get('quiz_id')  # Get the quiz ID
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        correct_answer = request.POST.get('correct_answer')
        
        # Store course as plain text - no JSON encoding
        
        # Create the question
        new_question = Questions.objects.create(
            question=question_text,
            course=course,  # Store as plain text
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_answer=correct_answer
        )
        
        # Associate the question with the quiz if provided
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                # Store quiz-question relationship (you might need to add a field to your Quiz model)
                # For example: quiz.questions.add(new_question)
                messages.success(request, f"Question added successfully and associated with quiz {quiz_id}!")
            except Quiz.DoesNotExist:
                messages.warning(request, "Quiz not found, question added but not associated with any quiz.")
        else:
            messages.success(request, f"Question for course {course} added successfully!")
            
        return redirect('admin_view')
        
    # Ensure users_data is properly JSON serialized for JavaScript
    import json
    users_json = json.dumps(users_data)
    
    # Fix course display formatting
    for question in questions:
        # Fix the course display format
        if isinstance(question.course, str):
            try:
                # Try to parse as JSON
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    # Join list elements into a readable string
                    question.display_course = ", ".join([str(c) for c in courses if c])
                else:
                    question.display_course = str(courses)
            except:
                # If parsing fails, use as is
                question.display_course = question.course
        elif isinstance(question.course, list):
            question.display_course = ", ".join([str(c) for c in question.course if c])
        else:
            question.display_course = str(question.course)
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    return render(request, 'admin_page.html', {
        'all_quiz_history': all_quiz_history,
        'quizzes': quizzes, 
        'users': users_data,  
        'users_json': users_json,  # Add this new variable for JavaScript
        'questions': questions, 
        'active_user': active_user,
        'num_questions_choices': num_questions_choices,
        'distinct_courses': courses_with_counts,
        'today_date': today_date
    })

def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses')
        
        # Process courses to ensure they're stored as plain text
        # If multiple courses are provided as comma-separated, store them as-is
        # No JSON encoding
        
        # Create the user
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses  # Store as plain text
        )
        
        return redirect('admin_view')
    
    return redirect('admin_view')

def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    user.delete()
    return redirect('admin_view')

def modify_question(request, question_id):
    question = Questions.objects.get(pk=question_id)
    
    if request.method == 'POST':
        # Handle modification logic here
        question.question = request.POST.get('question')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_answer = request.POST.get('correct_answer')
        question.course = request.POST.get('question_course')
        question.save()
        return redirect('admin_view')

    return render(request, 'modify_question.html', {'question': question})

def delete_question(request, question_id):
    quiz = Questions.objects.get(pk=question_id)
    quiz.delete()
    return redirect('admin_view')

def create_quiz(request):
    if request.method == 'POST':
        course = request.POST.get('course')
        student_id = request.POST.get('student_id')
        
        # Get num_questions as an integer
        try:
            num_questions = int(request.POST.get('num_questions', 10))
            # Enforce reasonable limits
            if num_questions < 1:
                num_questions = 1
            elif num_questions > 50:
                num_questions = 50
        except ValueError:
            # Default to 10 if conversion fails
            num_questions = 10
            
        quiz_duration = int(request.POST.get('quiz_duration', 30))
        quiz_expire_date = request.POST.get('quiz_expire_date')
        
        # Ensure the student exists
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            messages.error(request, "Invalid student selection")
            return redirect('admin_view')
        
        # Check if this course exists for the selected student
        student_courses = []
        if isinstance(student.courses, str):
            try:
                import json
                student_courses = json.loads(student.courses)
            except:
                student_courses = []
        else:
            student_courses = student.courses
            
        if course not in student_courses:
            messages.error(request, f"Course '{course}' is not assigned to student {student.username}")
            return redirect('admin_view')
            
        # Check how many questions are available for this course
        # First try exact match
        questions = Questions.objects.filter(course__exact=course)
        
        # If no questions found, try contains with quotes for JSON stored courses
        if questions.count() == 0:
            questions = Questions.objects.filter(course__icontains=f'"{course}"')
        
        # Third attempt: Try with more flexible approach for JSON array fields
        if questions.count() == 0:
            from django.db.models import Q
            questions = Questions.objects.filter(
                Q(course__icontains=course) | 
                Q(course__icontains=f'"{course}"')
            )
        
        available_question_count = questions.count()
        
        if available_question_count == 0:
            messages.error(request, f"No questions available for the course '{course}'")
            return redirect('admin_view')
            
        if available_question_count < num_questions:
            messages.warning(request, f"Only {available_question_count} questions available for this course. Quiz created with {available_question_count} questions.")
            num_questions = available_question_count
            
        # Create the quiz
        Quiz.objects.create(
            course=course,
            num_questions=num_questions,
            quiz_duration=quiz_duration,
            quiz_expire_date=quiz_expire_date,
            student=student
        )
        
        messages.success(request, f"Quiz created successfully for {student.username} with {num_questions} questions")
        return redirect('admin_view')
    
    # If not POST request, redirect to admin view
    return redirect('admin_view')

def delete_quiz(request, quiz_id):
    quiz = Quiz.objects.get(pk=quiz_id)
    quiz.delete()
    return redirect('admin_view')

def user_view(request):
    active_user = request.session.get('user')
    
    if not active_user:
        return redirect('login')
    
    try:
        user = User.objects.get(username=active_user)
    except User.DoesNotExist:
        return redirect('login')
    
    # Get current date - important for expiration comparison
    today = timezone.now().date()
    
    # Get quizzes assigned to this specific user that are not expired
    available_quizzes = Quiz.objects.filter(
        student=user,
        quiz_expire_date__gte=today  # Only get quizzes not expired
    ).order_by('quiz_expire_date')
    
    # Debug output
    print(f"DEBUG: Today: {today}")
    print(f"DEBUG: Available quizzes: {list(available_quizzes.values('id', 'course', 'quiz_expire_date'))}")
    
    # Get the user's course list
    user_courses = []
    if user.courses:
        if isinstance(user.courses, str):
            try:
                import json
                user_courses = json.loads(user.courses)
            except:
                user_courses = []
        else:
            user_courses = user.courses
    
    # Get quiz history
    quiz_history = QuizHistory.objects.filter(quiz__student=user).order_by('-quiz_date')
    
    return render(request, 'user_page.html', {
        'username': active_user,
        'user': user,
        'available_quizzes': available_quizzes,
        'user_courses': user_courses,
        'quiz_history': quiz_history,
        'today': today  # Pass current date to template
    })

def take_quiz(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')
    
    # Check if quiz is expired
    today = timezone.now().date()
    if quiz.quiz_expire_date < today:
        messages.error(request, f"This quiz expired on {quiz.quiz_expire_date}. Please contact your instructor.")
        return redirect('user_view')
    
    num_questions = quiz.num_questions
    course = quiz.course
    
    # Improved question filtering - try multiple methods to find questions
    # First attempt: Try exact match
    questions = Questions.objects.filter(course__exact=course)
    
    # Second attempt: Try contains with quotes (for JSON stored courses)
    if questions.count() == 0:
        questions = Questions.objects.filter(course__contains=course)
    
    # Third attempt: Try icontains to make it case insensitive
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=course)
    
    # Fourth attempt: Try with JSON formatting
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=f'"{course}"')
    
    # Fifth attempt: If course is stored as a list, try a more generic approach
    if questions.count() == 0:
        # Get all questions and filter manually
        all_questions = Questions.objects.all()
        filtered_questions = []
        
        for question in all_questions:
            # Try to parse the course field if it's a string
            question_courses = question.course
            if isinstance(question_courses, str):
                try:
                    import json
                    question_courses = json.loads(question_courses)
                except:
                    # If parsing fails, treat it as a single course
                    question_courses = [question_courses]
            
            # Check if the course exists in the list
            if course in question_courses:
                filtered_questions.append(question)
        
        # Convert the filtered list to a queryset if needed
        if filtered_questions:
            from django.db.models import Q
            question_ids = [q.id for q in filtered_questions]
            questions = Questions.objects.filter(id__in=question_ids)
    
    # Check if we have enough questions for this quiz
    available_question_count = questions.count()
    
    if available_question_count == 0:
        # Debug information to help troubleshoot
        print(f"DEBUG: No questions found for course {course}")
        print(f"DEBUG: Quiz ID: {quiz_id}")
        print(f"DEBUG: All questions: {list(Questions.objects.all().values_list('id', 'course'))}")
        
        messages.error(request, f"No questions are available for course {course}. Please contact your instructor.")
        return redirect('user_view')
    
    if available_question_count < num_questions:
        # Not enough questions available, adjust num_questions
        num_questions = available_question_count
        messages.warning(
            request, 
            f"This quiz was configured for {quiz.num_questions} questions, but only {num_questions} are available for course {course}."
        )
    
    # Now safely select random questions
    selected_questions = random.sample(list(questions), num_questions)
    
    # For POST method (submitting the quiz)
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        num_correct = 0
        num_wrong = 0
        
        for question in selected_questions:
            # Get user's answer for this question
            user_answer = request.POST.get(f'answer_{question.id}')
            
            # Check if answer is correct
            if user_answer == question.correct_answer:
                num_correct += 1
            else:
                num_wrong += 1
        
        # Calculate score
        total_questions = num_correct + num_wrong
        if total_questions > 0:
            score = (num_correct / total_questions) * 100
        
        # Save quiz history
        quiz_history = QuizHistory.objects.create(
            quiz=quiz,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,
            quiz_date=today
        )
        
        # Render results page
        return render(request, 'submit_quiz.html', {
            'score': score,
            'num_correct': num_correct,
            'num_wrong': num_wrong,
            'quiz_date': today
        })
    
    # For GET method (displaying the quiz)
    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': selected_questions,
        'quiz_duration': quiz.quiz_duration
    })

def submit_quiz(request, quiz_id_active):
    if request.method == 'POST':
        user_inputs = {key: request.POST[key] for key in request.POST.keys() if key.startswith('answer_')}
        quiz_ids = [int(key.replace('answer_', '')) for key in user_inputs.keys()]
        correct_answers = Questions.objects.filter(id__in=quiz_ids).values_list('id', 'correct_answer')

        num_correct = 0
        num_wrong = 0
        for quiz_id, correct_answer in correct_answers:
            user_input = user_inputs.get(f'answer_{quiz_id}')
            if user_input == correct_answer:
                num_correct += 1
            else:
                num_wrong += 1

        total_questions=num_correct+num_wrong
        if total_questions > 0:
            score = (num_correct/total_questions)*100
        else:
            score = 0  
        # Save quiz data to QuizHistory table
        quiz_date = timezone.now().date()
        quiz_instance = Quiz.objects.get(pk=quiz_id_active)
        
        QuizHistory.objects.create(
            quiz=quiz_instance,
            quiz_date=quiz_date,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,            
        )        
        # Display the results on submit_quiz.html
        return render(request, 'submit_quiz.html', {'score':round(score, 2), 'num_correct': num_correct, 'num_wrong': num_wrong, 'quiz_date':quiz_date})

def signup(request, role):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign user to appropriate group based on role
            if role == 'student':
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
            elif role == 'professor':
                professor_group, _ = Group.objects.get_or_create(name='Professor')
                user.groups.add(professor_group)
            
            return redirect('login')
    else:
        form = UserCreationForm()
    
    # Add Bootstrap classes to form fields
    form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
    form.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
    form.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    return render(request, 'signup.html', {
        'form': form,
        'role': role
    })

def admin_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'user')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses', '[]')
        
        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'admin_signup.html')
        
        # Create user using your custom User model
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses
        )
        
        # Add success message - this will be displayed on the signup page before redirecting
        success_message = f"{username}'s account is created successfully!"
        
        # Render the template with the success message
        context = {'success_message': success_message}
        return render(request, 'signup_success.html', context)
    
    return render(request, 'admin_signup.html')

def create_test_questions(request):
    """Create test questions for troubleshooting"""
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        num_to_create = int(request.POST.get('num_questions', 1))
        
        # Format course name properly
        import json
        course_json = json.dumps([course_name])
        
        # Create the specified number of questions
        questions_created = 0
        for i in range(1, num_to_create + 1):
            Questions.objects.create(
                question=f"Test question #{i} for {course_name}",
                course=course_json,
                option1=f"Option 1 for question {i}",
                option2=f"Option 2 for question {i}",
                option3=f"Option 3 for question {i}",
                option4=f"Option 4 for question {i}",
                correct_answer="option1"  # Make option1 always correct for test questions
            )
            questions_created += 1
        
        return HttpResponse(
            f"<h3>Created {questions_created} test questions for course {course_name}</h3>" +
            f"<p>Course stored as: {course_json}</p>" +
            f"<p><a href='/quiz/admin/'>Return to Admin Dashboard</a></p>"
        )
    
    # Display form for GET request
    return render(request, 'create_test_questions.html', {})

def admin_view(request):
    active_user = request.session.get('user')
    users = User.objects.all()
    questions = Questions.objects.all()
    quizzes = Quiz.objects.all()
    all_quiz_history = QuizHistory.objects.all()
    
    # Clean up the course data display
    distinct_courses = set()
    for question in questions:
        # Extract courses as plain text
        if question.course:
            # Try to detect if it's a JSON string (from older data)
            if question.course.startswith('[') and question.course.endswith(']'):
                try:
                    import json
                    parsed_courses = json.loads(question.course)
                    if isinstance(parsed_courses, list):
                        for course in parsed_courses:
                            if course:  # Skip empty entries
                                distinct_courses.add(course.strip())
                    else:
                        distinct_courses.add(str(parsed_courses).strip())
                except:
                    # If JSON parsing fails, add as is
                    distinct_courses.add(question.course.strip())
            else:
                # It's already plain text
                distinct_courses.add(question.course.strip())
    
    # Convert to list and sort
    distinct_courses = sorted(list(distinct_courses))
    
    # Count questions per course
    course_question_counts = {}
    for course in distinct_courses:
        # Count questions with exact course match
        count = Questions.objects.filter(course=course).count()
        
        # Also try with JSON formatted courses for backwards compatibility
        if count == 0:
            count = Questions.objects.filter(course__icontains=f'"{course}"').count()
            
        course_question_counts[course] = count
    
    # Format for template
    courses_with_counts = [
        {'name': course, 'question_count': course_question_counts.get(course, 0)} 
        for course in distinct_courses
    ]
    
    # Prepare users data with properly formatted courses for JavaScript
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_role': user.user_role,
        }
        
        # Clean and parse courses to ensure it's always a properly formatted array
        clean_courses = []
        if user.courses is None:
            pass  # Keep empty list
        elif isinstance(user.courses, str):
            try:
                import json
                parsed_courses = json.loads(user.courses)
                if isinstance(parsed_courses, list):
                    for course in parsed_courses:
                        if isinstance(course, str):
                            # Clean up any poorly formatted course names
                            clean_course = course.replace('\n', '').replace('"', '').strip()
                            clean_courses.append(clean_course)
                        else:
                            clean_courses.append(str(course))
                else:
                    clean_course = str(parsed_courses).replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
            except:
                # If parsing fails, try to clean the string itself
                if user.courses:
                    clean_course = user.courses.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
        elif isinstance(user.courses, list):
            for course in user.courses:
                if isinstance(course, str):
                    clean_course = course.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
                else:
                    clean_courses.append(str(course))
        
        user_data['courses'] = clean_courses
        users_data.append(user_data)
    
    # Get today's date for the minimum date in the expiry date picker
    today_date = timezone.now()

    # Define choices for number of questions (for dropdowns etc.)
    num_questions_choices = list(range(1, 51))
    
    # Add a field to track which quiz is currently selected for adding questions
    active_quiz_id = None
    
    # Process POST request for adding questions
    if request.method == 'POST' and request.POST.get('form_type') == 'add_question':
        question_text = request.POST.get('question')
        course = request.POST.get('course')
        quiz_id = request.POST.get('quiz_id')  # Get the quiz ID
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        correct_answer = request.POST.get('correct_answer')
        
        # Store course as plain text - no JSON encoding
        
        # Create the question
        new_question = Questions.objects.create(
            question=question_text,
            course=course,  # Store as plain text
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_answer=correct_answer
        )
        
        # Associate the question with the quiz if provided
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                # Store quiz-question relationship (you might need to add a field to your Quiz model)
                # For example: quiz.questions.add(new_question)
                messages.success(request, f"Question added successfully and associated with quiz {quiz_id}!")
            except Quiz.DoesNotExist:
                messages.warning(request, "Quiz not found, question added but not associated with any quiz.")
        else:
            messages.success(request, f"Question for course {course} added successfully!")
            
        return redirect('admin_view')
        
    # Ensure users_data is properly JSON serialized for JavaScript
    import json
    users_json = json.dumps(users_data)
    
    # Fix course display formatting
    for question in questions:
        # Fix the course display format
        if isinstance(question.course, str):
            try:
                # Try to parse as JSON
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    # Join list elements into a readable string
                    question.display_course = ", ".join([str(c) for c in courses if c])
                else:
                    question.display_course = str(courses)
            except:
                # If parsing fails, use as is
                question.display_course = question.course
        elif isinstance(question.course, list):
            question.display_course = ", ".join([str(c) for c in question.course if c])
        else:
            question.display_course = str(question.course)
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    return render(request, 'admin_page.html', {
        'all_quiz_history': all_quiz_history,
        'quizzes': quizzes, 
        'users': users_data,  
        'users_json': users_json,  # Add this new variable for JavaScript
        'questions': questions, 
        'active_user': active_user,
        'num_questions_choices': num_questions_choices,
        'distinct_courses': courses_with_counts,
        'today_date': today_date
    })

def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses')
        
        # Process courses to ensure they're stored as plain text
        # If multiple courses are provided as comma-separated, store them as-is
        # No JSON encoding
        
        # Create the user
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses  # Store as plain text
        )
        
        return redirect('admin_view')
    
    return redirect('admin_view')

def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    user.delete()
    return redirect('admin_view')

def modify_question(request, question_id):
    question = Questions.objects.get(pk=question_id)
    
    if request.method == 'POST':
        # Handle modification logic here
        question.question = request.POST.get('question')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_answer = request.POST.get('correct_answer')
        question.course = request.POST.get('question_course')
        question.save()
        return redirect('admin_view')

    return render(request, 'modify_question.html', {'question': question})

def delete_question(request, question_id):
    quiz = Questions.objects.get(pk=question_id)
    quiz.delete()
    return redirect('admin_view')

def create_quiz(request):
    if request.method == 'POST':
        course = request.POST.get('course')
        student_id = request.POST.get('student_id')
        
        # Get num_questions as an integer
        try:
            num_questions = int(request.POST.get('num_questions', 10))
            # Enforce reasonable limits
            if num_questions < 1:
                num_questions = 1
            elif num_questions > 50:
                num_questions = 50
        except ValueError:
            # Default to 10 if conversion fails
            num_questions = 10
            
        quiz_duration = int(request.POST.get('quiz_duration', 30))
        quiz_expire_date = request.POST.get('quiz_expire_date')
        
        # Ensure the student exists
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            messages.error(request, "Invalid student selection")
            return redirect('admin_view')
        
        # Check if this course exists for the selected student
        student_courses = []
        if isinstance(student.courses, str):
            try:
                import json
                student_courses = json.loads(student.courses)
            except:
                student_courses = []
        else:
            student_courses = student.courses
            
        if course not in student_courses:
            messages.error(request, f"Course '{course}' is not assigned to student {student.username}")
            return redirect('admin_view')
            
        # Check how many questions are available for this course
        # First try exact match
        questions = Questions.objects.filter(course__exact=course)
        
        # If no questions found, try contains with quotes for JSON stored courses
        if questions.count() == 0:
            questions = Questions.objects.filter(course__icontains=f'"{course}"')
        
        # Third attempt: Try with more flexible approach for JSON array fields
        if questions.count() == 0:
            from django.db.models import Q
            questions = Questions.objects.filter(
                Q(course__icontains=course) | 
                Q(course__icontains=f'"{course}"')
            )
        
        available_question_count = questions.count()
        
        if available_question_count == 0:
            messages.error(request, f"No questions available for the course '{course}'")
            return redirect('admin_view')
            
        if available_question_count < num_questions:
            messages.warning(request, f"Only {available_question_count} questions available for this course. Quiz created with {available_question_count} questions.")
            num_questions = available_question_count
            
        # Create the quiz
        Quiz.objects.create(
            course=course,
            num_questions=num_questions,
            quiz_duration=quiz_duration,
            quiz_expire_date=quiz_expire_date,
            student=student
        )
        
        messages.success(request, f"Quiz created successfully for {student.username} with {num_questions} questions")
        return redirect('admin_view')
    
    # If not POST request, redirect to admin view
    return redirect('admin_view')

def delete_quiz(request, quiz_id):
    quiz = Quiz.objects.get(pk=quiz_id)
    quiz.delete()
    return redirect('admin_view')

def user_view(request):
    active_user = request.session.get('user')
    
    if not active_user:
        return redirect('login')
    
    try:
        user = User.objects.get(username=active_user)
    except User.DoesNotExist:
        return redirect('login')
    
    # Get current date - important for expiration comparison
    today = timezone.now().date()
    
    # Get quizzes assigned to this specific user that are not expired
    available_quizzes = Quiz.objects.filter(
        student=user,
        quiz_expire_date__gte=today  # Only get quizzes not expired
    ).order_by('quiz_expire_date')
    
    # Debug output
    print(f"DEBUG: Today: {today}")
    print(f"DEBUG: Available quizzes: {list(available_quizzes.values('id', 'course', 'quiz_expire_date'))}")
    
    # Get the user's course list
    user_courses = []
    if user.courses:
        if isinstance(user.courses, str):
            try:
                import json
                user_courses = json.loads(user.courses)
            except:
                user_courses = []
        else:
            user_courses = user.courses
    
    # Get quiz history
    quiz_history = QuizHistory.objects.filter(quiz__student=user).order_by('-quiz_date')
    
    return render(request, 'user_page.html', {
        'username': active_user,
        'user': user,
        'available_quizzes': available_quizzes,
        'user_courses': user_courses,
        'quiz_history': quiz_history,
        'today': today  # Pass current date to template
    })

def take_quiz(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')
    
    # Check if quiz is expired
    today = timezone.now().date()
    if quiz.quiz_expire_date < today:
        messages.error(request, f"This quiz expired on {quiz.quiz_expire_date}. Please contact your instructor.")
        return redirect('user_view')
    
    num_questions = quiz.num_questions
    course = quiz.course
    
    # Improved question filtering - try multiple methods to find questions
    # First attempt: Try exact match
    questions = Questions.objects.filter(course__exact=course)
    
    # Second attempt: Try contains with quotes (for JSON stored courses)
    if questions.count() == 0:
        questions = Questions.objects.filter(course__contains=course)
    
    # Third attempt: Try icontains to make it case insensitive
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=course)
    
    # Fourth attempt: Try with JSON formatting
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=f'"{course}"')
    
    # Fifth attempt: If course is stored as a list, try a more generic approach
    if questions.count() == 0:
        # Get all questions and filter manually
        all_questions = Questions.objects.all()
        filtered_questions = []
        
        for question in all_questions:
            # Try to parse the course field if it's a string
            question_courses = question.course
            if isinstance(question_courses, str):
                try:
                    import json
                    question_courses = json.loads(question_courses)
                except:
                    # If parsing fails, treat it as a single course
                    question_courses = [question_courses]
            
            # Check if the course exists in the list
            if course in question_courses:
                filtered_questions.append(question)
        
        # Convert the filtered list to a queryset if needed
        if filtered_questions:
            from django.db.models import Q
            question_ids = [q.id for q in filtered_questions]
            questions = Questions.objects.filter(id__in=question_ids)
    
    # Check if we have enough questions for this quiz
    available_question_count = questions.count()
    
    if available_question_count == 0:
        # Debug information to help troubleshoot
        print(f"DEBUG: No questions found for course {course}")
        print(f"DEBUG: Quiz ID: {quiz_id}")
        print(f"DEBUG: All questions: {list(Questions.objects.all().values_list('id', 'course'))}")
        
        messages.error(request, f"No questions are available for course {course}. Please contact your instructor.")
        return redirect('user_view')
    
    if available_question_count < num_questions:
        # Not enough questions available, adjust num_questions
        num_questions = available_question_count
        messages.warning(
            request, 
            f"This quiz was configured for {quiz.num_questions} questions, but only {num_questions} are available for course {course}."
        )
    
    # Now safely select random questions
    selected_questions = random.sample(list(questions), num_questions)
    
    # For POST method (submitting the quiz)
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        num_correct = 0
        num_wrong = 0
        
        for question in selected_questions:
            # Get user's answer for this question
            user_answer = request.POST.get(f'answer_{question.id}')
            
            # Check if answer is correct
            if user_answer == question.correct_answer:
                num_correct += 1
            else:
                num_wrong += 1
        
        # Calculate score
        total_questions = num_correct + num_wrong
        if total_questions > 0:
            score = (num_correct / total_questions) * 100
        
        # Save quiz history
        quiz_history = QuizHistory.objects.create(
            quiz=quiz,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,
            quiz_date=today
        )
        
        # Render results page
        return render(request, 'submit_quiz.html', {
            'score': score,
            'num_correct': num_correct,
            'num_wrong': num_wrong,
            'quiz_date': today
        })
    
    # For GET method (displaying the quiz)
    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': selected_questions,
        'quiz_duration': quiz.quiz_duration
    })

def submit_quiz(request, quiz_id_active):
    if request.method == 'POST':
        user_inputs = {key: request.POST[key] for key in request.POST.keys() if key.startswith('answer_')}
        quiz_ids = [int(key.replace('answer_', '')) for key in user_inputs.keys()]
        correct_answers = Questions.objects.filter(id__in=quiz_ids).values_list('id', 'correct_answer')

        num_correct = 0
        num_wrong = 0
        for quiz_id, correct_answer in correct_answers:
            user_input = user_inputs.get(f'answer_{quiz_id}')
            if user_input == correct_answer:
                num_correct += 1
            else:
                num_wrong += 1

        total_questions=num_correct+num_wrong
        if total_questions > 0:
            score = (num_correct/total_questions)*100
        else:
            score = 0  
        # Save quiz data to QuizHistory table
        quiz_date = timezone.now().date()
        quiz_instance = Quiz.objects.get(pk=quiz_id_active)
        
        QuizHistory.objects.create(
            quiz=quiz_instance,
            quiz_date=quiz_date,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,            
        )        
        # Display the results on submit_quiz.html
        return render(request, 'submit_quiz.html', {'score':round(score, 2), 'num_correct': num_correct, 'num_wrong': num_wrong, 'quiz_date':quiz_date})

def signup(request, role):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign user to appropriate group based on role
            if role == 'student':
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
            elif role == 'professor':
                professor_group, _ = Group.objects.get_or_create(name='Professor')
                user.groups.add(professor_group)
            
            return redirect('login')
    else:
        form = UserCreationForm()
    
    # Add Bootstrap classes to form fields
    form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
    form.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
    form.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    return render(request, 'signup.html', {
        'form': form,
        'role': role
    })

def admin_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'user')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses', '[]')
        
        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'admin_signup.html')
        
        # Create user using your custom User model
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses
        )
        
        # Add success message - this will be displayed on the signup page before redirecting
        success_message = f"{username}'s account is created successfully!"
        
        # Render the template with the success message
        context = {'success_message': success_message}
        return render(request, 'signup_success.html', context)
    
    return render(request, 'admin_signup.html')

def create_test_questions(request):
    """Create test questions for troubleshooting"""
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        num_to_create = int(request.POST.get('num_questions', 1))
        
        # Format course name properly
        import json
        course_json = json.dumps([course_name])
        
        # Create the specified number of questions
        questions_created = 0
        for i in range(1, num_to_create + 1):
            Questions.objects.create(
                question=f"Test question #{i} for {course_name}",
                course=course_json,
                option1=f"Option 1 for question {i}",
                option2=f"Option 2 for question {i}",
                option3=f"Option 3 for question {i}",
                option4=f"Option 4 for question {i}",
                correct_answer="option1"  # Make option1 always correct for test questions
            )
            questions_created += 1
        
        return HttpResponse(
            f"<h3>Created {questions_created} test questions for course {course_name}</h3>" +
            f"<p>Course stored as: {course_json}</p>" +
            f"<p><a href='/quiz/admin/'>Return to Admin Dashboard</a></p>"
        )
    
    # Display form for GET request
    return render(request, 'create_test_questions.html', {})

def admin_view(request):
    active_user = request.session.get('user')
    users = User.objects.all()
    questions = Questions.objects.all()
    quizzes = Quiz.objects.all()
    all_quiz_history = QuizHistory.objects.all()
    
    # Clean up the course data display
    distinct_courses = set()
    for question in questions:
        # Extract courses as plain text
        if question.course:
            # Try to detect if it's a JSON string (from older data)
            if question.course.startswith('[') and question.course.endswith(']'):
                try:
                    import json
                    parsed_courses = json.loads(question.course)
                    if isinstance(parsed_courses, list):
                        for course in parsed_courses:
                            if course:  # Skip empty entries
                                distinct_courses.add(course.strip())
                    else:
                        distinct_courses.add(str(parsed_courses).strip())
                except:
                    # If JSON parsing fails, add as is
                    distinct_courses.add(question.course.strip())
            else:
                # It's already plain text
                distinct_courses.add(question.course.strip())
    
    # Convert to list and sort
    distinct_courses = sorted(list(distinct_courses))
    
    # Count questions per course
    course_question_counts = {}
    for course in distinct_courses:
        # Count questions with exact course match
        count = Questions.objects.filter(course=course).count()
        
        # Also try with JSON formatted courses for backwards compatibility
        if count == 0:
            count = Questions.objects.filter(course__icontains=f'"{course}"').count()
            
        course_question_counts[course] = count
    
    # Format for template
    courses_with_counts = [
        {'name': course, 'question_count': course_question_counts.get(course, 0)} 
        for course in distinct_courses
    ]
    
    # Prepare users data with properly formatted courses for JavaScript
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_role': user.user_role,
        }
        
        # Clean and parse courses to ensure it's always a properly formatted array
        clean_courses = []
        if user.courses is None:
            pass  # Keep empty list
        elif isinstance(user.courses, str):
            try:
                import json
                parsed_courses = json.loads(user.courses)
                if isinstance(parsed_courses, list):
                    for course in parsed_courses:
                        if isinstance(course, str):
                            # Clean up any poorly formatted course names
                            clean_course = course.replace('\n', '').replace('"', '').strip()
                            clean_courses.append(clean_course)
                        else:
                            clean_courses.append(str(course))
                else:
                    clean_course = str(parsed_courses).replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
            except:
                # If parsing fails, try to clean the string itself
                if user.courses:
                    clean_course = user.courses.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
        elif isinstance(user.courses, list):
            for course in user.courses:
                if isinstance(course, str):
                    clean_course = course.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
                else:
                    clean_courses.append(str(course))
        
        user_data['courses'] = clean_courses
        users_data.append(user_data)
    
    # Get today's date for the minimum date in the expiry date picker
    today_date = timezone.now()

    # Define choices for number of questions (for dropdowns etc.)
    num_questions_choices = list(range(1, 51))
    
    # Add a field to track which quiz is currently selected for adding questions
    active_quiz_id = None
    
    # Process POST request for adding questions
    if request.method == 'POST' and request.POST.get('form_type') == 'add_question':
        question_text = request.POST.get('question')
        course = request.POST.get('course')
        quiz_id = request.POST.get('quiz_id')  # Get the quiz ID
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        correct_answer = request.POST.get('correct_answer')
        
        # Store course as plain text - no JSON encoding
        
        # Create the question
        new_question = Questions.objects.create(
            question=question_text,
            course=course,  # Store as plain text
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_answer=correct_answer
        )
        
        # Associate the question with the quiz if provided
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                # Store quiz-question relationship (you might need to add a field to your Quiz model)
                # For example: quiz.questions.add(new_question)
                messages.success(request, f"Question added successfully and associated with quiz {quiz_id}!")
            except Quiz.DoesNotExist:
                messages.warning(request, "Quiz not found, question added but not associated with any quiz.")
        else:
            messages.success(request, f"Question for course {course} added successfully!")
            
        return redirect('admin_view')
        
    # Ensure users_data is properly JSON serialized for JavaScript
    import json
    users_json = json.dumps(users_data)
    
    # Fix course display formatting
    for question in questions:
        # Fix the course display format
        if isinstance(question.course, str):
            try:
                # Try to parse as JSON
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    # Join list elements into a readable string
                    question.display_course = ", ".join([str(c) for c in courses if c])
                else:
                    question.display_course = str(courses)
            except:
                # If parsing fails, use as is
                question.display_course = question.course
        elif isinstance(question.course, list):
            question.display_course = ", ".join([str(c) for c in question.course if c])
        else:
            question.display_course = str(question.course)
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    return render(request, 'admin_page.html', {
        'all_quiz_history': all_quiz_history,
        'quizzes': quizzes, 
        'users': users_data,  
        'users_json': users_json,  # Add this new variable for JavaScript
        'questions': questions, 
        'active_user': active_user,
        'num_questions_choices': num_questions_choices,
        'distinct_courses': courses_with_counts,
        'today_date': today_date
    })

def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses')
        
        # Process courses to ensure they're stored as plain text
        # If multiple courses are provided as comma-separated, store them as-is
        # No JSON encoding
        
        # Create the user
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses  # Store as plain text
        )
        
        return redirect('admin_view')
    
    return redirect('admin_view')

def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    user.delete()
    return redirect('admin_view')

def modify_question(request, question_id):
    question = Questions.objects.get(pk=question_id)
    
    if request.method == 'POST':
        # Handle modification logic here
        question.question = request.POST.get('question')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_answer = request.POST.get('correct_answer')
        question.course = request.POST.get('question_course')
        question.save()
        return redirect('admin_view')

    return render(request, 'modify_question.html', {'question': question})

def delete_question(request, question_id):
    quiz = Questions.objects.get(pk=question_id)
    quiz.delete()
    return redirect('admin_view')

def create_quiz(request):
    if request.method == 'POST':
        course = request.POST.get('course')
        student_id = request.POST.get('student_id')
        
        # Get num_questions as an integer
        try:
            num_questions = int(request.POST.get('num_questions', 10))
            # Enforce reasonable limits
            if num_questions < 1:
                num_questions = 1
            elif num_questions > 50:
                num_questions = 50
        except ValueError:
            # Default to 10 if conversion fails
            num_questions = 10
            
        quiz_duration = int(request.POST.get('quiz_duration', 30))
        quiz_expire_date = request.POST.get('quiz_expire_date')
        
        # Ensure the student exists
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            messages.error(request, "Invalid student selection")
            return redirect('admin_view')
        
        # Check if this course exists for the selected student
        student_courses = []
        if isinstance(student.courses, str):
            try:
                import json
                student_courses = json.loads(student.courses)
            except:
                student_courses = []
        else:
            student_courses = student.courses
            
        if course not in student_courses:
            messages.error(request, f"Course '{course}' is not assigned to student {student.username}")
            return redirect('admin_view')
            
        # Check how many questions are available for this course
        # First try exact match
        questions = Questions.objects.filter(course__exact=course)
        
        # If no questions found, try contains with quotes for JSON stored courses
        if questions.count() == 0:
            questions = Questions.objects.filter(course__icontains=f'"{course}"')
        
        # Third attempt: Try with more flexible approach for JSON array fields
        if questions.count() == 0:
            from django.db.models import Q
            questions = Questions.objects.filter(
                Q(course__icontains=course) | 
                Q(course__icontains=f'"{course}"')
            )
        
        available_question_count = questions.count()
        
        if available_question_count == 0:
            messages.error(request, f"No questions available for the course '{course}'")
            return redirect('admin_view')
            
        if available_question_count < num_questions:
            messages.warning(request, f"Only {available_question_count} questions available for this course. Quiz created with {available_question_count} questions.")
            num_questions = available_question_count
            
        # Create the quiz
        Quiz.objects.create(
            course=course,
            num_questions=num_questions,
            quiz_duration=quiz_duration,
            quiz_expire_date=quiz_expire_date,
            student=student
        )
        
        messages.success(request, f"Quiz created successfully for {student.username} with {num_questions} questions")
        return redirect('admin_view')
    
    # If not POST request, redirect to admin view
    return redirect('admin_view')

def delete_quiz(request, quiz_id):
    quiz = Quiz.objects.get(pk=quiz_id)
    quiz.delete()
    return redirect('admin_view')

def user_view(request):
    active_user = request.session.get('user')
    
    if not active_user:
        return redirect('login')
    
    try:
        user = User.objects.get(username=active_user)
    except User.DoesNotExist:
        return redirect('login')
    
    # Get current date - important for expiration comparison
    today = timezone.now().date()
    
    # Get quizzes assigned to this specific user that are not expired
    available_quizzes = Quiz.objects.filter(
        student=user,
        quiz_expire_date__gte=today  # Only get quizzes not expired
    ).order_by('quiz_expire_date')
    
    # Debug output
    print(f"DEBUG: Today: {today}")
    print(f"DEBUG: Available quizzes: {list(available_quizzes.values('id', 'course', 'quiz_expire_date'))}")
    
    # Get the user's course list
    user_courses = []
    if user.courses:
        if isinstance(user.courses, str):
            try:
                import json
                user_courses = json.loads(user.courses)
            except:
                user_courses = []
        else:
            user_courses = user.courses
    
    # Get quiz history
    quiz_history = QuizHistory.objects.filter(quiz__student=user).order_by('-quiz_date')
    
    return render(request, 'user_page.html', {
        'username': active_user,
        'user': user,
        'available_quizzes': available_quizzes,
        'user_courses': user_courses,
        'quiz_history': quiz_history,
        'today': today  # Pass current date to template
    })

def take_quiz(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')
    
    # Check if quiz is expired
    today = timezone.now().date()
    if quiz.quiz_expire_date < today:
        messages.error(request, f"This quiz expired on {quiz.quiz_expire_date}. Please contact your instructor.")
        return redirect('user_view')
    
    num_questions = quiz.num_questions
    course = quiz.course
    
    # Improved question filtering - try multiple methods to find questions
    # First attempt: Try exact match
    questions = Questions.objects.filter(course__exact=course)
    
    # Second attempt: Try contains with quotes (for JSON stored courses)
    if questions.count() == 0:
        questions = Questions.objects.filter(course__contains=course)
    
    # Third attempt: Try icontains to make it case insensitive
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=course)
    
    # Fourth attempt: Try with JSON formatting
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=f'"{course}"')
    
    # Fifth attempt: If course is stored as a list, try a more generic approach
    if questions.count() == 0:
        # Get all questions and filter manually
        all_questions = Questions.objects.all()
        filtered_questions = []
        
        for question in all_questions:
            # Try to parse the course field if it's a string
            question_courses = question.course
            if isinstance(question_courses, str):
                try:
                    import json
                    question_courses = json.loads(question_courses)
                except:
                    # If parsing fails, treat it as a single course
                    question_courses = [question_courses]
            
            # Check if the course exists in the list
            if course in question_courses:
                filtered_questions.append(question)
        
        # Convert the filtered list to a queryset if needed
        if filtered_questions:
            from django.db.models import Q
            question_ids = [q.id for q in filtered_questions]
            questions = Questions.objects.filter(id__in=question_ids)
    
    # Check if we have enough questions for this quiz
    available_question_count = questions.count()
    
    if available_question_count == 0:
        # Debug information to help troubleshoot
        print(f"DEBUG: No questions found for course {course}")
        print(f"DEBUG: Quiz ID: {quiz_id}")
        print(f"DEBUG: All questions: {list(Questions.objects.all().values_list('id', 'course'))}")
        
        messages.error(request, f"No questions are available for course {course}. Please contact your instructor.")
        return redirect('user_view')
    
    if available_question_count < num_questions:
        # Not enough questions available, adjust num_questions
        num_questions = available_question_count
        messages.warning(
            request, 
            f"This quiz was configured for {quiz.num_questions} questions, but only {num_questions} are available for course {course}."
        )
    
    # Now safely select random questions
    selected_questions = random.sample(list(questions), num_questions)
    
    # For POST method (submitting the quiz)
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        num_correct = 0
        num_wrong = 0
        
        for question in selected_questions:
            # Get user's answer for this question
            user_answer = request.POST.get(f'answer_{question.id}')
            
            # Check if answer is correct
            if user_answer == question.correct_answer:
                num_correct += 1
            else:
                num_wrong += 1
        
        # Calculate score
        total_questions = num_correct + num_wrong
        if total_questions > 0:
            score = (num_correct / total_questions) * 100
        
        # Save quiz history
        quiz_history = QuizHistory.objects.create(
            quiz=quiz,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,
            quiz_date=today
        )
        
        # Render results page
        return render(request, 'submit_quiz.html', {
            'score': score,
            'num_correct': num_correct,
            'num_wrong': num_wrong,
            'quiz_date': today
        })
    
    # For GET method (displaying the quiz)
    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': selected_questions,
        'quiz_duration': quiz.quiz_duration
    })

def submit_quiz(request, quiz_id_active):
    if request.method == 'POST':
        user_inputs = {key: request.POST[key] for key in request.POST.keys() if key.startswith('answer_')}
        quiz_ids = [int(key.replace('answer_', '')) for key in user_inputs.keys()]
        correct_answers = Questions.objects.filter(id__in=quiz_ids).values_list('id', 'correct_answer')

        num_correct = 0
        num_wrong = 0
        for quiz_id, correct_answer in correct_answers:
            user_input = user_inputs.get(f'answer_{quiz_id}')
            if user_input == correct_answer:
                num_correct += 1
            else:
                num_wrong += 1

        total_questions=num_correct+num_wrong
        if total_questions > 0:
            score = (num_correct/total_questions)*100
        else:
            score = 0  
        # Save quiz data to QuizHistory table
        quiz_date = timezone.now().date()
        quiz_instance = Quiz.objects.get(pk=quiz_id_active)
        
        QuizHistory.objects.create(
            quiz=quiz_instance,
            quiz_date=quiz_date,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,            
        )        
        # Display the results on submit_quiz.html
        return render(request, 'submit_quiz.html', {'score':round(score, 2), 'num_correct': num_correct, 'num_wrong': num_wrong, 'quiz_date':quiz_date})

def signup(request, role):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign user to appropriate group based on role
            if role == 'student':
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
            elif role == 'professor':
                professor_group, _ = Group.objects.get_or_create(name='Professor')
                user.groups.add(professor_group)
            
            return redirect('login')
    else:
        form = UserCreationForm()
    
    # Add Bootstrap classes to form fields
    form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
    form.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
    form.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    return render(request, 'signup.html', {
        'form': form,
        'role': role
    })

def admin_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'user')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses', '[]')
        
        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'admin_signup.html')
        
        # Create user using your custom User model
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses
        )
        
        # Add success message - this will be displayed on the signup page before redirecting
        success_message = f"{username}'s account is created successfully!"
        
        # Render the template with the success message
        context = {'success_message': success_message}
        return render(request, 'signup_success.html', context)
    
    return render(request, 'admin_signup.html')

def create_test_questions(request):
    """Create test questions for troubleshooting"""
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        num_to_create = int(request.POST.get('num_questions', 1))
        
        # Format course name properly
        import json
        course_json = json.dumps([course_name])
        
        # Create the specified number of questions
        questions_created = 0
        for i in range(1, num_to_create + 1):
            Questions.objects.create(
                question=f"Test question #{i} for {course_name}",
                course=course_json,
                option1=f"Option 1 for question {i}",
                option2=f"Option 2 for question {i}",
                option3=f"Option 3 for question {i}",
                option4=f"Option 4 for question {i}",
                correct_answer="option1"  # Make option1 always correct for test questions
            )
            questions_created += 1
        
        return HttpResponse(
            f"<h3>Created {questions_created} test questions for course {course_name}</h3>" +
            f"<p>Course stored as: {course_json}</p>" +
            f"<p><a href='/quiz/admin/'>Return to Admin Dashboard</a></p>"
        )
    
    # Display form for GET request
    return render(request, 'create_test_questions.html', {})

def admin_view(request):
    active_user = request.session.get('user')
    users = User.objects.all()
    questions = Questions.objects.all()
    quizzes = Quiz.objects.all()
    all_quiz_history = QuizHistory.objects.all()
    
    # Clean up the course data display
    distinct_courses = set()
    for question in questions:
        # Extract courses as plain text
        if question.course:
            # Try to detect if it's a JSON string (from older data)
            if question.course.startswith('[') and question.course.endswith(']'):
                try:
                    import json
                    parsed_courses = json.loads(question.course)
                    if isinstance(parsed_courses, list):
                        for course in parsed_courses:
                            if course:  # Skip empty entries
                                distinct_courses.add(course.strip())
                    else:
                        distinct_courses.add(str(parsed_courses).strip())
                except:
                    # If JSON parsing fails, add as is
                    distinct_courses.add(question.course.strip())
            else:
                # It's already plain text
                distinct_courses.add(question.course.strip())
    
    # Convert to list and sort
    distinct_courses = sorted(list(distinct_courses))
    
    # Count questions per course
    course_question_counts = {}
    for course in distinct_courses:
        # Count questions with exact course match
        count = Questions.objects.filter(course=course).count()
        
        # Also try with JSON formatted courses for backwards compatibility
        if count == 0:
            count = Questions.objects.filter(course__icontains=f'"{course}"').count()
            
        course_question_counts[course] = count
    
    # Format for template
    courses_with_counts = [
        {'name': course, 'question_count': course_question_counts.get(course, 0)} 
        for course in distinct_courses
    ]
    
    # Prepare users data with properly formatted courses for JavaScript
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_role': user.user_role,
        }
        
        # Clean and parse courses to ensure it's always a properly formatted array
        clean_courses = []
        if user.courses is None:
            pass  # Keep empty list
        elif isinstance(user.courses, str):
            try:
                import json
                parsed_courses = json.loads(user.courses)
                if isinstance(parsed_courses, list):
                    for course in parsed_courses:
                        if isinstance(course, str):
                            # Clean up any poorly formatted course names
                            clean_course = course.replace('\n', '').replace('"', '').strip()
                            clean_courses.append(clean_course)
                        else:
                            clean_courses.append(str(course))
                else:
                    clean_course = str(parsed_courses).replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
            except:
                # If parsing fails, try to clean the string itself
                if user.courses:
                    clean_course = user.courses.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
        elif isinstance(user.courses, list):
            for course in user.courses:
                if isinstance(course, str):
                    clean_course = course.replace('\n', '').replace('"', '').strip()
                    clean_courses.append(clean_course)
                else:
                    clean_courses.append(str(course))
        
        user_data['courses'] = clean_courses
        users_data.append(user_data)
    
    # Get today's date for the minimum date in the expiry date picker
    today_date = timezone.now()

    # Define choices for number of questions (for dropdowns etc.)
    num_questions_choices = list(range(1, 51))
    
    # Add a field to track which quiz is currently selected for adding questions
    active_quiz_id = None
    
    # Process POST request for adding questions
    if request.method == 'POST' and request.POST.get('form_type') == 'add_question':
        question_text = request.POST.get('question')
        course = request.POST.get('course')
        quiz_id = request.POST.get('quiz_id')  # Get the quiz ID
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        option4 = request.POST.get('option4')
        correct_answer = request.POST.get('correct_answer')
        
        # Store course as plain text - no JSON encoding
        
        # Create the question
        new_question = Questions.objects.create(
            question=question_text,
            course=course,  # Store as plain text
            option1=option1,
            option2=option2,
            option3=option3,
            option4=option4,
            correct_answer=correct_answer
        )
        
        # Associate the question with the quiz if provided
        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id)
                # Store quiz-question relationship (you might need to add a field to your Quiz model)
                # For example: quiz.questions.add(new_question)
                messages.success(request, f"Question added successfully and associated with quiz {quiz_id}!")
            except Quiz.DoesNotExist:
                messages.warning(request, "Quiz not found, question added but not associated with any quiz.")
        else:
            messages.success(request, f"Question for course {course} added successfully!")
            
        return redirect('admin_view')
        
    # Ensure users_data is properly JSON serialized for JavaScript
    import json
    users_json = json.dumps(users_data)
    
    # Fix course display formatting
    for question in questions:
        # Fix the course display format
        if isinstance(question.course, str):
            try:
                # Try to parse as JSON
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    # Join list elements into a readable string
                    question.display_course = ", ".join([str(c) for c in courses if c])
                else:
                    question.display_course = str(courses)
            except:
                # If parsing fails, use as is
                question.display_course = question.course
        elif isinstance(question.course, list):
            question.display_course = ", ".join([str(c) for c in question.course if c])
        else:
            question.display_course = str(question.course)
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    # Fix course display for questions
    for question in questions:
        # If it looks like JSON, parse it for display purposes
        if isinstance(question.course, str) and question.course.startswith('['):
            try:
                import json
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    question.display_course = ", ".join(c for c in courses if c)
                else:
                    question.display_course = str(courses)
            except:
                question.display_course = question.course
        else:
            # It's already plain text
            question.display_course = question.course
    
    return render(request, 'admin_page.html', {
        'all_quiz_history': all_quiz_history,
        'quizzes': quizzes, 
        'users': users_data,  
        'users_json': users_json,  # Add this new variable for JavaScript
        'questions': questions, 
        'active_user': active_user,
        'num_questions_choices': num_questions_choices,
        'distinct_courses': courses_with_counts,
        'today_date': today_date
    })

def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses')
        
        # Process courses to ensure they're stored as plain text
        # If multiple courses are provided as comma-separated, store them as-is
        # No JSON encoding
        
        # Create the user
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses  # Store as plain text
        )
        
        return redirect('admin_view')
    
    return redirect('admin_view')

def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    user.delete()
    return redirect('admin_view')

def modify_question(request, question_id):
    question = Questions.objects.get(pk=question_id)
    
    if request.method == 'POST':
        # Handle modification logic here
        question.question = request.POST.get('question')
        question.option1 = request.POST.get('option1')
        question.option2 = request.POST.get('option2')
        question.option3 = request.POST.get('option3')
        question.option4 = request.POST.get('option4')
        question.correct_answer = request.POST.get('correct_answer')
        question.course = request.POST.get('question_course')
        question.save()
        return redirect('admin_view')

    return render(request, 'modify_question.html', {'question': question})

def delete_question(request, question_id):
    quiz = Questions.objects.get(pk=question_id)
    quiz.delete()
    return redirect('admin_view')

def create_quiz(request):
    if request.method == 'POST':
        course = request.POST.get('course')
        student_id = request.POST.get('student_id')
        
        # Get num_questions as an integer
        try:
            num_questions = int(request.POST.get('num_questions', 10))
            # Enforce reasonable limits
            if num_questions < 1:
                num_questions = 1
            elif num_questions > 50:
                num_questions = 50
        except ValueError:
            # Default to 10 if conversion fails
            num_questions = 10
            
        quiz_duration = int(request.POST.get('quiz_duration', 30))
        quiz_expire_date = request.POST.get('quiz_expire_date')
        
        # Ensure the student exists
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            messages.error(request, "Invalid student selection")
            return redirect('admin_view')
        
        # Check if this course exists for the selected student
        student_courses = []
        if isinstance(student.courses, str):
            try:
            try:
                import json
                user_courses = json.loads(user.courses)
            except:
                user_courses = []
        else:
            user_courses = user.courses
    
    # Get quiz history
    quiz_history = QuizHistory.objects.filter(quiz__student=user).order_by('-quiz_date')
    
    return render(request, 'user_page.html', {
        'username': active_user,
        'user': user,
        'available_quizzes': available_quizzes,
        'user_courses': user_courses,
        'quiz_history': quiz_history,
        'today': today  # Pass current date to template
    })

def take_quiz(request, quiz_id):
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')
    
    # Check if quiz is expired
    today = timezone.now().date()
    if quiz.quiz_expire_date < today:
        messages.error(request, f"This quiz expired on {quiz.quiz_expire_date}. Please contact your instructor.")
        return redirect('user_view')
    
    num_questions = quiz.num_questions
    course = quiz.course
    
    # Improved question filtering - try multiple methods to find questions
    # First attempt: Try exact match
    questions = Questions.objects.filter(course__exact=course)
    
    # Second attempt: Try contains with quotes (for JSON stored courses)
    if questions.count() == 0:
        questions = Questions.objects.filter(course__contains=course)
    
    # Third attempt: Try icontains to make it case insensitive
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=course)
    
    # Fourth attempt: Try with JSON formatting
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=f'"{course}"')
    
    # Fifth attempt: If course is stored as a list, try a more generic approach
    if questions.count() == 0:
        # Get all questions and filter manually
        all_questions = Questions.objects.all()
        filtered_questions = []
        
        for question in all_questions:
            # Try to parse the course field if it's a string
            question_courses = question.course
            if isinstance(question_courses, str):
                try:
                    import json
                    question_courses = json.loads(question_courses)
                except:
                    # If parsing fails, treat it as a single course
                    question_courses = [question_courses]
            
            # Check if the course exists in the list
            if course in question_courses:
                filtered_questions.append(question)
        
        # Convert the filtered list to a queryset if needed
        if filtered_questions:
            from django.db.models import Q
            question_ids = [q.id for q in filtered_questions]
            questions = Questions.objects.filter(id__in=question_ids)
    
    # Check if we have enough questions for this quiz
    available_question_count = questions.count()
    
    if available_question_count == 0:
        # Debug information to help troubleshoot
        print(f"DEBUG: No questions found for course {course}")
        print(f"DEBUG: Quiz ID: {quiz_id}")
        print(f"DEBUG: All questions: {list(Questions.objects.all().values_list('id', 'course'))}")
        
        messages.error(request, f"No questions are available for course {course}. Please contact your instructor.")
        return redirect('user_view')
    
    if available_question_count < num_questions:
        # Not enough questions available, adjust num_questions
        num_questions = available_question_count
        messages.warning(
            request, 
            f"This quiz was configured for {quiz.num_questions} questions, but only {num_questions} are available for course {course}."
        )
    
    # Now safely select random questions
    selected_questions = random.sample(list(questions), num_questions)
    
    # For POST method (submitting the quiz)
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        num_correct = 0
        num_wrong = 0
        
        for question in selected_questions:
            # Get user's answer for this question
            user_answer = request.POST.get(f'answer_{question.id}')
            
            # Check if answer is correct
            if user_answer == question.correct_answer:
                num_correct += 1
            else:
                num_wrong += 1
        
        # Calculate score
        total_questions = num_correct + num_wrong
        if total_questions > 0:
            score = (num_correct / total_questions) * 100
        
        # Save quiz history
        quiz_history = QuizHistory.objects.create(
            quiz=quiz,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,
            quiz_date=today
        )
        
        # Render results page
        return render(request, 'submit_quiz.html', {
            'score': score,
            'num_correct': num_correct,
            'num_wrong': num_wrong,
            'quiz_date': today
        })
    
    # For GET method (displaying the quiz)
    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': selected_questions,
        'quiz_duration': quiz.quiz_duration
    })

def submit_quiz(request, quiz_id_active):
    if request.method == 'POST':
        user_inputs = {key: request.POST[key] for key in request.POST.keys() if key.startswith('answer_')}
        quiz_ids = [int(key.replace('answer_', '')) for key in user_inputs.keys()]
        correct_answers = Questions.objects.filter(id__in=quiz_ids).values_list('id', 'correct_answer')

        num_correct = 0
        num_wrong = 0
        for quiz_id, correct_answer in correct_answers:
            user_input = user_inputs.get(f'answer_{quiz_id}')
            if user_input == correct_answer:
                num_correct += 1
            else:
                num_wrong += 1

        total_questions=num_correct+num_wrong
        if total_questions > 0:
            score = (num_correct/total_questions)*100
        else:
            score = 0  
        # Save quiz data to QuizHistory table
        quiz_date = timezone.now().date()
        quiz_instance = Quiz.objects.get(pk=quiz_id_active)
        
        QuizHistory.objects.create(
            quiz=quiz_instance,
            quiz_date=quiz_date,
            score=score,
            num_correct=num_correct,
            num_wrong=num_wrong,            
        )        
        # Display the results on submit_quiz.html
        return render(request, 'submit_quiz.html', {'score':round(score, 2), 'num_correct': num_correct, 'num_wrong': num_wrong, 'quiz_date':quiz_date})

def signup(request, role):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Assign user to appropriate group based on role
            if role == 'student':
                student_group, _ = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
            elif role == 'professor':
                professor_group, _ = Group.objects.get_or_create(name='Professor')
                user.groups.add(professor_group)
            
            return redirect('login')
    else:
        form = UserCreationForm()
    
    # Add Bootstrap classes to form fields
    form.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Username'})
    form.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
    form.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})
    
    return render(request, 'signup.html', {
        'form': form,
        'role': role
    })

def admin_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'user')
        user_type = request.POST.get('user_type')
        courses = request.POST.get('courses', '[]')
        
        # Basic validation
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return render(request, 'admin_signup.html')
        
        # Create user using your custom User model
        User.objects.create(
            username=username,
            password=password,
            user_role=user_role,
            user_type=user_type,
            courses=courses
        )
        
        # Add success message - this will be displayed on the signup page before redirecting
        success_message = f"{username}'s account is created successfully!"
        
        # Render the template with the success message
        context = {'success_message': success_message}
        return render(request, 'signup_success.html', context)
    
    return render(request, 'admin_signup.html')

def create_test_questions(request):
    """Create test questions for troubleshooting"""
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        num_to_create = int(request.POST.get('num_questions', 1))
        
        # Format course name properly
        import json
        course_json = json.dumps([course_name])
        
        # Create the specified number of questions
        questions_created = 0
        for i in range(1, num_to_create + 1):
            Questions.objects.create(
                question=f"Test question #{i} for {course_name}",
                course=course_json,
                option1=f"Option 1 for question {i}",
                option2=f"Option 2 for question {i}",
                option3=f"Option 3 for question {i}",
                option4=f"Option 4 for question {i}",
                correct_answer="option1"  # Make option1 always correct for test questions
            )
            questions_created += 1
        
        return HttpResponse(
            f"<h3>Created {questions_created} test questions for course {course_name}</h3>" +
            f"<p>Course stored as: {course_json}</p>" +
            f"<p><a href='/quiz/admin/'>Return to Admin Dashboard</a></p>"
        )
    
    # Display form for GET request
    return render(request, 'create_test_questions.html', {})

def admin_view(request):
    active_user = request.session.get('user')
    users = User.objects.all()
    questions = Questions.objects.all()
    quizzes = Quiz.objects.all()
    all_quiz_history = QuizHistory.objects.all()
    
    # Clean up the course data display
    distinct_courses = set()
    for question in questions:
        # Extract courses as plain text
        if question.course:
            # Try to detect if it's a JSON string (from older data)
            if question.course.startswith('[') and question.course.endswith(']'):
                try:
                    import json
                    parsed_courses = json.loads(question.course)
                    if isinstance(parsed_courses, list):
                        for course in parsed_courses:
                            if course:  # Skip empty entries
                                distinct_courses.add(course.strip())
                    else:
                        distinct_courses.add(str(parsed_courses).strip())
                except:
                    # If JSON parsing fails, add as is
                    distinct_courses.add(question.course.strip())
            else:
                # It's already plain text
                distinct_courses.add(question.course.strip())
    
    # Convert to list and sort
    distinct_courses = sorted(list(distinct_courses))
    
    # Count questions per course
    course_question_counts = {}
    for course in distinct_courses:
        # Count questions with exact course match
        count = Questions.objects.filter(course=course).count()
        
        # Also try with JSON formatted courses for backwards compatibility
        if count == 0:
            count = Questions.objects.filter(course__icontains=f'"{course}"').count()
            
        course_question_counts[course] = count
    
    # Format for template
    courses_with_counts = [
        {'name': course, 'question_count': course_question_counts.get(course, 0)} 
        for course in distinct_courses
    ]
    
    # Prepare users data with properly formatted courses for JavaScript
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'user_type': user.user_type,
            'user_role': user.user_role,
        }
        
        # Clean and parse courses to ensure it's always a properly formatted array
        clean_courses = []
        if user.courses is None:
            pass  # Keep empty list
        elif isinstance(user.courses, str):
            try: