# Como publicar o projeto no GitHub

Execute os comandos no PowerShell, dentro da pasta do projeto. O repositório do grupo é <https://github.com/BrenoFA/CuiudosSystem>.

## 1. Criar o repositório no GitHub

1. Acesse <https://github.com/new>.
2. Em **Repository name**, escreva `CuiudosSystem`.
3. Marque **Public**.
4. Deixe **desmarcadas** as opções de README, `.gitignore` e licença. O projeto já tem esses arquivos, e um repositório que não está vazio faz o `git push` ser recusado.
5. Clique em **Create repository**.

## 2. Identificar seus commits

Só é preciso fazer isso uma vez por computador:

```powershell
git config --global user.name "Seu Nome"
git config --global user.email "seu-email@exemplo.com"
```

## 3. Criar o repositório local e o primeiro commit

```powershell
git init
git add .
git status
```

**Confira a lista antes de continuar.** Os arquivos `.env` e `db.sqlite3` não podem aparecer nela. O repositório é público, e o `.env` guarda a chave secreta.

```powershell
git commit -m "Projeto Campus Eventos: eventos, inscrições e controle de acesso"
```

## 4. Enviar para o GitHub

```powershell
git branch -M main
git remote add origin https://github.com/BrenoFA/CuiudosSystem.git
git push -u origin main
```

Na primeira vez, o Git abre uma janela para você entrar na conta do GitHub.

## 5. Conferir

Abra `https://github.com/BrenoFA/CuiudosSystem`. O README deve aparecer na página inicial, com a imagem do site.

## Enviar alterações depois

```powershell
git add .
git commit -m "Descreva aqui o que mudou"
git push
```

## Problemas comuns

| Mensagem | O que fazer |
|---|---|
| `remote origin already exists` | Execute `git remote set-url origin https://github.com/BrenoFA/CuiudosSystem.git` |
| `failed to push some refs` | O repositório do GitHub não está vazio. Execute `git pull origin main --allow-unrelated-histories --no-rebase`, depois `git push -u origin main` |
| `.env` apareceu no `git status` | Não faça o commit. Confira se o arquivo `.gitignore` está na pasta do projeto |

Se o `.env` for enviado por engano, gere outra chave secreta. Apagar o arquivo depois não basta, porque ele continua no histórico do Git.
