from os import listdir
from json import load, dump, loads
from urllib.parse import unquote
from modules.utils import filtrar_vaga
from time import sleep
from requests import get, Session
from bs4 import BeautifulSoup, PageElement
from unidecode import unidecode
from numpy import split, arange
from re import sub


def scrape_vagas_recomendadas() -> dict:
    cookies = {cookie['name']: cookie['value'].replace('\"', '') for cookie in load(open('data/cookies.json', 'r', encoding='utf-8'))}

    sessao = Session()
    
    vagas = {}
    vagas_recusadas = 0
    
    page = 0
    while True:
        request = sessao.get(f'https://www.linkedin.com/jobs/collections/recommended/?start={25 * page}', cookies=cookies)
        if request.status_code in [400, 429]:
            sleep(1)
            continue
        soup = BeautifulSoup(request.content, 'html.parser')
        
        conta_atual = len(vagas) + vagas_recusadas
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
                        
                        vagas[codigo] = {'titulo': titulo, 'local': local, 'empresa': empresa, 'modalidade': modalidade, 'plataforma': 'LinkedIn'}
                    else:
                        vagas_recusadas += 1
        
        if conta_atual >= len(vagas) + vagas_recusadas:
            break

        sleep(.5)
        page += 1

    return vagas


def extrair_vagas(itens: list) -> dict:
    vagas = {}

    for vaga in itens:
        codigo_entidade: PageElement = vaga.find('div', {'class': 'base-card'})
        if not codigo_entidade:
            codigo_entidade = vaga.find('a', {'class': 'base-card'})
        
        codigo: str = codigo_entidade['data-entity-urn'].replace('urn:li:jobPosting:', '')
        if codigo not in vagas:
            titulo = sub(r' {2,}|\n', '', vaga.find('h3', {'class': 'base-search-card__title'}).get_text().strip())
            local = vaga.find('span', {'class': 'job-search-card__location'}).get_text().strip()

            modalidade: str = 'Remoto' if 'Remoto' in local else 'Presencial/Hibrido'
            if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, modalidade):
                empresa = vaga.find('a', {'class': 'hidden-nested-link'}).get_text().strip()
                
                vagas[codigo] = {'titulo': titulo, 'local': local, 'empresa': empresa, 'modalidade': modalidade, 'plataforma': 'LinkedIn'}
    
    return vagas


def scrape_vagas_empresas(lista_empresas: dict) -> dict:
    vagas = {}

    for lista in split(list(lista_empresas), arange(10, len(list(lista_empresas)), 10)):
        empresas_code = '%2C'.join([lista_empresas[empresa]['linkedin_id'] for empresa in lista])

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

            vagas |= extrair_vagas(itens)

            sleep(.5)
            page += 1

    return vagas


def scrape_vagas_remotos() -> dict:
    vagas = {}

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

        vagas |= extrair_vagas(itens)
            
        sleep(.5)
        page += 1

    return vagas


def scrape_detalhes_vagas(vagas: dict) -> dict:
    for vaga in filter(lambda x: vagas[x]['plataforma'] == 'LinkedIn', vagas):
        detalhes_vaga = get(f'https://www.linkedin.com/jobs/view/{vaga}/')

        if detalhes_vaga.status_code in [400, 429]:
            sleep(1)
            continue
        detalhes_soup = BeautifulSoup(detalhes_vaga.content, 'html.parser')

        link_el = detalhes_soup.select_one('a.sign-up-modal__company_webiste')
        if link_el:
            vagas[vaga]['link_inscricao'] = unquote(detalhes_soup.select_one('a.sign-up-modal__company_webiste')['href'] \
                .replace(f'https://www.linkedin.com/jobs/view/externalApply/{vaga}?url=', '') \
                .split('&')[0])
        else:
            vagas[vaga]['link_inscricao'] = f'https://www.linkedin.com/jobs/view/{vaga}/'
        
        vagas[vaga]['descricao'] = detalhes_soup.find('div', {'class': 'description__text description__text--rich'}).find('div', {'class': 'show-more-less-html__markup'}).decode_contents().strip()

        vagas[vaga]['n_candidaturas'] =  detalhes_soup.select_one('.num-applicants__caption').get_text().strip()

        vagas[vaga]['tempo_publicado'] = detalhes_soup.select_one('span.posted-time-ago__text').get_text().strip()


        sleep(0.2)

    return vagas


def get_followed_companies() -> dict:
    empresas = {}
    cookies = {cookie['name']: cookie['value'].replace('\"', '') for cookie in load(open('data/cookies.json', 'r', encoding='utf-8'))}
    armazenamento_local = load(open('data/armazenamento_local.json', 'r', encoding='utf-8'))

    sessao = Session()
    
    profile_id = armazenamento_local['profile_id']
    detalhes_empresas_iniciais = sessao.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:0,count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28{profile_id}%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c', cookies=cookies, headers={'csrf-token': cookies['JSESSIONID']})
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
            'linkedin_id': id,
            'imagem': logo_url,
            'linkedin_seguidores': follow_count
        }
        
    total = data['data']['identityDashProfileComponentsByPagedListComponent']['paging']['total']

    for i in range(100, total, 100):
        detalhes_empresas_restantes = sessao.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:{i},count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28ACoAADNkf4EBpG80N1CmufGBMrJ8O3nrwFhhedY%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c', cookies=cookies, headers={'csrf-token': cookies['JSESSIONID']})
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
                'linkedin_id': id,
                'imagem': logo_url,
                'linkedin_seguidores': follow_count
            }

    dump(empresas, open('data/companies_followed.json', 'w', encoding='utf-8'), ensure_ascii=False)
    return empresas


def get_jobs(update_followed: bool = False):
    if 'companies_followed.json' not in listdir('data') or update_followed:
        lista_empresas = get_followed_companies()
    else:
        lista_empresas = load(open('data/companies_followed.json', 'r', encoding='utf-8'))

    vagas = {}

    res_vagas_empresas = scrape_vagas_empresas(lista_empresas)
    vagas |= res_vagas_empresas

    res_vagas_recomendadas = scrape_vagas_recomendadas()
    vagas |= res_vagas_recomendadas

    res_vagas_recentes_remo = scrape_vagas_remotos()
    vagas |= res_vagas_recentes_remo

    dump(vagas, open('data/vagas_accepted.json', 'w', encoding='utf-8'), ensure_ascii=False)

    vagas = scrape_detalhes_vagas(vagas)

    dump(vagas, open('data/vagas_accepted.json', 'w', encoding='utf-8'), ensure_ascii=False)

    return vagas

    # pegar info das vagas por requests
    #f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/3705238738'