let current_listing = null
let current_index = 0
let update_func = null

function remove_city(removed_city) {
    queried_cities = queried_cities.filter((city) => city != removed_city)

    container = document.getElementById('query_city_container')
    new_content = ''
    for (let city of queried_cities) {
        new_content += `<span class="query_multivalue_option" onclick="remove_city('${city}')">${city}</span>`
    }
    container.innerHTML = new_content
}

function remove_company(removed_company) {
    queried_companies = queried_companies.filter((company) => company != removed_company)

    container = document.getElementById('query_company_container')
    new_content = ''
    for (let company of queried_companies) {
        new_content += `<span class="query_multivalue_option" onclick="remove_company('${company}')">${company}</span>`
    }
    container.innerHTML = new_content
}

function remove_platform(removed_platform) {
    queried_platforms = queried_platforms.filter((platform) => platform != removed_platform)

    container = document.getElementById('query_platform_container')
    new_content = ''
    for (let platform of queried_platforms) {
        new_content += `<span class="query_multivalue_option" onclick="remove_platform('${platform}')">${platform}</span>`
    }
    container.innerHTML = new_content
}

function applied_to_listing() {
    let dismiss_button = document.getElementById('dismissed_button')
    let applied_button = document.getElementById('applied_button')
    if (!dismiss_button.classList.contains('button_disabled'))
        fetch('http://localhost:8000/vagas/applied_to_listing?id=' + current_listing.id, {method: 'POST'})
        .then((response) => response.json())
        .then((data) => {
            listings[current_index].applied_to = true;
            current_listing = listings[current_index];
            let listing_status = document.querySelector(`#listing_${current_index} .listing_status`)

            listing_status.src = 'http://localhost:8000/static/check.svg'
        
            dismiss_button.classList.add('button_disabled')
            if (applied_button.classList.contains('button_disabled'))
                applied_button.classList.remove('button_disabled')
        })
    else
        nullify_listing()
}

function apply_new_filter(filter_type) {
    if (confirm('Deseja adicionar isto aos filtros mesmo? As vagas com estas características já presentes no banco de dados serão marcadas como "Dispensada" automaticamente.')) {
        fetch('http://localhost:8000/vagas/apply_new_filter?filtered=' + last_text + '&filter_type=' + highlight_mode + '_' + filter_type, {method: 'POST'})
        .then((response) => response.json())
        .then((data) => {
            
        })
    }
}

function dismiss_listing() {
    let dismiss_button = document.getElementById('dismissed_button')
    let applied_button = document.getElementById('applied_button')
    if (!applied_button.classList.contains('button_disabled'))
        fetch('http://localhost:8000/vagas/dismiss_listing?id=' + current_listing.id, {method: 'POST'})
        .then((response) => response.json())
        .then((data) => {
            listings[current_index].applied_to = false;
            current_listing = listings[current_index];
            let listing_status = document.querySelector(`#listing_${current_index} .listing_status`)
            
            listing_status.src ='http://localhost:8000/static/x.svg'

            applied_button.classList.add('button_disabled')
            if (dismiss_button.classList.contains('button_disabled'))
                dismiss_button.classList.remove('button_disabled')
        })
    else
        nullify_listing()
}

function nullify_listing() {
    let dismiss_button = document.getElementById('dismissed_button')
    let applied_button = document.getElementById('applied_button')

    fetch('http://localhost:8000/vagas/nullify_listing?id=' + current_listing.id, {method: 'POST'})
    .then((response) => response.json())
    .then((data) => {
        listings[current_index].applied_to = null;
        current_listing = listings[current_index];
        let listing_status = document.querySelector(`#listing_${current_index} .listing_status`)

        listing_status.src = 'http://localhost:8000/static/transparent.svg'

        if (applied_button.classList.contains('button_disabled'))
            applied_button.classList.remove('button_disabled')
        if (dismiss_button.classList.contains('button_disabled'))
            dismiss_button.classList.remove('button_disabled')
    })
}

function extract_listings() {
    fetch('http://localhost:8000/vagas/start_listing_extraction', {method: 'POST'})
    .then((response) => response.json())
    .then((data) => {
        update_func = window.setInterval(get_listings_extraction_status, 1000)
    })
}

function get_listings_extraction_status() {
    fetch('http://localhost:8000/vagas/get_listing_extraction_status')
    .then((response) => response.json())
    .then((data) => {
        results = data['results']
        console.log(data)
        let progress_bar_overall = document.getElementById('progress_bar_overall')
        let progress_bar_linkedin = document.getElementById('progress_linkedin')
        let progress_bar_glassdoor = document.getElementById('progress_glassdoor')
        let progress_bar_catho = document.getElementById('progress_catho')
        let progress_bar_vagas_com = document.getElementById('progress_vagas_com')
        if  (results['linkedin']['status'] || results['glassdoor']['status'] || results['catho']['status'] || results['vagas_com']['status']) {
            if (!update_func) 
                update_func = window.setInterval(get_listings_extraction_status, 1000)
            
            
            if (progress_bar_overall.style.visibility = 'hidden')
                progress_bar_overall.style.visibility = 'visible'
            if (progress_bar_overall.classList.contains('disabled'))
                progress_bar_overall.classList.remove('disabled')
        
            document.getElementById('new_listings_linkedin').textContent = '+' + results['linkedin']['new_listings'];
            document.getElementById('new_listings_glassdoor').textContent = '+' + results['glassdoor']['new_listings'];
            document.getElementById('new_listings_catho').textContent = '+' + results['catho']['new_listings'];
            document.getElementById('new_listings_vagas_com').textContent = '+' + results['vagas_com']['new_listings'];

            document.getElementById('extraction_results').textContent = '+' + (results['linkedin']['new_listings'] + results['glassdoor']['new_listings'] + results['catho']['new_listings'] + results['vagas_com']['new_listings']);
        }
        else if (update_func) {
            progress_bar_overall.classList.add('disabled')
            clearTimeout(update_func);
        }

        alternate_progress_bar(results, 'linkedin', progress_bar_linkedin)
        alternate_progress_bar(results, 'glassdoor', progress_bar_glassdoor)
        alternate_progress_bar(results, 'catho', progress_bar_catho)
        alternate_progress_bar(results, 'vagas_com', progress_bar_vagas_com)
    })
}

function alternate_progress_bar(results, platform, progress_element) {
    if (results[platform]['status'] && progress_element.classList.contains('disabled'))
        progress_element.classList.remove('disabled')
    else if (!results[platform]['status'])
        progress_element.classList.add('disabled')

    if ('exception' in results[platform]) {
        progress_element.classList.add('errored')
        progress_element.title = results[platform]['exception']
    }
    else if (progress_element.classList.contains('errored')) {
        progress_element.classList.remove('errored')
        progress_element.removeAttribute('title')
    }
}

function show_extraction_progress_menu() {
    let extraction_progress_menu = document.getElementById('extraction_progress_menu');

    extraction_progress_menu.style.visibility = extraction_progress_menu.style.visibility == 'hidden' ? 'visible' : 'hidden';
}

function search(cur_query) {
    let search_value = document.getElementById('search_bar').value.trim();
    let get_new = document.getElementById('query_new').checked
    let get_applied = document.getElementById('query_applied').checked
    let get_dismissed = document.getElementById('query_dismissed').checked
    let get_local = document.getElementById('query_local_listings').checked
    let get_remote = document.getElementById('query_remote_listings').checked
    
    url = `http://localhost:8000/vagas/?page=1&listing=[${get_applied},${get_dismissed},${get_new},${get_local},${get_remote}]`;
    if (search_value !== '') {
        if (search_value !== cur_query) 
            url += '&query=' + search_value;
        else if (search_value)
            url += '&query=' + cur_query;
    }
    if (queried_companies.length > 0) {
        url += `&companies=["${queried_companies.join('","')}"]`
    }
    if (queried_cities.length > 0) {
        url += `&cities=["${queried_cities.join('","')}"]`
    }
    if (queried_platforms.length > 0) {
        url += `&platforms=["${queried_platforms.join('","')}"]`
    }

    window.location.replace(url);
}

function show(listing_index) {
    current_index = listing_index
    current_listing = listings[current_index]

    if (document.getElementsByClassName('current_listing').length != 0)
        document.getElementsByClassName('current_listing')[0].classList.remove('current_listing')
    document.getElementById('listing_' + current_index).classList.add('current_listing')

    let container = document.getElementById('listing_details');
    if (container.style.display == 'none')
        container.style.display = 'flex';

    let listing_title_det = document.getElementById('listing_title_det');
    if (current_listing.title)
        listing_title_det.innerText = current_listing.title;

    let listing_company_det = document.getElementById('listing_company_det');
    if (current_listing.company_name)
        listing_company_det.innerText = current_listing.company_name;

    let listing_location_det = document.getElementById('listing_location_det');
    if (current_listing.location)
        listing_location_det.innerText = current_listing.location;

    let listing_publish_date_det = document.getElementById('listing_publish_date_det');
    if (current_listing.publication_date)
        listing_publish_date_det.innerText = current_listing.publication_date;

    let listing_applies_det = document.getElementById('listing_applies_det');
    if (current_listing.applies)
        listing_applies_det.innerText = current_listing.applies + " candidato(s)";
    else
        listing_applies_det.innerText = "Desconhecido";

    let listing_workplace_type_det = document.getElementById('listing_workplace_type_det');
    let listing_workplace_type_ico = document.getElementById('listing_workplace_type_ico');
    if (current_listing.workplace_type)
        listing_workplace_type_det.innerText = current_listing.workplace_type;
    if (current_listing.workplace_type == 'Remoto') 
        listing_workplace_type_ico.src = 'http://localhost:8000/static/laptop.svg'
    else
        listing_workplace_type_ico.src = 'http://localhost:8000/static/briefcase.svg'

    let listing_description_det = document.getElementById('listing_description_det');
    if (current_listing.description)
        listing_description_det.innerHTML = current_listing.description;

    let platform_logo = document.getElementById('platform_logo');
    let platform_name = document.getElementById('platform_name');
    let platform_id = document.getElementById('platform_id');
    if (current_listing.platform) {
        platform_logo.src = `http://localhost:8000/static/${current_listing.platform}.svg`;
        platform_name.innerText = current_listing.platform;
        platform_id.innerText = "#" + current_listing.platform_id;
    }

    let apply_button = document.getElementById('apply_button');
    if (current_listing.application_url)
        apply_button.href = current_listing.application_url

    let dismiss_button = document.getElementById('dismissed_button')
    let applied_button = document.getElementById('applied_button')
    let listing_status = document.querySelector(`#listing_${current_index} .listing_status`)
    if (current_listing.applied_to) {
        listing_status.src = 'http://localhost:8000/static/check.svg'
    
        dismiss_button.classList.add('button_disabled')
        if (applied_button.classList.contains('button_disabled'))
            applied_button.classList.remove('button_disabled')
    } else if (current_listing.applied_to === false) {
        listing_status.src = 'http://localhost:8000/static/x.svg'

        applied_button.classList.add('button_disabled')
        if (dismiss_button.classList.contains('button_disabled'))
            dismiss_button.classList.remove('button_disabled')
    } else {
        listing_status.src = 'http://localhost:8000/static/transparent.svg'

        if (applied_button.classList.contains('button_disabled'))
            applied_button.classList.remove('button_disabled')
        if (dismiss_button.classList.contains('button_disabled'))
            dismiss_button.classList.remove('button_disabled')
    }
    
}

function show_filter_menu() {
    let filter_menu = document.getElementById('querying_filter_menu')
    if (filter_menu.style.display == 'none') {
        filter_menu.style.display = 'flex';
    } else {
        filter_menu.style.display = 'none';
    }
}

if (!window.highlighter) {
    highlighter = {};
    highlighter.get_highlighted = function() {
        let text = '';
        if (window.getSelection)
            text = window.getSelection();
        else if (document.getSelection)
            text = document.getSelection();
        else if (document.selection)
            text = document.selection.createRange().text;
        
        return text;
    }
}

var last_text = null
var highlight_mode = null
window.addEventListener("mousedown", function(e){
    let menu = document.getElementById('highlight_tools')
    
    if (e.target.classList.contains('listing_title') || e.target.classList.contains('listing_company')) {
        if (e.target.classList.contains('listing_title'))
            highlight_mode = 'title'
        else
            highlight_mode = 'company'

        highlighter.posX = e.pageX;
        highlighter.posY = e.pageY;
        window.addEventListener("mouseup", function() {
            let menu = document.getElementById('highlight_tools');
            let highlight = highlighter.get_highlighted();
            let highlighted_text = highlight.toString().trim();
            let filter_word_button = document.getElementById('filter_word_button');
            if (highlighted_text.length > 0 && highlighted_text !== last_text && highlight.type == 'Range') {
                if (~highlighted_text.indexOf(' '))
                    filter_word_button.disabled = true;
                else if (filter_word_button.disabled)
                    filter_word_button.disabled = false;                
                menu.style = 'position: absolute; left:' + (highlighter.posX ) + 'px; top: ' + (highlighter.posY - 35) + 'px';
                last_text = highlighted_text
            }
            else {
                last_text = null;
                menu.style = 'display: none';
            }
        }, { once: true });
    } else if (menu.style !== 'display: none' && !['filter_word_button', 'filter_term_button'].includes(e.target.id) && !['filter_word_button', 'filter_term_button'].includes(e.target.parentElement.id)) {
        menu.style = 'display: none';
        last_text = null;
    }
});