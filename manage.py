from os import environ
from sys import argv

from django.core.management import execute_from_command_line


def main() -> None:
    environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.django_settings.settings')

    if 'runserver' in argv:
        execute_from_command_line([argv[0], 'makemigrations', 'api', '--verbosity', '0'])
        execute_from_command_line([argv[0], 'migrate', '--verbosity', '0'])
    execute_from_command_line(argv)


if __name__ == '__main__':
    main()
