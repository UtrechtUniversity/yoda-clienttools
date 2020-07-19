from setuptools import setup

setup(
    author="Sietse Snel",
    author_email="s.t.snel@uu.nl",
    description=('Client-side tools for Yoda / iRODS'),
    install_requires=[
        'python-irodsclient',
        'enum34',
        'six',
        'humanize>=0.5'
    ],
    name='yclienttools',
    packages=['yclienttools', 'irodsutils'],
    entry_points={
        'console_scripts': [
            'yreport_dataobjectspercollection= yclienttools.reportdoc:entry',
            'yreport_collectionsize= yclienttools.reportsize:entry',
            'yreport_intake= yclienttools.reportintake:entry',
            'yreport_linecount= yclienttools.reportlinecount:entry',
            'ycleanup_files= yclienttools.cleanupfiles:entry',
            'ywhichgroups=yclienttools.whichgroups:entry',
            'ygrepgroups=yclienttools.grepgroups:entry'
        ]
    },
    version='0.0.1'
)
