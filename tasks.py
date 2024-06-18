from invoke import task
import os
import shutil
import venv


if os.name == 'nt':
    path = 'env\\Scripts'
else:
    path = 'env/bin'
path = os.path.join(os.path.split(__file__)[0], path)


@task
def clean(c):
    """Remove arquivos gerados durante a build anterior"""
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('consulta_cep.egg-info'):
        shutil.rmtree('consulta_cep.egg-info')
    print("Arquivos de build removidos.")


@task
def build(c):
    """Constrói os pacotes da biblioteca"""
    print(f"{path}/python setup.py sdist bdist_wheel")
    c.run(f"{path}/python setup.py sdist bdist_wheel")
    print("Pacotes construídos.")


@task
def upload(c):
    """Faz upload dos pacotes para o PyPI"""
    c.run(f"twine upload dist/* --repository-url https://upload.pypi.org/legacy/")
    print("Pacotes enviados para o PyPI.")


@task
def test(c):
    """Executa os testes"""
    c.run(f"{path}/pytest tests")
    print("Testes executados.")


@task
def dist(c):
    """Executa todas as tarefas: clean, build, test e upload"""
    clean(c)
    build(c)
    test(c)
    upload(c)


@task
def create_virtualenv(c):
    """Cria um ambiente virtual e instala as dependências"""
    if os.path.exists('env'):
        shutil.rmtree('env')
    venv.create('env', with_pip=True)
    c.run(f"{path}/pip install -r requirements_dev.txt")
    print("Ambiente virtual criado e dependências instaladas.")


@task(pre=[create_virtualenv])
def setup(c):
    """Configura o ambiente de desenvolvimento"""
    print("Ambiente de desenvolvimento configurado.")
