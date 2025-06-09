from django.shortcuts import render, redirect
from django.contrib import messages
from .models import User, Questions, Quiz, QuizHistory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.contrib.auth import logout
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.http import HttpResponse, JsonResponse
import json

def login_view(request):
    """Handle user login with proper authentication"""
    # Check for signup success parameter - this could come from redirects
    signup_success = request.GET.get('signup_success')
    if signup_success == 'true':
        messages.success(request, "Account created successfully! You can now log in.")

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(username=username, password=password)
            request.session['user'] = username
            
            if user.role == 'admin':
                return redirect('admin_view')
            else:
                return redirect('user_view')
        except User.DoesNotExist:
            messages.error(request, "Invalid username or password")
    
# For GET requests or failed login attempts
    return render(request, 'login.html')

def logout_view(request):
    """Log out the current user and redirect to login page"""
    logout(request)
    if 'user' in request.session:
        del request.session['user']
    return redirect('login')

def admin_view(request):
    """Display the admin dashboard with quizzes, questions, and users"""
    # Check if user is logged in and is an admin
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Please log in to access this page")
        return redirect('login')
    
    try:
        # Get the active user
        active_user = User.objects.get(id=user_id)
        
        # Verify admin role
        if active_user.user_role != 'admin':
            messages.error(request, "You do not have permission to access this page")
            return redirect('user_view')
            
        # Get all students (users with role 'user' and type 'student')
        # Use distinct() to avoid duplicates
        students = User.objects.filter(user_role='user', user_type='student').distinct()

        # Prepare users data for JavaScript with better formatting
        seen_user_ids = set()  # Track IDs we've already processed
        users_data = []
        for user in User.objects.all():
            # Skip if we've already seen this user ID
            if user.id in seen_user_ids:
                continue
            
            # Mark this user ID as seen
            seen_user_ids.add(user.id)
            
            # Process courses data to ensure consistency
            processed_courses = []
            
            if hasattr(user, 'courses') and user.courses:
                # Handle different course data types
                try:
                    if isinstance(user.courses, list):
                        # Already a list, just use it
                        processed_courses = user.courses
                    elif isinstance(user.courses, str):
                        # Try to parse as JSON first
                        if user.courses.startswith('[') and user.courses.endswith(']'):
                            try:
                                # Replace single quotes with double quotes for proper JSON
                                json_str = user.courses.replace("'", '"')
                                parsed_courses = json.loads(json_str)
                                if isinstance(parsed_courses, list):
                                    processed_courses = parsed_courses
                                else:
                                    processed_courses = [parsed_courses]
                            except json.JSONDecodeError:
                                # If JSON parsing fails, try direct string manipulation
                                content = user.courses[1:-1]  # Remove [ and ]
                                if content:
                                    # Split by comma and clean each item
                                    items = [item.strip().strip("'").strip('"') for item in content.split(',')]
                                    processed_courses = [item for item in items if item]
                                else:
                                    processed_courses = []
                        else:
                            # Assume it's a single course or comma-separated string
                            processed_courses = [c.strip() for c in user.courses.split(',') if c.strip()]
                except Exception as e:
                    print(f"Error processing courses for user {user.username}: {e}")
                    processed_courses = []
            
            # Add comprehensive debug info
            original_courses = getattr(user, 'courses', None)
            print(f"User {user.username}: Original courses={original_courses}, Processed={processed_courses}")
            
            # Create user data object
            user_data = {
                'id': user.id,
                'username': user.username,
                'role': user.user_role,
                'type': user.user_type,
                'courses': processed_courses,  # Use the processed courses list
                '_original_courses': str(original_courses)  # Add original for debugging
            }
            users_data.append(user_data)
        
        # Make sure we have JSON-serializable data
        try:
            users_json = json.dumps(users_data)
            print(f"Successfully serialized users_data to JSON")
        except Exception as e:
            print(f"Error serializing users_data: {e}")
            # Create a simplified version that can be serialized
            simplified_data = []
            for user in users_data:
                simplified_user = {
                    'id': user['id'],
                    'username': user['username'],
                    'courses': []  # Empty list as fallback
                }
                simplified_data.append(simplified_user)
            users_json = json.dumps(simplified_data)
        
        # Fetch all questions for use in the admin view
        questions = Questions.objects.all()
        for user in students:
            # Check where to get each piece of data based on the model structure
        
            # Get role - fix this section to use user_role instead of role
            user_role = None
            if hasattr(user, 'user_role'):  # Changed from 'role' to 'user_role'
                user_role = user.user_role
            elif hasattr(user, 'groups') and user.groups.exists():
                user_role = user.groups.first().name
        
            # Default role if none found
            if not user_role:
                user_role = "user"
        
            # Get type - fix this section to use user_type instead of type
            user_type = None
            if hasattr(user, 'user_type'):  # Changed from 'type' to 'user_type'
                user_type = user.user_type
            else:
                user_type = "student"
            
            # Get courses
            user_courses = []
            if hasattr(user, 'courses') and user.courses:
                if isinstance(user.courses, str):
                    try:
                        user_courses = json.loads(user.courses)
                    except json.JSONDecodeError:
                        user_courses = [user.courses]
                elif isinstance(user.courses, list):
                    user_courses = user.courses
            elif hasattr(user, 'profile') and hasattr(user.profile, 'courses'):
                user_courses = user.profile.courses
                
            # Format courses for display
            courses_display = ", ".join(user_courses) if user_courses else "No courses assigned"
        
            # Build user data dictionary
            user_data = {
                'id': user.id,
                'username': user.username,
                'role': user_role,
                'type': user_type,
                'courses': user_courses,
                'courses_display': courses_display
            }
        
            users_data.append(user_data)
    
        # Get today's date for the minimum date in the expiry date picker
        today_date = timezone.now().date()  # Use .date() to get just the date part

        # Define choices for number of questions (for dropdowns etc.)
        num_questions_choices = list(range(1, 51))
    
        # Process POST request for adding questions
        if request.method == 'POST' and request.POST.get('form_type') == 'add_question':
            # Extract form data
            question_text = request.POST.get('question_text')
            option1 = request.POST.get('option1')
            option2 = request.POST.get('option2')
            option3 = request.POST.get('option3', '')
            option4 = request.POST.get('option4', '')
            correct_answer = request.POST.get('correct_answer')
            course = request.POST.get('course')
        
            # Validate required fields
            if not question_text or not option1 or not option2 or not correct_answer or not course:
                messages.error(request, "Please fill all required fields: question, at least 2 options, correct answer, and course.")
            else:
                # Create new question
                Questions.objects.create(
                    question=question_text,
                    option1=option1,
                    option2=option2,
                    option3=option3,
                    option4=option4,
                    correct_answer=correct_answer,
                    course=course
                )
                messages.success(request, "Question added successfully.")
    
        # Ensure users_data is properly JSON serialized for JavaScript
        users_json = json.dumps(users_data)
    
        # Fix course display formatting for questions
        for question in questions:
            if isinstance(question.course, str):
                try:
                    # Try to parse as JSON and convert to formatted string
                    course_data = json.loads(question.course)
                    if isinstance(course_data, list):
                        question.display_course = ", ".join(course_data)
                    else:
                        question.display_course = course_data
                except json.JSONDecodeError:
                    question.display_course = question.course
            elif isinstance(question.course, list):
                question.display_course = ", ".join(question.course)
            else:
                question.display_course = str(question.course)
    
        # Define all_quiz_history before rendering the template
        all_quiz_history = QuizHistory.objects.all()

        # Define quizzes variable (e.g., all quizzes in the system)
        quizzes = Quiz.objects.all()

        # Get the currently logged-in user from the session, if available
        active_user = request.session.get('user', None)

        # Prepare courses_with_counts for the context
        all_courses = get_all_courses()
        courses_with_counts = []
        for course in all_courses:
            question_count = Questions.objects.filter(
                Q(course__exact=course) |
                Q(course__icontains=f'"{course}"') |
                Q(course__icontains=course)
            ).distinct().count()
            courses_with_counts.append({'name': course, 'question_count': question_count})
        
        # Get all user courses too (to include courses that might not have questions yet)
        user_courses = []
        for user in User.objects.all():
            if hasattr(user, 'courses') and user.courses:
                try:
                    if isinstance(user.courses, list):
                        user_courses.extend(user.courses)
                    elif isinstance(user.courses, str):
                        user_courses.append(user.courses)
                except Exception as e:
                    print(f"Error processing user courses: {e}")
    
        # Combine all courses and remove duplicates
        all_unique_courses = list(set(all_courses + user_courses))
        all_course_options = [{'name': course} for course in all_unique_courses]

        # Add students to context
        return render(request, 'admin_page.html', {
            'all_quiz_history': all_quiz_history,
            'quizzes': quizzes, 
            'users': users_data,  
            'users_json': users_json,
            'questions': questions, 
            'active_user': active_user,
            'num_questions_choices': num_questions_choices,
            'distinct_courses': courses_with_counts,
            'today_date': today_date,
            'students': students,  # Add distinct students list
            'all_course_options': all_course_options,  # Add all course options
        })
    
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect('login')
    

def add_user(request):
    """Add a new user from the admin dashboard"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user_role = request.POST.get('user_role', 'user')
        user_type = request.POST.get('user_type', 'student')
        
        # Process courses - first try to get as JSON
        courses = []
        try:
            courses_str = request.POST.get('courses', '[]')
            courses = json.loads(courses_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, try getting as a list
            courses_list = request.POST.getlist('courses[]')
            if courses_list:
                courses = courses_list
            else:
                # Last attempt: split by comma if it's a flat string
                flat_courses = request.POST.get('courses', '')
                if flat_courses and isinstance(flat_courses, str):
                    courses = [c.strip() for c in flat_courses.split(',') if c.strip()]
        
        # Debug output
        print(f"Creating user: {username}, Role: {user_role}, Type: {user_type}, Courses: {courses}")
        
        # Validate input
        if not username or not password:
            messages.error(request, "Username and password are required")
            return redirect('admin_view')
            
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists")
            return redirect('admin_view')
        
        try:
            # Create user with the correct field names
            user = User(
                username=username,
                password=password,
                user_role=user_role,
                user_type=user_type,
                courses=courses  # Store as list directly as the model uses JSONField
            )
            user.save()
            
            messages.success(request, f"User '{username}' created successfully with role '{user_role}' and type '{user_type}'")
        except Exception as e:
            messages.error(request, f"Error creating user: {str(e)}")
            import traceback
            print(traceback.format_exc())
    
    return redirect('admin_view')

def delete_user(request, user_id):
    """Delete a user by ID"""
    try:
        user = User.objects.get(id=user_id)
        
        # Don't allow deleting the admin user
        if user.username == 'admin':
            messages.error(request, "Cannot delete the admin user")
            return redirect('admin_view')
            
        # Find all quizzes assigned to this user
        try:
            user_quizzes = Quiz.objects.filter(student=user)
            
            # Get the quiz IDs before deleting the quizzes
            quiz_ids = list(user_quizzes.values_list('id', flat=True))
            
            # Delete quiz history records using quiz IDs, not student
            if quiz_ids:
                QuizHistory.objects.filter(quiz_id__in=quiz_ids).delete()
            
            # Delete the quizzes
            user_quizzes.delete()
        except Exception as e:
            print(f"Error cleaning up quizzes: {e}")
            # Continue with user deletion even if quiz cleanup fails
        
        # Delete the user
        user.delete()
        messages.success(request, f"User '{user.username}' deleted successfully")
    except User.DoesNotExist:
        messages.error(request, "User not found")
    except Exception as e:
        messages.error(request, f"Error deleting user: {str(e)}")
        import traceback
        print(traceback.format_exc())  # Print detailed error for debugging
    
    return redirect('admin_view')

def add_question(request):
    """Add a new question to a quiz"""
    if request.method == 'POST':
        # Get quiz ID from form or session
        quiz_id = request.POST.get('quiz_id') or request.session.get('last_created_quiz_id')
        
        if not quiz_id:
            messages.error(request, "No quiz selected. Please create a quiz first.")
            return redirect('admin_view')
        
        # Get form data
        question_text = request.POST.get('question_text')
        course = request.POST.get('course') or request.session.get('last_created_quiz_course')
        option_a = request.POST.get('option_a')
        option_b = request.POST.get('option_b')
        option_c = request.POST.get('option_c')
        option_d = request.POST.get('option_d')
        correct_answer = request.POST.get('correct_answer')
        
        # Validate inputs
        if not all([question_text, course, option_a, option_b, option_c, option_d, correct_answer]):
            messages.error(request, "All fields are required")
            return redirect('admin_view')
            
        try:
            # Get the quiz
            quiz = Quiz.objects.get(id=quiz_id)
            
            # Create the question
            question = Questions(
                quiz=quiz,
                course=course,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer
            )
            question.save()
            
            # Update quiz questions count
            quiz.questions_count = quiz.questions_count + 1 if quiz.questions_count else 1
            quiz.save()
            
            messages.success(request, "Question added successfully")
            
        except Quiz.DoesNotExist:
            messages.error(request, "Quiz not found")
        except Exception as e:
            messages.error(request, f"Error adding question: {str(e)}")
            print(f"Error adding question: {e}")
    
    return redirect('admin_view')

def modify_question(request, question_id):
    """Modify an existing question"""
    if request.method == 'POST':
        try:
            question = Questions.objects.get(id=question_id)
            
            # Update fields
            question.question = request.POST.get('question_text')
            question.option1 = request.POST.get('option1')
            question.option2 = request.POST.get('option2')
            question.option3 = request.POST.get('option3', '')
            question.option4 = request.POST.get('option4', '')
            question.correct_answer = request.POST.get('correct_answer')
            question.course = request.POST.get('course')
            
            # Validate required fields
            if not question.question or not question.option1 or not question.option2 or not question.correct_answer or not question.course:
                messages.error(request, "Please fill all required fields")
                return redirect('admin_view')
                
            question.save()
            messages.success(request, "Question updated successfully")
        except Questions.DoesNotExist:
            messages.error(request, "Question not found")
    
    return redirect('admin_view')

def delete_question(request, question_id):
    """Delete a question by ID"""
    try:
        question = Questions.objects.get(id=question_id)
        question.delete()
        messages.success(request, "Question deleted successfully")
    except Questions.DoesNotExist:
        messages.error(request, "Question not found")
    
    return redirect('admin_view')

def create_quiz(request):
    """Create a new quiz for a student"""
    if request.method == 'POST':
        student_id = request.POST.get('student')
        course = request.POST.get('course', '')
        manual_course = request.POST.get('manual_course', '')
        
        # Debug output
        print(f"Create quiz form data: student_id={student_id}, course={course}, manual_course={manual_course}")
        
        # Use manual course if provided, otherwise use selected course
        final_course = manual_course.strip() if manual_course.strip() else course.strip()

        # Get number of questions, quiz duration, and expiry date from POST data
        num_questions = int(request.POST.get('num_questions', 0))
        quiz_duration = int(request.POST.get('quiz_duration', 0))
        quiz_expire_date = request.POST.get('quiz_expire_date', '')

        # Validate inputs
        if not student_id or not final_course:
            messages.error(request, "Student and course are required")
            return redirect('admin_view')
        if not num_questions or not quiz_duration or not quiz_expire_date:
            messages.error(request, "Please provide number of questions, quiz duration, and expiry date")
            return redirect('admin_view')
            
        try:
            # Get the student
            student = User.objects.get(id=student_id)
            
            # Add the course to student's courses if needed
            if hasattr(student, 'courses'):
                # Initialize courses as empty list if None
                if student.courses is None:
                    student.courses = []
                    
                # Convert string representation to list if needed
                if isinstance(student.courses, str):
                    if student.courses.startswith('[') and student.courses.endswith(']'):
                        try:
                            courses_list = json.loads(student.courses)
                            if not isinstance(courses_list, list):
                                courses_list = [student.courses]
                        except:
                            courses_list = [student.courses]
                    else:
                        courses_list = [student.courses]
                elif isinstance(student.courses, list):
                    courses_list = student.courses
                else:
                    courses_list = []
                    
                # Add the course if it's not already in the list
                if final_course not in courses_list:
                    courses_list.append(final_course)
                    student.courses = courses_list
                    student.save()
                    print(f"Added course '{final_course}' to student {student.username}")
            else:
                # If no courses attribute, initialize with this course
                student.courses = [final_course]
                student.save()
                print(f"Created courses list with '{final_course}' for student {student.username}")
            
            # Create the quiz
            quiz = Quiz(
                student=student,
                course=final_course,
                num_questions=num_questions,
                quiz_duration=quiz_duration,
                quiz_expire_date=quiz_expire_date,
                questions_count=0  # Start with 0, will be updated as questions are added
            )
            quiz.save()
            
            # Store quiz ID and course in session for adding questions
            request.session['last_created_quiz_id'] = quiz.id
            request.session['last_created_quiz_course'] = final_course
            
            messages.success(request, f"Quiz for {student.username} created successfully. You can now add questions.")
            
        except User.DoesNotExist:
            messages.error(request, "Student not found")
        except Exception as e:
            messages.error(request, f"Error creating quiz: {str(e)}")
            print(f"Error creating quiz: {e}")
            import traceback
            traceback.print_exc()
    
    return redirect('admin_view')

def get_questions_for_course(course):
    """
    Get questions for a course using multiple query methods to handle different storage formats.
    """
    # First attempt: Try exact match
    questions = Questions.objects.filter(course__exact=course)
    
    # Second attempt: Try contains with quotes (for JSON stored courses)
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=f'"{course}"')
    
    # Third attempt: Try icontains to make it case insensitive
    if questions.count() == 0:
        questions = Questions.objects.filter(course__icontains=course)
    
    # Get distinct questions to avoid duplicates
    return questions.distinct()

def user_view(request):
    """Display the user dashboard with quizzes and history"""
    # Check if user is logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "Please log in to access this page")
        return redirect('login')
    
    try:
        # Get the active user
        active_user = User.objects.get(id=user_id)
        
        # Debug line to check user details
        print(f"User view accessed by: {active_user.username}, Role: {active_user.user_role}, Type: {active_user.user_type}")
        
        # If an admin somehow gets here, redirect them
        if active_user.user_role == 'admin':
            return redirect('admin_view')
        
        # Get quizzes for this student
        quizzes = Quiz.objects.filter(student=active_user)
        
        # Get quiz history by finding QuizHistory records where the related quiz is for this student
        try:
            quiz_history = QuizHistory.objects.filter(quiz__student=active_user)
        except Exception as e:
            print(f"Error fetching quiz history: {e}")
            quiz_history = []
        
        # Calculate average score safely
        avg_score = 0
        try:
            if quiz_history and len(quiz_history) > 0:
                valid_scores = [h.score for h in quiz_history if h.score is not None]
                if valid_scores:
                    avg_score = round(sum(valid_scores) / len(valid_scores), 1)
        except Exception as e:
            print(f"Error calculating average score: {e}")
        
        return render(request, 'user_page.html', {
            'active_user': active_user,
            'quizzes': quizzes,
            'quiz_history': quiz_history,
            'avg_score': avg_score
        })
    
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect('login')
    except Exception as e:
        # Add better error handling to help troubleshoot issues
        print(f"Error in user_view: {e}")
        messages.error(request, "An error occurred while loading your dashboard.")
        return redirect('login')

def take_quiz(request, quiz_id):
    """Allow a student to take a specific quiz"""
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "You must be logged in to take a quiz")
        return redirect('login')
        
    try:
        user = User.objects.get(id=user_id)
        quiz = Quiz.objects.get(id=quiz_id)
        
        # Verify this quiz is assigned to this user
        if quiz.student != user:
            messages.error(request, "This quiz is not assigned to you")
            return redirect('user_view')
            
        # Check if quiz is expired
        if quiz.quiz_expire_date < timezone.now().date():
            messages.error(request, "This quiz has expired")
            return redirect('user_view')
            
        # Check if quiz was already taken
        if QuizHistory.objects.filter(quiz=quiz, student=user).exists():
            messages.error(request, "You have already taken this quiz")
            return redirect('user_view')
            
        # Get questions for this quiz
        questions_for_course = get_questions_for_course(quiz.course)
        
        # Select random questions up to the quiz's num_questions
        questions = questions_for_course.order_by('?')[:quiz.num_questions]
        
        return render(request, 'take_quiz.html', {
            'quiz': quiz,
            'questions': questions,
            'quiz_duration': quiz.quiz_duration
        })
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect('login')
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')

def submit_quiz(request, quiz_id_active):
    """Process a submitted quiz and calculate the result"""
    username = request.session.get('user')
    if not username or request.method != 'POST':
        messages.error(request, "Invalid request")
        return redirect('login')
        
    try:
        user = User.objects.get(username=username)
        quiz = Quiz.objects.get(id=quiz_id_active)
        
        # Check if this quiz belongs to this user
        if quiz.student != user:
            messages.error(request, "This quiz is not assigned to you")
            return redirect('user_view')
            
        # Check if quiz was already taken
        if QuizHistory.objects.filter(quiz=quiz, student=user).exists():
            messages.error(request, "You have already taken this quiz")
            return redirect('user_view')
            
        # Initialize variables for tracking answers
        total_questions = 0
        correct_answers = 0
        
        # Process each question
        for key, value in request.POST.items():
            if key.startswith('question_'):
                total_questions += 1
                question_id = key.split('_')[1]
                selected_answer = value
                
                try:
                    question = Questions.objects.get(id=question_id)
                    if selected_answer == question.correct_answer:
                        correct_answers += 1
                except Questions.DoesNotExist:
                    pass
        
        # Calculate score
        score = 0
        if total_questions > 0:
            score = (correct_answers / total_questions) * 100
        
        # Create quiz history record
        QuizHistory.objects.create(
            quiz=quiz,
            student=user,
            score=score,
            correct_answers=correct_answers,
            total_questions=total_questions,
            date_completed=timezone.now()
        )
        
        messages.success(request, f"Quiz submitted successfully. Your score: {score:.1f}%")
        return redirect('user_view')
        
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect('login')
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
        return redirect('user_view')

def delete_quiz(request, quiz_id):
    """Delete a quiz by ID"""
    # Check if user is logged in as admin
    active_user = request.session.get('user')
    if not active_user:
        messages.error(request, "You must be logged in to delete quizzes")
        return redirect('login')
    
    try:
        user_obj = User.objects.get(username=active_user)
        
        # Check if user should have admin access
        is_admin = False
        
        # If the user has a role attribute, check if it's 'admin'
        if hasattr(user_obj, 'role'):
            is_admin = (user_obj.role == 'admin')
        else:
            # If no role attribute, check if username is 'admin'
            is_admin = (user_obj.username == 'admin')
            
        if not is_admin:
            messages.error(request, "You don't have permission to delete quizzes")
            return redirect('login')
            
        # Try to get and delete the quiz
        quiz = Quiz.objects.get(id=quiz_id)
        
        # Get information for the success message
        student_username = quiz.student.username if quiz.student else "Unknown student"
        course_name = quiz.course
        
        # Delete quiz history related to this quiz
        QuizHistory.objects.filter(quiz_id=quiz_id).delete()
        
        # Delete the quiz
        quiz.delete()
        
        messages.success(request, f"Quiz for {student_username} on {course_name} was deleted successfully")
    except User.DoesNotExist:
        messages.error(request, "User not found")
    except Quiz.DoesNotExist:
        messages.error(request, "Quiz not found")
    except Exception as e:
        messages.error(request, f"Error deleting quiz: {str(e)}")
        import traceback
        print(traceback.format_exc())  # Print detailed error for debugging
    
    return redirect('admin_view')

# Helper function to get all available courses
def get_all_courses():
    questions = Questions.objects.all()
    distinct_courses = set()
    
    for question in questions:
        if isinstance(question.course, str):
            try:
                courses = json.loads(question.course)
                if isinstance(courses, list):
                    for course in courses:
                        distinct_courses.add(course)
                else:
                    distinct_courses.add(courses)
            except json.JSONDecodeError:
                distinct_courses.add(question.course)
        elif isinstance(question.course, list):
            for course in question.course:
                distinct_courses.add(course)
    
    return sorted(list(distinct_courses))

def signup(request, role=None):
    """Unified signup function for both students and admin"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Create auth user
            user = form.save(commit=False)
            
            # Get additional form data
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            
            # Get the role from POST data or from the parameter
            # Make sure we're using the correct field name and default value
            user_role = request.POST.get('user_role', request.POST.get('role', role or 'user'))
            user_type = request.POST.get('user_type', request.POST.get('type', 'student'))
            
            # Ensure student users have 'user' role
            if user_type == 'student' and not role == 'admin':
                user_role = 'user'
            
            # Ensure admin users have 'professor' type
            if user_role == 'admin':
                user_type = 'professor'
            
            # Debug output
            print(f"Creating user: {username}, Role: {user_role}, Type: {user_type}")
            
            # Get courses from POST
            courses_str = request.POST.get('courses', '')
            courses = []
            if courses_str:
                courses = [c.strip() for c in courses_str.split(',') if c.strip()]
            
            # Save the auth user
            user.save()
            
            # Create our custom User model instance with explicit role
            custom_user = User(
                username=username,
                password=password,
                user_role=user_role,  # Make sure this is explicitly set
                user_type=user_type,  # Make sure this is explicitly set
                courses=courses
            )
            custom_user.save()
            
            # Double-check that the user was saved correctly
            saved_user = User.objects.get(username=username)
            print(f"Saved user: {saved_user.username}, Role: {saved_user.user_role}, Type: {saved_user.user_type}")
            
            # Add user to appropriate group
            if user_role == 'admin':
                admin_group, created = Group.objects.get_or_create(name='Admins')
                user.groups.add(admin_group)
            
            messages.success(request, f'Account created successfully!')
            
            return render(request, 'signup_success.html')
    else:
        form = UserCreationForm()
    
    # Context variables
    is_admin_signup = (role == 'admin')
    signup_type = "Admin" if is_admin_signup else "Student"
    
    return render(request, 'signup.html', {
        'form': form, 
        'is_admin_signup': is_admin_signup,
        'signup_type': signup_type
    })

# Update the admin_signup function to use the unified signup
def admin_signup(request):
    """View for admin signup - reuses the unified signup function"""
    # Make sure the role is explicitly set to 'admin'
    if request.method == 'POST':
        # Ensure the role is set correctly
        request.POST = request.POST.copy()  # Make a mutable copy
        request.POST['role'] = 'admin'
        request.POST['user_role'] = 'admin'
        
    return signup(request, role='admin')

def login_view(request):
    """Handle user login with proper authentication"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Validate input
        if not username or not password:
            messages.error(request, "Please provide both username and password")
            return render(request, 'login.html')
        
        # Attempt to find the user in our custom User model
        try:
            user = User.objects.get(username=username)
            
            # Debug output to check what role the user has
            print(f"Found user: {username}, Role: {user.user_role}, Type: {user.user_type}")
            
            # Check password
            if user.password != password:
                messages.error(request, "Invalid credentials")
                return render(request, 'login.html')
                
            # Set session data
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['user_role'] = user.user_role
            request.session['user_type'] = user.user_type
            
            # Explicit logging for debugging
            print(f"Login successful for {username}")
            print(f"Session data: user_id={user.id}, user_role={user.user_role}")
            
            # Fix the role check - use string comparison
            admin_roles = ['admin', 'Admin', 'ADMIN']  # Case-insensitive check
            if user.user_role in admin_roles:
                print(f"Redirecting {username} to admin_view (role: {user.user_role})")
                return redirect('admin_view')
            else:
                print(f"Redirecting {username} to user_view (role: {user.user_role})")
                return redirect('user_view')
                
        except User.DoesNotExist:
            messages.error(request, "User does not exist")
            return render(request, 'login.html')
        except Exception as e:
            print(f"Error during login: {e}")
            messages.error(request, "An error occurred during login. Please try again.")
            return render(request, 'login.html')
    
    # For GET requests or failed login attempts
    return render(request, 'login.html')

def create_test_questions(request):
    """Create sample questions for testing purposes"""
    if not request.session.get('user'):
        messages.error(request, "You must be logged in as admin to create test questions")
        return redirect('login')
    
    try:
        user_obj = User.objects.get(username=request.session.get('user'))
        if user_obj.role != 'admin':
            messages.error(request, "Only admin users can create test questions")
            return redirect('login')
    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect('login')
    
    # Sample courses
    courses = ['Mathematics', 'Physics', 'Computer Science', 'Biology', 'Chemistry']
    
    # Create sample questions
    for course in courses:
        # Create 5 sample questions per course
        for i in range(1, 6):
            Questions.objects.create(
                question=f"Sample question #{i} for {course}",
                option1=f"Option 1 for question #{i}",
                option2=f"Option 2 for question #{i}",
                option3=f"Option 3 for question #{i}",
                option4=f"Option 4 for question #{i}",
                correct_answer=f"Option 1 for question #{i}",
                course=course
            )
    
    messages.success(request, f"Created {len(courses) * 5} test questions across {len(courses)} courses")
    return redirect('admin_view')