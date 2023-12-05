from playwright.sync_api import sync_playwright, Page
from json import load
from os import listdir

filtros = load(open('filtros.json', 'r', encoding='utf-8'))

from interfaces.vagas_interface.models import Empresa, Vaga

def empresa_existe(e_id, plataforma) -> bool:
    if plataforma == 'linkedin':
        return Empresa.objects.filter(linkedin_id__exact=e_id).exists()
    elif plataforma == 'glassdoor':
        return Empresa.objects.filter(glassdoor_id__exact=e_id).exists()
    

def empresa_existe_nome(e_nome, plataforma) -> bool:
    try:
        if plataforma == 'linkedin':
            return Empresa.objects.get(linkedin_nome__exact=e_nome)
        elif plataforma == 'glassdoor':
            return Empresa.objects.get(glassdoor_nome__exact=e_nome)
        
    except:
        return Empresa()


def vaga_existe(e_id) -> bool:
    return Vaga.objects.filter(id_vaga__exact=e_id).exists()


def filtrar_vaga(titulo, local, tipo):
    if local.count(',') == 2:
        cidade, estado, pais = local.split(', ')
    elif local.count(',') == 1:
        estado, pais = local.split(', ')
    elif local.count(',') == 0:
        cidade = local.split(', ')[0]

    if tipo == 'Presencial/Hibrido':
        if 'cidade' in locals() and not any(map(lambda x: x == cidade, filtros['cidades'])):
            return False
        if 'estado' in locals() and not any(map(lambda x: x == estado, filtros['estados'])):
            return False
        if 'pais' in locals() and not any(map(lambda x: x == pais, filtros['paises'])):
            return False
        
    if any(map(lambda x: x in titulo.split(), filtros['excludeWords'])):
        return False
    
    if any(map(lambda x: x in titulo, filtros['excludeTerms'])):
        return False
    
    return True
    