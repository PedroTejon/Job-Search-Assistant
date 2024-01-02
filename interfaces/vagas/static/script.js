let current_listing = null
let current_index = 0

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

            listing_status.classList.add('fa-check')
            if (listing_status.classList.contains('fa-x'))
                listing_status.classList.remove('fa-x')
        
            dismiss_button.classList.add('button_disabled')
            if (applied_button.classList.contains('button_disabled'))
                applied_button.classList.remove('button_disabled')
        })
    else
        nullify_listing()
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
            
            listing_status.classList.add('fa-x')
            if (listing_status.classList.contains('fa-check'))
                listing_status.classList.remove('fa-check')

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

            if (listing_status.classList.contains('fa-x'))
                listing_status.classList.remove('fa-x')
            if (listing_status.classList.contains('fa-check'))
                listing_status.classList.remove('fa-check')

            if (applied_button.classList.contains('button_disabled'))
                applied_button.classList.remove('button_disabled')
            if (dismiss_button.classList.contains('button_disabled'))
                dismiss_button.classList.remove('button_disabled')
        })
}

function search(cur_query) {
    let search_value = document.getElementById('search_bar').value.trim();
    let get_new = document.getElementById('query_new').checked
    let get_applied = document.getElementById('query_applied').checked
    let get_dismissed = document.getElementById('query_dismissed').checked
    
    url = `http://localhost:8000/vagas/?page=1&new=${get_new}&applied=${get_applied}&dismissed=${get_dismissed}`;
    if (search_value !== '') {
        if (search_value !== cur_query) 
            url += '&query=' + search_value;
        else (search_value)
            url += '&query=' + cur_query;
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
    if (current_listing.workplace_type == 'Remoto') {
        listing_workplace_type_ico.classList.add('fa-laptop')
        listing_workplace_type_ico.classList.remove('fa-briefcase')
    }
    else {
        listing_workplace_type_ico.classList.add('fa-briefcase')
        listing_workplace_type_ico.classList.remove('fa-laptop')
    }

    let listing_description_det = document.getElementById('listing_description_det');
    if (current_listing.description)
        listing_description_det.innerHTML = current_listing.description;

    let logos = {
        "Glassdoor": "PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iNDguMDAwMDAwcHQiIGhlaWdodD0iNDguMDAwMDAwcHQiIHZpZXdCb3g9IjAgMCA0OC4wMDAwMDAgNDguMDAwMDAwIgogcHJlc2VydmVBc3BlY3RSYXRpbz0ieE1pZFlNaWQgbWVldCI+Cgo8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgwLjAwMDAwMCw0OC4wMDAwMDApIHNjYWxlKDAuMTAwMDAwLC0wLjEwMDAwMCkiCmZpbGw9IiMwMDAwMDAiIHN0cm9rZT0ibm9uZSI+CjxwYXRoIGQ9Ik0yODAgMzYwIGMwIC02IDQgLTEwIDkgLTEwIDE2IDAgNDEgLTMxIDQxIC01MCAwIC0xNCAtOSAtMjAgLTMyIC0yMgotMzAgLTMgLTMzIC02IC0zMyAtMzggMCAtMzQgMSAtMzUgNDMgLTM4IGw0MiAtMyAwIDYzIGMwIDM1IC00IDY4IC04IDczIC0xMQoxNiAtNjIgMzYgLTYyIDI1eiIvPgo8cGF0aCBkPSJNMTMwIDI0MSBjMCAtMzcgMiAtNDEgMjUgLTQxIDE0IDAgMjggLTcgMzIgLTE1IDYgLTE4IC0yMyAtNTUgLTQ0Ci01NSAtNyAwIC0xMyAtNCAtMTMgLTEwIDAgLTE1IDExIC0xMiA0NyAxMCAzNCAyMCA0OCA2MCA0MSAxMTYgLTMgMjYgLTcgMjkKLTQ1IDMyIGwtNDMgMyAwIC00MHoiLz4KPC9nPgo8L3N2Zz4K",
        "LinkedIn": "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGhlaWdodD0iMTYiIHdpZHRoPSIxNCIgdmlld0JveD0iMCAwIDQ0OCA1MTIiPjwhLS0hRm9udCBBd2Vzb21lIEZyZWUgNi41LjEgYnkgQGZvbnRhd2Vzb21lIC0gaHR0cHM6Ly9mb250YXdlc29tZS5jb20gTGljZW5zZSAtIGh0dHBzOi8vZm9udGF3ZXNvbWUuY29tL2xpY2Vuc2UvZnJlZSBDb3B5cmlnaHQgMjAyMyBGb250aWNvbnMsIEluYy4tLT48cGF0aCBvcGFjaXR5PSIxIiBmaWxsPSIjMDAwMDAwIiBkPSJNNDE2IDMySDMxLjlDMTQuMyAzMiAwIDQ2LjUgMCA2NC4zdjM4My40QzAgNDY1LjUgMTQuMyA0ODAgMzEuOSA0ODBINDE2YzE3LjYgMCAzMi0xNC41IDMyLTMyLjNWNjQuM2MwLTE3LjgtMTQuNC0zMi4zLTMyLTMyLjN6TTEzNS40IDQxNkg2OVYyMDIuMmg2Ni41VjQxNnptLTMzLjItMjQzYy0yMS4zIDAtMzguNS0xNy4zLTM4LjUtMzguNVM4MC45IDk2IDEwMi4yIDk2YzIxLjIgMCAzOC41IDE3LjMgMzguNSAzOC41IDAgMjEuMy0xNy4yIDM4LjUtMzguNSAzOC41em0yODIuMSAyNDNoLTY2LjRWMzEyYzAtMjQuOC0uNS01Ni43LTM0LjUtNTYuNy0zNC42IDAtMzkuOSAyNy0zOS45IDU0LjlWNDE2aC02Ni40VjIwMi4yaDYzLjd2MjkuMmguOWM4LjktMTYuOCAzMC42LTM0LjUgNjIuOS0zNC41IDY3LjIgMCA3OS43IDQ0LjMgNzkuNyAxMDEuOVY0MTZ6Ii8+PC9zdmc+",
        "Catho": "PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iMzIuMDAwMDAwcHQiIGhlaWdodD0iMzIuMDAwMDAwcHQiIHZpZXdCb3g9IjAgMCAzMi4wMDAwMDAgMzIuMDAwMDAwIgogcHJlc2VydmVBc3BlY3RSYXRpbz0ieE1pZFlNaWQgbWVldCI+Cgo8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgwLjAwMDAwMCwzMi4wMDAwMDApIHNjYWxlKDAuMTAwMDAwLC0wLjEwMDAwMCkiCmZpbGw9IiMwMDAwMDAiIHN0cm9rZT0ibm9uZSI+CjxwYXRoIGQ9Ik04MCAyNDAgbDcyIC04MCAtNzIgLTgwIC03MiAtODAgODAgMCA4MCAwIDcyIDgwIDcyIDgwIC03MiA4MCAtNzIKODAgLTgwIDAgLTgwIDAgNzIgLTgweiIvPgo8L2c+Cjwvc3ZnPgo=",
        "Vagas.com": "PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiLS8vVzNDLy9EVEQgU1ZHIDIwMDEwOTA0Ly9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAxL1JFQy1TVkctMjAwMTA5MDQvRFREL3N2ZzEwLmR0ZCI+CjxzdmcgdmVyc2lvbj0iMS4wIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiB3aWR0aD0iMTYuMDAwMDAwcHQiIGhlaWdodD0iMTYuMDAwMDAwcHQiIHZpZXdCb3g9IjAgMCAxNi4wMDAwMDAgMTYuMDAwMDAwIgogcHJlc2VydmVBc3BlY3RSYXRpbz0ieE1pZFlNaWQgbWVldCI+Cgo8ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSgwLjAwMDAwMCwxNi4wMDAwMDApIHNjYWxlKDAuMTAwMDAwLC0wLjEwMDAwMCkiCmZpbGw9IiMwMDAwMDAiIHN0cm9rZT0ibm9uZSI+CjxwYXRoIGQ9Ik0zNiAxMjQgYy0yMiAtMjEgLTIwIC02NyAyIC04NyA0MCAtMzYgMTAyIC05IDEwMiA0NSAwIDQ5IC02OSA3OAotMTA0IDQyeiBtMzQgLTMxIGMxMCAtMTcgMTAgLTE3IDIwIDAgNiA5IDE1IDE3IDIwIDE3IDE3IDAgMTEgLTI2IC0xMCAtNTEKbC0yMCAtMjQgLTIwIDI0IGMtMjEgMjUgLTI3IDUxIC0xMCA1MSA1IDAgMTQgLTggMjAgLTE3eiIvPgo8L2c+Cjwvc3ZnPgo="
    }
    let platform_logo = document.getElementById('platform_logo');
    let platform_name = document.getElementById('platform_name');
    let platform_id = document.getElementById('platform_id');
    if (current_listing.platform) {
        platform_logo.src = "data:image/svg+xml;base64," + logos[current_listing.platform];
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
        listing_status.classList.add('fa-check')
        if (listing_status.classList.contains('fa-x'))
            listing_status.classList.remove('fa-x')
    
        dismiss_button.classList.add('button_disabled')
        if (applied_button.classList.contains('button_disabled'))
            applied_button.classList.remove('button_disabled')
    } else if (current_listing.applied_to === false) {
        listing_status.classList.add('fa-x')
        if (listing_status.classList.contains('fa-check'))
            listing_status.classList.remove('fa-check')

        applied_button.classList.add('button_disabled')
        if (dismiss_button.classList.contains('button_disabled'))
            dismiss_button.classList.remove('button_disabled')
    } else {
        if (listing_status.classList.contains('fa-x'))
            listing_status.classList.remove('fa-x')
        if (listing_status.classList.contains('fa-check'))
            listing_status.classList.remove('fa-check')

        if (applied_button.classList.contains('button_disabled'))
            applied_button.classList.remove('button_disabled')
        if (dismiss_button.classList.contains('button_disabled'))
            dismiss_button.classList.remove('button_disabled')
    }
    
}