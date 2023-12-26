from datetime import timedelta, datetime
from django.utils.timezone import now, make_aware
from django.db.models import Model, JSONField, PositiveIntegerField, TextField, AutoField, BooleanField, ForeignKey, CASCADE


class Company(Model):
    class Meta:
        verbose_name_plural = "companies"

    id: AutoField = AutoField(primary_key=True)
    image_url: TextField = TextField(null=True)
    employee_count: PositiveIntegerField = PositiveIntegerField(null=True)
    followed: BooleanField = BooleanField(default=False)

    def get_default_platforms(self) -> dict:
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
            },
            'catho': {
                'id': None,
                'name': None,
                'last_check': None
            },
            'vagas_com': {
                'id': None,
                'name': None,
                'last_check': None
            }
        }

    platforms: JSONField = JSONField(default=get_default_platforms)

    def checked_recently(self, platform) -> bool:
        # pylint: disable=E1136
        return now() < make_aware(datetime.strptime(self.platforms[platform]['last_check'], '%Y-%m-%dT%H:%M:%S')) + timedelta(days=1) \
            if self.platforms[platform]['last_check'] else False

    def __str__(self) -> str:
        return f'{{\n"id": "{self.id}"\n"image": "{self.image_url}",\n"employee_count": {self.employee_count},\n"followed": {self.followed},\n"platforms": {self.platforms}}}'


class Listing(Model):
    class Meta:
        verbose_name_plural = "listings"

    id: AutoField = AutoField(primary_key=True)
    title: TextField = TextField()
    location: TextField = TextField()
    workplace_type: TextField = TextField()
    description: TextField = TextField()
    company: ForeignKey = ForeignKey(Company, on_delete=CASCADE)
    platform_id: TextField = TextField()
    platform: TextField = TextField()
    applies: PositiveIntegerField = PositiveIntegerField(null=True)
    application_url: TextField = TextField()
    publication_date: TextField = TextField()

    def __str__(self) -> str:
        return f'{{\n"id": "{self.id}"\n"title": "{self.title}",\n"location": "{self.location}",\n"company": "{self.company.id}",\n"workplace_type": "{self.workplace_type}",\n"platform_id": "{self.platform_id}"\n"platform": "{self.platform}",\n"application_url": "{self.application_url}",\n"description": "{self.description}",\n"applies": "{self.applies}",\n"publication_date": "{self.publication_date}"\n}}'
