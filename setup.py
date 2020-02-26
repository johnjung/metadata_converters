import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    author='John Jung',
    author_email='jej@uchicago.edu',
    description='Scripts to convert metadata to and from different formats.',
    entry_points={
        'console_scripts': [
            'marc2dc = metadata_converters.marc2dc:main',
            'marc2edm = metadata_converters.marc2edm:main',
            'marc2opengraph = metadata_converters.marc2opengraph:main',
            'marc2schemadotorg = metadata_converters.marc2schemadotorg:main',
            'marc2twittercard = metadata_converters.marc2twittercard:main',
            'query_marklogic = metadata_converters.query_marklogic:main',
            'upload_to_marklogic = metadata_converters.upload_to_marklogic:main'
        ]
    },
    install_requires=[
        'docopt'
    ],
    long_description=long_description,
    long_description_content_type='text/markdown',
    name='Metadata Converters',
    packages=setuptools.find_packages(),
    package_data={
        'metadata_converters': ['json/*.json']
    },
    url='https://github.com/johnjung/metadata_converters',
    version='0.0.1'
)
