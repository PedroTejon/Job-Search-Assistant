from django.db import models
from django.utils.timezone import now, make_aware

from datetime import timedelta, datetime


class Empresa(models.Model):
    id = models.AutoField(primary_key=True)
    imagem_url = models.TextField(null=True)
    employee_count = models.PositiveIntegerField(null=True)
    followed = models.BooleanField(default=False)


    def get_default_platforms() -> dict:
        return {
            'linkedin': {
                'id': None,
                'nome': None,
                'followers': None,
                'last_check': None
            },
            'glassdoor': {
                'id': None,
                'nome': None,
                'last_check': None
            }
        }


    plataformas = models.JSONField(default=get_default_platforms)


    def checado_recentemente_ln(self):
        return now() < make_aware(datetime.strptime(self.plataformas['linkedin']['last_check'], '%Y-%m-%dT%H:%M:%S')) + timedelta(days=1) \
            if self.plataformas['linkedin']['last_check'] else False
    

    def checado_recentemente_gl(self):
        return now() < make_aware(datetime.strptime(self.plataformas['glassdoor']['last_check'], '%Y-%m-%dT%H:%M:%S')) + timedelta(days=1) \
            if self.plataformas['glassdoor']['last_check'] else False


    def __str__(self):
        return f'{{\n"id": "{self.id}"\n"imagem": "{self.imagem_url}",\n"employee_count": {self.employee_count},\n"followed": {self.followed},\n"plataformas": {self.plataformas}}}'


class Vaga(models.Model):
    id = models.AutoField(primary_key=True)
    titulo = models.TextField()
    local = models.TextField()
    modalidade = models.TextField()
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    id_vaga = models.TextField()
    plataforma = models.TextField()
    n_candidaturas = models.PositiveIntegerField(null=True)
    link_inscricao = models.TextField()
    descricao = models.TextField()
    tempo_publicado = models.TextField()

    def __str__(self):
        return f'{{\n"id": "{self.id}"\n"titulo": "{self.titulo}",\n"local": "{self.local}",\n"empresa": "{self.empresa.id}",\n"modalidade": "{self.modalidade}",\n"id_vaga": "{self.id_vaga}"\n"plataforma": "{self.plataforma}",\n"link_inscricao": "{self.link_inscricao}",\n"descricao": "{self.descricao}",\n"n_candidaturas": "{self.n_candidaturas}",\n"tempo_publicado": "{self.tempo_publicado}"\n}}'