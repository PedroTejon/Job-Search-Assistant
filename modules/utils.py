from playwright.sync_api import sync_playwright, Page
from json import load
from os import listdir

filtros = load(open('filtros.json', 'r', encoding='utf-8'))


def initialize_puppet() -> Page:
    playwright =  sync_playwright().start()
    browser = playwright.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage', '--incognito', '--disable-blink-features=AutomationControlled', '--disable-gpu', '--disable-extensions', '--ignore-certificate-errors-spki-list', '--no-default-browser-check', '--window-size=1200,920'],
                                ignore_default_args=['--enable-automation'], 
                                headless=False)
    context = browser.new_context(viewport=None)
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver = context.new_page()
    if 'cookies.json' in listdir('data'):
        cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
        driver.context.add_cookies(cookies)
    
    return driver


def elemento_existe(elemento, selector, factor='', role=''):
    if factor == '':
        return True if elemento.locator(f'css={selector}').count() != 0 else False
    elif factor == 'name':
        return True if elemento.get_by_role(role, name=selector).count() != 0 else False


def filhos_de_el(elemento, selector):
    return elemento.locator(f'css={selector} > *').all()


def pai_n(elemento, quanto):
    for _ in range(quanto):
        elemento = elemento.locator('xpath=..')
    return elemento


def query_selector(elemento, selector):
    return elemento.locator(f'css={selector}').first


def query_selector_all(elemento, selector):
    return elemento.locator(f'css={selector}').all()


def filtrar_vaga(titulo, local, tipo):
    if local.count(',') == 2:
        cidade, estado, pais = local.split(', ')
    elif local.count(',') == 1:
        estado, pais = local.split(', ')
    elif local.count(',') == 0:
        cidade = local.split(', ')


    if tipo == 'Presencial/Hibrido':
        if 'cidade' in locals() and not any(map(lambda x: x == cidade, filtros['cidades'])):
            return False
        if 'estado' in locals() and not any(map(lambda x: x == estado, filtros['estados'])):
            return False
        if 'pais' in locals() and not any(map(lambda x: x == pais, filtros['paises'])):
            return False
        
    if any(map(lambda x: x in titulo.split(), filtros['excludeWords'])):
        return False
    
    if any(map(lambda x: x in titulo, filtros['excludeTerms'])):
        return False
    
    return True
    