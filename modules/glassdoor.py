from os import listdir
from json import load, dump, loads
from modules.utils import empresa_existe, empresa_existe_nome, filtrar_vaga, vaga_existe
from time import sleep
from cloudscraper import create_scraper
from unidecode import unidecode
from re import sub
from django.utils.timezone import now

from interfaces.vagas_interface.models import Empresa, Vaga


def job_listings_request(cookies, cursor, query, operation, variables):
    request_body = [{
        "operationName": operation,
        "variables": variables,
        "query": query
    }]
    if cursor:
        request_body[0]['variables']['pageNumber'] = cursor['pageNumber']
        request_body[0]['variables']['pageCursor'] = cursor['cursor']

    session = create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    })

    return session.post(f'https://www.glassdoor.com.br/graph', 
        headers={
            "accept": "*/*",
            "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "apollographql-client-name": "job-search-next",
            "apollographql-client-version": "6.5.0",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "gd-csrf-token": get_csrf_token(),
            "pragma": "no-cache",
            "sec-ch-ua": "\"Microsoft Edge\";v=\"119\", \"Chromium\";v=\"119\", \"Not?A_Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin"
        },
        cookies=cookies, 
        json=request_body
    )


def get_csrf_token():
    armazenamento_local = load(open('data/armazenamento_local.json', 'r', encoding='utf-8'))
    return armazenamento_local['glassdoor_csrf']


def extrair_vagas(itens: list):
    for vaga in itens:
        id_vaga = vaga['jobview']['job']['listingId']
        if vaga_existe(id_vaga):
            continue
    
        vaga_header = vaga['jobview']['header']
        titulo = vaga_header['jobTitleText']
        local = vaga_header['locationName']
        modalidade = 'Remoto' if 'remoto' in local else 'Presencial/Hibrido'
        empresa_nome = vaga_header['employerNameFromSearch']
        if filtrar_vaga(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(titulo).lower()), local, modalidade):
            if (empresa := empresa_existe_nome(empresa_nome, 'glassdoor')).plataformas['glassdoor']['nome'] == None:
                empresa.plataformas['glassdoor']['nome'] = empresa_nome
                if 'employer' in vaga['jobview']['header']:
                    empresa.plataformas['glassdoor']['id'] = str(vaga['jobview']['header']['employer']['id'])
                empresa.save()
            Vaga(
                id_vaga=str(vaga['jobview']['job']['listingId']),
                titulo=titulo,
                local=local,
                modalidade=modalidade,
                empresa=empresa,
                plataforma='Glassdoor'
            ).save()


def scrape_vagas_empresas():
    cookies = {cookie['name']: cookie['value'].replace('\"', '') for cookie in load(open('data/cookies.json', 'r', encoding='utf-8'))}

    for empresa in filter(lambda x: x.plataformas['glassdoor']['nome'] not in [None, 'not_found'] 
                          and x.plataformas['glassdoor']['id'] not in [None, 'not_found'] 
                          and not x.checado_recentemente_gl()
                          and x.followed, Empresa.objects.all()):
        cursor = None
        pagina = 1
        while cursor == None or cursor:
            response = job_listings_request(cookies, cursor, "query JobSearchResultsQuery($excludeJobListingIds: [Long!], $keyword: String, $locationId: Int, $locationType: LocationTypeEnum, $numJobsToShow: Int!, $pageCursor: String, $pageNumber: Int, $filterParams: [FilterParams], $originalPageUrl: String, $seoFriendlyUrlInput: String, $parameterUrlInput: String, $seoUrl: Boolean) {\n  jobListings(\n    contextHolder: {searchParams: {excludeJobListingIds: $excludeJobListingIds, keyword: $keyword, locationId: $locationId, locationType: $locationType, numPerPage: $numJobsToShow, pageCursor: $pageCursor, pageNumber: $pageNumber, filterParams: $filterParams, originalPageUrl: $originalPageUrl, seoFriendlyUrlInput: $seoFriendlyUrlInput, parameterUrlInput: $parameterUrlInput, seoUrl: $seoUrl, searchType: SR}}\n  ) {\n    companyFilterOptions {\n      id\n      shortName\n      __typename\n    }\n    filterOptions\n    indeedCtk\n    jobListings {\n      ...JobView\n      __typename\n    }\n    jobListingSeoLinks {\n      linkItems {\n        position\n        url\n        __typename\n      }\n      __typename\n    }\n    jobSearchTrackingKey\n    jobsPageSeoData {\n      pageMetaDescription\n      pageTitle\n      __typename\n    }\n    paginationCursors {\n      cursor\n      pageNumber\n      __typename\n    }\n    indexablePageForSeo\n    searchResultsMetadata {\n      searchCriteria {\n        implicitLocation {\n          id\n          localizedDisplayName\n          type\n          __typename\n        }\n        keyword\n        location {\n          id\n          shortName\n          localizedShortName\n          localizedDisplayName\n          type\n          __typename\n        }\n        __typename\n      }\n      footerVO {\n        countryMenu {\n          childNavigationLinks {\n            id\n            link\n            textKey\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      helpCenterDomain\n      helpCenterLocale\n      jobAlert {\n        jobAlertExists\n        __typename\n      }\n      jobSerpFaq {\n        questions {\n          answer\n          question\n          __typename\n        }\n        __typename\n      }\n      jobSerpJobOutlook {\n        occupation\n        paragraph\n        heading\n        __typename\n      }\n      showMachineReadableJobs\n      __typename\n    }\n    serpSeoLinksVO {\n      relatedJobTitlesResults\n      searchedJobTitle\n      searchedKeyword\n      searchedLocationIdAsString\n      searchedLocationSeoName\n      searchedLocationType\n      topCityIdsToNameResults {\n        key\n        value\n        __typename\n      }\n      topEmployerIdsToNameResults {\n        key\n        value\n        __typename\n      }\n      topEmployerNameResults\n      topOccupationResults\n      __typename\n    }\n    totalJobsCount\n    __typename\n  }\n}\n\nfragment JobView on JobListingSearchResult {\n  jobview {\n    header {\n      adOrderId\n      advertiserType\n      adOrderSponsorshipLevel\n      ageInDays\n      divisionEmployerName\n      easyApply\n      employer {\n        id\n        name\n        shortName\n        __typename\n      }\n      employerNameFromSearch\n      goc\n      gocConfidence\n      gocId\n      jobCountryId\n      jobLink\n      jobResultTrackingKey\n      jobTitleText\n      locationName\n      locationType\n      locId\n      needsCommission\n      payCurrency\n      payPeriod\n      payPeriodAdjustedPay {\n        p10\n        p50\n        p90\n        __typename\n      }\n      rating\n      salarySource\n      savedJobId\n      seoJobLink\n      sponsored\n      __typename\n    }\n    job {\n      descriptionFragments\n      importConfigId\n      jobTitleId\n      jobTitleText\n      listingId\n      __typename\n    }\n    jobListingAdminDetails {\n      cpcVal\n      importConfigId\n      jobListingId\n      jobSourceId\n      userEligibleForAdminJobDetails\n      __typename\n    }\n    overview {\n      shortName\n      squareLogoUrl\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n", "JobSearchResultsQuery", {
                "excludeJobListingIds": [],
                "filterParams": [{"filterKey": "companyId", "values": empresa.plataformas['glassdoor']['id']}],
                "keyword": "",
                "locationId": 0,
                "numJobsToShow": 50,
                "originalPageUrl": "https://www.glassdoor.com.br/Vaga/index.htm",
                "seoUrl": False
            })
            
            if response.status_code == 200:
                conteudo = loads(response.content)[0]['data']
            else:
                sleep(1)
                continue

            cursor = list(filter(lambda x: x['pageNumber'] > pagina, conteudo['jobListings']['paginationCursors']))
            if cursor:
                cursor = cursor[0]
                pagina = cursor['pageNumber']

            extrair_vagas(conteudo['jobListings']['jobListings'])
    
            sleep(.5)

        empresa.last_check_glassdoor = now().strftime("%Y-%m-%dT%H:%M:%S")
        empresa.save()


def scrape_vagas_recomendadas() -> dict:
    cookies = {cookie['name']: cookie['value'].replace('\"', '') for cookie in load(open('data/cookies.json', 'r', encoding='utf-8'))}
    
    cursor = None
    for pagina in range(20):
        response = job_listings_request(cookies, cursor, "query JobRecommendationsQuery($numJobsToShow: Int!, $pageNumber: Int, $pageCursor: String) {\n  jobListings(\n    contextHolder: {adSlotName: \"forYou-jobs-lsr\", searchParams: {numPerPage: $numJobsToShow, searchType: REC_JOBS, pageNumber: $pageNumber, pageCursor: $pageCursor}}\n  ) {\n    indeedCtk\n    jobListings {\n      ...JobView\n      __typename\n    }\n    jobSearchTrackingKey\n    paginationCursors {\n      cursor\n      pageNumber\n      __typename\n    }\n    searchResultsMetadata {\n      footerVO {\n        countryMenu {\n          childNavigationLinks {\n            id\n            link\n            textKey\n            __typename\n          }\n          __typename\n        }\n        __typename\n      }\n      helpCenterDomain\n      helpCenterLocale\n      __typename\n    }\n    jobsPageSeoData {\n      pageMetaDescription\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment JobView on JobListingSearchResult {\n  jobview {\n    header {\n      adOrderId\n      advertiserType\n      adOrderSponsorshipLevel\n      ageInDays\n      divisionEmployerName\n      easyApply\n      employer {\n        id\n        name\n        shortName\n        __typename\n      }\n      employerNameFromSearch\n      goc\n      gocConfidence\n      gocId\n      jobCountryId\n      jobLink\n      jobResultTrackingKey\n      jobTitleText\n      locationName\n      locationType\n      locId\n      needsCommission\n      payCurrency\n      payPeriod\n      payPeriodAdjustedPay {\n        p10\n        p50\n        p90\n        __typename\n      }\n      rating\n      salarySource\n      savedJobId\n      seoJobLink\n      sponsored\n      __typename\n    }\n    job {\n      descriptionFragments\n      importConfigId\n      jobTitleId\n      jobTitleText\n      listingId\n      __typename\n    }\n    jobListingAdminDetails {\n      cpcVal\n      importConfigId\n      jobListingId\n      jobSourceId\n      userEligibleForAdminJobDetails\n      __typename\n    }\n    overview {\n      shortName\n      squareLogoUrl\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n", "JobRecommendationsQuery", {
            "numJobsToShow": 50,
            "originalPageUrl": "https://www.glassdoor.com.br/Vaga/index.htm"
        })
        
        conteudo = loads(response.content)[0]['data']

        cursor = list(filter(lambda x: x['pageNumber'] > pagina + 1, conteudo['jobListings']['paginationCursors']))
        if not cursor:
            break
        else:
            cursor = cursor[0]

        extrair_vagas(conteudo['jobListings']['jobListings'])

        sleep(.5)


def scrape_detalhes_vagas():
    cookies = {cookie['name']: cookie['value'].replace('\"', '') for cookie in load(open('data/cookies.json', 'r', encoding='utf-8'))}

    for vaga in filter(lambda x: x.plataforma == 'Glassdoor' and x.descricao == '', Vaga.objects.all()):
        response = job_listings_request(cookies, None, "query JobDetailQuery($jl: Long!, $queryString: String, $enableReviewSummary: Boolean!, $pageTypeEnum: PageTypeEnum) {\n  jobview: jobView(\n    listingId: $jl\n    contextHolder: {queryString: $queryString, pageTypeEnum: $pageTypeEnum}\n  ) {\n    ...DetailFragment\n    employerReviewSummary @include(if: $enableReviewSummary) {\n      reviewSummary {\n        highlightSummary {\n          sentiment\n          sentence\n          categoryReviewCount\n          __typename\n        }\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment DetailFragment on JobView {\n  employerBenefits {\n    benefitsOverview {\n      benefitsHighlights {\n        benefit {\n          commentCount\n          icon\n          name\n          __typename\n        }\n        highlightPhrase\n        __typename\n      }\n      overallBenefitRating\n      employerBenefitSummary {\n        comment\n        __typename\n      }\n      __typename\n    }\n    benefitReviews {\n      benefitComments {\n        id\n        comment\n        __typename\n      }\n      cityName\n      createDate\n      currentJob\n      rating\n      stateName\n      userEnteredJobTitle\n      __typename\n    }\n    numReviews\n    __typename\n  }\n  employerContent {\n    featuredVideoLink\n    managedContent {\n      id\n      type\n      title\n      body\n      captions\n      photos\n      videos\n      __typename\n    }\n    diversityContent {\n      goals {\n        id\n        workPopulation\n        underRepresentedGroup\n        currentMetrics\n        currentMetricsDate\n        representationGoalMetrics\n        representationGoalMetricsDate\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  employerAttributes {\n    attributes {\n      attributeName\n      attributeValue\n      __typename\n    }\n    __typename\n  }\n  gaTrackerData {\n    isSponsoredFromIndeed\n    isSponsoredFromJobListingHit\n    jobViewDisplayTimeMillis\n    requiresTracking\n    pageRequestGuid\n    searchTypeCode\n    trackingUrl\n    __typename\n  }\n  header {\n    jobLink\n    adOrderId\n    adOrderSponsorshipLevel\n    advertiserType\n    ageInDays\n    applicationId\n    appliedDate\n    applyUrl\n    applyButtonDisabled\n    blur\n    coverPhoto {\n      url\n      __typename\n    }\n    divisionEmployerName\n    easyApply\n    easyApplyMethod\n    employerNameFromSearch\n    employer {\n      activeStatus\n      bestProfile {\n        id\n        __typename\n      }\n      id\n      name\n      shortName\n      size\n      squareLogoUrl\n      __typename\n    }\n    expired\n    goc\n    hideCEOInfo\n    indeedApplyMetadata\n    indeedJobAttribute {\n      education\n      skills\n      educationLabel\n      skillsLabel\n      yearsOfExperienceLabel\n      __typename\n    }\n    isIndexableJobViewPage\n    jobTitleText\n    jobType\n    jobTypeKeys\n    jobCountryId\n    jobResultTrackingKey\n    locId\n    locationName\n    locationType\n    needsCommission\n    normalizedJobTitle\n    organic\n    payCurrency\n    payPeriod\n    payPeriodAdjustedPay {\n      p10\n      p50\n      p90\n      __typename\n    }\n    rating\n    remoteWorkTypes\n    salarySource\n    savedJobId\n    seoJobLink\n    sgocId\n    sponsored\n    categoryMgocId\n    urgencySignal {\n      labelKey\n      messageKey\n      normalizedCount\n      __typename\n    }\n    __typename\n  }\n  similarJobs {\n    relatedJobTitle\n    careerUrl\n    __typename\n  }\n  job {\n    description\n    discoverDate\n    eolHashCode\n    importConfigId\n    jobReqId\n    jobSource\n    jobTitleId\n    jobTitleText\n    listingId\n    __typename\n  }\n  jobListingAdminDetails {\n    adOrderId\n    cpcVal\n    importConfigId\n    jobListingId\n    jobSourceId\n    userEligibleForAdminJobDetails\n    __typename\n  }\n  map {\n    address\n    cityName\n    country\n    employer {\n      id\n      name\n      __typename\n    }\n    lat\n    lng\n    locationName\n    postalCode\n    stateName\n    __typename\n  }\n  overview {\n    ceo {\n      name\n      photoUrl\n      __typename\n    }\n    id\n    name\n    shortName\n    squareLogoUrl\n    headquarters\n    links {\n      overviewUrl\n      benefitsUrl\n      photosUrl\n      reviewsUrl\n      salariesUrl\n      __typename\n    }\n    primaryIndustry {\n      industryId\n      industryName\n      sectorName\n      sectorId\n      __typename\n    }\n    ratings {\n      overallRating\n      ceoRating\n      ceoRatingsCount\n      recommendToFriendRating\n      compensationAndBenefitsRating\n      cultureAndValuesRating\n      careerOpportunitiesRating\n      seniorManagementRating\n      workLifeBalanceRating\n      __typename\n    }\n    revenue\n    size\n    sizeCategory\n    type\n    website\n    yearFounded\n    __typename\n  }\n  photos {\n    photos {\n      caption\n      photoId\n      photoId2x\n      photoLink\n      photoUrl\n      photoUrl2x\n      __typename\n    }\n    __typename\n  }\n  reviews {\n    reviews {\n      advice\n      cons\n      countHelpful\n      employerResponses {\n        response\n        responseDateTime\n        userJobTitle\n        __typename\n      }\n      employmentStatus\n      featured\n      isCurrentJob\n      jobTitle {\n        text\n        __typename\n      }\n      lengthOfEmployment\n      pros\n      ratingBusinessOutlook\n      ratingCareerOpportunities\n      ratingCeo\n      ratingCompensationAndBenefits\n      ratingCultureAndValues\n      ratingOverall\n      ratingRecommendToFriend\n      ratingSeniorLeadership\n      ratingWorkLifeBalance\n      reviewDateTime\n      reviewId\n      summary\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n", "JobDetailQuery", {
            "jl": vaga.id_vaga,
            "pageTypeEnum": "JOBS_FOR_YOU",
            "enableReviewSummary": True,
            "queryString": f"jobListingId={vaga.id_vaga}",
        })

        if response.status_code == 200:
            conteudo = loads(response.content)[0]['data']['jobview']
        else:
            sleep(1)
            continue

        vaga.link_inscricao = 'https://www.glassdoor.com.br/' + conteudo['header']['jobLink']

        vaga.n_candidaturas = None

        vaga.descricao = conteudo['job']['description']

        vaga.tempo_publicado = conteudo['job']['discoverDate']

        vaga.save()
        
        sleep(.5)


def get_followed_companies():
    cookies_json = load(open('data/cookies.json', 'r', encoding='utf-8'))
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])

    empresas = Empresa.objects.all()
    for empresa in filter(lambda x: x.plataformas['glassdoor']['id'] == None and x.followed, empresas):
        session = create_scraper(browser={
            'browser': 'firefox',
            'platform': 'windows',
            'mobile': False
        })

        response = session.get(f'http://www.glassdoor.com.br/api-web/employer/find.htm?autocomplete=true&term={empresa.plataformas["linkedin"]["nome"]}', 
            headers={
                'cookie': cookies
            })
        response_content = loads(response.text)
        
        if len(response_content):
            empresa.plataformas['glassdoor']['id'] = str(response_content[0]['id'])
            empresa.plataformas['glassdoor']['nome'] = response_content[0]['label']
        else:
            empresa.plataformas['glassdoor']['id'] = 'not_found'
            empresa.plataformas['glassdoor']['nome'] = 'not_found'

        empresa.save()        
        sleep(.5)


def get_jobs():
    get_followed_companies()

    scrape_vagas_empresas()

    scrape_vagas_recomendadas()

    scrape_detalhes_vagas()
