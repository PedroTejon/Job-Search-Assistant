from django.db import models
from django.utils.timezone import now

from datetime import timedelta


class Empresa(models.Model):
    id = models.AutoField(primary_key=True)
    linkedin_id = models.TextField(null=True)
    linkedin_nome = models.TextField(null=True)
    linkedin_seguidores = models.TextField(null=True)
    imagem_url = models.TextField(null=True)
    employee_count = models.PositiveIntegerField(null=True)
    glassdoor_id = models.TextField(null=True)
    glassdoor_nome = models.TextField(null=True)
    followed = models.BooleanField(default=False)

    last_check_linkedin = models.DateTimeField(null=True)
    last_check_glassdoor = models.DateTimeField(null=True)
    
    def checado_recentemente_ln(self):
        return now() < self.last_check_linkedin + timedelta(days=1) if self.last_check_linkedin else False
    

    def checado_recentemente_gl(self):
        return now() < self.last_check_glassdoor + timedelta(days=1) if self.last_check_glassdoor else False


    def __str__(self):
        return f'{{\n"id": "{self.id}"\n"imagem": "{self.imagem_url}",\n"linkedin_id": "{self.linkedin_id}",\n"linkedin_nome": "{self.linkedin_nome}"\n"linkedin_seguidores": {self.linkedin_seguidores},\n"glassdoor_id": "{self.glassdoor_id}",\n"glassdoor_nome": "{self.glassdoor_nome}",\n"followed":{self.followed}\n}}'


class Vaga(models.Model):
    id = models.AutoField(primary_key=True)
    titulo = models.TextField()
    local = models.TextField()
    modalidade = models.TextField(choices=[['l', 'Presencial/Hibrido'], ['r', 'Remoto']], default='Presencial/Hibrido', )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    id_vaga = models.TextField()
    plataforma = models.TextField(choices=[['li', 'LinkedIn'], ['gl', 'Glassdoor']])
    n_candidaturas = models.PositiveIntegerField(null=True)
    link_inscricao = models.TextField()
    descricao = models.TextField()
    tempo_publicado = models.TextField()

    def __str__(self):
        return f'{{\n"id": "{self.id}"\n"titulo": "{self.titulo}",\n"local": "{self.local}",\n"empresa": "{self.empresa.id}",\n"modalidade": "{self.modalidade}",\n"id_vaga": "{self.id_vaga}"\n"plataforma": "{self.plataforma}",\n"link_inscricao": "{self.link_inscricao}",\n"descricao": "{self.descricao}",\n"n_candidaturas": "{self.n_candidaturas}",\n"tempo_publicado": "{self.tempo_publicado}"\n}}'