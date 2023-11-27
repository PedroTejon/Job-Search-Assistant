from modules.utils import initialize_puppet
from json import dump, dumps

def setup():
    with initialize_puppet() as driver:
        print('Logue com sua conta do LinkedIn')      
        with driver.expect_response(lambda x: 'https://www.linkedin.com/feed/?trk=homepage-basic_sign-in-submit' in x.url and x.status == 200, timeout=0):
            driver.goto('https://www.linkedin.com/')
        print('Conta do LinkedIn conectada com sucesso')

        print('Logue com sua conta do Glassdoor')
        with driver.expect_response(lambda x: 'https://www.glassdoor.com.br/Vaga/index.htm' in x.url and x.status == 200, timeout=0):
            driver.goto('https://www.glassdoor.com.br/')
        print('Conta do Glassdoor conectada com sucesso')

        print('Salvando Cookies...')
        cookies = driver.context.cookies()
        dump(cookies, open('data/cookies.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Salvando Local Storage...')
        armazenamento_local = driver.evaluate("() => {var ls = window.localStorage, items = {}; for (var i = 0, k; i < ls.length; ++i)  items[k = ls.key(i)] = ls.getItem(k); return items;}")
        dump(armazenamento_local, open('data/armazenamento_local.json', 'w', encoding='utf-8'), ensure_ascii=False)

        print('Autenticação concluída')

if __name__ == '__main__':
    setup()