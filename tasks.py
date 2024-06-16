from invoke import task
import os
import shutil
import venv


if os.name == 'nt':
    python = 'env\\Scripts\\python'
else:
    python = 'env/bin/python'


@task
def clean(c):
    """Remove arquivos gerados durante a build anterior"""
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('cep_consulta.egg-info'):
        shutil.rmtree('cep_consulta.egg-info')
    print("Arquivos de build removidos.")


@task
def build(c):
    """Constrói os pacotes da biblioteca"""
    c.run(f"{python} setup.py build")
    print("Pacotes construídos.")


@task
def upload(c):
    """Faz upload dos pacotes para o PyPI"""
    c.run("twine upload dist/*")
    print("Pacotes enviados para o PyPI.")


@task
def test(c):
    """Executa os testes"""
    c.run("pytest tests")
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
    if os.name == 'nt':
        pip = 'env\\Scripts\\pip'
    else:
        pip = 'env/bin/pip'
    c.run(f"{pip} install -r requirements_dev.txt")
    print("Ambiente virtual criado e dependências instaladas.")


@task(pre=[create_virtualenv])
def setup(c):
    """Configura o ambiente de desenvolvimento"""
    print("Ambiente de desenvolvimento configurado.")
