from django.urls import path

from . import views

app_name = "eventos"

urlpatterns = [
    path("", views.EventoListView.as_view(), name="lista"),
    path("eventos/novo/", views.EventoCreateView.as_view(), name="criar"),
    path("eventos/<int:pk>/", views.EventoDetailView.as_view(), name="detalhe"),
    path("eventos/<int:pk>/editar/", views.EventoUpdateView.as_view(), name="editar"),
    path("eventos/<int:pk>/excluir/", views.EventoDeleteView.as_view(), name="excluir"),
    path("eventos/<int:pk>/inscrever/", views.InscreverView.as_view(), name="inscrever"),
    path(
        "eventos/<int:pk>/cancelar/",
        views.CancelarInscricaoView.as_view(),
        name="cancelar",
    ),
    path("meus-eventos/", views.MeusEventosView.as_view(), name="meus_eventos"),
    path(
        "minhas-inscricoes/",
        views.MinhasInscricoesView.as_view(),
        name="minhas_inscricoes",
    ),
]
