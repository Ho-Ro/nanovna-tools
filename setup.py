__version__ = '0.1'

import setuptools


# generic data files
data_files=[
    ( 'share/doc/nanovna-tools/', [ 'Changelog', 'README.md', 'LICENSE' ] ),
    ( 'bin/', [ 'nanovna_command', 'nanovna_capture' ] )
]


setuptools.setup(
    name='nanovna-tools',
    version=__version__,
    author='Ho-Ro',
    author_email='horo@localhost',
    url='https://github.com/Ho-Ro/nanovna-tools',
    description='Toolbox for NanoVNA',
    long_description='Small NanoVNA program(s) for scripting and automatisation.',
    license='GPLv3',
    platforms=[ 'all' ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GPLv3',
    ],
    python_requires='>=3.6',
    install_requires=[],
    scripts=[ 'nanovna_command.py', 'nanovna_capture.py', 'nanovna_snp.py',
              'check_s11.py', 'plot_snp.py' ],
    data_files=data_files,
)
