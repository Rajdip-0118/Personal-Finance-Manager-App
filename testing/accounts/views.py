from django.shortcuts import render, HttpResponse, redirect
from django.contrib import messages
from django.contrib.auth import login , logout, authenticate  
from .forms import CreateUserForm


# Create your views here.


def homepage(request):
    context = {}
    return render(request, 'accounts/homepage.html', context)


def register(request):
    form = CreateUserForm()
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully! You can now log in.")
            return redirect('login') 
    context= {'form': form}
    return render(request, 'accounts/register.html', context)

def loginpage(request):
    if "next" in request.GET:
        messages.warning(request, "Please login first to continue.")
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            next_url = request.GET.get("next")
            return redirect(next_url if next_url else 'dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'accounts/login.html')

def logoutpage(request):
    logout(request)
    return redirect('homepage')


