import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    author='John Jung',
    author_email='jej@uchicago.edu',
    description='Scripts to convert metadata to and from different formats.',
    entry_points={
        'console_scripts': [
            'marc2dc = metadata_converters.marc2dc:main',
            'marc2schemadotorg = metadata_converters.marc2schemadotorg:main'
        ]
    },
    install_requires=[
        'docopt'
    ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    name='Metadata Converters',
    packages=setuptools.find_packages(),
    package_dir='metadata_converters',
    package_data={
        'json': ['socscimaps_marc2dc.json']
    },
    url='https://github.com/johnjung/metadata_converters',
    version='0.0.1'
)
