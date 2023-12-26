from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
from json import dump, load, loads
from os import listdir


def initialize_puppet(load_cookies=False, headless=False) -> Page:
    playwright =  sync_playwright().start()
    browser = playwright.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage', '--incognito', '--disable-blink-features=AutomationControlled', '--disable-gpu', '--disable-extensions', '--ignore-certificate-errors-spki-list', '--no-default-browser-check', '--window-size=1280,720'],
                                ignore_default_args=['--enable-automation'], 
                                headless=headless)
    context = browser.new_context(viewport=None, user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.79')
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver: Page = context.new_page()

    if load_cookies:
        cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
        driver.context.add_cookies(cookies)
    
    return driver


def setup():
    with initialize_puppet() as driver:
        if 'cookies.json' in listdir('data') and input('Deseja manter seus cookies antigos e apenas substituir autenticações de sites específicos? (Sim/Não) ').lower() in ['sim', 's']:
            cookies = load(open('data/cookies.json', 'rb'))
        else:
            cookies = {
                'linkedin': [],
                'glassdoor': [],
                'catho': [],
                'vagas.com': []
            }

        if input('Deseja logar com sua conta do Linkedin? (Sim/Não) ').lower() in ['sim', 's']:
            with driver.expect_response(lambda x: 'https://www.linkedin.com/feed/?trk=homepage-basic_sign-in-submit' in x.url and x.status == 200, timeout=0) as response:
                driver.goto('https://www.linkedin.com/')
            print('Conta do LinkedIn conectada com sucesso')

            response_text = response.value.text()
            profile_id = response_text[response_text.find('fs_miniProfile:') + 15:response_text.find(',', response_text.find('fs_miniProfile:')) - 6]
            local_storage = {'profile_id': profile_id}

        if input('Deseja logar com sua conta do Glassdoor? (Sim/Não) ').lower() in ['sim', 's']:
            with driver.expect_response(lambda x: 'https://www.glassdoor.com.br/Vaga/index.htm' in x.url and x.status == 200, timeout=0) as response:
                driver.goto('https://www.glassdoor.com.br/')
            print('Conta do Glassdoor conectada com sucesso')

            soup = BeautifulSoup(response.value.text(), 'html.parser')
            data = loads(soup.find('script', {'id': '__NEXT_DATA__'}).get_text())['props']['pageProps']
            local_storage['glassdoor_csrf'] = data['token']
        
        if input('Deseja logar com sua conta da Catho? (Sim/Não) ').lower() in ['sim', 's']:
            with driver.expect_response(lambda x: 'https://www.catho.com.br/area-candidato' in x.url and x.status == 200, timeout=0) as response:
                driver.goto('https://seguro.catho.com.br/signin/')
            print('Conta da Catho conectada com sucesso')

            driver.goto('https://www.catho.com.br/area-candidato', wait_until='load')

        if input('Deseja logar com sua conta da Vagas.com? (Sim/Não) ').lower() in ['sim', 's']:
            with driver.expect_response(lambda x: 'https://www.vagas.com.br/meu-perfil' in x.url and x.status == 200, timeout=0) as response:
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

        dump(cookies, open('data/cookies.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Salvando Local Storage...')
        dump(local_storage, open('data/local_storage.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Autenticação concluída')


if __name__ == '__main__':
    setup()