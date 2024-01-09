from json import load
from os.path import split as path_split
from queue import Queue
from sys import exc_info
from time import sleep

from cloudscraper import create_scraper
from django.utils.timezone import now

from interfaces.vagas.models import Company, Listing
from modules.exceptions import MaxRetriesException
from modules.utils import (asciify_text, company_exists_by_id, filter_listing,
                           get_company_by_name, listing_exists, reload_filters)

with open('data/local_storage.json', 'rb') as f:
    token = load(f)['glassdoor_csrf']
with open('data/cookies.json', 'rb') as f:
    cookies_json = load(f)['glassdoor']
COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
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


def job_listings_request(cursor, query, operation, variables):
    request_body = [{
        'operationName': operation,
        'variables': variables,
        'query': query
    }]
    if cursor:
        request_body[0]['variables']['pageNumber'] = cursor['pageNumber']
        request_body[0]['variables']['pageCursor'] = cursor['cursor']

    session = create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    })

    return session.post('https://www.glassdoor.com.br/graph',
                        headers={
                            'accept': '*/*',
                            'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                            'apollographql-client-name': 'job-search-next',
                            'apollographql-client-version': '6.5.0',
                            'cache-control': 'no-cache',
                            'content-type': 'application/json',
                            'cookie': COOKIES,
                            'gd-csrf-token': token,
                            'pragma': 'no-cache',
                            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
                            'sec-ch-ua-mobile': '?0',
                            'sec-ch-ua-platform': '"Windows"',
                            'sec-fetch-dest': 'empty',
                            'sec-fetch-mode': 'cors',
                            'sec-fetch-site': 'same-site',
                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
                        },
                        json=request_body)


def extract_job_listings(job_listings: list):
    for listing in job_listings:
        listing_id = listing['jobview']['job']['listingId']
        if listing_exists(listing_id):
            continue
        listing_header = listing['jobview']['header']
        listing_title = listing_header['jobTitleText']
        listing_location = listing_header['locationName']
        listing_worktype = 'Remoto' if 'remoto' in listing_location else 'Presencial/Hibrido'

        company_name = listing_header['employerNameFromSearch']
        reload_if_configs_changed()
        if filter_listing(asciify_text(listing_title), listing_location, listing_worktype, asciify_text(company_name)):
            if (company := get_company_by_name(company_name, 'glassdoor')).platforms['glassdoor']['name'] is None:
                company.platforms['glassdoor']['name'] = company_name
                if 'employer' in listing['jobview']['header']:
                    company.platforms['glassdoor']['id'] = str(
                        listing['jobview']['header']['employer']['id'])
                company.save()

            get_listing_details(Listing(
                title=listing_title,
                location=listing_location,
                workplace_type=listing_worktype,
                company=company,
                company_name=company_name,
                platform_id=str(listing['jobview']['job']['listingId']),
                platform='Glassdoor'))


def get_companies_listings():
    for company in filter(lambda x: x.platforms['glassdoor']['name'] not in [None, 'not_found'] and x.platforms['glassdoor']['id'] not in [None, 'not_found'] and not x.checked_recently('glassdoor') and x.followed, Company.objects.all()):
        cursor = None
        page = 1
        while cursor is None or cursor:
            tries = 1
            while tries <= 3:
                sleep(.5)
                response = job_listings_request(cursor, 'query JobSearchResultsQuery($excludeJobListingIds: [Long!], $keyword: String, $locationId: Int, $locationType: LocationTypeEnum, $numJobsToShow: Int!, $pageCursor: String, $pageNumber: Int, $filterParams: [FilterParams], $originalPageUrl: String, $seoFriendlyUrlInput: String, $parameterUrlInput: String, $seoUrl: Boolean) {\n  jobListings(\n    contextHolder: {searchParams: {excludeJobListingIds: $excludeJobListingIds, keyword: $keyword, locationId: $locationId, locationType: $locationType, numPerPage: $numJobsToShow, pageCursor: $pageCursor, pageNumber: $pageNumber, filterParams: $filterParams, originalPageUrl: $originalPageUrl, seoFriendlyUrlInput: $seoFriendlyUrlInput, parameterUrlInput: $parameterUrlInput, seoUrl: $seoUrl, searchType: SR}}\n  ) {\n    companyFilterOptions {\n      id\n      shortName\n      __typename\n    }\n    filterOptions\n    indeedCtk\n    jobListings {\n      ...JobView\n      __typename\n    }\n    jobListingSeoLinks {\n      linkItems {\n        position\n        url\n        __typename\n      }\n      __typename\n    }\n    jobSearchTrackingKey\n    jobsPageSeoData {\n      pageMetaDescription\n      pageTitle\n      __typename\n    }\n    paginationCursors {\n      cursor\n      pageNumber\n      __typename\n    }\n    indexablePageForSeo\n    searchResultsMetadata {\n      searchCriteria {\n        implicitLocation {\n          id\n          localizedDisplayName\n          type\n          __typename\n        }\n        keyword\n        location {\n          id\n          shortName\n          localizedShortName\n          localizedDisplayName\n          type\n          __typename\n        }\n        __typename\n      }\n      footerVO {\n        countryMenu {\n          childNavigationLinks {\n            id\n            link\n            textKey\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      helpCenterDomain\n      helpCenterLocale\n      jobAlert {\n        jobAlertExists\n        __typename\n      }\n      jobSerpFaq {\n        questions {\n          answer\n          question\n          __typename\n        }\n        __typename\n      }\n      jobSerpJobOutlook {\n        occupation\n        paragraph\n        heading\n        __typename\n      }\n      showMachineReadableJobs\n      __typename\n    }\n    serpSeoLinksVO {\n      relatedJobTitlesResults\n      searchedJobTitle\n      searchedKeyword\n      searchedLocationIdAsString\n      searchedLocationSeoName\n      searchedLocationType\n      topCityIdsToNameResults {\n        key\n        value\n        __typename\n      }\n      topEmployerIdsToNameResults {\n        key\n        value\n        __typename\n      }\n      topEmployerNameResults\n      topOccupationResults\n      __typename\n    }\n    totalJobsCount\n    __typename\n  }\n}\n\nfragment JobView on JobListingSearchResult {\n  jobview {\n    header {\n      adOrderId\n      advertiserType\n      adOrderSponsorshipLevel\n      ageInDays\n      divisionEmployerName\n      easyApply\n      employer {\n        id\n        name\n        shortName\n        __typename\n      }\n      employerNameFromSearch\n      goc\n      gocConfidence\n      gocId\n      jobCountryId\n      jobLink\n      jobResultTrackingKey\n      jobTitleText\n      locationName\n      locationType\n      locId\n      needsCommission\n      payCurrency\n      payPeriod\n      payPeriodAdjustedPay {\n        p10\n        p50\n        p90\n        __typename\n      }\n      rating\n      salarySource\n      savedJobId\n      seoJobLink\n      sponsored\n      __typename\n    }\n    job {\n      descriptionFragments\n      importConfigId\n      jobTitleId\n      jobTitleText\n      listingId\n      __typename\n    }\n    jobListingAdminDetails {\n      cpcVal\n      importConfigId\n      jobListingId\n      jobSourceId\n      userEligibleForAdminJobDetails\n      __typename\n    }\n    overview {\n      shortName\n      squareLogoUrl\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n', 'JobSearchResultsQuery', {
                    'excludeJobListingIds': [],
                    'filterParams': [{'filterKey': 'companyId', 'values': company.platforms['glassdoor']['id']}],
                    'keyword': '',
                    'locationId': 0,
                    'numJobsToShow': 50,
                    'originalPageUrl': 'https://www.glassdoor.com.br/Vaga/index.htm',
                    'seoUrl': False
                })

                if response.status_code == 200:
                    content = response.json()[0]['data']
                    break
                tries += 1
                if tries > 3:
                    raise MaxRetriesException

            cursor = next(filter(
                lambda x, page=page: x['pageNumber'] > page, content['jobListings']['paginationCursors']), '')
            if cursor:
                page = cursor['pageNumber']

            extract_job_listings(content['jobListings']['jobListings'])

        company.platforms['glassdoor']['last_check'] = now().strftime('%Y-%m-%dT%H:%M:%S')
        company.save()


def get_recommended_listings():
    cursor = None
    for page in range(20):
        response = job_listings_request(cursor, 'query JobRecommendationsQuery($numJobsToShow: Int!, $pageNumber: Int, $pageCursor: String) {\n  jobListings(\n    contextHolder: {adSlotName: \"forYou-jobs-lsr\", searchParams: {numPerPage: $numJobsToShow, searchType: REC_JOBS, pageNumber: $pageNumber, pageCursor: $pageCursor}}\n  ) {\n    indeedCtk\n    jobListings {\n      ...JobView\n      __typename\n    }\n    jobSearchTrackingKey\n    paginationCursors {\n      cursor\n      pageNumber\n      __typename\n    }\n    searchResultsMetadata {\n      footerVO {\n        countryMenu {\n          childNavigationLinks {\n            id\n            link\n            textKey\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      helpCenterDomain\n      helpCenterLocale\n      __typename\n    }\n    jobsPageSeoData {\n      pageMetaDescription\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment JobView on JobListingSearchResult {\n  jobview {\n    header {\n      adOrderId\n      advertiserType\n      adOrderSponsorshipLevel\n      ageInDays\n      divisionEmployerName\n      easyApply\n      employer {\n        id\n        name\n        shortName\n        __typename\n      }\n      employerNameFromSearch\n      goc\n      gocConfidence\n      gocId\n      jobCountryId\n      jobLink\n      jobResultTrackingKey\n      jobTitleText\n      locationName\n      locationType\n      locId\n      needsCommission\n      payCurrency\n      payPeriod\n      payPeriodAdjustedPay {\n        p10\n        p50\n        p90\n        __typename\n      }\n      rating\n      salarySource\n      savedJobId\n      seoJobLink\n      sponsored\n      __typename\n    }\n    job {\n      descriptionFragments\n      importConfigId\n      jobTitleId\n      jobTitleText\n      listingId\n      __typename\n    }\n    jobListingAdminDetails {\n      cpcVal\n      importConfigId\n      jobListingId\n      jobSourceId\n      userEligibleForAdminJobDetails\n      __typename\n    }\n    overview {\n      shortName\n      squareLogoUrl\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n', 'JobRecommendationsQuery', {
            'numJobsToShow': 50,
            'originalPageUrl': 'https://www.glassdoor.com.br/Vaga/index.htm'
        })

        content = response.json()[0]['data']

        cursor = next(filter(
            lambda x, page=page: x['pageNumber'] > page + 1, content['jobListings']['paginationCursors']), None)
        if not cursor:
            break

        extract_job_listings(content['jobListings']['jobListings'])

        sleep(.5)


def get_listing_details(listing):
    tries = 1
    while tries <= 3:
        response = job_listings_request(None, 'query JobDetailQuery($jl: Long!, $queryString: String, $enableReviewSummary: Boolean!, $pageTypeEnum: PageTypeEnum) {\n  jobview: jobView(\n    listingId: $jl\n    contextHolder: {queryString: $queryString, pageTypeEnum: $pageTypeEnum}\n  ) {\n    ...DetailFragment\n    employerReviewSummary @include(if: $enableReviewSummary) {\n      reviewSummary {\n        highlightSummary {\n          sentiment\n          sentence\n          categoryReviewCount\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment DetailFragment on JobView {\n  employerBenefits {\n    benefitsOverview {\n      benefitsHighlights {\n        benefit {\n          commentCount\n          icon\n          name\n          __typename\n        }\n        highlightPhrase\n        __typename\n      }\n      overallBenefitRating\n      employerBenefitSummary {\n        comment\n        __typename\n      }\n      __typename\n    }\n    benefitReviews {\n      benefitComments {\n        id\n        comment\n        __typename\n      }\n      cityName\n      createDate\n      currentJob\n      rating\n      stateName\n      userEnteredJobTitle\n      __typename\n    }\n    numReviews\n    __typename\n  }\n  employerContent {\n    featuredVideoLink\n    managedContent {\n      id\n      type\n      title\n      body\n      captions\n      photos\n      videos\n      __typename\n    }\n    diversityContent {\n      goals {\n        id\n        workPopulation\n        underRepresentedGroup\n        currentMetrics\n        currentMetricsDate\n        representationGoalMetrics\n        representationGoalMetricsDate\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  employerAttributes {\n    attributes {\n      attributeName\n      attributeValue\n      __typename\n    }\n    __typename\n  }\n  gaTrackerData {\n    isSponsoredFromIndeed\n    isSponsoredFromJobListingHit\n    jobViewDisplayTimeMillis\n    requiresTracking\n    pageRequestGuid\n    searchTypeCode\n    trackingUrl\n    __typename\n  }\n  header {\n    jobLink\n    adOrderId\n    adOrderSponsorshipLevel\n    advertiserType\n    ageInDays\n    applicationId\n    appliedDate\n    applyUrl\n    applyButtonDisabled\n    blur\n    coverPhoto {\n      url\n      __typename\n    }\n    divisionEmployerName\n    easyApply\n    easyApplyMethod\n    employerNameFromSearch\n    employer {\n      activeStatus\n      bestProfile {\n        id\n        __typename\n      }\n      id\n      name\n      shortName\n      size\n      squareLogoUrl\n      __typename\n    }\n    expired\n    goc\n    hideCEOInfo\n    indeedApplyMetadata\n    indeedJobAttribute {\n      education\n      skills\n      educationLabel\n      skillsLabel\n      yearsOfExperienceLabel\n      __typename\n    }\n    isIndexableJobViewPage\n    jobTitleText\n    jobType\n    jobTypeKeys\n    jobCountryId\n    jobResultTrackingKey\n    locId\n    locationName\n    locationType\n    needsCommission\n    normalizedJobTitle\n    organic\n    payCurrency\n    payPeriod\n    payPeriodAdjustedPay {\n      p10\n      p50\n      p90\n      __typename\n    }\n    rating\n    remoteWorkTypes\n    salarySource\n    savedJobId\n    seoJobLink\n    sgocId\n    sponsored\n    categoryMgocId\n    urgencySignal {\n      labelKey\n      messageKey\n      normalizedCount\n      __typename\n    }\n    __typename\n  }\n  similarJobs {\n    relatedJobTitle\n    careerUrl\n    __typename\n  }\n  job {\n    description\n    discoverDate\n    eolHashCode\n    importConfigId\n    jobReqId\n    jobSource\n    jobTitleId\n    jobTitleText\n    listingId\n    __typename\n  }\n  jobListingAdminDetails {\n    adOrderId\n    cpcVal\n    importConfigId\n    jobListingId\n    jobSourceId\n    userEligibleForAdminJobDetails\n    __typename\n  }\n  map {\n    address\n    cityName\n    country\n    employer {\n      id\n      name\n      __typename\n    }\n    lat\n    lng\n    locationName\n    postalCode\n    stateName\n    __typename\n  }\n  overview {\n    ceo {\n      name\n      photoUrl\n      __typename\n    }\n    id\n    name\n    shortName\n    squareLogoUrl\n    headquarters\n    links {\n      overviewUrl\n      benefitsUrl\n      photosUrl\n      reviewsUrl\n      salariesUrl\n      __typename\n    }\n    primaryIndustry {\n      industryId\n      industryName\n      sectorName\n      sectorId\n      __typename\n    }\n    ratings {\n      overallRating\n      ceoRating\n      ceoRatingsCount\n      recommendToFriendRating\n      compensationAndBenefitsRating\n      cultureAndValuesRating\n      careerOpportunitiesRating\n      seniorManagementRating\n      workLifeBalanceRating\n      __typename\n    }\n    revenue\n    size\n    sizeCategory\n    type\n    website\n    yearFounded\n    __typename\n  }\n  photos {\n    photos {\n      caption\n      photoId\n      photoId2x\n      photoLink\n      photoUrl\n      photoUrl2x\n      __typename\n    }\n    __typename\n  }\n  reviews {\n    reviews {\n      advice\n      cons\n      countHelpful\n      employerResponses {\n        response\n        responseDateTime\n        userJobTitle\n        __typename\n      }\n      employmentStatus\n      featured\n      isCurrentJob\n      jobTitle {\n        text\n        __typename\n      }\n      lengthOfEmployment\n      pros\n      ratingBusinessOutlook\n      ratingCareerOpportunities\n      ratingCeo\n      ratingCompensationAndBenefits\n      ratingCultureAndValues\n      ratingOverall\n      ratingRecommendToFriend\n      ratingSeniorLeadership\n      ratingWorkLifeBalance\n      reviewDateTime\n      reviewId\n      summary\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n', 'JobDetailQuery', {
            'jl': listing.platform_id,
            'pageTypeEnum': 'JOBS_FOR_YOU',
            'enableReviewSummary': True,
            'queryString': f'jobListingId={listing.platform_id}',
        })

        if response.status_code == 200:
            content = response.json()[0]['data']['jobview']
            break
        tries += 1
        if tries > 3:
            raise MaxRetriesException

    listing.application_url = 'https://www.glassdoor.com.br/' + content['header']['jobLink']
    listing.applies = None
    listing.description = content['job']['description']
    listing.publication_date = content['job']['discoverDate']
    listing.save()

    queue.put(1)

    sleep(.5)


def get_followed_companies():
    companies = Company.objects.all()
    for company in filter(lambda x: x.platforms['glassdoor']['id'] is None and x.followed, companies):
        session = create_scraper(browser={
            'browser': 'firefox',
            'platform': 'windows',
            'mobile': False
        })

        response = session.get(f"http://www.glassdoor.com.br/api-web/employer/find.htm?autocomplete=true&term={company.platforms['linkedin']['name']}",
                               headers={
                                   'cookie': COOKIES
                               })
        content = response.json()

        if len(content) and not company_exists_by_id(str(content[0]['id']), 'glassdoor'):
            company.platforms['glassdoor']['id'] = str(content[0]['id'])
            company.platforms['glassdoor']['name'] = content[0]['label']
        else:
            company.platforms['glassdoor']['id'] = 'not_found'
            company.platforms['glassdoor']['name'] = 'not_found'

        company.save()
        sleep(.5)


def get_jobs(curr_queue, curr_log_queue):
    global queue, log_queue
    queue = curr_queue
    log_queue = curr_log_queue

    try:
        get_followed_companies()

        get_companies_listings()

        get_recommended_listings()
    except Exception:  # pylint: disable=W0718
        exc_class, _, exc_data = exc_info()
        file_name = path_split(exc_data.tb_next.tb_frame.f_code.co_filename)[1]
        log_queue.put({'type': 'error', 'exception': exc_class.__name__,
                      'file_name': file_name, 'file_line': exc_data.tb_next.tb_lineno})
