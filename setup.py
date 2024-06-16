# setup.py
from setuptools import setup, find_packages

setup(
    name="consulta_cep",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'consulta-cep=cep_consulta.main:main',
        ],
    },
    author="Andrey Sant'Anna",
    author_email="andreysantanna@gmail.com",
    description="Biblioteca para consulta de endereços a partir de CEP usando serviços variados.",
    long_description=open('readme.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/andreydani/consulta_cep",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
