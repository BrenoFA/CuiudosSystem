from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property


class InscricaoNaoPermitida(Exception):
    """Regra de negócio impediu a operação; a mensagem vai para o usuário."""


class Categoria(models.Model):
    nome = models.CharField("nome", max_length=60, unique=True)
    descricao = models.CharField("descrição", max_length=200, blank=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "categoria"
        verbose_name_plural = "categorias"

    def __str__(self):
        return self.nome


class EventoQuerySet(models.QuerySet):
    def com_total_inscritos(self):
        return self.annotate(total_inscritos=Count("inscricoes"))

    def futuros(self):
        return self.filter(data_inicio__gte=timezone.now())

    def encerrados(self):
        return self.filter(data_inicio__lt=timezone.now())


class Evento(models.Model):
    titulo = models.CharField("título", max_length=120)
    descricao = models.TextField("descrição")
    local = models.CharField("local", max_length=120)
    data_inicio = models.DateTimeField("data e hora")
    vagas = models.PositiveIntegerField("vagas", validators=[MinValueValidator(1)])
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name="eventos",
        verbose_name="categoria",
    )
    organizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="eventos_organizados",
        verbose_name="organizador",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    objects = EventoQuerySet.as_manager()

    class Meta:
        ordering = ["data_inicio"]
        verbose_name = "evento"
        verbose_name_plural = "eventos"

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("eventos:detalhe", args=[self.pk])

    @cached_property
    def total_inscritos(self):
        # Listagens preenchem este valor com com_total_inscritos(), o que
        # evita uma consulta extra por evento. Aqui fica só o caso avulso.
        return self.inscricoes.count()

    @property
    def vagas_restantes(self):
        return max(self.vagas - self.total_inscritos, 0)

    @property
    def lotado(self):
        return self.vagas_restantes == 0

    @property
    def encerrado(self):
        return self.data_inicio < timezone.now()

    @property
    def percentual_ocupado(self):
        return min(round(self.total_inscritos * 100 / self.vagas), 100)

    def inscrever(self, usuario):
        """Inscreve o usuário, ou levanta InscricaoNaoPermitida.

        A contagem de vagas e a criação ficam na mesma transação: sem isso,
        dois pedidos simultâneos poderiam ocupar a mesma última vaga.
        """
        with transaction.atomic():
            evento = Evento.objects.select_for_update().get(pk=self.pk)
            if evento.organizador_id == usuario.pk:
                raise InscricaoNaoPermitida(
                    "Você organiza este evento e não precisa se inscrever."
                )
            if evento.encerrado:
                raise InscricaoNaoPermitida("Este evento já aconteceu.")
            if evento.inscricoes.filter(participante=usuario).exists():
                raise InscricaoNaoPermitida("Você já tem inscrição neste evento.")
            if evento.inscricoes.count() >= evento.vagas:
                raise InscricaoNaoPermitida("As vagas deste evento acabaram.")
            return evento.inscricoes.create(participante=usuario)

    def cancelar_inscricao(self, usuario):
        if self.encerrado:
            raise InscricaoNaoPermitida(
                "Este evento já aconteceu; a inscrição não pode ser cancelada."
            )
        removidas, _ = self.inscricoes.filter(participante=usuario).delete()
        if not removidas:
            raise InscricaoNaoPermitida("Você não tem inscrição neste evento.")


class Inscricao(models.Model):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name="inscricoes",
        verbose_name="evento",
    )
    participante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inscricoes",
        verbose_name="participante",
    )
    criada_em = models.DateTimeField("inscrito em", auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]
        verbose_name = "inscrição"
        verbose_name_plural = "inscrições"
        constraints = [
            models.UniqueConstraint(
                fields=["evento", "participante"],
                name="inscricao_unica_por_evento",
            ),
        ]

    def __str__(self):
        return f"{self.participante} em {self.evento}"
