from django.urls import path
from . import views

urlpatterns = [
    path('cadastro/', views.cadastro, name='cadastro'),
    path('login/', views.login, name='login'),
    path('clientes/', views.clientes, name='clientes'),
    path('clientes/<int:pk>/', views.paciente, name='paciente'),
    path('consultas/<int:pk>/', views.consulta, name='consulta'),
    path('clientes/<int:id_cliente>/triagem/', views.triagem, name='triagem'),
    path('clientes/<int:pk>/chat/', views.chat, name='chat'),
    path('chat/stream/', views.stream_resposta, name='stream_resposta'),
    path('perguntas/<int:pk>/fontes/', views.fontes, name='fontes'),
    path("webhook_whatsapp/", views.webhook_whatsapp, name='webhook_whatsapp'),
    
]