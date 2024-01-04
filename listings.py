# pylint: disable=C0413
import os
from queue import Queue

import django

# from json import load
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_config.settings')
django.setup()

from modules.catho import get_jobs as catho
from modules.glassdoor import get_jobs as glassdoor
from modules.linkedin import get_jobs as linkedin
from modules.vagas_com import get_jobs as vagas_com


def main():
    # configs = load(open('config.json', 'r', encoding='utf-8'))
    linkedin(Queue())
    glassdoor(Queue())
    catho(Queue())
    vagas_com(Queue())


if __name__ == '__main__':
    main()
