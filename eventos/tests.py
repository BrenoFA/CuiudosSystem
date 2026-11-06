import warnings
from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.paginator import UnorderedObjectListWarning
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import EventoForm
from .models import Categoria, Evento, Inscricao, InscricaoNaoPermitida

User = get_user_model()


class BaseEventos(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dono = User.objects.create_user("dono", password="x")
        cls.ana = User.objects.create_user("ana", password="x")
        cls.bia = User.objects.create_user("bia", password="x")
        cls.categoria = Categoria.objects.create(nome="Oficina")
        cls.evento = cls.criar_evento()

    @classmethod
    def criar_evento(cls, dias=5, vagas=2, titulo="Oficina de Django"):
        return Evento.objects.create(
            titulo=titulo,
            descricao="Descrição",
            local="Laboratório",
            data_inicio=timezone.now() + timedelta(days=dias),
            vagas=vagas,
            categoria=cls.categoria,
            organizador=cls.dono,
        )

    def dados_formulario(self, **extras):
        data = timezone.localtime() + timedelta(days=3)
        return {
            "titulo": "Novo",
            "categoria": self.categoria.pk,
            "descricao": "Texto",
            "data_inicio": data.strftime("%Y-%m-%dT%H:%M"),
            "local": "Auditório",
            "vagas": 10,
            **extras,
        }


class ControleDeAcessoTests(BaseEventos):
    def rotas_protegidas(self):
        pk = self.evento.pk
        return [
            reverse("eventos:criar"),
            reverse("eventos:editar", args=[pk]),
            reverse("eventos:excluir", args=[pk]),
            reverse("eventos:inscrever", args=[pk]),
            reverse("eventos:cancelar", args=[pk]),
            reverse("eventos:meus_eventos"),
            reverse("eventos:minhas_inscricoes"),
        ]

    def test_anonimo_e_enviado_ao_login_em_todas_as_rotas_protegidas(self):
        for url in self.rotas_protegidas():
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertRedirects(
                    resposta, f"{reverse('contas:login')}?next={url}"
                )

    def test_post_anonimo_nao_altera_nada(self):
        self.client.post(reverse("eventos:inscrever", args=[self.evento.pk]))
        self.client.post(reverse("eventos:excluir", args=[self.evento.pk]))
        self.client.post(reverse("eventos:criar"), self.dados_formulario())
        self.assertEqual(Inscricao.objects.count(), 0)
        self.assertEqual(Evento.objects.count(), 1)

    def test_paginas_publicas_abrem_sem_login(self):
        self.assertEqual(self.client.get(reverse("eventos:lista")).status_code, 200)
        self.assertEqual(self.client.get(self.evento.get_absolute_url()).status_code, 200)

    def test_quem_nao_e_dono_recebe_403_e_nao_altera_o_evento(self):
        self.client.force_login(self.ana)
        editar = reverse("eventos:editar", args=[self.evento.pk])
        excluir = reverse("eventos:excluir", args=[self.evento.pk])
        self.assertEqual(self.client.get(editar).status_code, 403)
        self.assertEqual(
            self.client.post(editar, self.dados_formulario()).status_code, 403
        )
        self.assertEqual(self.client.post(excluir).status_code, 403)
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.titulo, "Oficina de Django")

    def test_dono_edita_e_exclui(self):
        self.client.force_login(self.dono)
        self.client.post(
            reverse("eventos:editar", args=[self.evento.pk]),
            self.dados_formulario(titulo="Renomeado"),
        )
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.titulo, "Renomeado")
        self.client.post(reverse("eventos:excluir", args=[self.evento.pk]))
        self.assertFalse(Evento.objects.filter(pk=self.evento.pk).exists())

    def test_lista_de_inscritos_so_aparece_para_o_organizador(self):
        self.ana.email = "ana@example.com"
        self.ana.save()
        self.evento.inscrever(self.ana)
        self.client.force_login(self.bia)
        resposta = self.client.get(self.evento.get_absolute_url())
        self.assertNotContains(resposta, "ana@example.com")
        self.client.force_login(self.dono)
        resposta = self.client.get(self.evento.get_absolute_url())
        self.assertContains(resposta, "ana@example.com")


class CriacaoDeEventoTests(BaseEventos):
    def test_organizador_vem_da_sessao_e_nao_do_formulario(self):
        self.client.force_login(self.ana)
        self.client.post(
            reverse("eventos:criar"),
            self.dados_formulario(organizador=self.dono.pk),
        )
        self.assertEqual(Evento.objects.get(titulo="Novo").organizador, self.ana)

    def test_data_no_passado_e_rejeitada(self):
        passado = timezone.localtime() - timedelta(days=1)
        dados = self.dados_formulario(data_inicio=passado.strftime("%Y-%m-%dT%H:%M"))
        form = EventoForm(data=dados)
        self.assertIn("data_inicio", form.errors)

    def test_horario_digitado_e_o_horario_exibido(self):
        self.client.force_login(self.ana)
        data = (timezone.localtime() + timedelta(days=2)).replace(hour=14, minute=30)
        self.client.post(
            reverse("eventos:criar"),
            self.dados_formulario(data_inicio=data.strftime("%Y-%m-%dT%H:%M")),
        )
        evento = Evento.objects.get(titulo="Novo")
        self.assertEqual(timezone.localtime(evento.data_inicio).hour, 14)
        self.assertEqual(timezone.localtime(evento.data_inicio).minute, 30)

    def test_formulario_de_edicao_mostra_a_data_no_formato_do_navegador(self):
        self.client.force_login(self.dono)
        resposta = self.client.get(reverse("eventos:editar", args=[self.evento.pk]))
        esperado = timezone.localtime(self.evento.data_inicio).strftime("%Y-%m-%dT%H:%M")
        self.assertContains(resposta, f'value="{esperado}"')

    def test_nao_reduz_vagas_abaixo_do_total_de_inscritos(self):
        self.evento.inscrever(self.ana)
        self.evento.inscrever(self.bia)
        form = EventoForm(data=self.dados_formulario(vagas=1), instance=self.evento)
        self.assertIn("vagas", form.errors)

    def test_vagas_zero_e_rejeitado(self):
        form = EventoForm(data=self.dados_formulario(vagas=0))
        self.assertIn("vagas", form.errors)


class InscricaoTests(BaseEventos):
    def url(self, nome="inscrever", evento=None):
        return reverse(f"eventos:{nome}", args=[(evento or self.evento).pk])

    def test_usuario_se_inscreve_e_cancela(self):
        self.client.force_login(self.ana)
        self.client.post(self.url())
        self.assertTrue(self.evento.inscricoes.filter(participante=self.ana).exists())
        self.client.post(self.url("cancelar"))
        self.assertFalse(self.evento.inscricoes.exists())

    def test_get_nao_inscreve_e_volta_para_o_evento(self):
        # Caminho de quem perdeu a sessão: login devolve para esta URL via GET.
        self.client.force_login(self.ana)
        resposta = self.client.get(self.url())
        self.assertRedirects(resposta, self.evento.get_absolute_url())
        self.assertFalse(self.evento.inscricoes.exists())

    def test_inscricao_repetida_e_recusada(self):
        self.evento.inscrever(self.ana)
        with self.assertRaises(InscricaoNaoPermitida):
            self.evento.inscrever(self.ana)
        self.assertEqual(self.evento.inscricoes.count(), 1)

    def test_nao_passa_do_limite_de_vagas(self):
        evento = self.criar_evento(vagas=1)
        evento.inscrever(self.ana)
        with self.assertRaises(InscricaoNaoPermitida):
            evento.inscrever(self.bia)
        self.assertEqual(evento.inscricoes.count(), 1)

    def test_mensagem_de_erro_chega_ao_usuario(self):
        evento = self.criar_evento(vagas=1)
        evento.inscrever(self.bia)
        self.client.force_login(self.ana)
        resposta = self.client.post(self.url(evento=evento), follow=True)
        self.assertContains(resposta, "As vagas deste evento acabaram.")

    def test_organizador_nao_se_inscreve_no_proprio_evento(self):
        with self.assertRaises(InscricaoNaoPermitida):
            self.evento.inscrever(self.dono)

    def test_evento_encerrado_nao_aceita_inscricao_nem_cancelamento(self):
        evento = self.criar_evento(dias=2)
        evento.inscrever(self.ana)
        Evento.objects.filter(pk=evento.pk).update(
            data_inicio=timezone.now() - timedelta(days=1)
        )
        evento.refresh_from_db()
        with self.assertRaises(InscricaoNaoPermitida):
            evento.inscrever(self.bia)
        with self.assertRaises(InscricaoNaoPermitida):
            evento.cancelar_inscricao(self.ana)

    def test_cancelar_sem_inscricao_e_recusado(self):
        with self.assertRaises(InscricaoNaoPermitida):
            self.evento.cancelar_inscricao(self.ana)

    def test_banco_barra_duplicata_mesmo_sem_passar_pela_regra(self):
        Inscricao.objects.create(evento=self.evento, participante=self.ana)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Inscricao.objects.create(evento=self.evento, participante=self.ana)


class ListagemTests(BaseEventos):
    def test_proximos_eventos_vem_do_mais_proximo_para_o_mais_distante(self):
        self.criar_evento(dias=30, titulo="Distante")
        self.criar_evento(dias=1, titulo="Amanhã")
        with warnings.catch_warnings():
            warnings.simplefilter("error", UnorderedObjectListWarning)
            resposta = self.client.get(reverse("eventos:lista"))
        self.assertEqual(
            [e.titulo for e in resposta.context["eventos"]],
            ["Amanhã", "Oficina de Django", "Distante"],
        )

    def test_busca_filtra_por_titulo(self):
        self.criar_evento(titulo="Palestra de Redes")
        resposta = self.client.get(reverse("eventos:lista"), {"q": "redes"})
        self.assertEqual(
            [e.titulo for e in resposta.context["eventos"]], ["Palestra de Redes"]
        )

    def test_filtro_por_categoria(self):
        outra = Categoria.objects.create(nome="Palestra")
        resposta = self.client.get(reverse("eventos:lista"), {"categoria": outra.pk})
        self.assertEqual(len(resposta.context["eventos"]), 0)

    def test_categoria_invalida_na_url_nao_quebra_a_pagina(self):
        resposta = self.client.get(reverse("eventos:lista"), {"categoria": "abc"})
        self.assertEqual(resposta.status_code, 200)

    def test_evento_encerrado_sai_da_lista_principal(self):
        Evento.objects.filter(pk=self.evento.pk).update(
            data_inicio=timezone.now() - timedelta(days=1)
        )
        lista = reverse("eventos:lista")
        self.assertEqual(len(self.client.get(lista).context["eventos"]), 0)
        encerrados = self.client.get(lista, {"periodo": "encerrados"})
        self.assertEqual(len(encerrados.context["eventos"]), 1)

    def test_listagem_nao_faz_uma_consulta_por_evento(self):
        for numero in range(5):
            evento = self.criar_evento(titulo=f"Evento {numero}", vagas=5)
            evento.inscrever(self.ana)
        with self.assertNumQueries(3):  # contagem, eventos e categorias
            self.client.get(reverse("eventos:lista"))

    def test_minhas_inscricoes_conta_todos_os_inscritos_do_evento(self):
        self.evento.inscrever(self.ana)
        self.evento.inscrever(self.bia)
        self.client.force_login(self.ana)
        resposta = self.client.get(reverse("eventos:minhas_inscricoes"))
        self.assertEqual(resposta.context["eventos"][0].total_inscritos, 2)

    def test_meus_eventos_mostra_apenas_os_do_usuario(self):
        self.client.force_login(self.ana)
        resposta = self.client.get(reverse("eventos:meus_eventos"))
        self.assertEqual(len(resposta.context["eventos"]), 0)


class ModeloTests(BaseEventos):
    def test_categoria_com_eventos_nao_pode_ser_apagada(self):
        with self.assertRaises(ProtectedError):
            self.categoria.delete()

    def test_apagar_usuario_remove_as_inscricoes_dele(self):
        self.evento.inscrever(self.ana)
        self.ana.delete()
        self.assertEqual(self.evento.inscricoes.count(), 0)


class AdminTests(BaseEventos):
    def test_paginas_do_admin_abrem_para_os_tres_models(self):
        self.client.force_login(
            User.objects.create_superuser("admin", password="x")
        )
        inscricao = self.evento.inscrever(self.ana)
        for objeto in (self.categoria, self.evento, inscricao):
            modelo = objeto._meta.model_name
            urls = [
                reverse(f"admin:eventos_{modelo}_changelist"),
                reverse(f"admin:eventos_{modelo}_add"),
                reverse(f"admin:eventos_{modelo}_change", args=[objeto.pk]),
            ]
            for url in urls:
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_usuario_comum_nao_entra_no_admin(self):
        self.client.force_login(self.ana)
        resposta = self.client.get(reverse("admin:eventos_evento_changelist"))
        self.assertEqual(resposta.status_code, 302)


class PopularDadosTests(TestCase):
    def test_comando_pode_rodar_duas_vezes_sem_duplicar(self):
        call_command("popular_dados", stdout=StringIO())
        total = Evento.objects.count()
        self.assertGreater(total, 0)
        call_command("popular_dados", stdout=StringIO())
        self.assertEqual(Evento.objects.count(), total)

    def test_conta_de_exemplo_nao_tem_senha_utilizavel(self):
        call_command("popular_dados", stdout=StringIO())
        self.assertFalse(User.objects.get(username="organizacao").has_usable_password())
