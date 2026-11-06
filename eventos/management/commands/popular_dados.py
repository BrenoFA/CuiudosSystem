from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from eventos.models import Categoria, Evento

CATEGORIAS = [
    ("Palestra", "Apresentações abertas ao público"),
    ("Oficina", "Atividades práticas em pequenos grupos"),
    ("Minicurso", "Formações curtas com vários encontros"),
    ("Competição", "Maratonas, hackathons e torneios"),
    ("Cultura", "Mostras, música e integração"),
]

# título, categoria, local, dias a partir de hoje, hora, vagas, descrição
EVENTOS = [
    (
        "Introdução ao Django na prática", "Oficina",
        "Laboratório de Informática 2", 7, 14, 20,
        "Do projeto vazio à primeira página: models, views e templates em uma "
        "tarde. Traga seu notebook com Python instalado.",
    ),
    (
        "Carreira em tecnologia no Norte do Brasil", "Palestra",
        "Auditório", 10, 19, 80,
        "Profissionais da região contam como começaram e o que o mercado "
        "procura em quem está se formando.",
    ),
    (
        "Git e GitHub sem medo", "Minicurso",
        "Laboratório de Informática 1", 12, 8, 25,
        "Commits, branches e pull requests explicados com exercícios em dupla.",
    ),
    (
        "Maratona de Programação do Campus", "Competição",
        "Bloco C", 18, 9, 30,
        "Equipes de três pessoas resolvem problemas de lógica durante cinco "
        "horas. Há premiação para os três primeiros lugares.",
    ),
    (
        "Banco de dados: do modelo ao SQL", "Oficina",
        "Laboratório de Informática 2", 21, 14, 3,
        "Modelagem de tabelas, chaves estrangeiras e consultas em exemplos "
        "reais. Turma reduzida para acompanhamento individual.",
    ),
    (
        "Mostra de Projetos Integradores", "Cultura",
        "Pátio central", 28, 16, 150,
        "As turmas apresentam os projetos desenvolvidos no semestre. Entrada "
        "livre para toda a comunidade.",
    ),
]


class Command(BaseCommand):
    help = "Cria categorias e eventos de exemplo. Pode ser executado mais de uma vez."

    def handle(self, *args, **options):
        User = get_user_model()
        organizador, criado = User.objects.get_or_create(
            username="organizacao",
            defaults={"first_name": "Organização do Campus"},
        )
        if criado:
            # Conta apenas para ser dona dos exemplos: ninguém faz login nela,
            # então não existe senha conhecida publicada no repositório.
            organizador.set_unusable_password()
            organizador.save()

        categorias = {}
        for nome, descricao in CATEGORIAS:
            categorias[nome], _ = Categoria.objects.get_or_create(
                nome=nome, defaults={"descricao": descricao}
            )

        hoje = timezone.localtime().replace(minute=0, second=0, microsecond=0)
        novos = 0
        for titulo, categoria, local, dias, hora, vagas, descricao in EVENTOS:
            _, criado = Evento.objects.get_or_create(
                titulo=titulo,
                organizador=organizador,
                defaults={
                    "categoria": categorias[categoria],
                    "local": local,
                    "data_inicio": (hoje + timedelta(days=dias)).replace(hour=hora),
                    "vagas": vagas,
                    "descricao": descricao,
                },
            )
            novos += criado

        self.stdout.write(self.style.SUCCESS(f"{novos} evento(s) novo(s) criado(s)."))
