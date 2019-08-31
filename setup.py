from setuptools import setup

setup(name='objective-turk',
      version='0.2.0',
      description="Object-oriented API to help interact with Amazon's Mechanical Turk",
      url='https://github.com/nmalkin/objective-turk',
      author='nmalkin',
      license='BSD',
      packages=['mturk', 'objective_turk'],
      python_requires='>=3.6',
      install_requires=[
          'boto3>=1.5,<2',
          'colorlog>=4.0',
          'peewee>=3.8'
      ],
      scripts=[
          'bin/approve_assignments',
          'bin/assign_qualification',
          'bin/check_balance',
          'bin/create_additional_assignments',
          'bin/create_qualification',
          'bin/delete_qualification',
          'bin/get_column_from_csv',
          'bin/intersect',
          'bin/list_hit_assignments',
          'bin/list_qualification_types',
          'bin/list_workers_with_qualification_type',
          'bin/really_delete_hit',
          'bin/remove_qualification',
          'bin/print_hit_workers',
          'bin/print_submitted_assignments',
          'bin/subtract',
      ])
