import logging

import objective_turk

logger = logging.getLogger(__name__)


EXTERNAL_URL_QUESTION = """<?xml version="1.0"?>
<ExternalQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd">
    <ExternalURL>{}</ExternalURL>
    <FrameHeight>600</FrameHeight>
</ExternalQuestion>
"""


def get_external_question(url: str):
    """
    Return a Question string for an External URL HIT pointing to the given URL.
    """
    return EXTERNAL_URL_QUESTION.format(url)


class BuiltinQualificationType:
    """
    An Enum for QualificationTypeId constants
    https://github.com/nmalkin/mturk-python/blob/master/mturk/mturk.py#L16
    """

    P_SUBMITTED = "00000000000000000000"
    P_ABANDONED = "00000000000000000070"
    P_RETURNED = "000000000000000000E0"
    P_APPROVED = "000000000000000000L0"
    P_REJECTED = "000000000000000000S0"
    N_APPROVED = "00000000000000000040"
    LOCALE = "00000000000000000071"
    ADULT = "00000000000000000060"
    S_MASTERS = "2ARFPLSP75KLA8M8DH1HTEQVJT3SY6"
    MASTERS = "2F1QJWKUDD8XADTFD2Q0G6UTO95ALH"
    S_CATMASTERS = "2F1KVCNHMVHV8E9PBUB2A4J79LU20F"
    CATMASTERS = "2NDP2L92HECWY8NS8H3CK0CP5L9GHO"
    S_PHOTOMASTERS = "2TGBB6BFMFFOM08IBMAFGGESC1UWJX"
    PHOTOMASTERS = "21VZU98JHSTLZ5BPP4A9NOBJEK3DPG"


MINIMUM_PERCENTAGE_APPROVED = 95


def get_qualifications(exclude: str = None, include: str = None):
    qualifications = [
        {
            'QualificationTypeId': BuiltinQualificationType.LOCALE,
            'Comparator': 'EqualTo',
            'LocaleValues': [{'Country': 'US'}],
            'RequiredToPreview': True,
        },
        {
            'QualificationTypeId': BuiltinQualificationType.P_APPROVED,
            'Comparator': 'GreaterThan',
            'IntegerValues': [MINIMUM_PERCENTAGE_APPROVED],
            'RequiredToPreview': True,
        },
    ]

    if exclude is not None:
        for qualification_id in exclude:
            logging.debug('excluding workers with qualification %s', qualification_id)
            qualifications.append(
                {
                    'QualificationTypeId': qualification_id,
                    'Comparator': 'DoesNotExist',
                    'RequiredToPreview': True,
                }
            )

    if include is not None:
        for qualification_id in include:
            logging.debug(
                'allowing only workers with qualification %s', qualification_id
            )
            qualifications.append(
                {
                    'QualificationTypeId': qualification_id,
                    'Comparator': 'Exists',
                    'RequiredToPreview': True,
                }
            )

    return qualifications


def create_hit_with_hit_type(hit_type: str, **kwargs):
    """
    Create HIT using provided HITTypeId %s.

    You still need to pass 'LifetimeInSeconds', 'MaxAssignments', 'Question'.
    Title, Description, Reward, and Keywords from calling script will be ignored.
    """
    logger.info(
        'creating HIT using HITTypeId %s. Title, Description, Reward, and Keywords from calling script will be ignored.',
        hit_type,
    )
    new_args = {
        arg: kwargs[arg] for arg in ['LifetimeInSeconds', 'MaxAssignments', 'Question']
    }
    new_args.update(HITTypeId=hit_type)
    response = objective_turk.client().create_hit_with_hit_type(**new_args)
    logger.debug(response)
    #pylint: disable=protected-access
    return objective_turk.Hit._new_from_response(response['HIT'])


def create_hit(**kwargs):
    """
    Create a HIT with the given arguments.
    
    For arguments, see:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html#MTurk.Client.create_hit
    """
    response = objective_turk.client().create_hit(**kwargs)
    logger.debug(response)
    #pylint: disable=protected-access
    return objective_turk.Hit._new_from_response(response['HIT'])
