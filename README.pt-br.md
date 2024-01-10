# Job Search Assistant
[![en](https://img.shields.io/badge/lang-en-blue.svg)](./README.md)

Uma aplicação em Django simples desenvolvida para ajudar pessoas atualmente à procura de trabalho, juntando vagas de diversas fontes de vagas diferentes em um só lugar. (Pode receber mais funções em breve!)

O front-end básico desse projeto foi desenvolvido usando HTML, CSS e JavaScript, enquanto o back-end foi feito com Python, Django e SQLite3 (para uma solução de armazenamento simples).

Seus módulos de integração de fontes foram cuidadosamente feitos ao analisar o funcionamento interno da comunicação entre o lado cliente e servidor (API) dessas fontes, com a implementação de técnicas de extração de dados e web scraping para extrair os dados desejados.
 
Job Search Assistant atualmente tem integração com estas fontes:
- **LinkedIn**
- **Glassdoor**
- **Catho**
- **Vagas.com**

<br>

> ⚠️ **Aviso**: Embora eu tenha implementado medidas de precaução para evitar fazer muitas solicitações e abusar do TOS das fontes, eu NÃO me responsabilizo por qualquer coisa que aconteça com você enquanto usa este aplicativo. Utilize-o ciente disto.


## Como instalar
1. [Baixe](https://github.com/PedroTejon/Job-Search-Assistant/archive/refs/heads/main.zip) ou clone este repositório para um local de sua escolha.
2. Abra uma janela de terminal na pasta do projeto e rode os seguintes comandos para instalar os pacotes Python necessários:
```cmd
    pip install -r requirements.txt
    playwright install
```
3. Rode seguinte comando para executar o script de autenticação e logar nas fontes de vagas desejadas:
```cmd
    python auth_setup.py
```
4. Finalmente, depois de tudo isso, inicie a aplicação em http://localhost:8000 ao rodar:
```cmd
    python manage.py runserver
```

## Funcionalidades

**Obtenha as vagas mais fresquinhas**: Após acessar a aplicação web, clique no símbolo de mais no canto superior direito da tela para receber sua encomenda de vagas recentes!

<img src="./docs/start_extraction.gif" />

---
<br>

**Exclua vagas com certas características**: Se você está recebendo vagas relacionadas a coisas que você não possui interesse, você pode proibir certas vagas de serem recebidas no futuro ao selecionar palavras únicas no título ou termos (cadeias de caracteres que podem conter várias palavras ou que pode até ser encontrada dentro de outras palavras, se você não tomar cuidado) no título da vaga, e escolhendo qual opção você quer no menu que aparecerá.

<img src="./docs/forbidding_listings.gif" />

Você também pode proibir vagas daquelas empresas que ficam spammando seu LinkedIn ao selecionar o nome delas com essa funcionalidade!

<img src="./docs/forbidding_companies.gif" />

---
<br>

**Consulte as vagas locais**: Após usar esse aplicativo por um tempo, você pode acabar acumulando tantas vagas que pode acabar ficando difícil navegar e encontrar a vaga certa para você, então você pode usar nossas opções de consulta para encontrá-la nesse mar de vagas!

<img src="./docs/querying_listings.gif" />

Você também pode marcar vagas como "Inscrito" e "Dispensada", usando os botões à direita do botão de "Cadastre-se", para ajudar a diferenciá-las!

## Funcionalidades planejadas (To-Do)
- [x] Extração de vagas (LinkedIn, Glassdoor, Catho and Vagas.com)
- [x] GUI simples com Django
- [ ] Adicionar suporte para mais fontes
- [ ] Dashboard para visualizar mais estatísticas de sua jornada procurando emprego (com base nas vagas no banco de dados)
- [ ] Fazer um gerador de currículo simples de se usar que também atualiza automaticamente suas informações em sites suportados após mudanças