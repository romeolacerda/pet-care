from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.messages import constants
from django.contrib.auth import authenticate
from django.contrib import auth
from .models import Cliente
import json
from .wrapper_evolutionapi import SendMessage
from .agent import AssistentAgent, SecretariaAI
from django.shortcuts import get_object_or_404
from .models import Consulta
from .agent import TriagemAgent
from agno.agent import RunOutput
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Pergunta
from .agent import TriagemAgent
from agno.agent import RunOutputEvent, RunEvent
from typing import Iterator
from django.http import StreamingHttpResponse
from .models import ContextRag


def cadastro(request):
    if request.method == "GET":
        return render(request, "cadastro.html")
    elif request.method == "POST":
        username = request.POST.get("username")
        senha = request.POST.get("senha")
        confirmar_senha = request.POST.get("confirmar_senha")

        if senha != confirmar_senha:
            messages.add_message(
                request, constants.ERROR, "Senha e confirmar senha não conferem"
            )
            return redirect("cadastro")

        if len(senha) < 6:
            messages.add_message(
                request, constants.ERROR, "Sua senha deve ter pelo menos 6 caracteres."
            )
            return redirect("cadastro")

        users = User.objects.filter(username=username)

        if users.exists():
            messages.add_message(
                request, constants.ERROR, "Já existe um usuário com esse username."
            )
            return redirect("cadastro")

        User.objects.create_user(username=username, password=senha)

        return redirect("login")


def login(request):
    if request.method == "GET":
        return render(request, "login.html")
    elif request.method == "POST":
        username = request.POST.get("username")
        senha = request.POST.get("senha")

        user = authenticate(username=username, password=senha)
        if user is not None:
            auth.login(request, user)
            return redirect("clientes")
        else:
            messages.add_message(request, constants.ERROR, "Usuário ou senha inválidos")
            return redirect("login")


def clientes(request):
    if request.method == "GET":
        tipo = request.GET.get("tipo")
        clientes = Cliente.objects.all()
        if tipo:
            clientes = clientes.filter(especie=tipo.upper())
        return render(request, "clientes.html", {"clientes": clientes})
    elif request.method == "POST":
        nome = request.POST.get("nome")
        cpf = request.POST.get("cpf")
        telefone = request.POST.get("telefone")
        especie = request.POST.get("especie")
        nome_animal = request.POST.get("nome_animal")
        raca = request.POST.get("raca")
        idade = request.POST.get("idade")
        peso = request.POST.get("peso")

        cliente = Cliente(
            nome=nome,
            cpf=cpf,
            telefone=telefone,
            especie=especie,
            nome_animal=nome_animal,
            raca=raca,
            idade=idade,
            peso=peso,
        )
        cliente.save()
        messages.add_message(
            request, constants.SUCCESS, "Cliente cadastrado com sucesso."
        )
        return redirect("clientes")


def paciente(request, pk):
    if request.method == "GET":
        cliente = get_object_or_404(Cliente, pk=pk)
        consultas = Consulta.objects.filter(cliente=cliente)
        return render(
            request, "paciente.html", {"cliente": cliente, "consultas": consultas}
        )
    elif request.method == "POST":
        observacao = request.POST.get("observacao")
        video = request.FILES.get("video")
        exames = request.FILES.get("exames")

        cliente = get_object_or_404(Cliente, pk=pk)
        consulta = Consulta(
            cliente=cliente, observacao=observacao, video=video, pdf=exames
        )
        consulta.save()

        return redirect("paciente", pk)


def consulta(request, pk):
    consulta_obj = get_object_or_404(Consulta.objects.select_related("cliente"), pk=pk)
    return render(
        request,
        "consulta.html",
        {
            "consulta": consulta_obj,
            "cliente": consulta_obj.cliente,
        },
    )


def triagem(request, id_cliente):
    frequencia_cardiaca = request.POST.get("frequencia_cardiaca")
    frequencia_respiratoria = request.POST.get("frequencia_respiratoria")
    temperatura = request.POST.get("temperatura")
    peso = request.POST.get("peso")
    queixa = request.POST.get("queixa")
    observacao = request.POST.get("observacao")

    cliente = get_object_or_404(Cliente, id=id_cliente)

    agent = TriagemAgent.build_agent()

    prompt = TriagemAgent.mount_prompt(
        frequencia_cardiaca,
        frequencia_respiratoria,
        temperatura,
        peso,
        queixa,
        observacao,
    )
    print(prompt)

    response: RunOutput = agent.run(prompt)

    result = response.content.cor

    cliente.triagem = result
    cliente.save()

    return redirect("paciente", id_cliente)


@csrf_exempt
def chat(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "GET":
        consultas = Consulta.objects.filter(cliente=cliente).order_by("-data")
        ultima_consulta = consultas.first()
        total_exames = consultas.filter(pdf__isnull=False).exclude(pdf="").count()
        return render(
            request,
            "chat.html",
            {
                "cliente": cliente,
                "ultima_consulta": ultima_consulta,
                "total_consultas": consultas.count(),
                "total_exames": total_exames,
            },
        )
    elif request.method == "POST":
        pergunta = request.POST.get("pergunta")
        pergunta_model = Pergunta(pergunta=pergunta, cliente=cliente)
        pergunta_model.save()
        return JsonResponse({"id": pergunta_model.id})


@csrf_exempt
def stream_resposta(request):
    id_pergunta = request.POST.get("id_pergunta")
    pergunta = get_object_or_404(Pergunta, id=id_pergunta)

    def gerar_resposta():
        agent = AssistentAgent.build_agent(
            knowledge_filters={"paciente_id": pergunta.cliente.id}
        )

        stream: Iterator[RunOutputEvent] = agent.run(
            pergunta.pergunta, stream=True, stream_events=True
        )

        for chunk in stream:
            if chunk.event == RunEvent.run_content:
                if chunk.content:
                    yield str(chunk.content)
            if chunk.event == RunEvent.tool_call_completed:
                context = ContextRag(
                    content=chunk.tool.result,
                    tool_name=chunk.tool.tool_name,
                    tool_args=chunk.tool.tool_args,
                    pergunta=pergunta,
                )
                context.save()

    response = StreamingHttpResponse(
        gerar_resposta(), content_type="text/plain; charset=utf-8"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def fontes(request, pk):
    pergunta = get_object_or_404(Pergunta.objects.select_related("cliente"), pk=pk)
    contextos = ContextRag.objects.filter(pergunta=pergunta).order_by("id")
    return render(
        request,
        "fontes.html",
        {
            "pergunta": pergunta,
            "cliente": pergunta.cliente,
            "contextos": contextos,
            "total_fontes": contextos.count(),
        },
    )


@csrf_exempt
def webhook_whatsapp(request):
    data = json.loads(request.body)
    phone = data.get("data").get("key").get("remoteJid").split("@")[0]
    message = data.get("data").get("message").get("extendedTextMessage").get("text")

    agent = SecretariaAI.build_agent(session_id=phone)
    response = agent.run(message)
    send_message = SendMessage()
    send_message.send_message(
        instance="Numero_do_Caio",
        body={"phone": phone, "text_response": response.content},
    )
    return JsonResponse({"status": "ok"})
