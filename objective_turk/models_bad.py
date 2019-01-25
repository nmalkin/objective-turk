from datetime import date, datetime
import enum
import json
from typing import Dict

import peewee
import playhouse.sqlite_ext as peewee_sqlite

import mturk

CASCADE = 'CASCADE'

database = peewee_sqlite.SqliteExtDatabase(None)
database.init('turk.db', pragmas={'foreign_keys': 1})


class Environment(enum.Enum):
    sandbox = 'sandbox'
    production = 'production'


class SerializableJSONField(peewee_sqlite.JSONField):
    @staticmethod
    def serialize_dates(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    def db_value(self, value):
        if value is not None:
            return json.dumps(value, default=self.serialize_dates)


class MTurk:
    def init(self, env: Environment):
        self._environment = env
        self._client = None

    @property
    def client(self):
        """
        Get the client that connects to the MTurk API.
        Initializes it if that hasn't happened yet.
        Uses the sandbox if the --debug flag was set.
        """

        if self._environment is None:
            raise Exception('environment not initialized yet. Please call `init`.')

        if self._client is None:
            sandbox = self._environment is Environment.sandbox
            self._client = mturk.get_client(sandbox)

        return self._client

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
                cls.client.list_qualification_types,
                'QualificationTypes',
                MustBeOwnedByCaller=True,
                MustBeRequestable=False,
            ):
                cls.insert(
                    id=qualification_type['QualificationTypeId'],
                    details=qualification_type,
                ).on_conflict_replace().execute()

    class Qualification(BaseModel):
        """
        The Qualification data structure represents a Qualification assigned to a user, including the Qualification type and the value (score).

        http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationDataStructureArticle.html
        """

        qualification_type = peewee.ForeignKeyField(
            MTurk.QualificationType,
            on_delete=CASCADE,
            backref='qualifications',
            column_name='QualificationTypeId',
        )
        worker = peewee.ForeignKeyField(
            MTurk.Worker,
            on_delete=CASCADE,
            backref='qualifications',
            column_name='WorkerId',
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
        def download(cls, qualification_type: MTurk.QualificationType):
            for qualification in mturk.get_pages(
                cls.client.list_workers_with_qualification_type,
                'Qualifications',
                QualificationTypeId=qualification_type.id,
            ):
                cls.insert(
                    qualification_id=qualification['QualificationTypeId'],
                    worker=MTurk.Worker.get_or_create(id=qualification['WorkerId'])[0],
                    GrantTime=qualification['GrantTime'].isoformat(),
                    Status=qualification['Status'],
                    details=qualification,
                ).on_conflict_replace().execute()

    class Hit(BaseModel):
        """
        http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_HITDataStructureArticle.html
        """

        id = peewee.CharField(max_length=256, primary_key=True, column_name='HITId')
        details = SerializableJSONField()

    class Assignment(BaseModel):
        """
        https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_AssignmentDataStructureArticle.html
        """

        id = peewee.CharField(
            max_length=256, primary_key=True, column_name='AssignmentId'
        )
        worker = peewee.ForeignKeyField(
            MTurk.Worker,
            on_delete=CASCADE,
            backref='assignments',
            column_name='WorkerId',
        )
        hit = peewee.ForeignKeyField(
            MTurk.Hit, on_delete=CASCADE, backref='assignments', column_name='HITId'
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

    def create_db(self):
        database.create_tables(
            [
                MTurk.Worker,
                MTurk.QualificationType,
                MTurk.Qualification,
                MTurk.Hit,
                MTurk.Assignment,
            ]
        )
