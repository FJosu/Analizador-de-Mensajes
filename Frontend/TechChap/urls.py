from django.urls import path
from . import views

urlpatterns=[
    
    path('', views.index, name='index'),
    path('main/', views.main, name = 'main'),
    path('studentdata/', views.studentdata, name = 'studentdata'),
    path('uploadfile/',views.uploadfile, name = 'uploadfile'),
    path('uploadXML/',views.uploadXML,name='uploadXML'),



]

