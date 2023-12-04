import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_config.settings')
django.setup()

from json import load
import modules.burh as burh
import modules.linkedin as linkedin
import modules.glassdoor as glassdoor
import modules.indeed as indeed


def main():
    configs = load(open('config.json', 'r', encoding='utf-8'))
    linkedin.get_jobs()
    glassdoor.get_jobs()
    # glassdoor = puppet
    # indeed = puppet
    # burh = https://api-v2.burh.com.br/api/company/career/[empresa]/jobs?page=[pagina]


if __name__ == '__main__':
    main()