import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_config.settings')
django.setup()

from interfaces.vagas_interface.models import Company, Listing
from modules.utils import filter_listing
from unidecode import unidecode
from re import sub


# vagas = Listing.objects.all()

# for vaga in vagas:
#     if not filter_listing(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(vaga.title).lower()), vaga.location, vaga.workplace_type):
#         print(vaga.title)
#         vaga.delete()


empresas = Company.objects.all()

for empresa in empresas:
    if 'vagas.com' in empresa.platforms:
        del empresa.platforms['vagas.com']
        empresa.platforms['vagas_com'] = {
            'id': None,
            'name': None,
            'last_check': None
        }
        empresa.save()