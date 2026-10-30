# Análise do projeto existente

Inspeção: 19/10/2026. Base Git: `a2solucoesemti/rdgen`, HEAD inicial `bec89aa`.

## Organização e geração

Não existem dois projetos completos de RustDesk nesta pasta. Existe um gerador
RDGen (Django) e workflows que fazem checkout do RustDesk upstream por tag.
Connect e ConnectAdmin são perfis da mesma base, configurados por secrets A2.
`connect-config.json` e `connect-admin-config.json`, um nível acima do repositório
RDGen, são referências locais. O workflow Windows usa os secrets
`A2_CLIENT_CONFIG_B64` e `A2_ADMIN_CONFIG_B64`; alterar apenas o JSON local não
altera o build remoto.

Windows: `.github/workflows/generator-windows.yml`, matriz x86_64/aarch64,
Flutter/Rust, empacotador portátil em `libs/portable`, MSI em `res/msi` via WiX
e MSBuild. `preprocess.py` extrai a versão Cargo e recebe `--app-name`.
O UpgradeCode upstream é derivado de UUIDv5 do nome do executável: manter
`Connect`/`ConnectAdmin` é necessário, mas não prova que o ID permaneça igual.
Não mudar nome, diretório e família MSI durante a migração sem ensaio.
O `Package.wxs` upstream permite upgrade da mesma versão; isso precisa ser
confirmado nos MSI efetivamente gerados e não substitui versionamento A2 crescente.

macOS: `.github/workflows/generator-macos.yml`, perfis e patches de marca próprios,
artefatos DMG separados por arquitetura. Não modificado nesta etapa.

Customizações existentes estão em `.github/patches/`, incluindo
`a2_connectadmin.py`, `a2_windows_install_only.py`, `a2_macos_branding.py` e
`a2_common_branding.py`. Preservadas. Os novos controles são um patch adicional
opt-in aplicado após a personalização Windows.

## Recursos nativos confirmados no RustDesk 1.4.9

| Recurso | Evidência no código | Consequência |
| --- | --- | --- |
| Serviço Windows | `src/core_main.rs`: `--install-service`, `--uninstall-service` | Reutilizar serviço nativo |
| Auto start | `src/platform/windows.rs`: `get_create_service`, `start= auto` | Não criar outro serviço de acesso remoto |
| Senha permanente | `core_main.rs`: `--password`; UI usa `mainSetPermanentPasswordWithResult` | Preferir IPC, evitando senha em linha de comando |
| Consulta de ID | `--get-id` | Coleta local sem abrir banco de credenciais |
| Aceitação por senha/clique | Settings `approve-mode`, `verification-method` | Senha sozinha não basta se o build fixa aprovação por clique |
| Upgrade EXE/MSI | `update_to`, `update_me`, `update_me_msi` | Existem primitivas, não a política A2 completa |
| Customização na atualização | `prepare_custom_client_update`, staging de `custom.txt` | Mecanismo existente precisa de compatibilidade real com o payload RDGen |
| Migração para serviço | `get_import_config` importa configuração no contexto do serviço | Há intenção de preservação; não comprova identidade ou senha em todas as migrações |

`install_service` chama `taskkill`; `get_import_config` para e recria o serviço.
Portanto essas rotinas não devem ser disparadas automaticamente durante uma
sessão remota. Por isso o preview exige serviço já instalado e em execução;
a instalação/remover serviço será homologada em manutenção local.

O assistente nativo de Segurança pode desbloquear por PIN. O novo controle pede
também a verificação administrativa do sistema em cada ação, mesmo com PIN.
No submódulo hbb_common fixado pela tag 1.4.9
(`7e1c392c62d39c364127307cd408421dd5f8cfb0`), `Config::set_permanent_password`
calcula o hash com salt e prepara armazenamento criptografado; o IPC aguarda
ACK do daemon e sincroniza o armazenamento/salt, sem ler a senha de volta.
A implementação foi conferida, mas proteção local/ACL, migração e equivalência
a DPAPI ou cofre corporativo não foram comprovadas em instalação real.

## Atualização e OSS/Pro

O controle `allow-auto-update` existe a partir de 1.4.6. A documentação pública
descreve download de releases oficiais do GitHub, incompatível com a exigência
de somente pacotes A2 hospedados em `/updates/`. As primitivas de atualização
de custom client no código não comprovam que RDGen tenha endpoint e assinatura
compatíveis com todos os requisitos pedidos.

Decisão desta etapa: fixar `allow-auto-update=N` nos dois perfis Windows;
usar validação e preparação próprias de pacote assinado A2, sem acionar o
instalador até existir política local, intertravamento de sessão e rollback.
Não usar o simples campo `downloadLink` como raiz de confiança.
O RDGen existente também remove a verificação da assinatura do fornecedor sobre
`custom.txt` e utiliza `custom_.txt` via `allowCustom.py`. Esse blob de configuração
não é uma assinatura A2. Antes de produção, revisar origem/ACL do blob e substituir
esse bypass por verificação A2 ou por configuração embutida autenticada. Não
reaproveitar automaticamente o staging nativo de custom client como confiança
para pacotes RDGen.

Acesso remoto por serviço e senha permanente existe no cliente OSS e não exige
trocar hbbs/hbbr por Pro. Console, assignment, políticas e APIs de administração
do Pro não são presumidos disponíveis no servidor atual. O servidor existente
não foi inspecionado por SSH nem modificado.

## Fontes verificadas

- [RustDesk 1.4.9: comandos nativos](https://github.com/rustdesk/rustdesk/blob/1.4.9/src/core_main.rs)
- [RustDesk 1.4.9: serviço, instalação e upgrade Windows](https://github.com/rustdesk/rustdesk/blob/1.4.9/src/platform/windows.rs)
- [RustDesk 1.4.9: tela de Segurança](https://github.com/rustdesk/rustdesk/blob/1.4.9/flutter/lib/desktop/pages/desktop_setting_page.dart)
- [RustDesk 1.4.9: definição de senha por IPC](https://github.com/rustdesk/rustdesk/blob/1.4.9/flutter/lib/desktop/pages/desktop_home_page.dart)
- [RustDesk 1.4.9: identidade do MSI](https://github.com/rustdesk/rustdesk/blob/1.4.9/res/msi/preprocess.py)
- [Armazenamento de senha no hbb_common fixado](https://github.com/rustdesk/hbb_common/blob/7e1c392c62d39c364127307cd408421dd5f8cfb0/src/config.rs)
- [IPC e ACK de gravação](https://github.com/rustdesk/rustdesk/blob/1.4.9/src/ipc.rs)
- [Configurações avançadas oficiais](https://rustdesk.com/docs/en/self-host/client-configuration/advanced-settings/)

Documentação online pode descrever versões posteriores; para comandos e pontos
de integração foram consultadas também as fontes fixadas em `1.4.9`.
