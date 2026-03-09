#!/usr/bin/python
from setuptools import setup
setup(
    name="me_cleaner_thinkpad",
    version="1.3",
    description="me_cleaner fork with hardware-confirmed HAP bit soft-disable for 8th-10th gen Intel ThinkPads (ME 12/14)",
    url="https://https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad",
    author="Nicola Corna",
    author_email="nicola@corna.info",
    license="GPLv3+",
    scripts=['me_cleaner.py'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ]
)
