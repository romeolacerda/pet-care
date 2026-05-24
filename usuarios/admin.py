from django.contrib import admin
from .models import Cliente, Consulta, Pergunta, ContextRag

admin.site.register(Cliente)
admin.site.register(Consulta)
admin.site.register(Pergunta)
admin.site.register(ContextRag)