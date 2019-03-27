import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='marc_tools',
    version='0.0.1',
    author='John Jung',
    author_email='jej@uchicago.edu',
    description='Scripts to convert MARC data to different formats',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/johnjung/marc_tools',
    packages=setuptools.find_packages()
)
