from django.contrib import admin
from django.db.models import Count

from .models import Categoria, Evento, Inscricao

admin.site.site_header = "Campus Eventos"
admin.site.site_title = "Campus Eventos"
admin.site.index_title = "Administração"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "descricao", "total_eventos")
    search_fields = ("nome",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_total=Count("eventos"))

    @admin.display(description="eventos", ordering="_total")
    def total_eventos(self, obj):
        return obj._total


class InscricaoInline(admin.TabularInline):
    model = Inscricao
    extra = 0
    autocomplete_fields = ("participante",)
    readonly_fields = ("criada_em",)


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = (
        "titulo",
        "categoria",
        "organizador",
        "data_inicio",
        "vagas",
        "inscritos",
    )
    list_filter = ("categoria", "data_inicio")
    list_select_related = ("categoria", "organizador")
    search_fields = ("titulo", "local", "organizador__username")
    date_hierarchy = "data_inicio"
    autocomplete_fields = ("categoria", "organizador")
    inlines = [InscricaoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).com_total_inscritos()

    @admin.display(description="inscritos", ordering="total_inscritos")
    def inscritos(self, obj):
        return obj.total_inscritos


@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ("evento", "participante", "criada_em")
    list_filter = ("evento__categoria",)
    list_select_related = ("evento", "participante")
    search_fields = ("evento__titulo", "participante__username")
    autocomplete_fields = ("evento", "participante")
