# A2 Connect — implementação incremental

Estado em 19/10/2026: **código de preview, ainda não homologado no Windows**.
Os binários anteriores, as configurações da raiz e o servidor existente não foram alterados.
O responsável confirmou disponibilidade de Windows para testes; o certificado SSL.com será adquirido.

## O que foi implementado nesta etapa

| Entrega | Estado |
| --- | --- |
| Análise do RDGen e RustDesk 1.4.9 | Documentada em `docs/ANALISE.md` |
| Política compartilhada de build | `profiles.py`, integrada ao workflow Windows |
| Aprovação por clique no primeiro uso | Mantida, inclusive no preview de acesso permanente |
| Credencial individual, renovação e revogação | Patch opt-in da tela Segurança, via IPC nativo; requer compilação e testes |
| Instalação e serviço Windows | Mecanismo nativo reaproveitado; instalação anterior ao assistente; teste de login/logout/reboot pendente |
| Assinatura EXE/MSI e bloqueio de produção | Scripts e gate preparados; certificado e execução Windows pendentes |
| Manifesto destacado assinado e preparação de MSI | Parser/CMS validados em CI; ensaio com pacote real pendente |
| Instalação automática, monitor de sessões, rollback | **Não implementados; nenhum agendamento criado** |
| Atualização portátil | Não implementada; EXE existente preservado |
| Atualização do ConnectAdmin macOS | Não implementada; DMGs e workflow existentes preservados |
| Inventário | Coletor local somente leitura; backend proposto separadamente |

Não considerar o atualizador concluído: `Stage-A2Update.ps1` apenas baixa e prepara um MSI,
não o instala. Não existe ainda prova de preservação do ID ou da senha em upgrade.
Não há publicação de `/updates/` nesta etapa.

## Gerar o preview

No workflow **Custom Windows Client Generator**, usar:

- `version`: `1.4.9` (tag upstream já utilizada).
- `profile`: `client`.
- `unattended_controls`: `true`.
- `production`: `false`.

O build continua usando os secrets A2 existentes (configuração, ícone e logo).
O nome do aplicativo continua sendo **Connect**, para não criar outro namespace de identidade.
Os artefatos passam a ser identificados como `preview-Connect-windows-...`.
Não habilitar o acesso permanente por meio de uma senha global no JSON de build.

O assistente fica em **Configurações → Segurança → Acesso não supervisionado**.
Para o perfil client, substitui os controles genéricos de senha por habilitação,
renovação e revogação. Exige instalação prévia, serviço Connect em execução,
consentimento e verificação administrativa do Windows em cada ação. A autorização
nativa fica em HKLM, com escrita restrita a Administradores/SYSTEM e leitura para
usuários autenticados, vinculada à identidade desta máquina e ao executável do
serviço Connect em execução. Preferências importadas não habilitam acesso por senha.
A habilitação configura início automático sem parar/reiniciar o serviço existente.
Na primeira migração, o assistente permite preservar uma credencial local existente
após novo consentimento administrativo, sem renová-la.
A instalação do serviço continua no fluxo nativo **Instalar**; esta etapa ainda
não reúne instalação e habilitação em um único botão.

O novo assistente usa `mainSetPermanentPasswordWithResult` por IPC. Não chama
`--password`, não grava a credencial em script, arquivo, log, clipboard ou argumento.
A senha aleatória de 192 bits é apresentada uma vez para armazenamento no cofre
autorizado. O armazenamento interno continua sendo o do RustDesk; proteção local
e migração desse armazenamento ainda precisam ser verificadas no ambiente real.
Não foi criada uma camada própria de DPAPI.

Revogar restaura aprovação por clique e remove a senha permanente. Não remove o
serviço nem encerra a sessão atual. Remoção do serviço é uma ação separada de
manutenção, conforme `docs/TESTES-E-OPERACAO.md`.

## Produção

`production=true` exige EXE e MSI com Authenticode válido, timestamp, EKU de code
signing e certificado/publicador fixados em variáveis do repositório:

- `A2_SIGNER_SHA256`: SHA-256 dos bytes DER do certificado, 64 hexadecimais.
- `A2_PUBLISHER_SUBJECT`: Subject completo e exato do certificado emitido à A2.
- `A2_UNATTENDED_APPROVED=true`: somente após homologação do preview no Windows.

O valor do Subject deve vir do certificado real; não inventar a representação
da razão social. Pins são públicos; chaves privadas, tokens e senhas não devem
ser versionados. A rotação de certificado exige novo trust bundle aprovado.

O serviço de assinatura já utilizado pelo RDGen foi mantido. O gate verifica os
arquivos finais e rejeita produção mesmo quando as etapas antigas de assinatura
usam fallback sem assinatura. Artefatos preview nunca devem ser promovidos
diretamente ao canal de produção. A flag `production` prepara/verifica o artefato;
não publica automaticamente um endpoint A2.

Para assinatura via certificado do Windows/KSP, há `Sign-A2Artifacts.ps1`.
Ele usa SignTool com SHA-256 e timestamp RFC3161 HTTPS. O certificado SSL.com OV
requer integração com o método de custódia contratado (token/HSM/KSP ou eSigner).
Não há integração eSigner pronta nem credenciais de assinatura nesta entrega.

## Manifesto e canais

Preparação: `windows/New-A2Release.ps1`. Verifica assinatura, identidade MSI,
arquitetura e versão, assina os bytes UTF-8 do JSON com CMS/PKCS#7 destacado
SHA-256 e gera um diretório novo com `manifest.json`, `manifest.json.p7s` e MSI.
A chave do manifesto pode ser separada da assinatura de código, com pin próprio.
O certificado de manifesto precisa ser confiável no Windows dos clientes.

Estrutura planejada:

```text
/updates/Connect/stable/windows/x86_64/
/updates/Connect/beta/windows/x86_64/
/updates/Connect/server/windows/x86_64/
/updates/ConnectAdmin/stable/windows/aarch64/
```

Cada combinação produto/canal/plataforma/arquitetura é isolada. Publicar primeiro
artefatos imutáveis e promover o manifesto e a assinatura como um conjunto
atômico no servidor; não sobrescrever arquivos de versões anteriores.
O manifesto vence em 14 dias; renovação exige nova sequência crescente, mesmo
sem alteração do pacote. O arquivo exato assinado não pode ser reformatado.

`Stage-A2Update.ps1` exige Windows PowerShell 5.1 elevado. Recebe pins confiáveis
do administrador, nunca do manifesto, e rejeita redirects, URLs fora do domínio
A2, versões antigas, sequência repetida, manifesto vencido, produto/arquitetura
errados, hash/tamanho diferentes, MSI sem assinatura ou publicador inesperado.
Confere a versão/arquitetura dentro do MSI assinado, não apenas o nome do arquivo.
Mantém estado de sequência e log de preparação sob ACL de Administradores/SYSTEM.
O estado indica **preparado**, nunca **instalado**.

Não executar este script como tarefa SYSTEM antes de homologar downloads,
limites de recursos, permissões e comportamento de falhas no Windows.
O download tem limite durante streaming (64 KiB para manifesto/assinatura,
tamanho assinado para o MSI), timeout de rede e duração máxima de 10 minutos.
O fluxo completo de rede ainda depende de ensaio com o endpoint A2 real.

## Próxima etapa do atualizador

1. Implementar política local autorizada, não alterável pelo manifesto: opt-in,
   canal, tipo de dispositivo, janela de manutenção, tratamento de portátil.
2. Integrar intertravamento no RustDesk para bloquear novas sessões e reservar
   uma janela sem conexões ativas. Verificar apenas um processo ou contar
   sessões uma vez não elimina a corrida; não usar essa aproximação.
3. Criar transação de upgrade com cópia protegida das configurações de usuário
   e SYSTEM, identidade MSI estável, pacote anterior assinado e backup íntegro.
4. Executar MSI com `/norestart REBOOT=ReallySuppress`, confirmar serviço,
   ID/servidor/credenciais/permissões e reverter em caso de falha.
5. Provar recuperação após falha de instalação e energia. Retornar código
   3010 como reinício pendente para o administrador; nunca reiniciar sozinho.
6. Só então agendar verificação automática e liberar stable/server.

Servidor e máquina crítica recebem somente preparação por padrão. Uma janela
administrativa futura não autoriza encerrar uma conexão ativa. Rollback nunca
pode depender de baixar um RustDesk oficial genérico.

## Verificação

Na pasta `rdgen-source`:

```sh
python3 -m unittest discover -s a2/tests -v
```

Teste de aplicação do patch com fonte upstream local:

```sh
A2_UPSTREAM_SETTINGS=/caminho/desktop_setting_page.dart python3 -m unittest discover -s a2/tests -v
```

Há workflow separado **A2 policy and update trust validation**, incluindo parser
PowerShell, CMS e downloads com limite de tamanho no Windows. A
[execução Windows/Linux](https://github.com/a2solucoesemti/rdgen/actions/runs/39272258641)
passou com 7 testes de perfil e 23 casos negativos, além de CMS válido, download
válido, ACLs e parser Dart. A
[análise de tipos da interface](https://github.com/a2solucoesemti/rdgen/actions/runs/39272963373)
também passou com os bindings gerados pelo projeto. Assinatura com certificado
A2 real continua pendente. Os testes criptográficos criam e removem um
certificado temporário somente no runner de CI isolado, nunca nos clientes.

O [roteiro da equipe](docs/ROTEIRO-EQUIPE.md), o plano de testes completo e a
arquitetura de inventário estão em `docs/`. A homologação será executada pela
equipe no Windows de testes, conforme definido pelo responsável.

## Cliente portátil e ícones Windows (30/10/2026)

O perfil cliente inicia o atendimento ao abrir o portátil, sem instalar serviço
Windows ou conceder acesso permanente. A rotina é executada uma vez ao abrir a
página inicial e é bloqueada para instalações existentes. Se a inicialização
falhar, o rodapé mantém o erro; não apresenta estado Pronto fictício.

Os recursos de ícone do cliente ficam em `.github/assets/connect/windows/`.
O carregamento Windows da bandeja usa o ICO próprio para pequenos tamanhos,
em vez de reduzir o PNG grande do aplicativo. ConnectAdmin mantém seus recursos
anteriores. Mudanças em fontes/assets só aparecem em novos EXE/MSI compilados.

### Identidade dos ícones e SmartScreen

A fonte visual autoritativa é o último PNG enviado pelo responsável em 30/10/2026,
`Design sem nome.png`, preservado em `.github/assets/connect/official/logo-aprovada.png`
(108×72). O arquivo é usado diretamente, sem recorte nem reconstrução das letras.
As fontes anteriores permanecem arquivadas, mas não alimentam a geração de ícones.

Para regenerar os PNG/ICO, executar `python a2/tools/generate_windows_icons.py`
com ImageMagick 7. A proporção horizontal original é mantida e centralizada com
espaço transparente nos recursos quadrados. Os wrappers SVG incorporam o PNG
oficial; não contêm letras redesenhadas. Conferir a renderização no Windows.

Assinatura não garante ausência de SmartScreen: certificados OV e EV exibem o
publicador validado, mas novos binários ainda podem gerar avisos até acumular
reputação. EV não concede dispensa imediata. Usar a identidade A2 consistente,
assinar os arquivos finais com timestamp, verificar depois de empacotar e
distribuir pelo domínio oficial HTTPS. Não modificar arquivos depois de assinados.
Certificado SSL de site não substitui certificado de assinatura de código.

Fonte: [Microsoft — SmartScreen reputation for Windows app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

## Compilação local Windows

A receita x64 independente do Actions fica em [local/README.md](local/README.md).
Os atalhos `PREPARAR-WINDOWS.cmd` e `COMPILAR-CONNECT.cmd` estão na raiz do
repositório. A preparação usa configuração pública A2 e não requer secrets da
pipeline. Não instala o Connect, não altera serviços e não publica atualizações.
A preparação dos fontes e o parser foram verificados; o build Windows completo
ainda será executado no notebook.
