from json import load, loads
from modules.utils import listing_exists, get_company_by_name
from time import sleep
from unidecode import unidecode
from re import sub
from cloudscraper import create_scraper

from interfaces.vagas_interface.models import Company, Listing
from django.utils.timezone import now
from datetime import datetime

filters = load(open('filters.json', 'r', encoding='utf-8'))


def filter_listing(title, listing_locations_ids, location_ids):
    if any(map(lambda x: x in title.split(), filters['exclude_words'])):
        return False
    
    if any(map(lambda x: x in title, filters['exclude_terms'])):
        return False
    
    if not any([int(city) in listing_locations_ids for city in location_ids['cities']]):
        return False

    return True


def get_bearer_token(cookies):
    for cookie in cookies:
        if cookie['name'] == 'cactk':
            return cookie['value'].strip('"')


def scrape_recommended_listings(location_ids):
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json if 'catho' in cookie['domain']]) + '; session_id=99be0cd2-0098-4f6e-9206-b4555d5c5172'
    token = get_bearer_token(cookies_json)

    listing_id = ''
    for _ in range(500):
        sleep(0.5)
        session = create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        })

        headers = {
            "accept": "*/*",
            "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "authorization": f"Bearer {token}",
            "cache-control": "no-cache",
            "cookie": 'session_id=99be0cd2-0098-4f6e-9206-b4555d5c5172; consent_cookie={"termVersion":6,"consentDate":"2023-12-20T17:14:26.819Z","consents":{"essentials":true,"marketing":false}}; CANDIDATE_ORIGIN=app-register-candidate; cactk=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJDYXRobyIsImVtcElkIjoiMCIsImV4cCI6MTcwMzE3OTA3NywiaWF0IjoxNzAzMDkyNjc3LCJpc3MiOiJodHRwczovL3NlZ3Vyby5jYXRoby5jb20uYnIiLCJqdGkiOiIxMzY5MzhlMi1jNTQ2LTQxY2QtYWEzMi1mMWQxN2QxMTk2YzciLCJuYmYiOjE3MDMwOTI2NzcsInNlc3Npb25Db250cm9sIjoiY2NmZDQ3YmQyNjYwNjJmYTI3YTM2MTNiODg2MTdmN2Q1MDZiYmIxZTY3MGQ2N2RhYWMyNTRiMzVjMDc5ZjEwNDBiODMxNTdlN2I1MWQ1ODAzMmIzNmYxZmM5N2E2MmY1YTY3ZDI2NzU4MGY2ZmVjMjk5NTI0NmViZDg3NzJhOWQiLCJzdWIiOiI3NjE0MjQyNSJ9.G_2d7uffkqYv2WQzor30m8XtiRR-IiYucNA0AG1c0CfervCZsaryKxEZMqXOsTCRj26eEz6r6mKEUdUjO5nDRa7SmCKpAYFda6eBmexr5KFYDVkqw-9a1aW6pZS1BpP19S7Tj-T6sM-apPj9iMrWYLIbfIqJ0-fQm8ylP5uiEvBzzittovzlIsU9Df6TbPPMEDlqZTX1QPdknTndydI4dUxYxORvUDSenCM9s1ULNNs7QsVLBjW3Wf0p9lOz5t6jEaXicEZ2sW24Bqne25G0EVP2hnrNo6ueu_r1T0a5RZ1hNmRCVSTaQnEqhAUzuucGhsYjLJaTiOJWqaiTbw9DWg; ckid=76142425; ckemp_id=0; newRegisterCandidate=1; ADS_POS_LOGIN=1; Catho=97f3cc3caecead5dc47416aac7300b9c; regionalizacao=br_brasil; udfcr=eyJ1c2VyX2lkIjoiNzYxNDI0MjUiLCJ1c2VyX25hbWUiOiJQZWRybyBUZWpvbiIsInVzZXJfZ2VuZGVyIjoiTSIsInVzZXJfdHlwZSI6MSwiY2l0eV9uYW1lIjoiU29yb2NhYmEiLCJjaXR5X2lkIjoiODEwIiwic3RhdHVzIjoiQSIsImNvbXBhbnlfaWQiOjAsIm9jY3VwYXRpb24iOiJEZXNlbnZvbHZlZG9yIn0; layoutPadrao=b2c; RecruiterTips=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJDYXRobyIsImVtcElkIjoiMCIsImV4cCI6MTcwMzE3OTA3NywiaWF0IjoxNzAzMDkyNjc3LCJpc3MiOiJodHRwczovL3NlZ3Vyby5jYXRoby5jb20uYnIiLCJqdGkiOiIxMzY5MzhlMi1jNTQ2LTQxY2QtYWEzMi1mMWQxN2QxMTk2YzciLCJuYmYiOjE3MDMwOTI2NzcsInNlc3Npb25Db250cm9sIjoiY2NmZDQ3YmQyNjYwNjJmYTI3YTM2MTNiODg2MTdmN2Q1MDZiYmIxZTY3MGQ2N2RhYWMyNTRiMzVjMDc5ZjEwNDBiODMxNTdlN2I1MWQ1ODAzMmIzNmYxZmM5N2E2MmY1YTY3ZDI2NzU4MGY2ZmVjMjk5NTI0NmViZDg3NzJhOWQiLCJzdWIiOiI3NjE0MjQyNSJ9.G_2d7uffkqYv2WQzor30m8XtiRR-IiYucNA0AG1c0CfervCZsaryKxEZMqXOsTCRj26eEz6r6mKEUdUjO5nDRa7SmCKpAYFda6eBmexr5KFYDVkqw-9a1aW6pZS1BpP19S7Tj-T6sM-apPj9iMrWYLIbfIqJ0-fQm8ylP5uiEvBzzittovzlIsU9Df6TbPPMEDlqZTX1QPdknTndydI4dUxYxORvUDSenCM9s1ULNNs7QsVLBjW3Wf0p9lOz5t6jEaXicEZ2sW24Bqne25G0EVP2hnrNo6ueu_r1T0a5RZ1hNmRCVSTaQnEqhAUzuucGhsYjLJaTiOJWqaiTbw9DWg; testAb_controlPlan=true; search-expanded-alert-hidden=true; blockModalIncentiveWebpush=true',
            "pragma": "no-cache",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        }
        if listing_id:
            headers['lasteventtype'] = 'discard'
            headers['lastjobid'] = str(listing_id)
        
        response = session.get(f'https://seguro.catho.com.br/area-candidato/api/suggested-job', headers=headers)
        if response.status_code == 204:
            break
        data = response.json()['data']
        listing_id = data['id']
        if not listing_exists(listing_id):
            listing_details_resp = session.get(f'https://www.catho.com.br/vagas/_next/data/K0FFX3tbYixCNuDCNvnHt/sugestao/{listing_id}.json?origem_apply=sugestao-de-vagas&entrada_apply=direto&slug={listing_id}', headers={
                "accept": "*/*",
                "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "cache-control": "no-cache",
                "cookie": cookies,
                "pragma": "no-cache",
                "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
            }).json()['pageProps']
            
            listing_details = listing_details_resp['jobAdData']

            if filter_listing(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(listing_details['titulo']).lower()), [listing['cidadeId'] for listing in listing_details['vagas']], location_ids):
                listing = Listing()
                listing.title = listing_details['titulo']
                listing.description = listing_details['descricao']
                listing.publication_date = listing_details['dataAtualizacao']
                listing.platform = 'Catho'
                listing.platform_id = listing_id
                if listing_details['aggregated_job']['aggregated_job']:
                    listing.application_url = listing_details['aggregated_job']['apply_url']
                else:
                    listing.application_url = f'https://www.catho.com.br/vagas/sugestao/{listing_id}'

                listing.applies = session.get(f'https://www.catho.com.br/anuncios/api/rank-position/{listing_id}/4740666336240438', headers={
                    "accept": "*/*",
                    "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                    "cache-control": "no-cache",
                    "cookie": cookies,
                    "pragma": "no-cache",
                    "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
                }).json()['balance']

                company_name = listing_details['contratante']['nome'] if not listing_details['contratante']['confidencial'] else 'Confidencial'
                if (company := get_company_by_name(company_name)).platforms['catho']['name'] == None:
                    company.platforms['catho']['name'] = company_name
                    company.platforms['catho']['id'] = listing_details['empId'] if not listing_details['contratante']['confidencial'] else 'Confidencial'
                    if not company.employee_count and not listing_details['contratante']['confidencial']:
                        company.employee_count = listing_details_resp['hirer']['numberOfEmployees']
                    company.save()

                listing.company = company
                listing.save()


def get_location_ids() -> dict:
    location_ids = {
        'cities': [],
        'states': [],
        'countries': []
    }
    
    session = create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    })

    for city in filters['cities']:
        response = session.get(f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={city}', headers={
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"})
        value = list(filter(lambda entry: entry['name'] == city and entry['type'] == 'city', response.json()['data']))
        if value:
            location_ids['cities'].append(value[0]['id'])
        
        sleep(0.2)

    for state in filters['states']:
        response_data = session.get(f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={state}')['data']
        value = list(filter(lambda entry: entry['name'] == state and entry['type'] == 'state', response_data))
        if value:
            location_ids['states'].append(value)

        sleep(0.2)
    
    for country in filters['countries']:
        response_data = session.get(f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={country}')['data']
        value = list(filter(lambda entry: entry['name'] == country and entry['type'] == 'country', response_data))
        if value:
            location_ids['countries'].append(value)

        sleep(0.2)
    
    return location_ids


def get_jobs():
    location_ids = get_location_ids()

    scrape_recommended_listings(location_ids)