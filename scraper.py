from json import load
import modules.burh as burh
import modules.linkedin as linkedin
import modules.glassdoor as glassdoor
import modules.indeed as indeed
from modules.utils import initialize_puppet


def main():
    env = load(open('config.json', 'r', encoding='utf-8'))
    linkedin.get_jobs(env)
    # linkedin = puppet
    # glassdoor = puppet
    # indeed = puppet
    # burh = https://api-v2.burh.com.br/api/company/career/[empresa]/jobs?page=[pagina]



if __name__ == '__main__':
    main()