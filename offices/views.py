from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def mayor(request):
    return render(request, 'offices/mayorsoffice.html')