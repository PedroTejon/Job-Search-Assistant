from datetime import datetime, timedelta
from typing import Self

from django.db.models import (
    CASCADE,
    AutoField,
    BooleanField,
    ForeignKey,
    JSONField,
    Model,
    PositiveIntegerField,
    TextField,
)
from django.utils.timezone import make_aware, now

from modules import PLATFORM_IDS


class Company(Model):
    class Meta:
        verbose_name_plural = 'companies'

    id: AutoField = AutoField(primary_key=True)
    image_url: TextField = TextField(null=True)
    employee_count: PositiveIntegerField = PositiveIntegerField(null=True)
    followed: BooleanField = BooleanField(default=False)

    def __str__(self: Self) -> str:
        return f'{{\n"id": "{self.id}"\n"image": "{self.image_url}",\n"employee_count": {self.employee_count},\n"followed": {self.followed},\n"platforms": {self.platforms}}}'  # noqa: E501

    def get_default_platforms() -> dict:  # type: ignore[misc]
        return {
            platform: {'id': None, 'name': None, 'followers': None, 'last_check': None} for platform in PLATFORM_IDS
        }

    platforms: JSONField = JSONField(default=get_default_platforms)

    def checked_recently(self: Self, platform: str) -> bool:
        return (
            now()
            < make_aware(datetime.strptime(self.platforms[platform]['last_check'], '%Y-%m-%dT%H:%M:%S'))
            + timedelta(days=1)
            if self.platforms[platform]['last_check']
            else False
        )


class Listing(Model):
    class Meta:
        verbose_name_plural = 'listings'

    id: AutoField = AutoField(primary_key=True)
    title: TextField = TextField()
    location: TextField = TextField()
    workplace_type: TextField = TextField()
    description: TextField = TextField()
    company: ForeignKey = ForeignKey(Company, on_delete=CASCADE)
    company_name: TextField = TextField()
    platform_id: TextField = TextField()
    platform: TextField = TextField()
    applies: PositiveIntegerField = PositiveIntegerField(null=True)
    application_url: TextField = TextField()
    publication_date: TextField = TextField()
    applied_to: BooleanField = BooleanField(null=True)
    closed: BooleanField = BooleanField(default=False)

    def __str__(self: Self) -> str:
        return f'{{\n"id": "{self.id}"\n"title": "{self.title}",\n"location": "{self.location}",\n"company": "{self.company.id}",\n"company_name": "{self.company_name}",\n"workplace_type": "{self.workplace_type}",\n"platform_id": "{self.platform_id}"\n"platform": "{self.platform}",\n"application_url": "{self.application_url}",\n"description": "{self.description}",\n"applies": "{self.applies}",\n"publication_date": "{self.publication_date}"\n"applied_to": "{self.applied_to}"\n}}'  # noqa: E501
