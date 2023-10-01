from os import listdir
from json import load, dump, loads
from modules.utils import elemento_existe, query_selector, query_selector_all, filtrar_vaga, initialize_puppet
from time import sleep
from requests import get, Session
from bs4 import BeautifulSoup
from unidecode import unidecode
from numpy import split, arange
from re import sub
from base64 import b64encode

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
        codigos = soup.find_all('code', id=lambda id: id and id.startswith("bpr-guid-"))

        conta_atual = len(vagas) + len(vagas_recusadas)
        for tag_codigo in codigos:
            resposta = loads(tag_codigo.get_text().replace('&quot;', '"').replace('&amp;', '&').replace('&#61;', '='))

            for elemento in filter(lambda obj: 'preDashNormalizedJobPostingUrn' in obj, resposta['included']):
                codigo = elemento['preDashNormalizedJobPostingUrn'].replace('urn:li:fs_normalized_jobPosting:', '')
                if codigo not in vagas:
                    titulo = elemento['jobPostingTitle']
                    local = elemento['secondaryDescription']['text']
                    if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, 0 if 'Remoto' in local else 1):
                        empresa = elemento['primaryDescription']['text']
                        
                        vagas[codigo] = {'titulo': titulo, 'local': local, 'empresa': empresa, 'modalidade': 'Remoto' if 'Remoto' in local else 'Presencial/Hibrido'}
                    else:
                        vagas_recusadas.add(titulo)
        
        if conta_atual == len(vagas) + len(vagas_recusadas):
            break

        sleep(1)
        page += 1

    return [vagas, vagas_recusadas]


def scrape_vagas_empresas(lista_empresas: dict, modalidade: str, ) -> [dict, set]:
    vagas = {}
    vagas_recusadas = set()

    for lista in split(list(lista_empresas.keys()), arange(10, len(list(lista_empresas.keys())), 10)):
        empresas_code = '%2C'.join([lista_empresas[empresa]['id'] for empresa in lista])

        page = 0
        while True:
            if modalidade == 'Presencial/Hibrido':
                request = get(f'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_C={empresas_code}&f_CR=106057199&geoId=92000000&start={page * 25}&f_WT=1%2C3')
            else:
                request = get(f'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_C={empresas_code}&f_CR=106057199&geoId=92000000&start={page * 25}&f_WT=2')
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
                    if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, 1):
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
            codigo = vaga.find('div', {'class': 'base-card'})
            if not codigo:
                codigo = vaga.find('a', {'class': 'base-card'})
            codigo = codigo['data-entity-urn'].replace('urn:li:jobPosting:', '')
            
            if codigo not in vagas:
                titulo = sub(r' {2,}|\n', '', vaga.find('h3', {'class': 'base-search-card__title'}).get_text().strip())
                local = vaga.find('span', {'class': 'job-search-card__location'}).get_text().strip()
                if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, 1):
                    empresa = vaga.find('a', {'class': 'hidden-nested-link'}).get_text().strip()
                    
                    vagas[codigo] = {'titulo': titulo, 'local': local, 'empresa': empresa, 'modalidade': 'Remoto'}
                else:
                    vagas_recusadas.add(titulo)
            
        sleep(1)
        page += 1

    return [vagas, vagas_recusadas]


def save_company_images(response: Response):
    global imagens
    if response.header_value('content-type') == 'image/jpeg' and 'company-logo' in response.url:
        imagens[response.url] = b64encode(response.body()).decode('ascii')


def block_unwanted_requests(route: Route):
    if route.request.resource_type in ['image'] and 'company-logo' not in route.request.url:
        route.abort()
    elif 'graphql' in route.request.url and not 'interests' in route.request.url.lower() :
        route.abort()
    else:
        route.continue_(headers=route.request.headers)


def get_followed_companies(url: str) -> dict:
    global imagens
    with initialize_puppet() as driver:
        imagens = {}

        driver.on('response', save_company_images)
        driver.route('**/*', block_unwanted_requests)

        # Espera a request do banco de dados que informa quantas empresas você segue
        with driver.expect_response(lambda x: 'interests' in x.url.lower() and 'graphql' in x.url) as response:
            driver.goto(url + 'details/interests/' if url[-1] == '/' else url + '/details/interests/')

        painel_lista = query_selector(driver, '.pvs-list')
        painel_lista.wait_for()

        botao = query_selector(driver, 'button.scaffold-finite-scroll__load-button')
        botao.wait_for(state='attached')
        while driver.evaluate('document.querySelector("button.scaffold-finite-scroll__load-button")'):
            with driver.expect_response(lambda x: 'interests' in x.url.lower() and 'graphql' in x.url) as response:
                botao.click()
            sleep(1)

        # Pega os links dos elementos <a> dentro da lista e escreve num arquivo de texto, com cada entrada em uma linha
        empresas = {}
        for secao in query_selector_all(painel_lista, '.pvs-list__paged-list-item.artdeco-list__item.pvs-list__item--line-separated.pvs-list__item--one-column'):
            id = query_selector(secao, 'a.optional-action-target-wrapper').get_attribute('href').split('/')[4]
            nome = query_selector(secao, 'div.mr1 span').text_content().strip()

            if elemento_existe(secao, 'img.evi-image'):
                imagem = 'data:image/png;base64,' + imagens[query_selector(secao, 'img.evi-image').get_attribute('src')]
            else:
                imagem = None

            empresas[nome] = {
                'id': id,
                'imagem': imagem
            }

        dump(empresas, open('data/linkedin_followed.json', 'w', encoding='utf-8'))

        return empresas

    # cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
    # cookies_simplificados = {cookie['name']: cookie['value'].replace('\"', '') for cookie in cookies}

    # sessao = Session()
    
    # vagas = []
    # vagas_recusadas = set()
    
    # page = 0
    # while True:
    #     request = sessao.get(f'https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(profileUrn:urn%3Ali%3Afsd_profile%3AACoAADNkf4EBpG80N1CmufGBMrJ8O3nrwFhhedY,sectionType:interests,tabIndex:0)&&queryId=voyagerIdentityDashProfileComponents.154576510fd702ad99462a05a20e019d', cookies=cookies_simplificados, headers={'csrf-token': 'ajax:4070828514612690837'})
    #     with open('aaa.html', 'w', encoding='utf-8') as file:
    #         file.write(request.content.decode('utf-8'))

    #     if request.status_code in [400, 429]:
    #         sleep(1)
    #         continue
    #     soup = BeautifulSoup(request.content, 'html.parser')
    #     codigos = soup.find_all('code', id=lambda id: id and id.startswith("bpr-guid-"))

    #     conta_atual = len(vagas) + len(vagas_recusadas)
    #     for tag_codigo in codigos:
    #         resposta = loads(tag_codigo.get_text().replace('&quot;', '"').replace('&amp;', '&').replace('&#61;', '='))
        
    #         for elemento in filter(lambda obj: 'preDashNormalizedJobPostingUrn' in obj, resposta['included']):
    #             titulo = elemento['jobPostingTitle']
    #             local = elemento['secondaryDescription']['text']
    #             if filtrar_vaga(sub(r'[\[\]\(\),./\\\n ]+', ' ', unidecode(titulo).lower()), local, 0 if 'Remoto' in local else 1):
    #                 empresa = elemento['primaryDescription']['text']
    #                 codigo = elemento['preDashNormalizedJobPostingUrn'].replace('urn:li:fs_normalized_jobPosting:', '')
    #                 if 'Remoto' in local:
    #                     vagas.append([titulo, local, empresa, 'Remoto', codigo])
    #                 else:
    #                     vagas.append([titulo, local, empresa, 'Presencial/Hibrido', codigo])
    #             else:
    #                 vagas_recusadas.add(titulo)
        
    #     if conta_atual == len(vagas) + len(vagas_recusadas):
    #         break

    #     sleep(1)
    #     page += 1

    # return [vagas, vagas_recusadas]


def get_jobs(env: dict, update_followed: bool = False):
    if 'linkedin_followed.json' not in listdir('data') or update_followed:
        lista_empresas = get_followed_companies(env['lnProfile'])
    else:
        lista_empresas = load(open('data/linkedin_followed.json', 'r', encoding='utf-8'))

    vagas = {}
    vagas_recusadas = set()

    res_vagas_empresas_pres = scrape_vagas_empresas(lista_empresas, 'Presencial/Hibrido')
    vagas |= res_vagas_empresas_pres[0]
    vagas_recusadas.update(res_vagas_empresas_pres[1])

    res_vagas_empresas_remo = scrape_vagas_empresas(lista_empresas, 'Remoto')
    vagas |= res_vagas_empresas_remo[0]
    vagas_recusadas.update(res_vagas_empresas_remo[1])

    res_vagas_recomendadas = scrape_vagas_recomendadas()
    vagas |= res_vagas_recomendadas[0]
    vagas_recusadas.update(res_vagas_recomendadas[1])

    res_vagas_recentes_remo = scrape_vagas_remotos()
    vagas |= res_vagas_recentes_remo[0]
    vagas_recusadas.update(res_vagas_recentes_remo[1])

    dump(vagas, open('data/vagas_accepted.json', 'w', encoding='utf-8'))
    with open('data/vagas_refused.txt', 'w', encoding='utf-8') as file:
        file.write('\n'.join(vagas_recusadas))

    # pegar info das vagas por requests
    #f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/3705238738'