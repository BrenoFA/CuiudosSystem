# Deploy no PythonAnywhere

Este guia publica o projeto em `https://SEU-USUARIO.pythonanywhere.com`. Em todos os passos, troque `SEU-USUARIO` pelo seu usuário do PythonAnywhere.

Antes de começar, o código precisa estar no GitHub (veja [GITHUB.md](GITHUB.md)).

## Limites da conta gratuita

Informações conferidas em novembro de 2026 na [documentação do PythonAnywhere](https://help.pythonanywhere.com/pages/FreeAccountsFeatures):

- **O site expira em 1 mês.** Se a avaliação acontecer depois disso, o professor encontra o site fora do ar. Veja o passo 9.
- Contas criadas depois de 15/01/2026 não têm MySQL. Por isso o projeto usa SQLite, que é um arquivo e funciona em qualquer conta.
- São 512 MiB de disco, o suficiente para este projeto.

## 1. Criar a conta

Crie uma conta gratuita em <https://www.pythonanywhere.com/registration/register/beginner/>. O nome de usuário escolhido vira o endereço do site.

## 2. Baixar o código e instalar as dependências

No painel, abra a aba **Consoles** e clique em **Bash**. Execute:

```bash
git clone https://github.com/BrenoFA/CuiudosSystem.git
cd CuiudosSystem
ls /usr/bin/python3.*
```

O último comando mostra as versões de Python disponíveis. Use a mais recente que aparecer, entre 3.10 e 3.13. Os exemplos usam a 3.13:

```bash
mkvirtualenv --python=/usr/bin/python3.13 campus-eventos-venv
pip install -r requirements.txt
```

Ao terminar, o terminal mostra `(campus-eventos-venv)` no início da linha.

## 3. Criar o arquivo `.env` de produção

Este comando gera uma chave secreta nova e cria o arquivo. Troque `SEU-USUARIO` nas duas linhas antes de executar:

```bash
cat > .env <<EOF
DJANGO_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=SEU-USUARIO.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://SEU-USUARIO.pythonanywhere.com
EOF
```

## 4. Preparar o banco e os arquivos estáticos

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py popular_dados
python manage.py createsuperuser
```

O `createsuperuser` pede um usuário e uma senha para o painel administrativo. Use uma senha forte, porque esse painel fica na internet.

## 5. Criar o web app

1. Abra a aba **Web** e clique em **Add a new web app**.
2. Clique em **Next**.
3. Escolha **Manual configuration**. **Não escolha a opção Django**, que serve para projetos novos.
4. Escolha a mesma versão de Python do passo 2 e avance até o fim.

Ainda na aba **Web**, preencha:

| Seção | Campo | Valor |
|---|---|---|
| Code | Source code | `/home/SEU-USUARIO/CuiudosSystem` |
| Code | Working directory | `/home/SEU-USUARIO/CuiudosSystem` |
| Virtualenv | Enter path to a virtualenv | `campus-eventos-venv` |

## 6. Configurar o arquivo WSGI

Na seção **Code**, clique no link do **WSGI configuration file**. O nome é parecido com `/var/www/seu-usuario_pythonanywhere_com_wsgi.py`.

Apague **todo** o conteúdo e cole o texto abaixo, trocando `SEU-USUARIO`:

```python
import os
import sys

path = "/home/SEU-USUARIO/CuiudosSystem"
if path not in sys.path:
    sys.path.insert(0, path)

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

Clique em **Save**. Este é o arquivo que o PythonAnywhere usa, e não o `config/wsgi.py` do projeto.

## 7. Configurar os arquivos estáticos e o HTTPS

Na aba **Web**, seção **Static files**, adicione:

| URL | Directory |
|---|---|
| `/static/` | `/home/SEU-USUARIO/CuiudosSystem/staticfiles` |

Na seção **Security**, ative **Force HTTPS**. Este passo é obrigatório: em produção os cookies de login só trafegam por HTTPS, então quem abrir o site por `http://` não conseguiria entrar.

## 8. Publicar e testar

Clique no botão verde **Reload** no topo da aba **Web** e confira:

- [ ] A página inicial abre com o visual correto e com os eventos de exemplo
- [ ] É possível criar uma conta e entrar
- [ ] É possível criar um evento e se inscrever com outra conta
- [ ] `/admin/` abre com o visual correto e aceita o superusuário
- [ ] Abrir `/meus-eventos/` em uma janela anônima leva para o login

## 9. Manter o site no ar

Na aba **Web**, use o botão que estende a validade do site (**Run until...**). Faça isso perto da data da entrega e confira a data exibida. O PythonAnywhere também avisa por e-mail antes de desativar o site.

## Atualizar o site depois de mudar o código

No computador, envie as mudanças com `git push`. Depois, em um console Bash do PythonAnywhere:

```bash
workon campus-eventos-venv
cd ~/CuiudosSystem
git pull
python manage.py migrate
python manage.py collectstatic --noinput
```

Por fim, clique em **Reload** na aba **Web**. Sem esse clique, o site continua rodando o código antigo.

## Se algo der errado

A aba **Web** tem o link do **Error log**. Leia sempre o fim do arquivo, onde ficam as mensagens mais recentes.

| Sintoma | Causa provável | Solução |
|---|---|---|
| Página "Something went wrong" | Erro ao iniciar o Django | Leia o Error log |
| `ImproperlyConfigured: DJANGO_SECRET_KEY` no log | O `.env` não existe ou está em outra pasta | Refaça o passo 3 dentro de `~/CuiudosSystem` |
| `ModuleNotFoundError: No module named 'django'` | Virtualenv errado | Confira o campo Virtualenv e se a versão de Python é a mesma do passo 2 |
| `ModuleNotFoundError: No module named 'config'` | Caminho errado no WSGI | Confira o `path` do passo 6 |
| Erro 400 (Bad Request) | Endereço fora do `ALLOWED_HOSTS` | Confira `DJANGO_ALLOWED_HOSTS` no `.env` e clique em Reload |
| Site sem visual, ou admin sem CSS | Arquivos estáticos | Refaça o `collectstatic` e confira o mapeamento do passo 7 |
| Erro 403 ao enviar formulários | Verificação CSRF | Confira `DJANGO_CSRF_TRUSTED_ORIGINS`, que precisa começar com `https://` |
| Login não mantém a sessão | Site aberto por `http://` | Ative o Force HTTPS do passo 7 |
| `no such table` | Migrações não executadas | Rode `python manage.py migrate` com o virtualenv ativo |
| Mudança no `.env` sem efeito | O site não foi recarregado | Clique em Reload |
