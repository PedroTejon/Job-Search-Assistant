let currentListing = null;
let currentIndex = 0;
let updateFunc = null;
let currentMenuId = null;

// eslint-disable-next-line no-unused-vars
function removeMultiValueQuery(removedValue, type) {
  queryValues[type] = queryValues[type].filter((value) => value != removedValue);

  container = document.getElementById(type + '_container');
  newContent = '';
  for (const value of queryValues[type]) {
    // eslint-disable-next-line max-len
    newContent += `<span class="query_multivalue_option" onclick="remove_multivalue_query('${value}', '${type}')">${value}</span>`;
  }
  container.innerHTML = newContent;
}

// eslint-disable-next-line no-unused-vars
function removeMultiValueFilter(removedValue, type) {
  filters[type] = filters[type].filter((value) => value != removedValue);

  fetch('http://localhost:8000/vagas/remove_filter?removed_filter=' + removedValue + '&filter_type=' + type,
      {method: 'POST'});

  container = document.getElementById(type + '_container');
  newContent = '';
  for (const value of filters[type]) {
    // eslint-disable-next-line max-len
    newContent += `<span class="query_multivalue_option" onclick="removeMultiValueFilter('${value}', '${type}')">${value}</span>`;
  }
  container.innerHTML = newContent;
}

// eslint-disable-next-line no-unused-vars
function appliedToListing() {
  const dismissButton = document.getElementById('dismissed_button');
  const appliedButton = document.getElementById('applied_button');
  if (!dismissButton.classList.contains('button_disabled')) {
    fetch('http://localhost:8000/vagas/applied_to_listing?id=' + currentListing.id, {method: 'POST'})
        .then((response) => response.json())
        .then((data) => {
          listings[currentIndex].applied_to = true;
          currentListing = listings[currentIndex];
          const listingStatus = document.querySelector(`#listing_${currentIndex} .listing_status`);

          listingStatus.src = 'http://localhost:8000/static/check.svg';

          dismissButton.classList.add('button_disabled');
          if (appliedButton.classList.contains('button_disabled')) {
            appliedButton.classList.remove('button_disabled');
          }
        });
  } else {
    nullify_listing();
  }
}

// eslint-disable-next-line no-unused-vars
function applyNewFilter(filterType) {
  // eslint-disable-next-line max-len
  if (confirm('Deseja adicionar isto aos filtros mesmo? As vagas com estas características já presentes no banco de dados serão marcadas como "Dispensada" automaticamente.')) {
    const type = highlightMode + '_' + filterType;
    fetch(`http://localhost:8000/vagas/apply_new_filter?filtered=${lastText}&filter_type=${type}`, {method: 'POST'})
        .then((response) => response.json())
        .then((data) => {
          if (data.status != 409) {
            // eslint-disable-next-line max-len
            document.getElementById(type + '_container').innerHTML += `<span class="query_multivalue_option" onclick="removeMultiValueFilter('${data.asciified_text}', '${type}')">${data.asciified_text}</span>`;
          }
        });
  }
}

// eslint-disable-next-line no-unused-vars
function dismissListing() {
  const dismissButton = document.getElementById('dismissed_button');
  const appliedButton = document.getElementById('applied_button');
  if (!appliedButton.classList.contains('button_disabled')) {
    fetch('http://localhost:8000/vagas/dismiss_listing?id=' + currentListing.id, {method: 'POST'})
        .then((response) => response.json())
        .then((data) => {
          listings[currentIndex].applied_to = false;
          currentListing = listings[currentIndex];
          const listingStatus = document.querySelector(`#listing_${currentIndex} .listing_status`);

          listingStatus.src ='http://localhost:8000/static/x.svg';

          appliedButton.classList.add('button_disabled');
          if (dismissButton.classList.contains('button_disabled')) {
            dismissButton.classList.remove('button_disabled');
          }
        });
  } else {
    nullifyListing();
  }
}

function nullifyListing() {
  const dismissButton = document.getElementById('dismissed_button');
  const appliedButton = document.getElementById('applied_button');

  fetch('http://localhost:8000/vagas/nullify_listing?id=' + currentListing.id, {method: 'POST'})
      .then((response) => response.json())
      .then((data) => {
        listings[currentIndex].applied_to = null;
        currentListing = listings[currentIndex];
        const listingStatus = document.querySelector(`#listing_${currentIndex} .listing_status`);

        listingStatus.src = 'http://localhost:8000/static/transparent.svg';

        if (appliedButton.classList.contains('button_disabled')) {
          appliedButton.classList.remove('button_disabled');
        }
        if (dismissButton.classList.contains('button_disabled')) {
          dismissButton.classList.remove('button_disabled');
        }
      });
}

// eslint-disable-next-line no-unused-vars
function extractListings() {
  fetch('http://localhost:8000/vagas/start_listing_extraction', {method: 'POST'})
      .then((response) => response.json())
      .then((data) => {
        updateFunc = window.setInterval(getListingExtractionStatus, 1000);
      });
}

function getListingExtractionStatus() {
  fetch('http://localhost:8000/vagas/get_listing_extraction_status')
      .then((response) => response.json())
      .then((data) => {
        results = data['results'];
        const progressBarOverall = document.getElementById('progress_bar_overall');
        const progressLinkedin = document.getElementById('progress_linkedin');
        const progressGlassdoor = document.getElementById('progress_glassdoor');
        const progressCatho = document.getElementById('progress_catho');
        const progressVagasCom = document.getElementById('progress_vagas_com');
        if (results['linkedin']['status'] || results['glassdoor']['status'] ||
            results['catho']['status'] || results['vagas_com']['status']) {
          if (!updateFunc) {
            updateFunc = window.setInterval(getListingExtractionStatus, 1000);
          }

          if (progressBarOverall.style.visibility = 'hidden') {
            progressBarOverall.style.visibility = 'visible';
          }
          if (progressBarOverall.classList.contains('disabled')) {
            progressBarOverall.classList.remove('disabled');
          }

          document.getElementById('new_listings_linkedin').textContent = '+' + results['linkedin']['new_listings'];
          document.getElementById('new_listings_glassdoor').textContent = '+' + results['glassdoor']['new_listings'];
          document.getElementById('new_listings_catho').textContent = '+' + results['catho']['new_listings'];
          document.getElementById('new_listings_vagas_com').textContent = '+' + results['vagas_com']['new_listings'];

          // eslint-disable-next-line max-len
          const total = results['linkedin']['new_listings'] + results['glassdoor']['new_listings'] + results['catho']['new_listings'] + results['vagas_com']['new_listings'];
          document.getElementById('extraction_results').textContent = '+' + total;
        } else if (updateFunc) {
          progressBarOverall.classList.add('disabled');
          clearTimeout(updateFunc);
        }

        alternateProgressBar(results, 'linkedin', progressLinkedin);
        alternateProgressBar(results, 'glassdoor', progressGlassdoor);
        alternateProgressBar(results, 'catho', progressCatho);
        alternateProgressBar(results, 'vagas_com', progressVagasCom);
      });
}

function alternateProgressBar(results, platform, progressElement) {
  if (results[platform]['status'] && progressElement.classList.contains('disabled')) {
    progressElement.classList.remove('disabled');
  } else if (!results[platform]['status']) {
    progressElement.classList.add('disabled');
  }

  if ('exception' in results[platform]) {
    progressElement.classList.add('errored');
    progressElement.title = results[platform]['exception'];
  } else if (progressElement.classList.contains('errored')) {
    progressElement.classList.remove('errored');
    progressElement.removeAttribute('title');
  }
}

function closeUnfocusedMenu(event) {
  const menu = document.getElementById(currentMenuId);
  if (event.target.id != currentMenuId && !menu.contains(event.target)) {
    currentMenuId = null;
    document.removeEventListener('mouseup', closeUnfocusedMenu);
  }
}

// eslint-disable-next-line no-unused-vars
function showFloatingMenu(id) {
  if (currentMenuId == id) {
    return;
  }

  const menu = document.getElementById(id);

  if (menu.style.visibility != 'visible') {
    menu.style.visibility = 'visible';

    currentMenuId = id;
    document.addEventListener('mouseup', closeUnfocusedMenu);
  } else {
    menu.style.visibility = 'hidden';
  }
}

// eslint-disable-next-line no-unused-vars
function showFilterMenu() {
  const filterMenu = document.getElementById('querying_filter_menu');
  if (filterMenu.style.display != 'flex') {
    filterMenu.style.display = 'flex';
  } else {
    filterMenu.style.display = 'none';
  }
}

function search() {
  const searchValue = document.getElementById('search_bar').value.trim();
  const getNew = document.getElementById('query_new').checked;
  const getApplied = document.getElementById('query_applied').checked;
  const getDismissed = document.getElementById('query_dismissed').checked;
  const getLocal = document.getElementById('query_local_listings').checked;
  const getRemote = document.getElementById('query_remote_listings').checked;

  // eslint-disable-next-line max-len
  let url = `http://localhost:8000/vagas/?page=1&listing=[${getApplied},${getDismissed},${getNew},${getLocal},${getRemote}]`;
  if (searchValue !== '') {
    url += '&query=' + searchValue;
  }

  if (queryValues['query_company'].length > 0) {
    url += `&companies=["${queryValues['query_company'].join('","')}"]`;
  }
  if (queryValues['query_city'].length > 0) {
    url += `&cities=["${queryValues['query_city'].join('","')}"]`;
  }
  if (queryValues['query_platform'].length > 0) {
    url += `&platforms=["${queryValues['query_platform'].join('","')}"]`;
  }

  window.location.replace(url);
}

function show(listingIndex) {
  currentIndex = listingIndex;
  currentListing = listings[currentIndex];

  if (document.getElementsByClassName('current_listing').length != 0) {
    document.getElementsByClassName('current_listing')[0].classList.remove('current_listing');
  }
  document.getElementById('listing_' + currentIndex).classList.add('current_listing');

  const container = document.getElementById('listing_details');
  if (container.style.display == 'none') {
    container.style.display = 'flex';
  }

  const listingTitleDetails = document.getElementById('listing_title_det');
  if (currentListing.title) {
    listingTitleDetails.innerText = currentListing.title;
  }

  const listingCompanyDetails = document.getElementById('listing_company_det');
  if (currentListing.company_name) {
    listingCompanyDetails.innerText = currentListing.company_name;
  }

  const listingLocationDetails = document.getElementById('listing_location_det');
  if (currentListing.location) {
    listingLocationDetails.innerText = currentListing.location;
  }

  const listingPublicationDateDetails = document.getElementById('listing_publish_date_det');
  if (currentListing.publication_date) {
    listingPublicationDateDetails.innerText = currentListing.publication_date;
  }

  const listingAppliesDetails = document.getElementById('listing_applies_det');
  if (currentListing.applies) {
    listingAppliesDetails.innerText = currentListing.applies + ' candidato(s)';
  } else {
    listingAppliesDetails.innerText = 'Desconhecido';
  }

  const listingWorkplaceTypeDetails = document.getElementById('listing_workplace_type_det');
  const listingWorkplaceTypeIcon = document.getElementById('listing_workplace_type_ico');
  if (currentListing.workplace_type) {
    listingWorkplaceTypeDetails.innerText = currentListing.workplace_type;
  }

  if (currentListing.workplace_type == 'Remoto') {
    listingWorkplaceTypeIcon.src = 'http://localhost:8000/static/laptop.svg';
  } else {
    listingWorkplaceTypeIcon.src = 'http://localhost:8000/static/briefcase.svg';
  }

  const listingDescriptionDetails = document.getElementById('listing_description_det');
  if (currentListing.description) {
    listingDescriptionDetails.innerHTML = currentListing.description;
  }

  const platformLogo = document.getElementById('platform_logo');
  const platformName = document.getElementById('platform_name');
  const platformId = document.getElementById('platform_id');
  if (currentListing.platform) {
    platformLogo.src = `http://localhost:8000/static/${currentListing.platform}.svg`;
    platformName.innerText = currentListing.platform;
    platformId.innerText = '#' + currentListing.platform_id;
  }

  const applyButton = document.getElementById('apply_button');
  if (currentListing.application_url) {
    applyButton.href = currentListing.application_url;
  }

  const dismissButton = document.getElementById('dismissed_button');
  const appliedButton = document.getElementById('applied_button');
  const listingStatus = document.querySelector(`#listing_${currentIndex} .listing_status`);
  if (currentListing.applied_to) {
    listingStatus.src = 'http://localhost:8000/static/check.svg';

    dismissButton.classList.add('button_disabled');
    if (appliedButton.classList.contains('button_disabled')) {
      appliedButton.classList.remove('button_disabled');
    }
  } else if (currentListing.applied_to === false) {
    listingStatus.src = 'http://localhost:8000/static/x.svg';

    appliedButton.classList.add('button_disabled');
    if (dismissButton.classList.contains('button_disabled')) {
      dismissButton.classList.remove('button_disabled');
    }
  } else {
    listingStatus.src = 'http://localhost:8000/static/transparent.svg';

    if (appliedButton.classList.contains('button_disabled')) {
      appliedButton.classList.remove('button_disabled');
    }
    if (dismissButton.classList.contains('button_disabled')) {
      dismissButton.classList.remove('button_disabled');
    }
  }
}

if (!window.highlighter) {
  highlighter = {};
  highlighter.get_highlighted = function() {
    let text = '';
    if (window.getSelection) {
      text = window.getSelection();
    } else if (document.getSelection) {
      text = document.getSelection();
    } else if (document.selection) {
      text = document.selection.createRange().text;
    }
    return text;
  };
}

let lastText = null;
let highlightMode = null;
window.addEventListener('mousedown', function(e) {
  const menu = document.getElementById('highlight_tools');

  if (e.target.classList.contains('listing_title') || e.target.classList.contains('listing_company')) {
    if (e.target.classList.contains('listing_title')) {
      highlightMode = 'title';
    } else {
      highlightMode = 'company';
    }

    highlighter.posX = e.pageX;
    highlighter.posY = e.pageY;
    window.addEventListener('mouseup', function() {
      const menu = document.getElementById('highlight_tools');
      const highlight = highlighter.get_highlighted();
      const highlightedText = highlight.toString().trim();
      const filterWordButton = document.getElementById('filterWordButton');
      if (highlightedText.length > 0 && highlightedText !== lastText && highlight.type == 'Range') {
        if (highlightedText.indexOf(' ') >= 0) {
          filterWordButton.disabled = true;
        } else if (filterWordButton.disabled) {
          filterWordButton.disabled = false;
        }
        menu.style = 'position: absolute; left:' + (highlighter.posX ) + 'px; top: ' + (highlighter.posY - 35) + 'px';
        lastText = highlightedText;
      } else {
        lastText = null;
        menu.style = 'display: none';
      }
    }, {once: true});
  } else if (menu.style !== 'display: none' &&
            !['filter_word_button', 'filter_term_button'].includes(e.target.id) &&
            !['filter_word_button', 'filter_term_button'].includes(e.target.parentElement.id)) {
    menu.style = 'display: none';
    lastText = null;
  }
});

listings = JSON.parse(document.getElementById('listings').textContent);
getListingExtractionStatus();
if (listings.length > 0) {
  show(0);

  for (let i = 0; i < listings.length; i++) {
    const listingStatus = document.querySelector(`#listing_${i} .listing_status`);
    const currentListing = listings[i];
    if (currentListing.applied_to) {
      listingStatus.src = 'http://localhost:8000/static/check.svg';
    } else if (currentListing.applied_to === false) {
      listingStatus.src = 'http://localhost:8000/static/x.svg';
    } else {
      listingStatus.src = 'http://localhost:8000/static/transparent.svg';
    }
  }
}

const queryValues = {
  query_company: JSON.parse(document.getElementById('queried_companies').textContent),
  query_city: JSON.parse(document.getElementById('queried_cities').textContent),
  query_platform: JSON.parse(document.getElementById('queried_platforms').textContent),
};

const filters = JSON.parse(document.getElementById('filters').textContent);

// eslint-disable-next-line no-unused-vars
function addMultiValueQuery(e) {
  if (e.code === 'Enter') {
    const value = e.target.value.trim();
    const type = e.target.id.replace('_input', '');
    e.target.value = '';
    if (value !== '' && !queryValues[type].includes(value)) {
      queryValues[type].push(value);
      // eslint-disable-next-line max-len
      document.getElementById(type + '_container').innerHTML += `<span class="query_multivalue_option" onclick="removeMultiValueQuery('${value}', '${type}')">${value}</span>`;
    }
  }
};

// eslint-disable-next-line no-unused-vars
function addMultiValueFilter(e) {
  if (e.code === 'Enter') {
    const value = e.target.value.trim();
    const type = e.target.id.replace('_input', '');
    e.target.value = '';

    if (!['cities', 'states', 'countries'].includes(type) &&
        // eslint-disable-next-line max-len
        !confirm('Deseja adicionar isto aos filtros mesmo? As vagas com estas características já presentes no banco de dados serão marcadas como "Dispensada" automaticamente.')) {
      return;
    }

    fetch('http://localhost:8000/vagas/apply_new_filter?filtered=' + value + '&filter_type=' + type, {method: 'POST'})
        .then((response) => response.json())
        .then((data) => {
          if (data.status != 409) {
            // eslint-disable-next-line max-len
            document.getElementById(type + '_container').innerHTML += `<span class="query_multivalue_option" onclick="removeMultiValueFilter('${data.asciified_text}', '${type}')">${data.asciified_text}</span>`;
          }
        });
  }
};

const queryPlatformInput = document.getElementById('query_platform_input');
queryPlatformInput.addEventListener('change', function(e) {
  const queriedPlatform = queryPlatformInput.value;
  queryPlatformInput.value = '-';
  if (queriedPlatform !== '-' && !queryValues['query_platform'].includes(queriedPlatform)) {
    queryValues['query_platform'].push(queriedPlatform);
    // eslint-disable-next-line max-len
    document.getElementById('query_platform_container').innerHTML += `<span class="query_multivalue_option" onclick="remove_platform('${queriedPlatform}')">${queriedPlatform}</span>`;
  }
});

const searchBar = document.getElementById('search_bar');
searchBar.addEventListener('keydown', function(e) {
  if (e.code === 'Enter') {
    search(searchBar.value);
  }
});
