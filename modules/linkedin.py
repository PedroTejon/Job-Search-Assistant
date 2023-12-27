from datetime import datetime
from json import load
from re import sub
from time import sleep

from cloudscraper import create_scraper
from django.utils.timezone import now
from requests import Session
from unidecode import unidecode

from interfaces.vagas_interface.models import Company, Listing
from modules.exceptions import MaxRetriesException
from modules.utils import (company_exists_by_id, filter_listing,
                           get_company_by_name, listing_exists)


def get_csrf_token():
    for cookie in cookies_json:
        if cookie['name'] == 'JSESSIONID' and 'linkedin' in cookie['domain']:
            return cookie['value'].strip('"')

    return ''


with open('data/cookies.json', 'rb') as f:
    cookies_json = load(f)['linkedin']
COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
token = get_csrf_token()


def get_companies_pfps(companies_json):
    companies_pfps = {}
    for company_json in companies_json:
        company_id = company_json['entityUrn'].replace('urn:li:fsd_company:', '')
        if 'logo' in company_json:
            logo_url = company_json['logo']['vectorImage']['rootUrl'] + \
                company_json['logo']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment']
        else:
            logo_url = company_json['logoResolutionResult']['vectorImage']['rootUrl'] + \
                company_json['logoResolutionResult']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment']
        companies_pfps[company_id] = logo_url

    return companies_pfps


def get_job_listings(url):
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

        response = session.get(url + f'&start={25 * page}', headers={
            'accept': 'application/vnd.linkedin.normalized+json+2.1',
            'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'no-cache',
            'csrf-token': token,
            'cookie': COOKIES,
            'pragma': 'no-cache',
            'sec-ch-ua': '\"Microsoft Edge\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '\"Windows\"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-li-deco-include-micro-schema': 'true',
            'x-li-lang': 'pt_BR',
            'x-li-page-instance': 'urn:li:page:d_flagship3_search_srp_jobs;xhW+cLKCSmyQdAS+CI2l+Q==',
            'x-li-pem-metadata': 'Voyager - Careers=jobs-search-results',
            'x-li-track': '{\"clientVersion\":\"1.13.7689\",\"mpVersion\":\"1.13.7689\",\"osName\":\"web\",\"timezoneOffset\":-3,\"timezone\":\"America/Sao_Paulo\",\"deviceFormFactor\":\"DESKTOP\",\"mpName\":\"voyager-web\",\"displayDensity\":1.25,\"displayWidth\":1920,\"displayHeight\":1080}',
            'x-restli-protocol-version': '2.0.0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'})

        if response.status_code in [400, 429]:
            sleep(1)
            continue

        curr_count = total_job_listings
        response = response.json()
        company_pfps = get_companies_pfps(filter(lambda obj: ('logo' in obj and obj['logo'] is not None and 'vectorImage' in obj['logo']) or (
            'logoResolutionResult' in obj and obj['logoResolutionResult'] is not None and 'vectorImage' in obj['logoResolutionResult']), response['included']))

        for element in filter(lambda obj: 'preDashNormalizedJobPostingUrn' in obj, response['included']):
            total_job_listings += 1

            listing_id = element['preDashNormalizedJobPostingUrn'].replace('urn:li:fs_normalized_jobPosting:', '')
            if listing_exists(listing_id):
                continue

            listing_title = element['jobPostingTitle']
            listing_location = element['secondaryDescription']['text']

            workplace_type = 'Remoto' if 'Remoto' in listing_location else 'Presencial/Hibrido'
            if filter_listing(sub(r'[\[\]\(\),./\\| !?#]+', ' ', unidecode(listing_title).lower()), listing_location, workplace_type):
                if 'detailData' not in element['logo']['attributes'][0]:
                    continue

                company_name = element['primaryDescription']['text']
                company_id = element['logo']['attributes'][0]['detailData']['*companyLogo'].replace(
                    'urn:li:fsd_company:', '')
                if (company := get_company_by_name(company_name)).platforms['linkedin']['name'] is None:
                    if company_id is None:
                        company.platforms['linkedin']['id'] = company_id
                    company.platforms['linkedin']['name'] = company_name
                    company.image_url = company_pfps.get(company_id, None)
                    company.save()

                get_listing_details(Listing(
                    title=listing_title,
                    location=listing_location,
                    company=company,
                    workplace_type=workplace_type,
                    platform_id=listing_id,
                    platform='LinkedIn'
                ))

        if curr_count >= total_job_listings:
            break

        sleep(.5)
        page += 1


def get_recommended_listings():
    get_job_listings('https://www.linkedin.com/voyager/api/graphql?variables=(count:25,jobCollectionSlug:recommended,query:(origin:GENERIC_JOB_COLLECTIONS_LANDING),includeJobState:true)&queryId=voyagerJobsDashJobCards.da56c4e71afbd3bcdb0a53b4ebd509c4')


def get_companies_listings():
    companies = list(filter(lambda x: not x.checked_recently(
        'linkedin') and x.followed, Company.objects.all()))
    if companies:
        for company in companies:
            get_job_listings(
                f"https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOB_SEARCH_PAGE_OTHER_ENTRY,locationUnion:(geoId:92000000),selectedFilters:(company:List({company.platforms['linkedin']['id']}),countryRegion:List(106057199)),spellCorrectionEnabled:true)")

            company.platforms['linkedin']['last_check'] = now().strftime('%Y-%m-%dT%H:%M:%S')
            company.save()


def get_remote_listings():
    get_job_listings('https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOBS_HOME_REMOTE_JOBS,locationUnion:(geoId:106057199),selectedFilters:(timePostedRange:List(r604800),workplaceType:List(2)),spellCorrectionEnabled:true)')


def get_listing_details(listing):
    listing_id = listing.platform_id

    tries = 1
    while tries <= 3:
        sleep(0.2)

        session = create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        })

        response = session.get(f'https://www.linkedin.com/voyager/api/jobs/jobPostings/{listing_id}?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebFullJobPosting-65&topN=1&topNRequestedFlavors=List(TOP_APPLICANT,IN_NETWORK,COMPANY_RECRUIT,SCHOOL_RECRUIT,HIDDEN_GEM,ACTIVELY_HIRING_COMPANY)', headers={
            'cookie': COOKIES,
            'accept': 'application/vnd.linkedin.normalized+json+2.1',
            'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'no-cache',
            'csrf-token': token,
            'pragma': 'no-cache',
            'sec-ch-ua': '\"Microsoft Edge\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '\"Windows\"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-li-lang': 'pt_BR',
            'x-li-page-instance': 'urn:li:page:d_flagship3_jobs_discovery_jymbii;ycV3lFUlTMONvjhem4yCrw==',
            'x-li-track': '{\"clientVersion\":\"1.13.7689\",\"mpVersion\":\"1.13.7689\",\"osName\":\"web\",\"timezoneOffset\":-3,\"timezone\":\"America/Sao_Paulo\",\"deviceFormFactor\":\"DESKTOP\",\"mpName\":\"voyager-web\",\"displayDensity\":1.25,\"displayWidth\":1920,\"displayHeight\":1080}',
            'x-restli-protocol-version': '2.0.0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
        })

        if response.status_code == 200:
            response = response.json()
            break
        tries += 1
        if tries > 3:
            raise MaxRetriesException

    listing_description = response['data']['description']['text']
    for attribute in sorted(response['data']['description']['attributes'], key=lambda x: x['start'], reverse=True):
        curr_index = attribute['start']
        before_text = listing_description[:curr_index]
        text = listing_description[curr_index:curr_index + attribute['length']]
        after_text = listing_description[curr_index + attribute['length']:]
        if attribute['type']['$type'] == 'com.linkedin.pemberly.text.LineBreak':
            listing_description = before_text + '\n' + listing_description[curr_index:]
        elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.ListItem':
            listing_description = before_text + '• ' + text + '\n' + after_text
        elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Bold':
            listing_description = before_text + '**' + text + '**' + after_text
        elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Italic':
            listing_description = before_text + '__' + text + '__' + after_text

    listing_description = sub('\n{2,}\*{2}\n{2,}', '**\n\n', listing_description)  # pylint: disable=W1401
    listing_description = sub('\n{2,}_{2}\n{2,}', '__\n\n', listing_description)
    listing.description = sub('\n{3,}', '\n\n', listing_description)

    listing.applies = response['data']['applies']
    listing.publication_date = datetime.fromtimestamp(response['data']['listedAt'] / 1000).strftime('%Y-%m-%dT%H:%M:%S')

    company = listing.company
    for element in response['included']:
        if 'followerCount' in element and company.platforms['linkedin']['followers'] is None:
            company.platforms['linkedin']['followers'] = element['followerCount']
        if 'staffCount' in element and company.employee_count is None:
            company.employee_count = element['staffCount']

    company.save()
    listing.save()


def get_followed_companies():
    with open('data/local_storage.json', 'rb') as f_local_storage:
        profile_id = load(f_local_storage)['profile_id']

    session = Session()

    max_index = 100
    curr_index = 0
    while curr_index < max_index:
        tries = 1
        while tries <= 3:
            response = session.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:{curr_index},count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28{profile_id}%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c',
                                   headers={
                                       'csrf-token': token,
                                       'cookie': COOKIES
                                   })

            if response.status_code == 200:
                company_details = response.json()
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesException

        max_index = company_details['data']['identityDashProfileComponentsByPagedListComponent']['paging']['total']

        for element in company_details['data']['identityDashProfileComponentsByPagedListComponent']['elements']:
            entity = element['components']['entityComponent']

            company_id = entity['textActionTarget'].replace('https://www.linkedin.com/company/', '').rstrip('/ ')
            if company_exists_by_id(company_id, 'linkedin'):
                continue
            company_follow_count = entity['subComponents']['components'][0]['components'][
                'actionComponent']['action']['followingStateAction']['followingState']['followerCount']
            company_name = entity['titleV2']['text']['text'].strip()

            logo = entity['image']['attributes'][0]['detailData']['companyLogo']['logoResolutionResult']
            company_image_url = logo['vectorImage']['rootUrl'] + \
                logo['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment'] if logo else None

            if (company := get_company_by_name(company_name)).platforms['linkedin']['name'] is None:
                company.platforms['linkedin']['id'] = company_id
                company.platforms['linkedin']['name'] = company_name
                company.platforms['linkedin']['followers'] = company_follow_count
                company.image_url = company_image_url
                company.followed = True
                company.save()

        curr_index += 100


def get_jobs():
    get_followed_companies()

    get_companies_listings()

    get_recommended_listings()

    get_remote_listings()
