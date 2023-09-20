from playwright.sync_api import sync_playwright
from json import load


def initialize_puppet():
    playwright =  sync_playwright().start()
    browser = playwright.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage', '--incognito', '--disable-blink-features=AutomationControlled', '--disable-gpu', '--disable-extensions', '--ignore-certificate-errors-spki-list', '--no-default-browser-check', '--window-size=1200,920'],
                                ignore_default_args=['--enable-automation'], 
                                headless=False)
    context = browser.new_context(viewport=None)
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver = context.new_page()
    
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
    filtros = load(open('filtros.json', 'r', encoding='utf-8'))
    if tipo == 1:
        if not any(map(lambda x: x in local, filtros['locais'])):
            return False
        
        if any(map(lambda x: x in titulo.split(), filtros['excludeWords'])):
            return False
        
        if any(map(lambda x: x in titulo, filtros['excludeTerms'])):
            return False
        
        return True