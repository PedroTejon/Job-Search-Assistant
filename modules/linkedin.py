from json import load, loads
from modules.utils import filter_listing, company_exists_by_id, listing_exists, get_company_by_name
from time import sleep
from requests import Session
from unidecode import unidecode
from re import sub
from cloudscraper import create_scraper

from interfaces.vagas_interface.models import Company, Listing
from django.utils.timezone import now
from datetime import datetime


def get_csrf_token(cookies):
    for cookie in cookies:
        if cookie['name'] == 'JSESSIONID':
            return cookie['value'].strip('"')


def get_job_listings(url, cookies, csrf_token):
    total_job_listings = 0
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
        
        curr_count = total_job_listings
        response = loads(request.text)
        company_pfps = {company_json['entityUrn'].replace('urn:li:fsd_company:', ''): 
                            company_json['logo']['vectorImage']['rootUrl'] + company_json['logo']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment'] 
                            if 'logo' in company_json else company_json['logoResolutionResult']['vectorImage']['rootUrl'] + company_json['logoResolutionResult']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment']
                            for company_json in filter(lambda obj: ('logo' in obj and obj['logo'] != None and 'vectorImage' in obj['logo']) or ('logoResolutionResult' in obj and obj['logoResolutionResult'] != None and 'vectorImage' in obj['logoResolutionResult']), response['included'])}

        for element in filter(lambda obj: 'preDashNormalizedJobPostingUrn' in obj, response['included']):
            total_job_listings += 1
            
            listing_id = element['preDashNormalizedJobPostingUrn'].replace('urn:li:fs_normalized_jobPosting:', '')
            if listing_exists(listing_id):
                continue

            listing_title = element['jobPostingTitle']
            listing_location = element['secondaryDescription']['text']

            workplace_type = 'Remoto' if 'Remoto' in listing_location else 'Presencial/Hibrido'
            if filter_listing(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(listing_title).lower()), listing_location, workplace_type):
                if 'detailData' not in element['logo']['attributes'][0]:
                    continue

                company_name = element['primaryDescription']['text']
                company_id = element['logo']['attributes'][0]['detailData']['*companyLogo'].replace('urn:li:fsd_company:', '')
                if (company := get_company_by_name(company_name)).platforms['linkedin']['name'] == None:
                    if company_id != None:
                        company.platforms['linkedin']['id'] = company_id
                    company.platforms['linkedin']['name'] = company_name
                    company.image_url = company_pfps.get(company_id, None)
                    company.save()
                
                Listing(
                    title=listing_title, 
                    location=listing_location, 
                    company=company, 
                    workplace_type=workplace_type, 
                    platform_id=listing_id, 
                    platform='LinkedIn'
                ).save()
                
        if curr_count >= total_job_listings:
            break

        sleep(.5)
        page += 1


def scrape_recommended_listings():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
    
    get_job_listings(f'https://www.linkedin.com/voyager/api/graphql?variables=(count:25,jobCollectionSlug:recommended,query:(origin:GENERIC_JOB_COLLECTIONS_LANDING),includeJobState:true)&queryId=voyagerJobsDashJobCards.da56c4e71afbd3bcdb0a53b4ebd509c4', cookies, get_csrf_token(cookies_json))


def scrape_companies_listings():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])

    companies = list(filter(lambda x: not x.checked_recently('linkedin') and x.followed, Company.objects.all()))
    if companies:
        for company in companies:
            get_job_listings(f'https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOB_SEARCH_PAGE_OTHER_ENTRY,locationUnion:(geoId:92000000),selectedFilters:(company:List({company.platforms["linkedin"]["id"]}),countryRegion:List(106057199)),spellCorrectionEnabled:true)', cookies, get_csrf_token(cookies_json))

            company.platforms['linkedin']['last_check'] = now().strftime("%Y-%m-%dT%H:%M:%S")
            company.save()


def scrape_remote_listings():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
    
    get_job_listings(f'https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOBS_HOME_REMOTE_JOBS,locationUnion:(geoId:106057199),selectedFilters:(timePostedRange:List(r604800),workplaceType:List(2)),spellCorrectionEnabled:true)', cookies, get_csrf_token(cookies_json))


def scrape_listings_details():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])

    for listing in filter(lambda x: x.platform == 'LinkedIn' and x.description == '', Listing.objects.all()):
        listing_id = listing.platform_id

        while True:
            sleep(0.2)

            session = create_scraper(browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            })
            
            request = session.get(f'https://www.linkedin.com/voyager/api/jobs/jobPostings/{listing_id}?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebFullJobPosting-65&topN=1&topNRequestedFlavors=List(TOP_APPLICANT,IN_NETWORK,COMPANY_RECRUIT,SCHOOL_RECRUIT,HIDDEN_GEM,ACTIVELY_HIRING_COMPANY)', headers={
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
    
            if request.status_code == 200:
                response = loads(request.text)
                break

        listing_description = response['data']['description']['text']
        for attribute in sorted(response['data']['description']['attributes'], key=lambda x: x['start'], reverse=True):
            curr_index = attribute['start']
            if attribute['type']['$type'] == 'com.linkedin.pemberly.text.LineBreak':
                listing_description = listing_description[:curr_index] + '\n' + listing_description[curr_index:]
            elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.ListItem':
                listing_description = listing_description[:curr_index] + '• ' + listing_description[curr_index:curr_index + attribute['length']] + '\n' + listing_description[curr_index + attribute['length']:]
            elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Bold':
                listing_description = listing_description[:curr_index] + '**' + listing_description[curr_index: curr_index + attribute['length']] + '**' + listing_description[curr_index + attribute['length']:]
            elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Italic':
                listing_description = listing_description[:curr_index] + '__' + listing_description[curr_index: curr_index + attribute['length']] + '__' + listing_description[curr_index + attribute['length']:]                

        listing_description = sub('\n{2,}\*{2}\n{2,}', '**\n\n',  listing_description)
        listing_description = sub('\n{2,}_{2}\n{2,}', '__\n\n', listing_description)
        listing.description = sub('\n{3,}', '\n\n', listing_description)

        listing.applies =  response['data']['applies']
        listing.publication_date = datetime.fromtimestamp(response['data']['listedAt'] / 1000).strftime("%Y-%m-%dT%H:%M:%S")

        company = listing.company
        for element in response['included']:
            if 'followerCount' in element and company.platforms['linkedin']['followers'] is None:
                company.platforms['linkedin']['followers'] = element['followerCount']
            if 'staffCount' in element and company.employee_count is None:
                company.employee_count = element['staffCount']

        company.save()
        listing.save()


def get_followed_companies():
    cookies = {cookie['name']: cookie['value'].replace('\"', '') for cookie in load(open('data/cookies.json', 'r', encoding='utf-8'))}
    profile_id = load(open('data/local_storage.json', 'r', encoding='utf-8'))['profile_id']

    session = Session()

    max_index = 100
    curr_index = 0
    while curr_index < max_index:
        while tries := 1:
            company_details = session.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:{curr_index},count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28{profile_id}%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c', cookies=cookies, headers={'csrf-token': cookies['JSESSIONID']})
        
            if company_details.status_code == 200 or tries > 3:
                break
            tries += 1
        
        if company_details.status_code != 200:
            raise('MaxRetriesError: possible error in authentication/cookies or request body and requests don\'t return OK')

        data = loads(company_details.content.decode('utf-8'))
        max_index = data['data']['identityDashProfileComponentsByPagedListComponent']['paging']['total']

        for element in data['data']['identityDashProfileComponentsByPagedListComponent']['elements']:
            entity = element['components']['entityComponent']

            company_id = entity['textActionTarget'].replace('https://www.linkedin.com/company/', '').rstrip('/ ')
            if company_exists_by_id(company_id, 'linkedin'):
                continue
            company_follow_count = entity['subComponents']['components'][0]['components']['actionComponent']['action']['followingStateAction']['followingState']['followerCount']
            company_name = entity['titleV2']['text']['text'].strip()

            logo = entity['image']['attributes'][0]['detailData']['companyLogo']['logoResolutionResult']
            company_image_url = logo['vectorImage']['rootUrl'] + logo['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment'] if logo else None

            if (company := get_company_by_name(company_name)).platforms['linkedin']['name'] == None:
                company.platforms['linkedin']['id'] = company_id
                company.platforms['linkedin']['name'] = company_name
                company.platforms['linkedin']['followers'] = company_follow_count
                company.image_url = company_image_url
                company.followed = True
                company.save()
        
        curr_index += 100


def get_jobs():
    get_followed_companies()

    scrape_companies_listings()

    scrape_recommended_listings()

    scrape_remote_listings()

    scrape_listings_details()