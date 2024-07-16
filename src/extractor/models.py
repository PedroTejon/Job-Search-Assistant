from django.db.models import (
    AutoField,
    DateTimeField,
    Model,
    PositiveIntegerField,
    TextField,
)
from django.forms import model_to_dict
from django.utils.timezone import now


class ExtractionLog(Model):
    id: TextField = TextField(primary_key=True)
    platform: TextField = TextField()
    result: TextField = TextField(default='')
    message: TextField = TextField(default='')
    start_time: DateTimeField = DateTimeField(default=now)
    end_time: DateTimeField = DateTimeField(null=True)
    amount_extracted: AutoField = PositiveIntegerField(default=0)

    def __str__(self):
        return str(model_to_dict(self, exclude=['_state']))


class ExtractionFilter(Model):
    id: AutoField = AutoField(primary_key=True)
    category: TextField = TextField()
    value: TextField = TextField()

    def __str__(self):
        return str(model_to_dict(self, exclude=['_state']))
