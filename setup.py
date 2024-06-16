# setup.py
from setuptools import setup, find_packages

setup(
    name="cep-consulta",
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
    author="Seu Nome",
    author_email="seuemail@example.com",
    description="Biblioteca para consulta de endereços a partir de CEP usando serviços variados.",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/seuusuario/cep-consulta",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
