from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
from json import dump, load, loads


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

        print('Logue com sua conta do LinkedIn')      
        with driver.expect_response(lambda x: 'https://www.linkedin.com/feed/?trk=homepage-basic_sign-in-submit' in x.url and x.status == 200, timeout=0) as response:
            driver.goto('https://www.linkedin.com/')
        print('Conta do LinkedIn conectada com sucesso')

        response_text = response.value.text()
        profile_id = response_text[response_text.find('fs_miniProfile:') + 15:response_text.find(',', response_text.find('fs_miniProfile:')) - 6]
        local_storage = {'profile_id': profile_id}

        print('Logue com sua conta do Glassdoor')
        with driver.expect_response(lambda x: 'https://www.glassdoor.com.br/Vaga/index.htm' in x.url and x.status == 200, timeout=0) as response:
            driver.goto('https://www.glassdoor.com.br/')
        print('Conta do Glassdoor conectada com sucesso')

        soup = BeautifulSoup(response.value.text(), 'html.parser')
        data = loads(soup.find('script', {'id': '__NEXT_DATA__'}).get_text())['props']['pageProps']
        local_storage['glassdoor_csrf'] = data['token']

        print('Salvando Cookies...')
        cookies = driver.context.cookies()
        dump(cookies, open('data/cookies.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Salvando Local Storage...')
        local_storage |= driver.evaluate("() => {var ls = window.localStorage, items = {}; for (var i = 0, k; i < ls.length; ++i)  items[k = ls.key(i)] = ls.getItem(k); return items;}")
        dump(local_storage, open('data/local_storage.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Autenticação concluída')


if __name__ == '__main__':
    setup()