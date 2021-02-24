from setuptools import setup, find_packages

setup(
    name='releasible',
    version='0',
    description='Release Engineering dashboard for Ansible Core',
    author='Rick Elrod',
    author_email='relrod@redhat.com',
    url='https://github.com/relrod/releasible',
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'arrow',
        'asyncio',
        'gql == 3.0.0a5',
        'requests',
        'staticjinja',
        'unidiff',
    ],
)
