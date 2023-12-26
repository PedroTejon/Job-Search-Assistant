# pylint: disable=C0413
import os
import django
# from json import load
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_config.settings')
django.setup()
import modules.linkedin as linkedin
import modules.glassdoor as glassdoor
import modules.catho as catho
import modules.vagas_com as vagas_com


def main():
    # configs = load(open('config.json', 'r', encoding='utf-8'))
    linkedin.get_jobs()
    glassdoor.get_jobs()
    catho.get_jobs()
    vagas_com.get_jobs()


if __name__ == '__main__':
    main()
