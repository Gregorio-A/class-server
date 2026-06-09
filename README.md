# class-server v2

Servidor local para compartilhar projetos web em sala de aula com acesso rápido por QR Code.

O foco principal do app é permitir que o professor abra um projeto HTML/CSS/JS no próprio computador e compartilhe esse servidor com os alunos da mesma rede, sem precisar repetir IP, porta, usuário e senha manualmente. O aluno escaneia o QR Code, acessa o projeto pelo navegador e acompanha as alterações em tempo real.

---

## Visão geral

**Live Server Pro v2** é um servidor de desenvolvimento local feito em Python com FastAPI, Uvicorn, WebSocket, Watchdog e QR Code.

Ele serve os arquivos da pasta atual, injeta automaticamente um script de recarregamento nas páginas HTML e permite que vários dispositivos conectados à mesma rede visualizem o projeto durante a aula.

---

## Principal motivo da criação

Em sala de aula, compartilhar um projeto local costuma ser trabalhoso:

* o professor precisa descobrir o IP da máquina;
* precisa escolher uma porta livre;
* precisa explicar o endereço para todos os alunos;
* precisa lidar com erros de digitação;
* precisa atualizar a página manualmente a cada alteração;
* precisa controlar minimamente quem consegue acessar;
* precisa evitar expor o servidor de forma insegura.

Este app resolve esse fluxo com uma ideia simples:

> Rodar o servidor no computador do professor e gerar um QR Code temporário para os alunos acessarem o projeto rapidamente.

Na prática, o QR Code funciona como uma “porta de entrada” para o servidor da aula.

---

## O que o servidor faz

* Serve arquivos estáticos da pasta onde o comando foi executado.
* Abre `index.html` automaticamente quando uma pasta é acessada.
* Bloqueia listagem de diretórios.
* Impede acesso a arquivos fora da pasta raiz do projeto.
* Gera usuário e senha para autenticação HTTP Basic.
* Gera senha aleatória automaticamente quando nenhuma senha é informada.
* Gera token temporário para login por QR Code.
* Cria cookie de autenticação para quem acessa via QR Code.
* Cria um WebSocket seguro por token para live reload.
* Recarrega a página quando arquivos HTML/JS/outros são alterados.
* Atualiza CSS sem recarregar a página inteira.
* Atualiza imagens sem recarregar a página inteira.
* Preserva posição de rolagem após reload.
* Preserva valores de inputs, textareas e selects após reload.
* Ignora pastas pesadas como `node_modules`, `.git`, `.venv`, `dist` e `build`.
* Usa debounce para evitar múltiplos reloads seguidos.
* Gera certificado SSL autoassinado quando roda em HTTPS.
* Cai para HTTP se a criação do certificado falhar.
* No modo HTTP, limita o acesso a `localhost` por segurança.
* Encontra automaticamente uma porta livre quando a porta padrão já está em uso.
* Cria ambiente virtual Python automaticamente.
* Instala dependências automaticamente via `pip`.
* Gera integração opcional com VS Code usando `tasks.json`.
* Salva logs em `live_server.log`.

---

## Uso rápido

```bash
python live_server.py --open
```

Com porta personalizada:

```bash
python live_server.py --port 3000 --open
```

Com usuário e senha definidos:

```bash
python live_server.py --user professor --password aula123 --open
```

---

## Problemas e soluções principais

| Problema                | Causa provável                                       | Solução                                                         |
| ----------------------- | ---------------------------------------------------- | --------------------------------------------------------------- |
| Celular não acessa      | redes diferentes, firewall ou isolamento do roteador | colocar todos na mesma rede e liberar a porta                   |
| Aviso de certificado    | HTTPS autoassinado                                   | aceitar o aviso em ambiente local ou gerar certificado adequado |
| QR Code não aparece     | terminal não renderiza bem                           | usar outro terminal ou copiar a URL manualmente                 |
| WebSocket não recarrega | certificado/firewall/cache                           | escanear o QR novamente e conferir firewall                     |
| Dependências falham     | `pip`, internet ou proxy                             | instalar manualmente com `pip install`                          |
| VS Code task falha      | script fora da raiz do projeto                       | deixar o script na pasta correta ou ajustar `tasks.json`        |

---

## Observações de segurança

* O QR Code dá acesso ao projeto enquanto o servidor estiver rodando.
* O servidor compartilha a pasta atual, então não rode dentro de diretórios com arquivos pessoais.
* Evite manter `.env`, `.key`, `.pem`, bancos locais ou backups dentro da pasta servida.
* O modo HTTP só roda localmente para evitar envio de credenciais sem criptografia pela rede.
* O app é feito para aula e desenvolvimento local, não para produção.

---

## Conclusão técnica

O servidor funciona como uma ponte entre o computador do professor e os dispositivos dos alunos.

Ele resolve o problema prático de compartilhar um projeto local em sala de aula com menos atrito: QR Code, autenticação temporária, live reload e acesso pela rede local.

Não substitui hospedagem real nem deploy em produção. A proposta é ser uma ferramenta rápida, portátil e eficiente para demonstrações, aulas de HTML/CSS/JS, testes em celulares e acompanhamento visual de projetos em tempo real.
