from playwright.sync_api import sync_playwright, Page
from json import load
from os import listdir

filtros = load(open('filtros.json', 'r', encoding='utf-8'))

from interfaces.vagas_interface.models import Empresa, Vaga


def initialize_puppet(load_cookies=False, headless=False) -> Page:
    playwright =  sync_playwright().start()
    browser = playwright.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage', '--incognito', '--disable-blink-features=AutomationControlled', '--disable-gpu', '--disable-extensions', '--ignore-certificate-errors-spki-list', '--no-default-browser-check', '--window-size=1280,720'],
                                ignore_default_args=['--enable-automation'], 
                                headless=headless)
    context = browser.new_context(viewport=None, user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.79')
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver: Page = context.new_page()

    if load_cookies:
        driver = set_cookies(driver)
    
    return driver


def set_cookies(driver):
    cookies = load(open('data/cookies.json', 'r', encoding='utf-8'))
    driver.context.add_cookies(cookies)
    return driver


def empresa_existe(e_id, plataforma) -> bool:
    if plataforma == 'linkedin':
        return Empresa.objects.filter(linkedin_id__exact=e_id).exists()
    elif plataforma == 'glassdoor':
        return Empresa.objects.filter(glassdoor_id__exact=e_id).exists()


def vaga_existe(e_id) -> bool:
    return Vaga.objects.filter(id_vaga__exact=e_id).exists()


def filtrar_vaga(titulo, local, tipo):
    if local.count(',') == 2:
        cidade, estado, pais = local.split(', ')
    elif local.count(',') == 1:
        estado, pais = local.split(', ')
    elif local.count(',') == 0:
        cidade = local.split(', ')[0]

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
    