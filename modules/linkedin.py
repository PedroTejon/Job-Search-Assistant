from os import listdir
from json import load, dump, loads
from urllib.parse import unquote
from modules.utils import filtrar_vaga, empresa_existe, vaga_existe
from time import sleep
from requests import get, Session
from bs4 import BeautifulSoup, PageElement
from unidecode import unidecode
from re import sub
from cloudscraper import create_scraper

from interfaces.vagas_interface.models import Empresa, Vaga
from django.db.models import Q
from django.db.models import Model
from django.utils.timezone import now
from datetime import datetime


def get_csrf_token(cookies):
    for cookie in cookies:
        if cookie['name'] == 'JSESSIONID':
            return cookie['value'].strip('"')


def graphql_request(url, cookies, csrf_token):
    vagas_total = 0
    page = 0

    session = create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    })
    while True:
        if 40 < page:
            break

        request = session.get(url + f'&start={25 * page}', headers={
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "cache-control": "no-cache",
            "csrf-token": csrf_token,
            "cookie": cookies,
            "pragma": "no-cache",
            "sec-ch-ua": "\"Microsoft Edge\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-li-deco-include-micro-schema": "true",
            "x-li-lang": "pt_BR",
            "x-li-page-instance": "urn:li:page:d_flagship3_search_srp_jobs;xhW+cLKCSmyQdAS+CI2l+Q==",
            "x-li-pem-metadata": "Voyager - Careers=jobs-search-results",
            "x-li-track": "{\"clientVersion\":\"1.13.7689\",\"mpVersion\":\"1.13.7689\",\"osName\":\"web\",\"timezoneOffset\":-3,\"timezone\":\"America/Sao_Paulo\",\"deviceFormFactor\":\"DESKTOP\",\"mpName\":\"voyager-web\",\"displayDensity\":1.25,\"displayWidth\":1920,\"displayHeight\":1080}",
            "x-restli-protocol-version": "2.0.0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"})
        if request.status_code in [400, 429]:
            sleep(1)
            continue
        
        conta_atual = vagas_total
        resposta = loads(request.text)
        fotos_empresas = {empresa_json['entityUrn'].replace('urn:li:fsd_company:', ''): 
                          empresa_json['logo']['vectorImage']['rootUrl'] + empresa_json['logo']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment'] 
                          if 'logo' in empresa_json else 
                          empresa_json['logoResolutionResult']['vectorImage']['rootUrl'] + empresa_json['logoResolutionResult']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment'] for empresa_json in filter(lambda obj: ('logo' in obj and obj['logo'] != None and 'vectorImage' in obj['logo']) or ('logoResolutionResult' in obj and obj['logoResolutionResult'] != None and 'vectorImage' in obj['logoResolutionResult']), resposta['included'])}

        for elemento in filter(lambda obj: 'preDashNormalizedJobPostingUrn' in obj, resposta['included']):
            codigo = elemento['preDashNormalizedJobPostingUrn'].replace('urn:li:fs_normalized_jobPosting:', '')
            if vaga_existe(codigo):
                continue
            titulo = elemento['jobPostingTitle']
            local = elemento['secondaryDescription']['text']

            modalidade = 'Remoto' if 'Remoto' in local else 'Presencial/Hibrido'
            if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, modalidade):
                empresa_nome = elemento['primaryDescription']['text']
                empresa_id = elemento['logo']['attributes'][0]['detailData']['*companyLogo'].replace('urn:li:fsd_company:', '')
                if not empresa_existe(empresa_id, 'linkedin'):
                    empresa = Empresa()
                    empresa.linkedin_id = empresa_id
                    empresa.linkedin_nome = empresa_nome
                    empresa.imagem_url = fotos_empresas.get(empresa_id, None)
                    empresa.save()
                
                vaga = Vaga(titulo=titulo, local=local, empresa=Empresa.objects.get(linkedin_nome__iexact=empresa_nome), modalidade=modalidade,id_vaga=codigo, plataforma='LinkedIn')
                vaga.save()
            
            vagas_total += 1
    
        if conta_atual >= vagas_total:
            break

        sleep(.5)
        page += 1


def scrape_vagas_recomendadas() -> dict:
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
    
    graphql_request(f'https://www.linkedin.com/voyager/api/graphql?variables=(count:25,jobCollectionSlug:recommended,query:(origin:GENERIC_JOB_COLLECTIONS_LANDING),includeJobState:true)&queryId=voyagerJobsDashJobCards.da56c4e71afbd3bcdb0a53b4ebd509c4', cookies, get_csrf_token(cookies_json))


def scrape_vagas_empresas():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])

    empresas = list(filter(lambda x: not x.checado_recentemente() and x.followed, Empresa.objects.all()))
    if empresas:
        for empresa in empresas:
            graphql_request(f'https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOB_SEARCH_PAGE_OTHER_ENTRY,locationUnion:(geoId:92000000),selectedFilters:(company:List({empresa.linkedin_id}),countryRegion:List(106057199)),spellCorrectionEnabled:true)', cookies, get_csrf_token(cookies_json))

            empresa.last_check = now()
            empresa.save()


def scrape_vagas_remotos():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
    
    graphql_request(f'https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOBS_HOME_REMOTE_JOBS,locationUnion:(geoId:106057199),selectedFilters:(timePostedRange:List(r604800),workplaceType:List(2)),spellCorrectionEnabled:true)', cookies, get_csrf_token(cookies_json))


def scrape_detalhes_vagas():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])


    for vaga in filter(lambda x: x.plataforma == 'LinkedIn' and x.descricao == '', Vaga.objects.all()):
        id_vaga = vaga.id_vaga

        session = create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        })
        
        request = session.get(f'https://www.linkedin.com/voyager/api/jobs/jobPostings/{id_vaga}?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebFullJobPosting-65&topN=1&topNRequestedFlavors=List(TOP_APPLICANT,IN_NETWORK,COMPANY_RECRUIT,SCHOOL_RECRUIT,HIDDEN_GEM,ACTIVELY_HIRING_COMPANY)', headers={
            "cookie": cookies,
            "accept": "application/vnd.linkedin.normalized+json+2.1",
            "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "cache-control": "no-cache",
            "csrf-token": get_csrf_token(cookies_json),
            "pragma": "no-cache",
            "sec-ch-ua": "\"Microsoft Edge\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-li-lang": "pt_BR",
            "x-li-page-instance": "urn:li:page:d_flagship3_jobs_discovery_jymbii;ycV3lFUlTMONvjhem4yCrw==",
            "x-li-track": "{\"clientVersion\":\"1.13.7689\",\"mpVersion\":\"1.13.7689\",\"osName\":\"web\",\"timezoneOffset\":-3,\"timezone\":\"America/Sao_Paulo\",\"deviceFormFactor\":\"DESKTOP\",\"mpName\":\"voyager-web\",\"displayDensity\":1.25,\"displayWidth\":1920,\"displayHeight\":1080}",
            "x-restli-protocol-version": "2.0.0",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        })

        resposta = loads(request.text)

        descricao = resposta['data']['description']['text']
        for atributo in sorted(resposta['data']['description']['attributes'], key=lambda x: x['start'], reverse=True):
            index = atributo['start']
            if atributo['type']['$type'] == 'com.linkedin.pemberly.text.LineBreak':
                descricao = descricao[:index] + '\n' + descricao[index:]
            elif atributo['type']['$type'] == 'com.linkedin.pemberly.text.ListItem':
                descricao = descricao[:index] + '• ' + descricao[index:index + atributo['length']] + '\n' + descricao[index + atributo['length']:]
            elif atributo['type']['$type'] == 'com.linkedin.pemberly.text.Bold':
                descricao = descricao[:index] + '**' + descricao[index: index + atributo['length']] + '**' + descricao[index + atributo['length']:]
            elif atributo['type']['$type'] == 'com.linkedin.pemberly.text.Italic':
                descricao = descricao[:index] + '__' + descricao[index: index + atributo['length']] + '__' + descricao[index + atributo['length']:]                

        descricao = sub('\n{2,}\*{2}\n{2,}', '**\n\n',  descricao)
        descricao = sub('\n{2,}_{2}\n{2,}', '__\n\n', descricao)
        vaga.descricao = sub('\n{3,}', '\n\n', descricao)

        vaga.n_candidaturas =  resposta['data']['applies']

        vaga.tempo_publicado = datetime.fromtimestamp(resposta['data']['listedAt'] / 1000)

        empresa = vaga.empresa
        for elemento in resposta['included']:
            if 'followerCount' in elemento and empresa.linkedin_seguidores is None:
                empresa.linkedin_seguidores = elemento['followerCount']
            if 'staffCount' in elemento and empresa.employee_count is None:
                empresa.employee_count = elemento['staffCount']

        empresa.save()
        vaga.save()
        
        sleep(0.2)


def get_followed_companies():
    cookies = {cookie['name']: cookie['value'].replace('\"', '') for cookie in load(open('data/cookies.json', 'r', encoding='utf-8'))}
    profile_id = load(open('data/armazenamento_local.json', 'r', encoding='utf-8'))['profile_id']
    sessao = Session()
    
    total = 100
    pos = 0
    while pos < total:
        detalhes_empresas = sessao.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:{pos},count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28{profile_id}%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c', cookies=cookies, headers={'csrf-token': cookies['JSESSIONID']})
        
        data = loads(detalhes_empresas.content.decode('utf-8'))
        total = data['data']['identityDashProfileComponentsByPagedListComponent']['paging']['total']

        for elemento in data['data']['identityDashProfileComponentsByPagedListComponent']['elements']:
            entity = elemento['components']['entityComponent']

            linkedin_id = entity['textActionTarget'].replace('https://www.linkedin.com/company/', '').rstrip('/ ')
            if empresa_existe(linkedin_id, 'linkedin'):
                continue

            linkedin_follow_count = entity['subComponents']['components'][0]['components']['actionComponent']['action']['followingStateAction']['followingState']['followerCount']
            linkedin_name = entity['titleV2']['text']['text'].strip()

            logo = entity['image']['attributes'][0]['detailData']['companyLogo']['logoResolutionResult']
            imagem_url = logo['vectorImage']['rootUrl'] + logo['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment'] if logo else None

            try:
                empresa = Empresa.objects.get(Q(linkedin_nome__iexact=linkedin_name) | Q(glassdoor_nome__iexact=linkedin_name))
            except Exception:
                empresa = Empresa()
            empresa.linkedin_id = linkedin_id
            empresa.linkedin_nome = linkedin_name
            empresa.linkedin_seguidores = linkedin_follow_count
            empresa.imagem_url = imagem_url
            empresa.followed = True
            empresa.save()
        
        pos += 100


def get_jobs():
    get_followed_companies()

    scrape_vagas_empresas()

    scrape_vagas_recomendadas()

    scrape_vagas_remotos()

    scrape_detalhes_vagas()