import enum
import json
from typing import Dict

import boto3
import peewee
import playhouse.sqlite_ext as peewee_sqlite

import mturk


CASCADE = 'CASCADE'

database = peewee_sqlite.SqliteExtDatabase(None)

_environment = None
_client = None


class Environment(enum.Enum):
    sandbox = 'sandbox'
    production = 'production'


def init(env: Environment):
    global _environment
    _environment = env
    # TODO: initialize the database using the current Turk account and environment - these will be part of the filename (or in a metadata table?) so that after you've init'ed, you don't need to worry about which account is being used
    database.init('turk.db', pragmas={'foreign_keys': 1})


def client():
    """
    Get the client that connects to the MTurk API.
    Initializes it if that hasn't happened yet.
    Uses the sandbox if the --debug flag was set.
    """
    global _environment, _client

    if _environment is None:
        raise Exception('environment not initialized yet. Please call `init`.')

    if _client is None:
        sandbox = _environment is Environment.sandbox
        _client = mturk.get_client(sandbox)

    return _client


from datetime import date, datetime


class SerializableJSONField(peewee_sqlite.JSONField):
    @staticmethod
    def serialize_dates(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    def db_value(self, value):
        if value is not None:
            return json.dumps(value, default=self.serialize_dates)


class BaseModel(peewee.Model):
    def __str__(self):
        return self.id

    class Meta:
        database = database


class Worker(BaseModel):
    id = peewee.CharField(max_length=256, primary_key=True, column_name='WorkerId')


class QualificationType(BaseModel):
    """
    http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationTypeDataStructureArticle.html
    """

    id = peewee.CharField(
        max_length=256, primary_key=True, column_name='QualificationTypeId'
    )
    details = SerializableJSONField()

    @classmethod
    def download_all(cls):
        for qualification_type in mturk.get_pages(
            client().list_qualification_types,
            'QualificationTypes',
            MustBeOwnedByCaller=True,
            MustBeRequestable=False,
        ):
            cls.insert(
                id=qualification_type['QualificationTypeId'], details=qualification_type
            ).on_conflict_replace().execute()

        return cls.select()


class Qualification(BaseModel):
    """
    The Qualification data structure represents a Qualification assigned to a user, including the Qualification type and the value (score).

    http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationDataStructureArticle.html
    """

    qualification_type = peewee.ForeignKeyField(
        QualificationType,
        on_delete=CASCADE,
        backref='qualifications',
        column_name='QualificationTypeId',
    )
    worker = peewee.ForeignKeyField(
        Worker, on_delete=CASCADE, backref='qualifications', column_name='WorkerId'
    )
    GrantTime = peewee.CharField(max_length=256)
    Status = peewee.CharField(
        max_length=16, choices=(('Granted', 'Granted'), ('Revoked', 'Revoked'))
    )
    details = SerializableJSONField()

    def __str__(self):
        return 'QualificationTypeId %s granted to %s' % (
            self.qualification_type_id,
            self.worker_id,
        )

    @classmethod
    def download_qualification_type(cls, qualification_type: QualificationType):
        for qualification in mturk.get_pages(
            client().list_workers_with_qualification_type,
            'Qualifications',
            QualificationTypeId=qualification_type.id,
        ):
            cls.insert(
                qualification_id=qualification['QualificationTypeId'],
                worker=Worker.get_or_create(id=qualification['WorkerId'])[0],
                GrantTime=qualification['GrantTime'].isoformat(),
                Status=qualification['Status'],
                details=qualification,
            ).on_conflict_replace().execute()

        return cls.select().where(cls.qualification_type == qualification_type.id)


class Hit(BaseModel):
    """
    http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_HITDataStructureArticle.html
    """

    id = peewee.CharField(max_length=256, primary_key=True, column_name='HITId')
    hit_type = peewee.CharField(max_length=256, column_name='HITTypeId')
    details = SerializableJSONField()

    @classmethod
    def new_from_response(cls, hit):
        id = hit['HITId']
        (
            cls.insert(id=hit['HITId'], hit_type=hit['HITTypeId'], details=hit)
            .on_conflict_replace()
            .execute()
        )
        return cls.get(cls.id == id)

    @classmethod
    def download(cls, hit_id: str):
        response = client().get_hit(HITId=hit_id)
        hit = response['HIT']
        return cls.new_from_response(hit)

    @classmethod
    def download_all(cls):
        for hit in mturk.get_pages(client().list_hits, 'HITs'):
            cls.new_from_response(hit)
        return cls.select()


class Assignment(BaseModel):
    """
    https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_AssignmentDataStructureArticle.html
    """

    id = peewee.CharField(max_length=256, primary_key=True, column_name='AssignmentId')
    worker = peewee.ForeignKeyField(
        Worker, on_delete=CASCADE, backref='assignments', column_name='WorkerId'
    )
    hit = peewee.ForeignKeyField(
        Hit, on_delete=CASCADE, backref='assignments', column_name='HITId'
    )
    AssignmentStatus = peewee.CharField(
        max_length=256,
        choices=(
            ('Submitted', 'Submitted'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
        ),
    )
    details = SerializableJSONField()


def create_db():
    database.create_tables([Worker, QualificationType, Qualification, Hit, Assignment])
