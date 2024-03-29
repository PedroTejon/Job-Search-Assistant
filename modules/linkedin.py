from __future__ import annotations

from datetime import datetime
from json import load
from queue import Queue
from re import sub
from traceback import format_exc
from typing import TYPE_CHECKING

from cloudscraper import CloudScraper, create_scraper  # type: ignore[import-untyped]
from django.utils.timezone import now

from interfaces.vagas.models import Company, Listing
from modules.utils import (
    DEFAULT_HEADERS,
    asciify_text,
    company_exists_by_id,
    filter_listing,
    get,
    get_company_by_name,
    listing_exists,
    reload_filters,
    sleep_r,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from requests import Response


def get_csrf_token() -> str:
    for cookie in cookies_json:
        if cookie['name'] == 'JSESSIONID' and 'linkedin' in cookie['domain']:
            return cookie['value'].strip('"')

    return ''


with open('data/cookies.json', 'rb') as f:
    cookies_json: list[dict[str, str]] = load(f)['linkedin']
token = get_csrf_token()
queue: Queue[int] = Queue()
log_queue: Queue[dict] = Queue()

COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
MODULE_HEADERS = DEFAULT_HEADERS | {
    'accept': 'application/vnd.linkedin.normalized+json+2.1',
    'csrf-token': token,
    'cookie': COOKIES,
    'x-li-deco-include-micro-schema': 'true',
    'x-li-lang': 'pt_BR',
    'x-li-track': '{"clientVersion":"1.13.7689","mpVersion":"1.13.7689","osName":"web","timezoneOffset":-3,"timezone":"America/Sao_Paulo","deviceFormFactor":"DESKTOP","mpName":"voyager-web","displayDensity":1.25,"displayWidth":1920,"displayHeight":1080}',  # noqa: E501
    'x-restli-protocol-version': '2.0.0',
}


def reload_if_configs_changed() -> None:
    if log_queue.qsize() > 0:
        temp_logs = []
        for _ in range(log_queue.qsize()):
            log = log_queue.get()
            if log['type'] == 'reload_request':
                reload_filters()
            else:
                temp_logs.append(log)


def get_companies_pfps(companies_json: Generator[dict, None, None]) -> dict[str, str]:
    companies_pfps: dict[str, str] = {}
    for company_json in companies_json:
        company_id: str = company_json['entityUrn'].replace('urn:li:fsd_company:', '')
        if 'logo' in company_json:
            logo_url: str = (
                company_json['logo']['vectorImage']['rootUrl']
                + company_json['logo']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment']
            )
        else:
            logo_url = (
                company_json['logoResolutionResult']['vectorImage']['rootUrl']
                + company_json['logoResolutionResult']['vectorImage']['artifacts'][2]['fileIdentifyingUrlPathSegment']
            )
        companies_pfps[company_id] = logo_url

    return companies_pfps


def get_job_listings(url: str) -> None:
    total_job_listings = 0
    page = 0

    session: CloudScraper = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    session.headers = MODULE_HEADERS | {
        'x-li-page-instance': 'urn:li:page:d_flagship3_search_srp_jobs;xhW+cLKCSmyQdAS+CI2l+Q==',
        'x-li-pem-metadata': 'Voyager - Careers=jobs-search-results',
    }
    while True:
        if page > 40:
            break

        response: Response = get(url + f'&start={25 * page}', session, (200, 400, 429))
        if response.status_code in {400, 429}:
            sleep_r(1)
            continue

        curr_count = total_job_listings
        response_json: dict = response.json()
        company_pfps = get_companies_pfps(
            obj
            for obj in response_json['included']
            if ('logo' in obj and obj['logo'] is not None and 'vectorImage' in obj['logo'])
            or (
                'logoResolutionResult' in obj
                and obj['logoResolutionResult'] is not None
                and 'vectorImage' in obj['logoResolutionResult']
            )
        )

        for element in filter(lambda obj: 'preDashNormalizedJobPostingUrn' in obj, response_json['included']):
            total_job_listings += 1

            listing_id: str = element['preDashNormalizedJobPostingUrn'].replace('urn:li:fs_normalized_jobPosting:', '')
            if listing_exists(listing_id):
                continue

            listing_title: str = element['jobPostingTitle']
            listing_location: str = element['secondaryDescription']['text']

            company_name: str = element['primaryDescription']['text']
            workplace_type = 'Remoto' if 'Remoto' in listing_location else 'Presencial/Hibrido'
            listing_location = sub(
                r'\s*\(\bPresencial\b\)|\s*\(\bHíbrido\b\)|\s*\(\bRemoto\b\)',
                '',
                listing_location.split(',')[0].strip(),
            )

            reload_if_configs_changed()
            if filter_listing(
                asciify_text(listing_title), listing_location, workplace_type, asciify_text(company_name)
            ):
                if 'detailData' not in element['logo']['attributes'][0]:
                    continue

                company_id: str = element['logo']['attributes'][0]['detailData']['*companyLogo'].replace(
                    'urn:li:fsd_company:', ''
                )
                if (company := get_company_by_name(company_name, 'linkedin')).platforms['linkedin']['name'] is None:
                    if company_id is None:
                        company.platforms['linkedin']['id'] = company_id
                    company.platforms['linkedin']['name'] = company_name
                    company.image_url = company_pfps.get(company_id, None)
                    company.save()

                get_listing_details(
                    Listing(
                        title=listing_title,
                        location=listing_location,
                        company=company,
                        company_name=company_name,
                        workplace_type=workplace_type,
                        platform_id=listing_id,
                        platform='LinkedIn',
                    )
                )

                queue.put(1)

        if curr_count >= total_job_listings:
            break

        sleep_r(0.5)
        page += 1


def get_recommended_listings() -> None:
    get_job_listings(
        'https://www.linkedin.com/voyager/api/graphql?variables=(count:25,jobCollectionSlug:recommended,query:(origin:GENERIC_JOB_COLLECTIONS_LANDING),includeJobState:true)&queryId=voyagerJobsDashJobCards.da56c4e71afbd3bcdb0a53b4ebd509c4'
    )


def get_companies_listings() -> None:
    companies = list(filter(lambda x: not x.checked_recently('linkedin') and x.followed, Company.objects.all()))
    if companies:
        for company in companies:
            get_job_listings(
                f"https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOB_SEARCH_PAGE_OTHER_ENTRY,locationUnion:(geoId:92000000),selectedFilters:(company:List({company.platforms['linkedin']['id']}),countryRegion:List(106057199)),spellCorrectionEnabled:true)"
            )

            company.platforms['linkedin']['last_check'] = now().strftime('%Y-%m-%dT%H:%M:%S')
            company.save()


def get_remote_listings() -> None:
    get_job_listings(
        'https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-191&count=25&q=jobSearch&query=(origin:JOBS_HOME_REMOTE_JOBS,locationUnion:(geoId:106057199),selectedFilters:(timePostedRange:List(r604800),workplaceType:List(2)),spellCorrectionEnabled:true)'
    )


def get_listing_details(listing: Listing) -> None:
    listing_id: str = listing.platform_id

    session: CloudScraper = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    session.headers = MODULE_HEADERS | {
        'x-li-page-instance': 'urn:li:page:d_flagship3_jobs_discovery_jymbii;ycV3lFUlTMONvjhem4yCrw==',
    }

    content = get(
        f'https://www.linkedin.com/voyager/api/jobs/jobPostings/{listing_id}?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebFullJobPosting-65&topN=1&topNRequestedFlavors=List(TOP_APPLICANT,IN_NETWORK,COMPANY_RECRUIT,SCHOOL_RECRUIT,HIDDEN_GEM,ACTIVELY_HIRING_COMPANY)',
        session,
    ).json()

    if listing.id is None:
        listing_description: str = content['data']['description']['text']
        for attribute in sorted(content['data']['description']['attributes'], key=lambda x: x['start'], reverse=True):
            curr_index: int = attribute['start']
            before_text: str = listing_description[:curr_index]
            text: str = listing_description[curr_index : curr_index + attribute['length']]
            after_text: str = listing_description[curr_index + attribute['length'] :]
            if attribute['type']['$type'] == 'com.linkedin.pemberly.text.ListItem':
                listing_description = before_text + '<li>' + text + '</li>' + after_text
            elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Bold':
                listing_description = (
                    before_text + '<b>' + text + '</b>' + listing_description[curr_index + attribute['length'] :]
                )
            elif attribute['type']['$type'] == 'com.linkedin.pemberly.text.Italic':
                listing_description = before_text + '<i>' + text + '</i>' + after_text

        listing.description = listing_description.replace('\n', '<br>').replace('•', '\n•')

        listing.publication_date = datetime.fromtimestamp(content['data']['listedAt'] / 1000).strftime(
            '%Y-%m-%dT%H:%M:%S'
        )

        listing.application_url = content['data']['applyMethod'].get(
            'companyApplyUrl', f'https://www.linkedin.com/jobs/view/{listing_id}/'
        )

        if listing.application_url is None or listing.application_url.startswith('https://www.linkedin.com/job-apply/'):
            listing.application_url = f'https://www.linkedin.com/jobs/view/{listing_id}/'

        company: Company = listing.company
        for element in content['included']:
            if 'followerCount' in element and company.platforms['linkedin']['followers'] is None:
                company.platforms['linkedin']['followers'] = element['followerCount']
            if 'staffCount' in element and company.employee_count is None:
                company.employee_count = element['staffCount']

        company.save()

    if content['data']['closedAt'] is not None or content['data']['jobState'] == 'SUSPENDED':
        listing.closed = True

    if content['data'] is not None and content['data']['applies'] is not None:
        listing.applies = content['data']['applies']

    sleep_r(0.5)

    listing.save()


def get_followed_companies() -> None:
    with open('data/local_storage.json', 'rb') as f_local_storage:
        profile_id: str = load(f_local_storage)['profile_id']

    session: CloudScraper = create_scraper()
    session.headers = MODULE_HEADERS | {
        'x-li-page-instance': 'urn:li:page:d_flagship3_profile_view_base_interests_details;SMBEUWK7RWSdHCxtKcrvaw=='
    }

    max_index = 100
    curr_index = 0
    while curr_index < max_index:
        company_details = get(
            f'https://www.linkedin.com/voyager/api/graphql?variables=(start:{curr_index},count:100,paginationToken:null,pagedListComponent:urn%3Ali%3Afsd_profilePagedListComponent%3A%28{profile_id}%2CINTERESTS_VIEW_DETAILS%2Curn%3Ali%3Afsd_profileTabSection%3ACOMPANIES_INTERESTS%2CNONE%2Cpt_BR%29)&queryId=voyagerIdentityDashProfileComponents.3efef764c5f936e8a825b8674c814b0c',
            session,
        ).json()

        max_index = company_details['data']['data']['identityDashProfileComponentsByPagedListComponent']['paging'][
            'total'
        ]

        company_pfps: dict[str, str] = get_companies_pfps(
            obj
            for obj in company_details['included']
            if ('logo' in obj and obj['logo'] is not None and 'vectorImage' in obj['logo'])
            or (
                'logoResolutionResult' in obj
                and obj['logoResolutionResult'] is not None
                and 'vectorImage' in obj['logoResolutionResult']
            )
        )

        for element in company_details['data']['data']['identityDashProfileComponentsByPagedListComponent']['elements']:
            entity: dict = element['components']['entityComponent']

            company_id: str = entity['textActionTarget'].replace('https://www.linkedin.com/company/', '').rstrip('/ ')
            if company_exists_by_id(company_id, 'linkedin'):
                continue
            company_follow_count = int(sub(r'[.a-zA-Z]*', '', entity['caption']['text']))
            company_name: str = entity['titleV2']['text']['text'].strip()

            company_image_url = company_pfps.get(company_id)

            if (company := get_company_by_name(company_name, 'linkedin')).platforms['linkedin']['name'] is None:
                company.platforms['linkedin']['id'] = company_id
                company.platforms['linkedin']['name'] = company_name
                company.platforms['linkedin']['followers'] = company_follow_count
                company.image_url = company_image_url
                company.followed = True
                company.save()

        curr_index += 100


def get_jobs(curr_queue: Queue, curr_log_queue: Queue) -> None:
    global queue, log_queue
    queue = curr_queue
    log_queue = curr_log_queue

    try:
        get_followed_companies()

        get_companies_listings()

        get_recommended_listings()

        get_remote_listings()
    except Exception:
        traceback = format_exc()

        log_queue.put({
            'type': 'error',
            'exception': traceback,
        })
