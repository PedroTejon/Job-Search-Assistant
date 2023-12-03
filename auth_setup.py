from bs4 import BeautifulSoup
from modules.utils import initialize_puppet
from json import dump, dumps, loads

def setup():
    with initialize_puppet() as driver:

        print('Logue com sua conta do LinkedIn')      
        with driver.expect_response(lambda x: 'https://www.linkedin.com/feed/?trk=homepage-basic_sign-in-submit' in x.url and x.status == 200, timeout=0) as response:
            driver.goto('https://www.linkedin.com/')
        print('Conta do LinkedIn conectada com sucesso')

        response_text = response.value.text()
        profile_id = response_text[response_text.find('fs_miniProfile:') + 15:response_text.find(',', response_text.find('fs_miniProfile:')) - 6]
        armazenamento_local = {'profile_id': profile_id}

        print('Logue com sua conta do Glassdoor')
        with driver.expect_response(lambda x: 'https://www.glassdoor.com.br/Vaga/index.htm' in x.url and x.status == 200, timeout=0) as response:
            driver.goto('https://www.glassdoor.com.br/')
        print('Conta do Glassdoor conectada com sucesso')

        soup = BeautifulSoup(response.value.text(), 'html.parser')
        data = loads(soup.find('script', {'id': '__NEXT_DATA__'}).get_text())['props']['pageProps']
        armazenamento_local['glassdoor_csrf'] = data['token']

        print('Salvando Cookies...')
        cookies = driver.context.cookies()
        dump(cookies, open('data/cookies.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Salvando Local Storage...')
        armazenamento_local |= driver.evaluate("() => {var ls = window.localStorage, items = {}; for (var i = 0, k; i < ls.length; ++i)  items[k = ls.key(i)] = ls.getItem(k); return items;}")
        dump(armazenamento_local, open('data/armazenamento_local.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Autenticação concluída')

if __name__ == '__main__':
    setup()