from setuptools import setup

setup(name='mturk',
      version='0.2.0',
      description="Utilities to help interact with Amazon's Mechanical Turk API",
      url='http://github.com/nmalkin/turk-scripts',
      author='nmalkin',
      license='BSD',
      packages=['mturk', 'objective_turk', 'ot'],
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
