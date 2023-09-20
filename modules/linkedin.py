from os import listdir
from json import load
from modules.utils import elemento_existe, filhos_de_el, query_selector, query_selector_all, filtrar_vaga, initialize_puppet
from time import sleep
from requests import get
from bs4 import BeautifulSoup
from unidecode import unidecode
from numpy import split, arange


def get_followed_companies(url: str) -> set:
    with initialize_puppet() as driver:
        cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
        driver.context.add_cookies(cookies)

        # Espera a request do banco de dados que informa quantas empresas você segue
        with driver.expect_response(lambda x: 'https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(profileUrn:urn' in x.url) as response:
            driver.goto(url + 'details/interests/' if url[-1] == '/' else url + '/details/interests/')

        painel_lista = query_selector(driver, '.pvs-list')
        painel_lista.wait_for()

        query_selector(driver, 'button.scaffold-finite-scroll__load-button').wait_for('attached')
        while driver.evaluate('document.querySelector("button.scaffold-finite-scroll__load-button")'):
            driver.keyboard.press('PageDown')
            sleep(.5)

        # Pega os links dos elementos <a> dentro da lista e escreve num arquivo de texto, com cada entrada em uma linha
        with open('data/linkedin_followed.txt', 'w', encoding='utf-8') as file:
            links = set([link.get_attribute('href').split('/')[4] for link in query_selector_all(painel_lista, 'a.optional-action-target-wrapper')])
            file.write('\n'.join(links))
        
        return links


def get_jobs(env: dict, update_followed=False):
    if 'linkedin_followed.txt' not in listdir('data') or update_followed:
        lista_empresas = get_followed_companies(env['lnProfile'])
    else:
        with open('data/linkedin_followed.txt', 'r', encoding='utf-8') as file:
            lista_empresas = file.read().split('\n')

    vagas = []
    for lista in split(lista_empresas, arange(10, len(lista_empresas), 10)):    
        empresas_code = '%2C'.join(lista)
        page = 0
        while True:
            request = get(f'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?f_C={empresas_code}&f_CR=106057199&geoId=92000000&start={page * 25}&f_WT=1%2C3')
            if request.status_code == 400:
                break
            elif request.status_code == 429:
                sleep(1)
                continue
            html = request.content
            soup = BeautifulSoup(html, 'html.parser')
            
            itens = soup.find_all('li')
            if not itens:
                break
            for vaga in itens:
                titulo = vaga.find('h3', {'class': 'base-search-card__title'}).get_text().strip()
                local = vaga.find('span', {'class': 'job-search-card__location'}).get_text().strip()
                if filtrar_vaga(unidecode(titulo).lower().replace('(', ' ').replace(')', ' '), local, 1):
                    codigo = vaga.find('div', {'class': 'base-card'})['data-entity-urn'].replace('urn:li:jobPosting:', '')
                    vagas.append([titulo, local, codigo])
                
            sleep(1)
            page += 1

            with open('vagas.txt', 'w', encoding='utf-8') as file:
                file.write('\n'.join(['|||||'.join(vaga) for vaga in vagas]))



    # pegar info das vagas por requests
    #f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/3693085925'
    
    