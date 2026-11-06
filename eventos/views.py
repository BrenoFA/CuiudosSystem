from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import EventoForm
from .models import Categoria, Evento, InscricaoNaoPermitida


class EventoListView(ListView):
    template_name = "eventos/lista.html"
    context_object_name = "eventos"
    paginate_by = 9

    def get_queryset(self):
        eventos = Evento.objects.com_total_inscritos().select_related("categoria")

        # order_by explícito: com annotate(Count) há GROUP BY, e o Django
        # ignora o ordering do Meta. A paginação ficaria sem ordem definida.
        if self.request.GET.get("periodo") == "encerrados":
            eventos = eventos.encerrados().order_by("-data_inicio")
        else:
            eventos = eventos.futuros().order_by("data_inicio")

        busca = self.request.GET.get("q", "").strip()
        if busca:
            eventos = eventos.filter(
                Q(titulo__icontains=busca)
                | Q(descricao__icontains=busca)
                | Q(local__icontains=busca)
            )

        categoria = self.request.GET.get("categoria", "")
        if categoria.isdigit():
            eventos = eventos.filter(categoria_id=categoria)

        return eventos

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["categorias"] = Categoria.objects.all()
        contexto["busca"] = self.request.GET.get("q", "").strip()
        contexto["categoria_atual"] = self.request.GET.get("categoria", "")
        contexto["periodo"] = self.request.GET.get("periodo", "")
        return contexto


class EventoDetailView(DetailView):
    template_name = "eventos/detalhe.html"
    context_object_name = "evento"
    queryset = Evento.objects.select_related("categoria", "organizador")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        evento = self.object
        contexto["eh_organizador"] = evento.organizador_id == usuario.pk
        contexto["inscrito"] = (
            usuario.is_authenticated
            and evento.inscricoes.filter(participante=usuario).exists()
        )
        if contexto["eh_organizador"]:
            contexto["inscricoes"] = evento.inscricoes.select_related("participante")
        return contexto


class OrganizadorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Anônimo vai para o login; logado sem ser o dono recebe 403."""

    def test_func(self):
        return self.get_object().organizador_id == self.request.user.pk


class EventoCreateView(LoginRequiredMixin, CreateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/form.html"

    def form_valid(self, form):
        # O organizador vem da sessão, nunca do formulário.
        form.instance.organizador = self.request.user
        messages.success(self.request, "Evento publicado.")
        return super().form_valid(form)


class EventoUpdateView(OrganizadorRequiredMixin, UpdateView):
    model = Evento
    form_class = EventoForm
    template_name = "eventos/form.html"

    def form_valid(self, form):
        messages.success(self.request, "Alterações salvas.")
        return super().form_valid(form)


class EventoDeleteView(OrganizadorRequiredMixin, DeleteView):
    model = Evento
    template_name = "eventos/confirmar_exclusao.html"
    context_object_name = "evento"
    success_url = reverse_lazy("eventos:meus_eventos")

    def form_valid(self, form):
        messages.success(self.request, "Evento excluído.")
        return super().form_valid(form)


class AcaoInscricaoView(LoginRequiredMixin, View):
    """Base das ações de inscrição, que só alteram dados via POST.

    O GET existe por um motivo: quem clica no botão com a sessão expirada
    passa pelo login e volta para esta URL com um GET. Sem este método a
    pessoa veria um erro 405 logo depois de entrar.
    """

    mensagem_sucesso = ""

    def executar(self, evento):
        raise NotImplementedError

    def get(self, request, pk):
        return redirect(get_object_or_404(Evento, pk=pk))

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        try:
            self.executar(evento)
        except InscricaoNaoPermitida as erro:
            messages.error(request, str(erro))
        else:
            messages.success(request, self.mensagem_sucesso)
        return redirect(evento)


class InscreverView(AcaoInscricaoView):
    mensagem_sucesso = "Inscrição confirmada."

    def executar(self, evento):
        evento.inscrever(self.request.user)


class CancelarInscricaoView(AcaoInscricaoView):
    mensagem_sucesso = "Inscrição cancelada."

    def executar(self, evento):
        evento.cancelar_inscricao(self.request.user)


class MeusEventosView(LoginRequiredMixin, ListView):
    template_name = "eventos/meus_eventos.html"
    context_object_name = "eventos"
    paginate_by = 9

    def get_queryset(self):
        return (
            Evento.objects.filter(organizador=self.request.user)
            .com_total_inscritos()
            .select_related("categoria")
            .order_by("-data_inicio")
        )


class MinhasInscricoesView(LoginRequiredMixin, ListView):
    template_name = "eventos/minhas_inscricoes.html"
    context_object_name = "eventos"
    paginate_by = 9

    def get_queryset(self):
        # A ordem importa: contar antes de filtrar. Invertendo, o Count usaria
        # o JOIN já filtrado e todo evento apareceria com 1 inscrito.
        return (
            Evento.objects.com_total_inscritos()
            .filter(inscricoes__participante=self.request.user)
            .select_related("categoria")
            .order_by("-data_inicio")
        )
