from os import listdir
from json import load
from modules.utils import filhos_de_el, query_selector, query_selector_all
from time import sleep

def get_followed_companies(driver, url: str) -> list:
    # Espera a request do banco de dados que informa quantas empresas você segue
    with driver.expect_response(lambda x: 'https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(profileUrn:urn' in x.url) as response:
        driver.goto(url + 'details/interests/' if url[-1] == '/' else url + '/details/interests/')


    # Pega a parte do texto onde a quantia está informada manualmente, vista que viajar pelo documento 
    # parseado parece mais problemático do que a alternativa
    response_text = response.value.text()
    qntd_total_i = response_text.rfind('"paging"')
    qntd_total_f = response_text.find('"$recipeTypes"', qntd_total_i)
    qntd_total = int(response_text[qntd_total_i:qntd_total_f].rsplit(':', maxsplit=1)[1].strip(', \n'))

    # Aperta PageDown até que a quantia de elementos filhos da lista seja maior/igual à quantidade total,
    # assim tendo certeza que todas as empresas foram carregadas
    painel_lista = query_selector(driver, '.pvs-list')
    while len(filhos_de_el(painel_lista, '.pvs-list__paged-list-item')) < qntd_total - 1:
        driver.keyboard.press('PageDown')
        sleep(.5)

    # Pega os links dos elementos <a> dentro da lista e escreve num arquivo de texto, com cada entrada em uma linha
    with open('data/linkedin_followed.txt', 'w', encoding='utf-8') as file:
        links = tuple([link.get_attribute('href') for link in query_selector_all(painel_lista, 'a.optional-action-target-wrapper')])
        file.write('\n'.join(links))


def get_jobs(driver, env, update_followed=False):
    cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
    driver.context.add_cookies(cookies)

    if 'linkedin_followed.txt' not in listdir('data') or update_followed:
        get_followed_companies(driver, env['lnProfile'])
    
    