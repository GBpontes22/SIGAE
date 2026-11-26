from django.test import SimpleTestCase
from django.urls import reverse


class InicioTests(SimpleTestCase):
    def test_inicio_renderiza_template_com_css_e_aviso_academico(self):
        response = self.client.get(reverse("atendimentos:inicio"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "atendimentos/inicio.html")
        self.assertContains(response, "SIGAE WEB")
        self.assertContains(response, "/static/css/base.css")
        self.assertContains(response, "simulador acadêmico")

    def test_inicio_nao_aceita_post(self):
        response = self.client.post(reverse("atendimentos:inicio"))

        self.assertEqual(response.status_code, 405)
