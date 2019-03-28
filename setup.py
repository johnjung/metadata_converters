import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='metadata_tools',
    version='0.0.1',
    author='John Jung',
    author_email='jej@uchicago.edu',
    description='Scripts to convert metadata to and from different formats.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/johnjung/metadata_tools',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'marc2dc = metadata_tools.marc2dc.main',
            'marc2schemadotorg = metadata_tools.marc2schemadotorg.main'
        ]
    }
)
