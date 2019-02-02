import datetime
import enum
import json
import logging
import os
import pathlib
import typing
import xml.etree.ElementTree

import peewee
import playhouse.sqlite_ext as peewee_sqlite

import objective_turk.color_logs
import mturk

CASCADE = "CASCADE"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Environment(enum.Enum):
    sandbox = "sandbox"
    production = "production"


_database: peewee.Database = peewee_sqlite.SqliteExtDatabase(None)
_environment: typing.Optional[Environment] = None
_client = None


def print_production_warning() -> None:
    """
    Warn about running in production
    """
    warning = """
*******************************************************************************
    THIS CLIENT IS RUNNING IN PRODUCTION
*******************************************************************************"""
    logger.warning(warning)


def init(
    env: Environment,
    db_path: typing.Union[str, pathlib.Path, None] = None,
    color_logs: bool = True,
) -> None:
    """
    Initialize the environment by specifying whether you're operating in production or the sandbox.
    This prepares (but doesn't instantiate) the AWS MTurk client and specifies the database to use.
    """
    if color_logs:
        objective_turk.color_logs.color_logs()

    logger.debug("Initializing Objective Turk with %s environment", env.value)
    global _environment
    _environment = env

    if _environment is Environment.production:
        print_production_warning()

    if db_path is None:
        # TODO: maybe take into account the AWS account too
        db_name = f"turk_{_environment.value}.db"
        db_path = pathlib.Path(".") / db_name

    logger.debug("Using database file %s", db_path)

    _database.init(db_path, pragmas={"foreign_keys": 1})


def init_sandbox() -> None:
    """
    Convenience function for initializing in the sandbox environment
    """
    init(Environment.sandbox)


def init_from_env_vars() -> None:
    """
    Initialize using variables from environment variables
    """
    production = os.getenv("TURK_SANDBOX", "").lower() == "false"
    environment = Environment.production if production else Environment.sandbox

    profile = os.getenv("AWS_PROFILE", "turk")
    db_path = pathlib.Path(".") / f"{profile}_{environment.value}.db"
    init(environment, db_path)


class EnvironmentNotInitializedError(Exception):
    """
    An error raised when the environment hasn't been initialized yet
    """

    def __init__(self):
        message = "environment not initialized yet. Please call `init`."
        super().__init__(message)


def client():
    """
    Get the client that connects to the MTurk API.
    Initializes it if that hasn't happened yet.
    Uses the sandbox if the --debug flag was set.
    """
    global _environment, _client

    if _environment is None:
        raise EnvironmentNotInitializedError()

    if _client is None:
        logger.debug("Initializing AWS boto3 client in %s", _environment)
        sandbox: bool = _environment is Environment.sandbox
        _client = mturk.get_client(sandbox)

    return _client


def production_confirmation():
    """
    If in production, show a warning that the user is about to do something impactful
    """
    if _environment is None:
        raise EnvironmentNotInitializedError()
    elif _environment is Environment.production:
        logger.warning("Performing operation with side-effects in production")
        proceed = None
        while proceed not in ["y", "n"]:
            proceed = input("Continue? [y/n]")
        if proceed == "n":
            raise Exception("operation canceled")


class SerializableJSONField(peewee_sqlite.JSONField):
    """
    A JSONField extended to not break when a date or datetime object tries to be serialized
    """

    @staticmethod
    def serialize_dates(obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        raise TypeError("Type %s not serializable" % type(obj))

    # pylint: disable=inconsistent-return-statements
    # This follows the model of peewee_sqlite.JSONField, which also has inconsistent return statements.
    def db_value(self, value):
        if value is not None:
            return json.dumps(value, default=self.serialize_dates)


class BaseModel(peewee.Model):
    """
    The base for all of our MTurk models
    """

    def __str__(self):
        return self.id

    class Meta:
        database = _database


class Worker(BaseModel):
    id = peewee.CharField(max_length=256, primary_key=True, column_name="WorkerId")

    def has_qualification(self, qualification_type: "QualificationType") -> bool:
        """
        Returns true if the given QualificationType has been assigned to the provided worker
        """
        return Qualification.exists(qualification_type, self)


class QualificationType(BaseModel):
    """
    http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationTypeDataStructureArticle.html
    """

    id = peewee.CharField(
        max_length=256, primary_key=True, column_name="QualificationTypeId"
    )
    details = SerializableJSONField()

    def assign(self, worker: Worker, send_notification: bool = False) -> None:
        """
        Associate the current qualification type with the given worker

        See:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html#MTurk.Client.associate_qualification_with_worker
        """
        production_confirmation()
        logger.debug("Assigning qualification to worker %s", worker)

        client().associate_qualification_with_worker(
            QualificationTypeId=self.id,
            WorkerId=worker.id,
            SendNotification=send_notification,
        )

        qualification = client().get_qualification_score(
            QualificationTypeId=self.id, WorkerId=worker.id
        )["Qualification"]
        Qualification.new_from_response(qualification, self)

    def download_qualifications(self) -> None:
        """
        Download all qualifications for this QualificationType
        """
        Qualification.download_qualification_type(self)

    @classmethod
    def _new_from_response(cls, qualification_type: typing.Dict):
        logger.debug(
            "Saving QualificationType %s", qualification_type["QualificationTypeId"]
        )
        return (
            cls.insert(
                id=qualification_type["QualificationTypeId"], details=qualification_type
            )
            .on_conflict_replace()
            .execute()
        )

    @classmethod
    def create_qualification_type(cls, name: str, description: str) -> None:
        """
        Create a new, basic QualificationType
        """
        logger.info("Creating new qualification named %s (%s)", name, description)
        response = client().create_qualification_type(
            Name=name, Description=description, QualificationTypeStatus="Active"
        )
        cls._new_from_response(response["QualificationType"])

    @classmethod
    def download_all(cls) -> None:
        """
        Download all QualificationTypes owned by the current MTurk account
        """
        for qualification_type in mturk.get_pages(
            client().list_qualification_types,
            "QualificationTypes",
            MustBeOwnedByCaller=True,
            MustBeRequestable=False,
        ):
            cls._new_from_response(qualification_type)


class Qualification(BaseModel):
    """
    The Qualification data structure represents a Qualification assigned to a user, including the Qualification type and the value (score).

    http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationDataStructureArticle.html
    """

    qualification_type = peewee.ForeignKeyField(
        QualificationType,
        on_delete=CASCADE,
        backref="qualifications",
        column_name="QualificationTypeId",
    )
    worker = peewee.ForeignKeyField(
        Worker, on_delete=CASCADE, backref="qualifications", column_name="WorkerId"
    )
    GrantTime = peewee.CharField(max_length=256)
    Status = peewee.CharField(
        max_length=16, choices=(("Granted", "Granted"), ("Revoked", "Revoked"))
    )
    details = SerializableJSONField()

    def __str__(self):
        return "QualificationTypeId %s granted to %s" % (
            self.qualification_type_id,
            self.worker_id,
        )

    @classmethod
    def exists(cls, qualification_type: QualificationType, worker: Worker) -> bool:
        """
        Returns true if the given QualificationType has been assigned to the provided worker
        """
        return (
            # Pylint compares about missing database parameter, but that's not required
            # pylint: disable=no-value-for-parameter
            cls.select(
                (Qualification.qualification_type == qualification_type)
                & (Qualification.worker == worker)
            ).count()
            > 0
        )

    @classmethod
    def new_from_response(
        cls, qualification: typing.Dict, qualification_type: QualificationType
    ) -> None:
        logger.debug(
            "Saving Qualification of Worker %s for QualificationType %s",
            qualification["WorkerId"],
            qualification_type.id,
        )
        cls.insert(
            qualification_type=qualification_type,
            worker=Worker.get_or_create(id=qualification["WorkerId"])[0],
            GrantTime=qualification["GrantTime"].isoformat(),
            Status=qualification["Status"],
            details=qualification,
        ).on_conflict_replace().execute()

    @classmethod
    def download_qualification_type(cls, qualification_type: QualificationType):
        """
        Download all qualifications for the given QualificationType
        """
        for qualification in mturk.get_pages(
            client().list_workers_with_qualification_type,
            "Qualifications",
            QualificationTypeId=qualification_type.id,
        ):
            cls.new_from_response(qualification, qualification_type)

        return cls.select().where(cls.qualification_type == qualification_type.id)


TypeHit = typing.TypeVar("TypeHit", bound="Hit")


class Hit(BaseModel):
    """
    http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_HITDataStructureArticle.html
    """

    id = peewee.CharField(max_length=256, primary_key=True, column_name="HITId")
    hit_type = peewee.CharField(max_length=256, column_name="HITTypeId")
    details = SerializableJSONField()

    def __str__(self):
        return f"HIT {self.id} (HITType {self.hit_type}"

    def expire_now(self) -> None:
        """
        Update the current HIT to expire now

        WARNING: the details of the current object (in particular its Expiration)
        will subsequently be out-of-date
        """
        logger.info("Expiring %s", self)
        production_confirmation()

        client().update_expiration_for_hit(
            HITId=self.id, ExpireAt=datetime.datetime.now()
        )
        self.download(self.id)

    @classmethod
    def _new_from_response(cls: typing.Type[TypeHit], hit: typing.Dict) -> TypeHit:
        hit_id = hit["HITId"]
        logger.debug("Saving HIT %s", hit_id)
        (
            cls.insert(id=hit["HITId"], hit_type=hit["HITTypeId"], details=hit)
            .on_conflict_replace()
            .execute()
        )
        return cls.get(cls.id == hit_id)

    @classmethod
    def download(cls, hit_id: str) -> TypeHit:
        """
        Download and return HIT specified by given HITId
        """
        response = client().get_hit(HITId=hit_id)
        hit = response["HIT"]
        return cls._new_from_response(hit)

    @classmethod
    def download_all(cls) -> None:
        """
        Download all HITs known to MTurk

        Remember that MTurk only retains more recent HITs.
        """
        for hit in mturk.get_pages(client().list_hits, "HITs"):
            cls._new_from_response(hit)

    def download_assignments(self) -> None:
        """
        Download all the assignments for the current HIT
        """
        logger.debug("Downloading assignments for Hit %s", self)
        Assignment.download_assignments_for_hit(self)


class Assignment(BaseModel):
    """
    https://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_AssignmentDataStructureArticle.html
    """

    id = peewee.CharField(max_length=256, primary_key=True, column_name="AssignmentId")
    worker = peewee.ForeignKeyField(
        Worker, on_delete=CASCADE, backref="assignments", column_name="WorkerId"
    )
    hit = peewee.ForeignKeyField(
        Hit, on_delete=CASCADE, backref="assignments", column_name="HITId"
    )
    AssignmentStatus = peewee.CharField(
        max_length=256,
        choices=(
            ("Submitted", "Submitted"),
            ("Approved", "Approved"),
            ("Rejected", "Rejected"),
        ),
    )
    details = SerializableJSONField()

    @classmethod
    def download_assignments_for_hit(cls, hit: Hit) -> None:
        """
        Download all the assignments for the given HIT
        """
        for assignment in mturk.get_pages(
            client().list_assignments_for_hit, "Assignments", HITId=hit.id
        ):
            logger.debug("Saving assignment %s", assignment["AssignmentId"])
            worker, _ = Worker.get_or_create(id=assignment["WorkerId"])
            Assignment.insert(
                id=assignment["AssignmentId"],
                worker=worker,
                hit=hit,
                AssignmentStatus=assignment["AssignmentStatus"],
                details=assignment,
            ).on_conflict_replace().execute()

    def __str__(self) -> str:
        return f"Assignment {self.id} by Worker {self.worker} for HIT {self.hit}"

    def approve(self) -> None:
        """
        Approve the current assignment via the MTurk API
        """
        logger.info("Approving %s", self)
        production_confirmation()
        client().approve_assignment(AssignmentId=self.id)

    @property
    def answers(self) -> typing.Dict:
        """
        Return a response's answers as a dictionary object
        """
        answer_xml = self.details["Answer"]
        root = xml.etree.ElementTree.fromstring(answer_xml)

        answer_dict = {}
        for answer in root:
            field = answer.find(
                "{http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd}QuestionIdentifier"
            )
            value = answer.find(
                "{http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd}FreeText"
            )
            if field is not None and value is not None:
                answer_dict[field.text] = value.text

        return answer_dict


def create_db() -> None:
    if _environment is None:
        raise EnvironmentNotInitializedError()

    _database.create_tables([Worker, QualificationType, Qualification, Hit, Assignment])
