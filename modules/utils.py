from json import load
from re import sub

filtros = load(open('filtros.json', 'r', encoding='utf-8'))

from interfaces.vagas_interface.models import Empresa, Vaga

def empresa_existe(e_id, plataforma) -> bool:
    if plataforma == 'linkedin':
        return Empresa.objects.filter(plataformas__linkedin__id__exact=e_id).exists()
    elif plataforma == 'glassdoor':
        return Empresa.objects.filter(plataformas__glassdoor__id__exact=e_id).exists()
    

def empresa_existe_nome(e_nome, plataforma) -> bool:
    try:
        if plataforma == 'linkedin':
            return Empresa.objects.get(plataformas__linkedin__nome__iexact=e_nome)
        elif plataforma == 'glassdoor':
            return Empresa.objects.get(plataformas__glassdoor__nome__iexact=e_nome)
        
    except:
        return Empresa()


def vaga_existe(e_id) -> bool:
    return Vaga.objects.filter(id_vaga__exact=e_id).exists()


def filtrar_vaga(titulo, local, tipo):
    local = sub(r'\s*\(\bPresencial\b\)|\s*\(\bHíbrido\b\)|\s*\(\bRemoto\b\)', '', local)
    if local.count(',') == 2:
        cidade, estado, pais = local.split(', ')
    elif local.count(',') == 1:
        estado, pais = local.split(', ')
    elif local.count(',') == 0:
        cidade = local.split(', ')[0]

    if tipo == 'Presencial/Hibrido':
        if 'cidade' in locals() and len(filtros['cidades']) and not any(map(lambda x: x == cidade, filtros['cidades'])):
            return False
        elif 'estado' in locals() and len(filtros['estados']) and not any(map(lambda x: x == estado, filtros['estados'])):
            return False
        elif 'pais' in locals() and len(filtros['paises']) and not any(map(lambda x: x == pais, filtros['paises'])):
            return False
        
    if any(map(lambda x: x in titulo.split(), filtros['excludeWords'])):
        return False
    
    if any(map(lambda x: x in titulo, filtros['excludeTerms'])):
        return False
    
    return True
    