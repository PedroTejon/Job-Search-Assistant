# Job Search Assistant
[![pt-br](https://img.shields.io/badge/lang-pt--br-green.svg)](./README.pt-br.md)

A simple Django application developed to assist people currently looking for a job, joining many listing sources in one place. (May get a few more features soon!)

This project's basic front-end was developed using HTML, CSS and JavaScript while the back-end was made with Python, Django and SQLite3 (for a simple data storage solution).

It's sources' integration modules were carefully made by analysing the inner workings between the client and server-side communication (API) on their websites, while implementing data extraction and web scraping techniques to gather the wanted data.
 
Job Search Assistant currently supports these sources:
- **LinkedIn**
- **Glassdoor**
- **Catho**
- **Vagas.com**

<br>

> ⚠️ **Warning**: Although I've implemented precautionary measures to avoid making a lot of requests at the same time and abusing sources' TOS, I'm NOT responsible for anything that happens to you while using this. Use at your own volition.


## How to setup
1. [Download](https://github.com/PedroTejon/Job-Search-Assistant/archive/refs/heads/main.zip) or clone this repository to a folder of your choice.
2. Open a terminal window on the project folder and run the following commands to install the required Python packages:
```cmd
    pip install -r requirements.txt
    playwright install
```
3. Run the authentication setup script to log-in on the sources with the command:
```cmd
    python auth_setup.py
```
4. Finally, start the application at http://localhost:8000 by running:
```cmd
    python manage.py runserver
```

## Features

**Get your freshest job listings**: After accessing the web application, click on the plus sign in the top right corner of the screen to get your latest batch of job listings!
<img src="./docs/start_extraction.gif" />

**Exclude listings with certain properties**: If you are getting job listings related to stuff you have no interest in, you can forbid certain listings from being chosen in the future by highlighting unique words or terms(strings of characters that may contain multiple words or may even be found inside another word, if you're not careful) on the listing's title, and choosing your option on the menu that pops up. 
<img src="./docs/forbidding_listings.gif" />

You can also forbid listings from those spammy companies by highlighting their name with this feature!
<img src="./docs/forbidding_companies.gif" />

**Query through your listings database**: After using this app for some time, you may accumulate so many listings that it may become hard to navigate and find the one you're looking for, so you can use our querying options to find it for you amidst the sea of listings! 
<img src="./docs/querying_listings.gif" />

You may also mark listings as "Applied to" or "Dismissed", using the checkmark and x buttons to the right of the "Apply" button, to help distinguish them!

## Planned features (To-Do)
[X] Listings extraction (LinkedIn, Glassdoor, Catho and Vagas.com)
[X] Simple GUI with Django
[ ] Add support to more sources
[ ] Dashboard for more stats related to your job search journey (based on listings in database)
[ ] Make an ease-of-use curriculum generator that also updates automatically your info on supported websites after changes