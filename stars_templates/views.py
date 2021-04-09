from django.shortcuts import render,redirect,reverse
from . import forms,models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect,HttpResponse
from django.contrib.auth.decorators import login_required,user_passes_test
from django.conf import settings
from datetime import date, timedelta
from quiz import models as QMODEL
from teacher import models as TMODEL
from django.contrib import messages
import random,string
from twilio.rest import Client #twilio
from twilio.base.exceptions import TwilioRestException #twilio exception
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from decouple import config
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import datetime


def error_404_view(request,exception):
    return render(request,'404.html')
#for showing signup/login button for student
# def studentclick_view(request):
#     if request.user.is_authenticated:
#         return HttpResponseRedirect('afterlogin')
#     return render(request,'student/studentclick.html')

# twilio settings
account_sid = config('account_sid')
auth_token = config('auth_token')
client = Client(account_sid, auth_token)

#სტუდენტის რეგისტრაცია otp კოდით
def student_signup_view(request):
    userForm=forms.StudentUserForm()
    studentForm=forms.StudentForm()
    if request.method=='POST':
        userForm=forms.StudentUserForm(request.POST)
        studentForm=forms.StudentForm(request.POST,request.FILES)
        mydict={'userForm':userForm,'studentForm':studentForm}
        print('ბოუნდია-----------%s',studentForm.is_bound)
        if userForm.is_valid() and studentForm.is_valid():
            phone=userForm.cleaned_data['username']
            passs=userForm.cleaned_data['password1']
            user=userForm.save()
            user.save()
            student=studentForm.save(commit=False)
            student.user = user
            my_student_group = Group.objects.get_or_create(name='STUDENT')
            my_student_group[0].user_set.add(user)
            student.save()
            messages.success(request,' თქვენ წარმატებით რეგისტრაცია  გაიარეთ')
            return redirect('studentlogin')
        else:
            if userForm.errors:
                for field in userForm:
                    msg = field.errors
                    print('field errors:',msg)
                    messages.error(request,f"{msg}")
            if studentForm.errors:
                for field in studentForm:
                    msg = field.errors
                    print('field errors:',msg)
                    messages.error(request,f"{msg}")
            print('UserForm erors:',userForm.errors.as_data(),'no no no UserForm erors:', studentForm.errors)
            return HttpResponseRedirect('studentsignup')
    else:
        mydict={'userForm':userForm,'studentForm':studentForm}
    return render(request,'student/studentsignup.html',context=mydict)


def reset_password(request):
    PhoneForm=forms.ResetPass()
    mydict={'PhoneForm':PhoneForm}
    if request.method=='POST':
        PhoneForm=forms.ResetPass(request.POST)
        if PhoneForm.is_valid():
            phone=PhoneForm.cleaned_data['phone']
            try:
                user1 = User.objects.get(username=phone)
                source = string.ascii_letters + string.digits
                otp = ''.join((random.choice(source) for i in range(9)))
                user1.set_password(otp)
                user1.save()
                # print('დაგენერირებული პაროლი არის',otp)
                try:
                    message = client.messages.create(
                    body="თქვენი დროებითი პაროლი არის:"+str(otp),
                    from_='+'+str(config('from_')),
                    to='+995'+str(phone)
                    )
                    # print(message.sid)
                    messages.success(request,'თქვენი დროებითი პაროლი გამოგეგზავნათ %s მობილურის ნომერზე' %phone)
                except TwilioRestException as e:
                    print(e)
                    messages.error(request,'გთხოვთ მიმართოთ ადმინისტრაციას')
                except Exception  as e:
                    print('bolo',e)
                    messages.error(request,'მობილურის ნომერი არ არის სწორი')
                return HttpResponseRedirect('studentlogin')
            except User.DoesNotExist:
                messages.warning(request,'ეს მომხმარებელი არ არსებობს')
            if PhoneForm.errors:
                for field in PhoneForm:
                    msg = field.errors
                    # print('field errors:',msg)
                    messages.error(request,f"{msg}")
    return render(request,'student/reset_password.html',context=mydict)


def is_student(user):
    return user.groups.filter(name='STUDENT').exists()


@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_settings_click(request):
    return render(request,'student/settings.html')

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_settings(request):
    user=get_object_or_404(User,id=request.user.id)
    student =get_object_or_404(models.Student,user_id=user.id)
    from student.choices import regions
    regions1=models.Student._meta.get_field('region').choices
    phone=request.POST.get('phone')
    first_name=request.POST.get('first_name')
    last_name=request.POST.get('last_name')
    school=request.POST.get('school')
    # region=request.POST.get('region')
    context={"user":user,"student":student,"regions":regions}
    if request.method=='POST':
        try:
            user.username=phone
            user.first_name=first_name
            user.last_name=last_name
            user.save()
            student.school=school
            # student.region=region
            student.save()
            messages.success(request,'თქვენი მონაცემი განახლდა წარმატებით')
        except Exception as e:
            messages.error(request,'ეს მომხმარებელი დაკავებულია')
        context={"user":user,"student":student}
    return render(request,'student/settings.html',context=context)

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_dashboard_view(request):
    users=request.user.student.id
    dict={
    'notification':QMODEL.Notifycation.objects.all(),
    'status_payment':QMODEL.Transactions.objects.filter(student_id=users),
    'total_subjects':QMODEL.Course.objects.all(),
    }
    return render(request,'student/student_dashboard.html',context=dict)

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_exam_view(request):
    context={
    'courses':QMODEL.Course.objects.all(),
    }
    return render(request,'student/student_exam.html',context=context)

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def take_exam_view(request,pk):
    course=get_object_or_404(QMODEL.Course,id=pk) 
    total_questions=QMODEL.Question.objects.all().filter(course=course).count()
    questions=QMODEL.Question.objects.all().filter(course=course)
    total_marks=0
    for q in questions:
        total_marks=total_marks + q.marks
    return render(request,'student/take_exam.html',{'course':course,'total_questions':total_questions,'total_marks':total_marks})


def is_payed(user):
    return QMODEL.Transactions.objects.filter(student_id = user.student.id).filter(amount = 10)


@login_required(login_url='studentlogin')
@user_passes_test(is_student)
# @user_passes_test(is_payed)
def start_exam_view(request,pk):
    course=get_object_or_404(QMODEL.Course,id=pk) 
    questions=QMODEL.Question.objects.all().filter(course=course)
    if request.method=='POST':
        pass
    response= render(request,'student/start_exam.html',{'course':course,'questions':questions})
    response.set_cookie('course_id',course.id)
    return response


@login_required(login_url='studentlogin')
@user_passes_test(is_student)
# @user_passes_test(is_payed)
def calculate_marks_view(request):
    if request.COOKIES.get('course_id') is not None:
        course_id = request.COOKIES.get('course_id')
        course=get_object_or_404(QMODEL.Course,id=course_id)
        total_marks=0
        questions=QMODEL.Question.objects.all().filter(course=course)
        data ={}
        for i in range(len(questions)): 
            selected_ans = request.COOKIES.get(str(i+1))
            data[str(i)]=selected_ans
            actual_answer = questions[i].answer
            if selected_ans == actual_answer:
                total_marks = total_marks + questions[i].marks
        student = models.Student.objects.get(user_id=request.user.id)
        result = QMODEL.Result()
        result.marks=total_marks
        result.exam=course
        result.student=student
        result.choice_answer=data
        questions=QMODEL.Question.objects.all().filter(course=course).aggregate(Sum('marks'))#ქულათა ჯამი
        questions=questions.get('marks__sum')
        result_precent=(total_marks*100)/questions
        status="F" #status F aris chbareba
        status1="X" #statusi X aris chachra
        if result_precent < 30 or round(result_precent) == 0:
            result.status=status1
            result.discount=0
        if result_precent >30 and result_precent < 60 or result_precent==30:
            discount=0
            result.status=status
            result.discount=discount
        if result_precent >60 and result_precent < 70  or result_precent==60:
            discount=20
            result.status=status
            result.discount=discount
        if result_precent >70 and result_precent < 80 or result_precent == 70:
            discount=30
            result.status=status
            result.discount=discount
        if result_precent >80 and result_precent < 90 or result_precent ==80:
            discount=40
            result.status=status
            result.discount=discount
        if result_precent >90 and result_precent <100 or result_precent==100 or result_precent == 90:
            discount=50
            result.status=status
            result.discount=discount
        result.save()
        discount = result.discount
        QMODEL.Transactions.objects.filter(student_id=request.user.student.id).update(amount = 0 )
       # print(QMODEL.Transactions.objects.filter(student_id=request.user.student.id).update(amount = 0 ))
    context={"result_precent":round(result_precent),"total_marks":total_marks,"questions":questions,"discount":discount}
    response= render(request,'student/quiz_final.html',context=context)
    # test cookie delete try
    try:
        course_id = request.COOKIES.get('course_id')
        course=get_object_or_404(QMODEL.Course,id=course_id)
        questions=QMODEL.Question.objects.all().filter(course=course)
        response.delete_cookie('course_id')
        for i in range(len(questions)):
            response.delete_cookie(str(i+1))
    except:
        pass
    return response
   
@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def view_result_view(request):
    courses=QMODEL.Course.objects.all()
    return render(request,'student/view_result.html',{'courses':courses})
    
@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def check_marks_view(request,pk):
    course=QMODEL.Course.objects.get(id=pk)
    student = models.Student.objects.get(user_id=request.user.id)
    results= QMODEL.Result.objects.all().filter(exam=course).filter(student=student)
    return render(request,'student/check_marks.html',{'results':results})

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_marks_view(request):
    courses=QMODEL.Course.objects.all()
    return render(request,'student/student_marks.html',{'courses':courses})
  

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_sertification(request):
    result = QMODEL.Result.objects.filter(student_id = request.user.student.id)
    context={}
    if result:
        for res in result:
            print(context)
            if res.status == 'F':
                if res.exam.course_name == 'გერმანული':
                    context['geo'] = 'ქართული'
                    context['geo_date'] = res.date.strftime('%x')
                if res.exam.course_name == 'მათემატიკა':
                    context['mat'] = 'მათემატიკა'
                    context['mat_date'] = res.date.strftime('%x')
                if res.exam.course_name in ['ინგლისური','ინგლისური1']:
                    print('inglisuriaaaa',res.exam.course_name)
                    context['eng'] = 'ინგლისური'
                    context['eng_date'] = res.date.strftime('%x')
    return render(request,'student/student_sertificates.html',context=context)



#ინგლისურის სერთიფიკატის ჩამოწერა
@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def sertificate(request):
    try:
        eng = QMODEL.Course.objects.filter(course_name__istartswith= 'ინგლის').first()
        print(eng)
        if eng:
            ress = QMODEL.Result.objects.filter(student_id = request.user.student.id,exam_id=eng).first()
            print('resiaaaaaa',ress)
            time=ress.date
            # print(time)
            dicts={'myvar':time.strftime('%x')}
            # print(create.date)
            return render(request,'student/sertificate.html',context=dicts)
    except Exception as e:
        # print(e)
        return render(request,'student/student_dashboard.html')
    return render(request,'student/student_dashboard.html')

#ქართულის სერთიფიკატის ჩამოწერა
@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_mat_sertificate(request):
    try:
        geo = QMODEL.Course.objects.filter(course_name__istartswith='გერმა').first()
        if geo:
            ress = QMODEL.Result.objects.filter(student_id = request.user.student.id,exam_id=geo).first()
            time=ress.date
            # print(time)
            dicts={'myvar':time.strftime('%x')}
            # print(create.date)
            return render(request,'student/sertificate_geo.html',context=dicts)
    except Exception as e:
        print(e)
        return render(request,'student/student_dashboard.html')
    return render(request,'student/student_dashboard.html')


#მათემატიკის სერთიფიკატის ჩამოწერა
@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_geo_sertificate(request):
    try:
        mat = QMODEL.Course.objects.filter(course_name__istartswith= 'მათემატ').first()
        if mat:
            ress = QMODEL.Result.objects.filter(student_id = request.user.student.id,exam_id=mat).first()
            time=ress.date
            # print(time)
            dicts={'myvar':time.strftime('%x')}
            # print(create.date)
            return render(request,'student/sertificate_mat.html',context=dicts)
    except Exception as e:
        # print(e)
        return render(request,'student/student_dashboard.html')
    return render(request,'student/student_dashboard.html')


@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_dashboard_payment(request):
    return render(request,'student/student_dashboard_payment.html')

@login_required(login_url='studentlogin')
@user_passes_test(is_student)
def student_dashboard_pretest(request):
    return render(request,'student/student_dashboard_pretest.html')