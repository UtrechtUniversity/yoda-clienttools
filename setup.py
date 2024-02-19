from setuptools import setup

setup(
    author="Utrecht University Yoda team",
    author_email="yoda@uu.nl",
    description=('Client-side tools for Yoda / iRODS'),
    install_requires=[
        'python-irodsclient==2.0.0',
        'enum34',
        'six',
        'humanize>=0.5',
        'iteration_utilities==0.11.0',
        'dnspython>=2.2.0',
        'backports.functools-lru-cache>=1.6.4',
        'PyYaml'
    ],
    name='yclienttools',
    packages=['yclienttools', 'irodsutils'],
    entry_points={
        'console_scripts': [
            'yreport_dataobjectspercollection= yclienttools.reportdoc:entry',
            'yreport_collectionsize= yclienttools.reportsize:entry',
            'yreport_grouplifecycle= yclienttools.reportgrouplifecycle:entry',
            'yreport_intake= yclienttools.reportintake:entry',
            'yreport_linecount= yclienttools.reportlinecount:entry',
            'ycleanup_files= yclienttools.cleanupfiles:entry',
            'ywhichgroups=yclienttools.whichgroups:entry',
            'ygrepgroups=yclienttools.grepgroups:entry',
            'ygroupinfo=yclienttools.groupinfo:entry',
            'yimportgroups=yclienttools.importgroups:entry',
            'yensuremembers=yclienttools.ensuremembers:entry',
            'yrmusers=yclienttools.rmusers:entry',
            'yrmgroups=yclienttools.rmgroups:entry'
        ]
    },
    version='0.0.1'
)
