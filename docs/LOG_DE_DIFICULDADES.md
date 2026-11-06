# Log de dificuldades e decisões técnicas

Roteiro para o vídeo de apresentação do Campus Eventos. Cada item traz o problema, a decisão tomada, onde ela está no código e o que mostrar na tela. Os itens estão na ordem sugerida para a apresentação.

## Resumo em uma frase por item

| # | Dificuldade | Decisão |
|---|---|---|
| 1 | Modelar a relação entre pessoas e eventos | `Inscricao` como tabela própria, com unicidade no banco |
| 2 | Bloquear visitantes e também quem está logado sem ser o dono | Duas camadas: login e verificação do organizador |
| 3 | Erro 405 depois do login | A rota de inscrição trata o GET com um redirecionamento |
| 4 | Duas pessoas disputando a última vaga | Transação com trava de escrita no início |
| 5 | Lista sem ordem definida depois do `Count` | `order_by` explícito |
| 6 | Contagem errada em "Minhas inscrições" | Contar antes de filtrar |
| 7 | Data e hora no formulário | Formato do navegador e fuso de Porto Velho |
| 8 | Do computador local para a internet | Configuração por `.env`, SQLite e Django 5.2 LTS |

---

## 1. Modelar a relação entre pessoas e eventos

**Problema.** O trabalho pede três tabelas ligadas por chave estrangeira, incluindo o usuário do Django. Só que o usuário tem dois papéis diferentes: ele organiza eventos e também participa deles.

**Decisão.** `Evento` tem uma chave estrangeira `organizador`, e `Inscricao` é uma tabela própria que liga `participante` e `evento`. Ela é própria, e não um simples `ManyToManyField`, porque a inscrição tem dado próprio: a data em que foi feita.

Dois detalhes merecem ser citados:

- **`related_name` diferentes.** Como `Evento` e `Inscricao` apontam para o mesmo usuário, os nomes `eventos_organizados` e `inscricoes` deixam o código legível.
- **`on_delete` escolhido caso a caso.** Apagar um evento apaga as inscrições dele (`CASCADE`), mas uma categoria em uso não pode ser apagada (`PROTECT`), para nenhum evento perder a classificação.

**Onde está:** [eventos/models.py](../eventos/models.py)

**O que mostrar:** o arquivo de models e o painel `/admin/`, abrindo um evento com as inscrições dentro da página.

## 2. Bloquear visitantes e também quem não é o dono

**Problema.** Exigir login não basta. Sem mais nada, qualquer pessoa logada poderia digitar `/eventos/7/excluir/` e apagar o evento de outra pessoa. Esconder o botão também não resolve, porque a rota continua existindo.

**Decisão.** O controle fica no servidor, em duas camadas:

- `LoginRequiredMixin` manda o visitante para o login.
- `OrganizadorRequiredMixin` responde 403 para quem está logado mas não organiza o evento.

O organizador também nunca vem do formulário. Ele sai da sessão, em `form.instance.organizador = self.request.user`. Assim, ninguém publica um evento em nome de outra pessoa alterando o HTML.

**Onde está:** [eventos/views.py](../eventos/views.py)

**O que mostrar:** com uma conta, copie a URL de edição de um evento. Entre com outra conta, cole a URL e mostre a página "Acesso negado". Depois repita em uma janela anônima e mostre o redirecionamento para o login.

## 3. O erro 405 depois do login

**Problema.** Inscrever-se altera dados, então a rota aceita só POST. Só que existe um caminho escondido: a pessoa deixa a página aberta, a sessão expira e ela clica em "Quero participar". O Django manda para o login com `next=/eventos/4/inscrever/`. Depois do login, o navegador volta para esse endereço com um **GET**, e a pessoa veria um erro 405 logo depois de entrar.

**Decisão.** A rota responde ao GET redirecionando para a página do evento, sem alterar nada. A pessoa cai no lugar certo e clica de novo no botão.

**Onde está:** `AcaoInscricaoView` em [eventos/views.py](../eventos/views.py)

**O que mostrar:** o método `get` da view e o teste `test_get_nao_inscreve_e_volta_para_o_evento`.

## 4. Duas pessoas disputando a última vaga

**Problema.** A regra parece simples: se há vaga, inscreve. Mas entre o "verificar" e o "inscrever", outro pedido pode passar pelo mesmo ponto. A solução usual é o `select_for_update()`, que trava a linha do banco, porém o SQLite ignora esse comando.

**Decisão.** A verificação e a inscrição ficam na mesma transação, e o banco usa `transaction_mode: IMMEDIATE`, que pega a trava de escrita já no início da transação.

**Como foi testado.** Um script disparou 30 pedidos simultâneos em um evento de 3 vagas, em 5 rodadas (150 pedidos no total):

| Configuração | Inscrições aceitas | Recusas corretas | Erros `database is locked` |
|---|---:|---:|---:|
| Padrão do SQLite (`DEFERRED`) | 5 | 0 | **145** |
| `IMMEDIATE` | **15** (3 por rodada) | 135 | **0** |

O resultado foi diferente do esperado. O medo inicial era vender vagas a mais, mas o que aconteceu no modo padrão foi outra coisa: as transações travaram umas às outras e quase todos os pedidos falharam, o que o usuário veria como erro 500. Com `IMMEDIATE`, os pedidos entram em fila, as vagas são preenchidas exatamente e os demais recebem a mensagem "As vagas deste evento acabaram".

**Onde está:** `DATABASES` em [config/settings.py](../config/settings.py) e `Evento.inscrever` em [eventos/models.py](../eventos/models.py)

**O que mostrar:** a tabela acima e o método `inscrever`.

## 5. A lista sem ordem definida

**Problema.** A listagem de eventos mostra quantos inscritos cada um tem, usando `annotate(Count("inscricoes"))`. Todos os testes passavam, mas a saída mostrava o aviso `UnorderedObjectListWarning`. O `Count` gera um `GROUP BY`, e nesse caso o Django ignora o `ordering` definido no `Meta` do model. Sem ordem definida, a paginação pode repetir ou pular eventos.

**Decisão.** A view chama `order_by("data_inicio")` explicitamente, e um novo teste transforma esse aviso em falha.

**Lição.** Um teste verde não quer dizer que está tudo certo. Foi um aviso no meio da saída que revelou o problema.

**Onde está:** `EventoListView` em [eventos/views.py](../eventos/views.py)

**O que mostrar:** o comentário na view e o teste `test_proximos_eventos_vem_do_mais_proximo_para_o_mais_distante`.

## 6. A contagem errada em "Minhas inscrições"

**Problema.** No Django, a ordem entre `filter()` e `annotate()` muda o resultado. Filtrando primeiro pelo usuário, o `Count` reaproveita o mesmo JOIN já filtrado e enxerga só a inscrição daquele usuário. Todo evento apareceria com 1 inscrito.

**Decisão.** Contar primeiro e filtrar depois: `com_total_inscritos().filter(inscricoes__participante=usuario)`.

**Como foi conferido.** A ordem foi invertida de propósito em uma cópia do projeto, e o teste falhou, o que prova que ele protege contra esse erro.

**Onde está:** `MinhasInscricoesView` em [eventos/views.py](../eventos/views.py)

**O que mostrar:** as duas versões da consulta e o teste `test_minhas_inscricoes_conta_todos_os_inscritos_do_evento`.

## 7. Data e hora no formulário

**Problema.** O campo `datetime-local` do navegador só aceita o formato `2026-11-10T14:30`. O Django, em português, entrega `10/11/2026 14:30`. O resultado é um erro silencioso: ao editar um evento, o campo de data aparece **vazio**. Além disso, o banco guarda os horários em UTC, e Rondônia fica em UTC-4.

**Decisão.** O widget define o formato explicitamente, e o projeto usa `USE_TZ = True` com `TIME_ZONE = "America/Porto_Velho"`. O banco guarda UTC, e a tela sempre mostra o horário local.

**Onde está:** [eventos/forms.py](../eventos/forms.py) e [config/settings.py](../config/settings.py)

**O que mostrar:** crie um evento às 15:45, confira o horário na página e abra a edição para mostrar o campo preenchido.

## 8. Do computador local para a internet

**Problema.** O repositório é público, então a chave secreta não pode estar no código. O site também precisa se comportar de um jeito no computador e de outro no servidor.

**Decisões.**

- **Configuração por `.env`.** Chave secreta, `DEBUG` e endereços permitidos ficam em um arquivo fora do Git, e o `.env.example` documenta o que é necessário.
- **Padrões seguros.** Sem configuração, o `DEBUG` fica desligado, e sem chave o projeto se recusa a iniciar, com uma mensagem explicando o que fazer.
- **SQLite.** Contas gratuitas do PythonAnywhere criadas depois de 15/01/2026 não têm MySQL.
- **Django 5.2 LTS, e não o 6.x.** O computador de desenvolvimento usa Python 3.14, e o PythonAnywhere vai até o 3.13. A versão 5.2 funciona nos dois, enquanto o Django 6 exige Python 3.12 ou mais recente e deixaria de fora as imagens antigas do servidor.
- **Arquivos estáticos.** Com `DEBUG` desligado, o Django não serve CSS. O `collectstatic` reúne os arquivos em `staticfiles/`, e o servidor os entrega diretamente.
- **Sem senha padrão.** O comando `popular_dados` cria uma conta dona dos eventos de exemplo, sem senha utilizável. Nenhuma senha fica publicada no GitHub.

**Onde está:** [config/settings.py](../config/settings.py), [.env.example](../.env.example) e [DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md)

**O que mostrar:** o `.gitignore`, o `.env.example`, a aba **Web** do PythonAnywhere e o site no ar.

---

## Como o projeto foi validado

- **41 testes automatizados** (`python manage.py test`), incluindo o acesso a todas as rotas protegidas sem login.
- **Teste dos próprios testes.** Nove erros foram introduzidos de propósito em uma cópia do projeto, como remover a verificação de dono ou o limite de vagas. Oito foram detectados na hora. O nono, mostrar os inscritos para todos, não causou falha porque o template também faz a verificação. Removendo as duas proteções, o teste falhou.
- **Teste em navegador real.** O fluxo completo foi percorrido no Chrome: cadastro, criação de evento, edição, inscrição, evento lotado, sessão expirada, exclusão e logout, inclusive em tela de celular.
- **Ensaio do deploy.** Os guias foram seguidos em uma cópia limpa: `git clone`, ambiente virtual novo, `.env` de produção, `collectstatic` e o mesmo arquivo WSGI do PythonAnywhere, com `DEBUG` desligado.

## Sugestão de divisão do vídeo

| Parte | Conteúdo | Itens |
|---|---|---|
| Abertura | O que é o sistema e demonstração rápida | |
| Modelagem | Tabelas, chaves estrangeiras e admin | 1 |
| Acesso | Cadastro, login e bloqueios | 2 e 3 |
| Regras e consultas | Vagas, ordem e contagem | 4, 5 e 6 |
| Publicação | Datas, configuração e deploy | 7 e 8 |
| Fechamento | Site no ar e o que o grupo aprendeu | |

Se o tempo for curto, priorize os itens 2, 4 e 8, que têm a demonstração mais clara.
