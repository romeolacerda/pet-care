from django.db import models

# Create your models here.
class Cliente(models.Model):
    especie_choices = [
        ('C', 'Cachorro'),
        ('G', 'Gato'),
    ]
    raca_choices = [
        ('SRD', 'SRD'),
        ('Labrador', 'Labrador'),
    ]
    triagem_choices = [
        ('verde', 'Verde'),
        ('amarelo', 'Amarelo'),
        ('laranja', 'Laranja'),
        ('vermelho', 'Vermelho'),
    ]
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, null=True, blank=True)
    telefone = models.CharField(max_length=15, null=True, blank=True)
    especie = models.CharField(max_length=1, choices=especie_choices, default='C')
    nome_animal = models.CharField(max_length=100, null=True, blank=True)
    raca = models.CharField(max_length=100, null=True, blank=True)
    idade = models.IntegerField(null=True, blank=True)
    peso = models.FloatField(null=True, blank=True)
    triagem = models.CharField(max_length=10, choices=triagem_choices, null=True, blank=True)

    def __str__(self):
        return self.nome