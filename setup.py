from setuptools import setup

setup(
    author="Sietse Snel, Ton Smeele",
    author_email="s.t.snel@uu.nl, a.p.m.smeele@uu.nl",
    description=('Client-side tools for Yoda / iRODS'),
    install_requires=[
        'python-irodsclient==1.1.1',
        'enum34',
        'six',
        'humanize>=0.5',
        'dnspython>=2.2.0',
        'backports.functools-lru-cache>=1.6.4'
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
            'ygrepgroups=yclienttools.grepgroups:entry',
            'ygroupinfo=yclienttools.groupinfo:entry',
            'yimportgroups=yclienttools.importgroups:entry',
            'yensuremembers=yclienttools.ensuremembers:entry',
            'yrmusers=yclienttools.rmusers:entry'
        ]
    },
    version='0.0.1'
)
