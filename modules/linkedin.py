from os import listdir
from json import load, dump, loads
from modules.utils import elemento_existe, query_selector, query_selector_all, filtrar_vaga, initialize_puppet
from time import sleep
from requests import get, Session
from bs4 import BeautifulSoup, PageElement
from unidecode import unidecode
from numpy import split, arange
from re import sub
from base64 import b64encode
from urllib.parse import unquote
from playwright.sync_api import Response, Route


def scrape_vagas_recomendadas() -> [set, set]:
    cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies_simplificados = {cookie['name']: cookie['value'].replace('\"', '') for cookie in cookies}

    sessao = Session()
    
    vagas = {}
    vagas_recusadas = set()
    
    page = 0
    while True:
        request = sessao.get(f'https://www.linkedin.com/jobs/collections/recommended/?start={25 * page}', cookies=cookies_simplificados)
        if request.status_code in [400, 429]:
            sleep(1)
            continue
        soup = BeautifulSoup(request.content, 'html.parser')
        
        conta_atual = len(vagas) + len(vagas_recusadas)
        codigos = soup.find_all('code', id=lambda id: id and id.startswith("bpr-guid-"))
        for tag_codigo in codigos:
            resposta = loads(tag_codigo.get_text().replace('&quot;', '"').replace('&amp;', '&').replace('&#61;', '='))

            for elemento in filter(lambda obj: 'preDashNormalizedJobPostingUrn' in obj, resposta['included']):
                codigo = elemento['preDashNormalizedJobPostingUrn'].replace('urn:li:fs_normalized_jobPosting:', '')
                if codigo not in vagas:
                    titulo = elemento['jobPostingTitle']
                    local = elemento['secondaryDescription']['text']

                    modalidade = 'Remoto' if 'Remoto' in local else 'Presencial/Hibrido'
                    if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, modalidade):
                        empresa = elemento['primaryDescription']['text']
                        
                        vagas[codigo] = {'titulo': titulo, 'local': local, 'empresa': empresa, 'modalidade': modalidade}
                    else:
                        vagas_recusadas.add(titulo)
        
        if conta_atual >= len(vagas) + len(vagas_recusadas):
            break

        sleep(1)
        page += 1

    return [vagas, vagas_recusadas]


def scrape_vagas_empresas(lista_empresas: dict) -> [dict, set]:
    vagas = {}
    vagas_recusadas = set()

    for lista in split(list(lista_empresas), arange(10, len(list(lista_empresas)), 10)):
        empresas_code = '%2C'.join([lista_empresas[empresa]['id'] for empresa in lista])

        page = 0
        while True:
            request = get(f'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_C={empresas_code}&f_CR=106057199&geoId=92000000&start={page * 25}')
            
            if request.status_code == 400:
                break
            elif request.status_code == 429:
                sleep(1)
                continue
            soup = BeautifulSoup(request.content, 'html.parser')
            
            itens = soup.find_all('li')
            if not itens:
                break

            for vaga in itens:
                codigo = vaga.find('div', {'class': 'base-card'})['data-entity-urn'].replace('urn:li:jobPosting:', '')
                if codigo not in vagas:
                    titulo = sub(r' {2,}|\n', '', vaga.find('h3', {'class': 'base-search-card__title'}).get_text().strip())
                    local = vaga.find('span', {'class': 'job-search-card__location'}).get_text().strip()

                    modalidade = 'Remoto' if 'Remoto' in local else 'Presencial/Hibrido'
                    if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local,  modalidade):
                        empresa = vaga.find('a', {'class': 'hidden-nested-link'}).get_text().strip()
                        
                        vagas[codigo] = {'titulo': titulo, 'local': local, 'empresa': empresa, 'modalidade': modalidade}
                    else:
                        vagas_recusadas.add(titulo)
                
            sleep(1)
            page += 1

    return [vagas, vagas_recusadas]


def scrape_vagas_remotos() -> [dict, set]:
    vagas = {}
    vagas_recusadas = set()

    page = 0
    while True:
        if 40 < page:
            break

        request = get(f'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_CR=106057199&geoId=92000000&start={page * 25}&f_WT=2&f_TPR=r604800&f_I=96%2C4%2C6%2C3231')
        if request.status_code == 400:
            break
        elif request.status_code == 429:
            sleep(1)
            continue
        soup = BeautifulSoup(request.content, 'html.parser')
        
        itens = soup.find_all('li')
        if not itens:
            break
        for vaga in itens:
            codigo_entidade: PageElement = vaga.find('div', {'class': 'base-card'})
            if not codigo_entidade:
                codigo_entidade = vaga.find('a', {'class': 'base-card'})
            
            codigo: str = codigo_entidade['data-entity-urn'].replace('urn:li:jobPosting:', '')
            if codigo not in vagas:
                titulo = sub(r' {2,}|\n', '', vaga.find('h3', {'class': 'base-search-card__title'}).get_text().strip())
                local = vaga.find('span', {'class': 'job-search-card__location'}).get_text().strip()

                if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, 'Remoto'):
                    empresa = vaga.find('a', {'class': 'hidden-nested-link'}).get_text().strip()
                    
                    vagas[codigo] = {'titulo': titulo, 'local': local, 'empresa': empresa, 'modalidade': 'Remoto'}
                else:
                    vagas_recusadas.add(titulo)
            
        sleep(1)
        page += 1

    return [vagas, vagas_recusadas]


# def scrape_detalhes_vagas(vagas: dict) -> [dict]:        
#     cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
#     cookies_simplificados = {cookie['name']: cookie['value'].replace('\"', '') for cookie in cookies}

#     sessao = Session()
    
#     for vaga in vagas:
#         detalhes_vaga = sessao.get(f'https://www.linkedin.com/jobs/view/{vaga}/', cookies=cookies_simplificados)
#         if detalhes_vaga.status_code in [400, 429]:
#             sleep(1)
#             continue
#         detalhes_soup = BeautifulSoup(detalhes_vaga.content, 'html.parser')

#         vagas[vaga]['lin_inscricao'] = unquote(detalhes_soup.select_one('.sign-up-modal__direct-apply-on-company-site > a')['href'] \
#             .replace(f'https://www.linkedin.com/jobs/view/externalApply/{vaga}?url=', '') \
#             .split('&')[0])    


def save_company_images(response: Response):
    global imagens
    if response.header_value('content-type') == 'image/jpeg' and 'company-logo' in response.url:
        imagens[response.url] = b64encode(response.body()).decode('ascii')


def get_followed_companies() -> dict:
    empresas = {}
    cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies_simplificados = {cookie['name']: cookie['value'].replace('\"', '') for cookie in cookies}

    sessao = Session()
    
    detalhes_empresas_iniciais = sessao.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:0,count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28ACoAADNkf4EBpG80N1CmufGBMrJ8O3nrwFhhedY%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c', cookies=cookies_simplificados, headers={'csrf-token': cookies_simplificados['JSESSIONID']})
    data = loads(detalhes_empresas_iniciais.content.decode('utf-8'))
    for elemento in data['data']['identityDashProfileComponentsByPagedListComponent']['elements']:
        entity = elemento['components']['entityComponent']

        id = entity['textActionTarget'].replace('https://www.linkedin.com/company/', '').rstrip('/')
        follow_count = entity['subComponents']['components'][0]['components']['actionComponent']['action']['followingStateAction']['followingState']['followerCount']
        nome_empresa = entity['titleV2']['text']['text']
        logo = entity['image']['attributes'][0]['detailData']['companyLogo']['logoResolutionResult']
        logo_url = None
        if logo:
            logo_url = logo['vectorImage']['rootUrl'] + \
                logo['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment']
        
        empresas[nome_empresa] = {
            'id': id,
            'imagem': logo_url,
            'seguidores': follow_count
        }
        
    total = data['data']['identityDashProfileComponentsByPagedListComponent']['paging']['total']

    for i in range(100, total, 100):
        detalhes_empresas_restantes = sessao.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:{i},count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28ACoAADNkf4EBpG80N1CmufGBMrJ8O3nrwFhhedY%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c', cookies=cookies_simplificados, headers={'csrf-token': cookies_simplificados['JSESSIONID']})
        data = loads(detalhes_empresas_restantes.content.decode('utf-8'))

        for elemento in data['data']['identityDashProfileComponentsByPagedListComponent']['elements']:
            entity = elemento['components']['entityComponent']

            id = entity['textActionTarget'].replace('https://www.linkedin.com/company/', '').rstrip('/')
            follow_count = entity['subComponents']['components'][0]['components']['actionComponent']['action']['followingStateAction']['followingState']['followerCount']
            nome_empresa = entity['titleV2']['text']['text']
            logo = entity['image']['attributes'][0]['detailData']['companyLogo']['logoResolutionResult']
            logo_url = None
            if logo:
                logo_url = logo['vectorImage']['rootUrl'] + logo['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment']
            
            empresas[nome_empresa] = {
                'id': id,
                'imagem': logo_url,
                'seguidores': follow_count
            }

    dump(empresas, open('data/linkedin_followed.json', 'w', encoding='utf-8'), ensure_ascii=False)


def get_jobs(env: dict, update_followed: bool = False):
    if 'linkedin_followed.json' not in listdir('data') or update_followed:
        lista_empresas = get_followed_companies()
    else:
        lista_empresas = load(open('data/linkedin_followed.json', 'r', encoding='utf-8'))

    vagas = {}
    vagas_recusadas = set()

    res_vagas_empresas = scrape_vagas_empresas(lista_empresas)
    vagas |= res_vagas_empresas[0]
    vagas_recusadas.update(res_vagas_empresas[1])

    res_vagas_recomendadas = scrape_vagas_recomendadas()
    vagas |= res_vagas_recomendadas[0]
    vagas_recusadas.update(res_vagas_recomendadas[1])

    res_vagas_recentes_remo = scrape_vagas_remotos()
    vagas |= res_vagas_recentes_remo[0]
    vagas_recusadas.update(res_vagas_recentes_remo[1])



    dump(vagas, open('data/vagas_accepted.json', 'w', encoding='utf-8'), ensure_ascii=False)
    with open('data/vagas_refused.txt', 'w', encoding='utf-8') as file:
        file.write('\n'.join(vagas_recusadas))

    # pegar info das vagas por requests
    #f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/3705238738'