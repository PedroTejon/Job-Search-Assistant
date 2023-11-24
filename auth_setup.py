from modules.utils import initialize_puppet
from json import dump, dumps

def setup():
    with initialize_puppet() as driver:
        driver.goto('https://www.linkedin.com/')
        input('Logue no LinkedIn para salvarmos sua sessão e aperte Enter')
        
        cookies = driver.context.cookies()
        dump({cookie['name']: cookie['value'].replace('\"', '') for cookie in cookies}, open('data/cookies.json', 'w', encoding='utf-8'), ensure_ascii=False)

        armazenamento_local = driver.evaluate("() => {var ls = window.localStorage, items = {}; for (var i = 0, k; i < ls.length; ++i)  items[k = ls.key(i)] = ls.getItem(k); return items;}")
        dump(armazenamento_local, open('data/armazenamento_local.json', 'w', encoding='utf-8'), ensure_ascii=False)


if __name__ == '__main__':
    setup()