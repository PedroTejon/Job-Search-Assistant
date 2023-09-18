from os import listdir
from json import load
from modules.utils import elemento_existe, filhos_de_el, query_selector, query_selector_all
from time import sleep

def get_followed_companies(driver, url: str) -> set:
    # Espera a request do banco de dados que informa quantas empresas você segue
    with driver.expect_response(lambda x: 'https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(profileUrn:urn' in x.url) as response:
        driver.goto(url + 'details/interests/' if url[-1] == '/' else url + '/details/interests/')

    painel_lista = query_selector(driver, '.pvs-list')
    painel_lista.wait_for()

    # Pega a parte do texto onde a quantia está informada manualmente, vista que viajar pelo documento 
    # parseado parece mais problemático do que a alternativa
    botaoExMais = query_selector(driver, 'button.scaffold-finite-scroll__load-button')
    botaoExMais.wait_for('attached')
    while driver.evaluate('document.querySelector("button.scaffold-finite-scroll__load-button")'):
        driver.keyboard.press('PageDown')
        sleep(.5)

    # Pega os links dos elementos <a> dentro da lista e escreve num arquivo de texto, com cada entrada em uma linha
    with open('data/linkedin_followed.txt', 'w', encoding='utf-8') as file:
        links = set([link.get_attribute('href').split('/')[4] for link in query_selector_all(painel_lista, 'a.optional-action-target-wrapper')])
        file.write('\n'.join(links))
    
    return links



def get_jobs(driver, env: dict, update_followed=False):
    cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
    driver.context.add_cookies(cookies)

    if 'linkedin_followed.txt' not in listdir('data') or update_followed:
        lista_empresas = get_followed_companies(driver, env['lnProfile'])
    else:
        with open('data/linkedin_followed.txt', 'r', encoding='utf-8') as file:
            lista_empresas = file.read().split('\n')
    
    vagas = {}
    empresas_code = '%2C'.join(lista_empresas)
    driver.goto(f'https://www.linkedin.com/jobs/search/?f_C={empresas_code}&f_CR=106057199')
    driver.wait_for_load_state()

    qntd_vagas = int(query_selector(driver, '.jobs-search-results-list__subtitle').text_content().strip().split(' ', maxsplit=1)[0].replace('.', ''))
    page = 0
    while page * 25 < qntd_vagas:
        if page != 0:
            driver.goto(f'https://www.linkedin.com/jobs/search/?f_C={empresas_code}&f_CR=106057199&start={page * 25}')
            driver.wait_for_load_state()
        
        input()
        page += 1
            
    # pegar info das vagas por requests
    #f'https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/[id_vaga]'
    
    