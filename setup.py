from setuptools import setup

setup(
    author="Utrecht University Yoda team",
    author_email="yoda@uu.nl",
    description=('Client-side tools for Yoda / iRODS'),
    install_requires=[
        'python-irodsclient==3.0.0',
        'enum34',
        'humanize>=0.5',
        'iteration_utilities==0.11.0',
        'dnspython>=2.2.0',
        'backports.functools-lru-cache>=1.6.4',
        'PyYaml'
    ],
    name='yclienttools',
    packages=['yclienttools'],
    entry_points={
        'console_scripts': [
            'yreport_datapackageinfo= yclienttools.reportdatapackageinfo:entry',
            'yreport_dataobjectspercollection= yclienttools.reportdoc:entry',
            'yreport_datapackagestatus= yclienttools.reportdatapackagestatus:entry',
            'yreport_collectionsize= yclienttools.reportsize:entry',
            'yreport_depositpending= yclienttools.reportdepositpending:entry',
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
    version='1.10.0'
)
