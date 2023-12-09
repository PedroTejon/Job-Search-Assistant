from django.db import models
from django.utils.timezone import now, make_aware

from datetime import timedelta, datetime


class Company(models.Model):
    id = models.AutoField(primary_key=True)
    image_url = models.TextField(null=True)
    employee_count = models.PositiveIntegerField(null=True)
    followed = models.BooleanField(default=False)

    def get_default_platforms() -> dict:
        return {
            'linkedin': {
                'id': None,
                'name': None,
                'followers': None,
                'last_check': None
            },
            'glassdoor': {
                'id': None,
                'name': None,
                'last_check': None
            }
        }


    platforms = models.JSONField(default=get_default_platforms)


    def checked_recently_ln(self):
        return now() < make_aware(datetime.strptime(self.platforms['linkedin']['last_check'], '%Y-%m-%dT%H:%M:%S')) + timedelta(days=1) \
            if self.platforms['linkedin']['last_check'] else False
    

    def checked_recently__gl(self):
        return now() < make_aware(datetime.strptime(self.platforms['glassdoor']['last_check'], '%Y-%m-%dT%H:%M:%S')) + timedelta(days=1) \
            if self.platforms['glassdoor']['last_check'] else False


    def __str__(self):
        return f'{{\n"id": "{self.id}"\n"image": "{self.image_url}",\n"employee_count": {self.employee_count},\n"followed": {self.followed},\n"platforms": {self.platforms}}}'


class Listing(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.TextField()
    location = models.TextField()
    workplace_type = models.TextField()
    description = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    platform_id = models.TextField()
    platform = models.TextField()
    applies = models.PositiveIntegerField(null=True)
    application_url = models.TextField()
    publication_date = models.TextField()

    def __str__(self):
        return f'{{\n"id": "{self.id}"\n"title": "{self.title}",\n"location": "{self.location}",\n"company": "{self.company.id}",\n"workplace_type": "{self.workplace_type}",\n"platform_id": "{self.platform_id}"\n"platform": "{self.platform}",\n"application_url": "{self.application_url}",\n"description": "{self.description}",\n"applies": "{self.applies}",\n"publication_date": "{self.publication_date}"\n}}'