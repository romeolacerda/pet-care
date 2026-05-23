from django.shortcuts import render, redirect
from django.contrib.messages import constants
from django.contrib import messages
from django.contrib.auth.models import User

from usuarios.models import Cliente

def cadastro(request):
    if request.method == 'GET':
        return render(request, 'cadastro.html')
    elif request.method == 'POST':
        username = request.POST.get('username')
        senha = request.POST.get('senha')
        confirmar_senha = request.POST.get('confirmar_senha')
        
        if not senha == confirmar_senha:
            messages.add_message(request, constants.ERROR, 'Senha e confirmar senha não são iguais.')
            return redirect('cadastro')
            
        if len(senha) < 6:
            messages.add_message(request, constants.ERROR, 'Sua senha deve ter pelo menos 6 caracteres.')
            return redirect('cadastro')

        users = User.objects.filter(username=username)
        
        if users.exists():
            messages.add_message(request, constants.ERROR, 'Já existe um usuário com esse username.')
            return redirect('cadastro')
        
        User.objects.create_user(
            username=username,
            password=senha
        )

        return redirect('login')

from django.contrib.auth import authenticate
from django.contrib import auth

def login(request):
    if request.method == 'GET':
        return render(request, 'login.html')
    elif request.method == 'POST':
        username = request.POST.get('username')
        senha = request.POST.get('senha')
        
        user = authenticate(username=username, password=senha)
        if user is not None:
            auth.login(request, user)
            return redirect('clientes')
        else:
            messages.add_message(request, constants.ERROR, 'Usuário ou senha inválidos.')

def clientes(request):
    if request.method == 'GET':
        tipo = request.GET.get('tipo')
        clientes = Cliente.objects.all()
        if tipo:
            clientes = clientes.filter(especie=tipo.upper())
        return render(request, 'clientes.html', {'clientes': clientes})
    elif request.method == 'POST':
        nome = request.POST.get('nome')
        cpf = request.POST.get('cpf')
        telefone = request.POST.get('telefone')
        especie = request.POST.get('especie')
        nome_animal = request.POST.get('nome_animal')
        raca = request.POST.get('raca')
        idade = request.POST.get('idade')
        peso = request.POST.get('peso')

        cliente = Cliente(
            nome=nome,
            cpf=cpf,
            telefone=telefone,
            especie=especie,
            nome_animal=nome_animal,
            raca=raca,
            idade=idade,
            peso=peso
        )
        cliente.save()
        messages.add_message(request, constants.SUCCESS, 'Cliente cadastrado com sucesso.')
        return redirect('clientes')
    else:
        messages.add_message(request, constants.ERROR, 'Erro ao cadastrar cliente.')
        return redirect('clientes')
 
def clientes(request):
    if request.method == 'GET':
        clientes = Cliente.objects.all()
        return render(request, 'clientes.html', {'clientes': clientes})