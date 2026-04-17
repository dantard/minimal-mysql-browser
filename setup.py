from setuptools import setup, find_packages

setup(
    name='minimal_sqlite_browser',
    version='0.0.7',
    packages=find_packages(where='src'),  # Specify src directory
    package_dir={'': 'src'},  # Tell setuptools that packages are under src
    install_requires=[
        'pyqt5',
        'watchdog',
    ],
    author='Danilo Tardioli',
    author_email='dantard@unizar.es',
    description='A Minimal SQLite Browser',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/dantard/minimal-sqlite-browser',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.10',
    entry_points={
        'console_scripts': [
            'msb=minimal_sql_browser.msb:main',
        ],
    },
)
