from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class CadastroTests(TestCase):
    dados = {
        "first_name": "Ana",
        "username": "ana",
        "email": "ana@example.com",
        "password1": "uma-senha-bem-forte-123",
        "password2": "uma-senha-bem-forte-123",
    }

    def test_cadastro_cria_usuario_e_ja_entra(self):
        resposta = self.client.post(reverse("contas:cadastro"), self.dados)
        self.assertRedirects(resposta, reverse("eventos:lista"))
        usuario = User.objects.get(username="ana")
        self.assertEqual(self.client.session["_auth_user_id"], str(usuario.pk))

    def test_cadastro_nao_da_poderes_de_administrador(self):
        self.client.post(reverse("contas:cadastro"), self.dados)
        usuario = User.objects.get(username="ana")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

    def test_email_repetido_e_rejeitado_sem_diferenciar_maiusculas(self):
        User.objects.create_user("outra", email="ana@example.com", password="x")
        dados = {**self.dados, "email": "ANA@example.com"}
        resposta = self.client.post(reverse("contas:cadastro"), dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(User.objects.filter(username="ana").exists())

    def test_quem_ja_esta_logado_nao_ve_o_cadastro(self):
        self.client.force_login(User.objects.create_user("bia", password="x"))
        resposta = self.client.get(reverse("contas:cadastro"))
        self.assertRedirects(resposta, reverse("eventos:lista"))


class SessaoTests(TestCase):
    def test_login_volta_para_a_pagina_pedida(self):
        User.objects.create_user("bia", password="senha-de-teste-1")
        destino = reverse("eventos:criar")
        resposta = self.client.post(
            reverse("contas:login"),
            {"username": "bia", "password": "senha-de-teste-1", "next": destino},
        )
        self.assertRedirects(resposta, destino)

    def test_logout_exige_post(self):
        self.client.force_login(User.objects.create_user("bia", password="x"))
        self.assertEqual(self.client.get(reverse("contas:logout")).status_code, 405)
        self.client.post(reverse("contas:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
