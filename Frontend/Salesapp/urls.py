from django.urls import path
from . import views

urlpatterns = [
    path('', views.index , name='index'),
    path('main/', views.main , name='main'),
    path('uploadfile/', views.uploadfile  , name='upload'),
    path('peticion/', views.peticion  , name = 'peticion'),
    path('uploadXML/',views.uploadXML,name='uploadXML'),
    path('CloseAlerts/', views.CloseAlerts, name='CloseAlerts'),
    path('SendXML/', views.SendXML,name = 'SendXML'),
    path('consultar', views.consultar, name = 'consultar'),
    path('get_file/', views.getFile, name='get_file'),
    path('Student/', views.studentdata , name = 'Student'),
    path('bydate/', views.bydate, name = 'bydate'),
    path('rangebydate/', views.rangebydate,name = 'rangebydate'),
    
]
