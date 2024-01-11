from json import JSONDecodeError, dump, load, loads
from os import listdir
from time import sleep

from bs4 import BeautifulSoup
from playwright.sync_api import Page, sync_playwright


def initialize_puppet(headless=False) -> Page:
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(
        args=['--no-sandbox', '--disable-dev-shm-usage', '--incognito', '--disable-blink-features=AutomationControlled', '--disable-gpu',
              '--disable-extensions', '--ignore-certificate-errors-spki-list', '--no-default-browser-check', '--window-size=1280,720'],
        ignore_default_args=['--enable-automation'],
        headless=headless)
    context = browser.new_context(
        viewport=None,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.79')
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver: Page = context.new_page()

    return driver


def setup():
    with initialize_puppet() as driver:
        if 'cookies.json' in listdir('data') and input('Deseja manter seus cookies antigos e apenas substituir autenticações de sites específicos? (Sim/Não) ').lower() in ['sim', 's']:
            try:
                with open('data/cookies.json', 'rb') as f:
                    cookies = load(f)
                with open('data/local_storage.json', 'rb') as f:
                    local_storage = load(f)
            except JSONDecodeError:
                if input('Arquivo de cookies inválido, criar novo arquivo vazio? (Sim/Não) ').lower() in ['sim', 's']:
                    cookies = {
                        'linkedin': [],
                        'glassdoor': [],
                        'catho': [],
                        'vagas.com': []
                    }
                    local_storage = {}
                else:
                    return
        else:
            cookies = {
                'linkedin': [],
                'glassdoor': [],
                'catho': [],
                'vagas.com': []
            }
            local_storage = {}
        if input('Deseja logar com sua conta do Linkedin? (Sim/Não) ').lower() in ['sim', 's']:
            cookies['linkedin'] = []
            with driver.expect_response(lambda x: 'https://www.linkedin.com/feed/?trk=homepage-basic_sign-in-submit' in x.url and x.status == 200, timeout=0):
                driver.goto('https://www.linkedin.com/')
            print('Conta do LinkedIn conectada com sucesso')

            driver.goto('https://www.linkedin.com/', wait_until='load')
            content_soup = BeautifulSoup(driver.content(), 'html.parser')
            element = next(filter(lambda el: '*miniProfile' in el.get_text(), content_soup.select('[id^=bpr-guid-]')))
            profile_id = loads(element.get_text())['data']['*miniProfile'].replace('urn:li:fs_miniProfile:', '')
            local_storage['profile_id'] = profile_id

        if input('Deseja logar com sua conta do Glassdoor? (Sim/Não) ').lower() in ['sim', 's']:
            cookies['glassdoor'] = []
            with driver.expect_response(lambda x: 'https://www.glassdoor.com.br/Vaga/index.htm' in x.url and x.status == 200, timeout=0):
                driver.goto('https://www.glassdoor.com.br/')
            print('Conta do Glassdoor conectada com sucesso')

            soup = BeautifulSoup(driver.content(), 'html.parser')
            data_element = soup.find('script', {'id': '__NEXT_DATA__'})
            data = loads(data_element.get_text())['props']['pageProps']
            local_storage['glassdoor_csrf'] = data['token']

        if input('Deseja logar com sua conta da Catho? (Sim/Não) ').lower() in ['sim', 's']:
            cookies['catho'] = []
            with driver.expect_response(lambda x: 'https://www.catho.com.br/area-candidato' in x.url and x.status == 200, timeout=0):
                driver.goto('https://seguro.catho.com.br/signin/')
            print('Conta da Catho conectada com sucesso')

            driver.goto('https://www.catho.com.br/vagas', wait_until='load')
            cur_build_id_soup = BeautifulSoup(driver.content(), 'html.parser')
            build_id = loads(cur_build_id_soup.find('script', {'id': '__NEXT_DATA__'}).get_text())['buildId']
            local_storage['catho_build_id'] = build_id
            sleep(1)

        if input('Deseja logar com sua conta da Vagas.com? (Sim/Não) ').lower() in ['sim', 's']:
            cookies['vagas.com'] = []
            with driver.expect_response(lambda x: 'https://www.vagas.com.br/meu-perfil' in x.url and x.status == 200, timeout=0):
                driver.goto('https://www.vagas.com.br/login-candidatos')
            print('Conta da Vagas.com conectada com sucesso')

        print('Salvando Cookies...')
        for cookie in driver.context.cookies():
            if 'linkedin' in cookie['domain']:
                cookies['linkedin'].append(cookie)
            elif 'glassdoor' in cookie['domain']:
                cookies['glassdoor'].append(cookie)
            elif 'catho' in cookie['domain']:
                cookies['catho'].append(cookie)
            elif 'vagas.com' in cookie['domain']:
                cookies['vagas.com'].append(cookie)

        with open('data/cookies.json', 'w', encoding='utf-8') as f:
            dump(cookies, f, ensure_ascii=False)

        print('Salvando Local Storage...')
        with open('data/local_storage.json', 'w', encoding='utf-8') as f:
            dump(local_storage, f, ensure_ascii=False)

        print('Autenticação concluída')


if __name__ == '__main__':
    setup()
