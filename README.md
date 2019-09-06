Objective Turk
================================================================================
This library provides an object-oriented API for Amazon Mechanical Turk operations, written in Python. It has three distinctive features:

1. All major components of the MTurk APIs (Workers, HITs, Assignments, Qualifications) are objects, and you perform operations by calling methods on them.
2. More importantly, the API exposes the relations between objects; for example, you can call `worker_instance.qualifications` to get that worker's qualifications.
3. All data is cached locally in a SQLite database. This allows you to query the relations through the ORM API or directly in SQL, and avoid making (relatively) time-consuming queries to the AWS endpoints.

Under the hood, the library uses Amazon's [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html) and the [Peewee ORM](http://docs.peewee-orm.com/en/latest/) library.


Rationale
---------
You might not want this library. You should first consider using Amazon's [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/mturk.html) library directly, or maybe [some scripts that operate on text files](https://github.com/nmalkin/turk-scripts).

In my case, I found that, as my data grew, the text files got cumbersome to manage and also made it hard to take advantage of the natural relations inherent to the data (e.g., a worker _has_ a qualification, an assignment _belongs_ to a HIT). This library is my solution to that specific need.


Prerequisites
-------------
You'll need to [set up your AWS credentials](https://boto3.readthedocs.io/en/latest/guide/configuration.html).


Installation
-------------
```
pip install git+https://github.com/nmalkin/objective-turk.git
```


Configuration
-------------
There are three main configuration options you need to set before using the library:

1. Are you running in the [Sandbox](https://requestersandbox.mturk.com) or in production?
2. Which AWS account/config are you using?
3. Where will the database file be stored?

You can set these by passing appropriate values to the `objective_turk.init` function, or you can set them using environment variables. The latter is described below.

### Environment
Set `MTURK_PRODUCTION=true` to run in production, otherwise the code will use the sandbox.

### AWS account
Set `AWS_PROFILE=<your-profile-name>` or use one of the alternate AWS configuration methods.

If you have a default profile set up, you can skip this step, but note that this variable is also used to determine the database filename: by default it is `<AWS_PROFILE>_<environment>.db`.

### Path
By default, the database will be stored in the current working directory, but you can change that by setting `MTURK_DB_PATH=<path>`.


Usage
-----
```python
import objective_turk

objective_turk.init()
# TODO
```

### Running in production
The library will ask you to confirm before performing operations with side effects in production. To skip this, you can set `MTURK_NO_CONFIRM=true`
