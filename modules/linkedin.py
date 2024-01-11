from datetime import datetime
from json import load
from os.path import split as path_split
from queue import Queue
from re import sub
from sys import exc_info

from cloudscraper import create_scraper
from django.utils.timezone import now

from interfaces.vagas.models import Company, Listing
from modules.exceptions import MaxRetriesException
from modules.utils import (asciify_text, company_exists_by_id, filter_listing,
                           get_company_by_name, listing_exists, reload_filters,
                           sleep_r)


def get_csrf_token():
    for cookie in cookies_json:
        if cookie['name'] == 'JSESSIONID' and 'linkedin' in cookie['domain']:
            return cookie['value'].strip('"')

    return ''


with open('data/cookies.json', 'rb') as f:
    cookies_json = load(f)['linkedin']
COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
token = get_csrf_token()
queue: Queue = None
log_queue: Queue = None


def reload_if_configs_changed():
    if log_queue.qsize() > 0:
        temp_logs = []
        for _ in range(log_queue.qsize()):
            log = log_queue.get()
            if log['type'] == 'reload_request':
                reload_filters()
            else:
                temp_logs.append(log)


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
            sleep_r(1)
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

            company_name = element['primaryDescription']['text']
            workplace_type = 'Remoto' if 'Remoto' in listing_location else 'Presencial/Hibrido'
            listing_location = sub(r'\s*\(\bPresencial\b\)|\s*\(\bHíbrido\b\)|\s*\(\bRemoto\b\)',
                                   '', listing_location.split(',')[0].strip())

            reload_if_configs_changed()
            if filter_listing(asciify_text(listing_title), listing_location, workplace_type, asciify_text(company_name)):
                if 'detailData' not in element['logo']['attributes'][0]:
                    continue

                company_id = element['logo']['attributes'][0]['detailData']['*companyLogo'].replace(
                    'urn:li:fsd_company:', '')
                if (company := get_company_by_name(company_name, 'linkedin')).platforms['linkedin']['name'] is None:
                    if company_id is None:
                        company.platforms['linkedin']['id'] = company_id
                    company.platforms['linkedin']['name'] = company_name
                    company.image_url = company_pfps.get(company_id, None)
                    company.save()

                get_listing_details(Listing(
                    title=listing_title,
                    location=listing_location,
                    company=company,
                    company_name=company_name,
                    workplace_type=workplace_type,
                    platform_id=listing_id,
                    platform='LinkedIn'
                ))

                queue.put(1)

        if curr_count >= total_job_listings:
            break

        sleep_r(.5)
        page += 1


def get_recommended_listings():
    get_job_listings('https://www.linkedin.com/voyager/api/graphql?variables=(count:25,jobCollectionSlug:recommended,query:(origin:GENERIC_JOB_COLLECTIONS_LANDING),includeJobState:true)&queryId=voyagerJobsDashJobCards.da56c4e71afbd3bcdb0a53b4ebd509c4')


def get_companies_listings():
    companies = list(filter(lambda x: not x.checked_recently('linkedin') and x.followed, Company.objects.all()))
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
        sleep_r(0.5)

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
        if attribute['type']['$type'] == 'com.linkedin.pemberly.text.ListItem':
            listing_description = before_text + '<li>' + text + '</li>' + after_text
        elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Bold':
            listing_description = before_text + '<b>' + text + '</b>' + \
                listing_description[curr_index + attribute['length']:]
        elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Italic':
            listing_description = before_text + '<i>' + text + '</i>' + after_text

    listing.description = listing_description.replace('\n', '<br>')

    listing.applies = response['data']['applies']
    listing.publication_date = datetime.fromtimestamp(response['data']['listedAt'] / 1000).strftime('%Y-%m-%dT%H:%M:%S')

    application_url_response = session.get(f'https://www.linkedin.com/voyager/api/graphql?includeWebMetadata=true&variables=(cardSectionTypes:List(TOP_CARD),jobPostingUrn:urn%3Ali%3Afsd_jobPosting%3A{listing_id},includeSecondaryActionsV2:true)&queryId=voyagerJobsDashJobPostingDetailSections.7a099d4cd4fe903e01deac5893fc08d0', headers={
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
    if application_url_response.status_code == 200:
        listing.application_url = next(filter(lambda element: 'companyApplyUrl' in element,
                                       application_url_response.json()['included']))['companyApplyUrl']

    if listing.application_url is None or listing.application_url.startswith('https://www.linkedin.com/job-apply/'):
        listing.application_url = f'https://www.linkedin.com/jobs/view/{listing_id}/'

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

    session = create_scraper()

    max_index = 100
    curr_index = 0
    while curr_index < max_index:
        tries = 1
        while tries <= 3:
            response = session.get(f'https://www.linkedin.com/voyager/api/graphql?variables=(start:{curr_index},count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28{profile_id}%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c', headers={
                "accept": "application/vnd.linkedin.normalized+json+2.1",
                "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "cache-control": "no-cache",
                'cookie': COOKIES,
                'csrf-token': token,
                "pragma": "no-cache",
                "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-li-lang": "en_US",
                "x-li-page-instance": "urn:li:page:d_flagship3_profile_view_base_interests_details;SMBEUWK7RWSdHCxtKcrvaw==",
                "x-li-track": "{\"clientVersion\":\"1.13.8499\",\"mpVersion\":\"1.13.8499\",\"osName\":\"web\",\"timezoneOffset\":-3,\"timezone\":\"America/Sao_Paulo\",\"deviceFormFactor\":\"DESKTOP\",\"mpName\":\"voyager-web\",\"displayDensity\":1.25,\"displayWidth\":1920,\"displayHeight\":1080}",
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
            })

            if response.status_code == 200:
                company_details = response.json()
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesException

        max_index = company_details['data']['data']['identityDashProfileComponentsByPagedListComponent']['paging']['total']

        company_pfps = get_companies_pfps(filter(lambda obj: ('logo' in obj and obj['logo'] is not None and 'vectorImage' in obj['logo']) or (
            'logoResolutionResult' in obj and obj['logoResolutionResult'] is not None and 'vectorImage' in obj['logoResolutionResult']), company_details['included']))

        for element in company_details['data']['data']['identityDashProfileComponentsByPagedListComponent']['elements']:
            entity = element['components']['entityComponent']

            company_id = entity['textActionTarget'].replace('https://www.linkedin.com/company/', '').rstrip('/ ')
            if company_exists_by_id(company_id, 'linkedin'):
                continue
            company_follow_count = int(entity['caption']['text'].replace(',', '').replace(' followers', ''))
            company_name = entity['titleV2']['text']['text'].strip()

            company_image_url = company_pfps[company_id] if company_id in company_pfps else None

            if (company := get_company_by_name(company_name, 'linkedin')).platforms['linkedin']['name'] is None:
                company.platforms['linkedin']['id'] = company_id
                company.platforms['linkedin']['name'] = company_name
                company.platforms['linkedin']['followers'] = company_follow_count
                company.image_url = company_image_url
                company.followed = True
                company.save()

        curr_index += 100


def get_jobs(curr_queue, curr_log_queue):
    global queue, log_queue
    queue = curr_queue
    log_queue = curr_log_queue

    try:
        get_followed_companies()

        get_companies_listings()

        get_recommended_listings()

        get_remote_listings()
    except Exception:  # pylint: disable=W0718
        exc_class, _, exc_data = exc_info()
        file_name = path_split(exc_data.tb_next.tb_frame.f_code.co_filename)[1]
        while exc_data.tb_next is not None and path_split(exc_data.tb_next.tb_frame.f_code.co_filename)[1]:
            exc_data = exc_data.tb_next
        log_queue.put({'type': 'error', 'exception': exc_class.__name__,
                       'file_name': file_name, 'file_line': exc_data.tb_lineno})
