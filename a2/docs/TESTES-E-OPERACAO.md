# Homologação e instalação permanente

## Condições e registro de evidências

Usar o Windows de testes informado pelo responsável, com console local/hipervisor
e snapshot antes de instalar. Não ensaiar em servidor de produção. Manter os
instaladores atuais e backup privado das configurações. Nunca anexar TOML,
senhas, chave privada ou logs de autenticação completos ao repositório.

Para cada caso, registrar data, arquitetura, sistema/build Windows, produto,
hash do instalador, ID antes/depois, nome/estado/start mode/caminho do serviço,
resultado de autenticação e permissões. Resultado não executado fica **pendente**.
Prints devem ocultar credenciais e informações dos clientes.

## Matriz mínima

| Plataforma | Cenário | Critério |
| --- | --- | --- |
| Windows x64 estação | Limpa via EXE e via MSI | Um produto, um serviço, marca A2, servidor A2 |
| Windows ARM64 | Limpa via EXE e via MSI | Mesmo comportamento, arquitetura nativa correta |
| Windows Server de teste | Antes do login, logout e reboot manual | Conecta com credencial individual; serviço Automatic/Running |
| Windows x64/ARM64 | Upgrade do EXE atual para novo EXE | Mesmo ID, serviço, servidor, chave, senha e permissões |
| Windows x64/ARM64 | Upgrade MSI→MSI | Mesmo ID, UpgradeCode compatível, sem duplicata em Aplicativos |
| Windows x64/ARM64 | EXE→MSI e MSI→EXE | Provar migração ou rejeitar caminho explicitamente |
| Windows | Usuário comum/PIN sem administração | Não habilita, renova ou revoga sem autorização administrativa |
| Windows | Cancelamento do consentimento/UAC | Não habilita acesso permanente |
| Windows | Cancelamento de salvar a credencial | Retorna à aprovação por clique |
| Windows | Credenciais em duas instalações limpas | Diferentes; nenhuma senha compartilhada no build |
| Windows | Renovação | Credencial antiga falha; nova funciona após reconectar |
| Windows | Revogação | Nova conexão por senha falha; clique continua disponível |
| Windows | Sessão ativa | Operações de credencial não encerram sessão; nenhuma instalação automática |
| Windows | Recursos | Teclado, clipboard e áudio funcionam; arquivo/terminal/túnel continuam bloqueados |
| Windows | Serviço parado/ausente | Assistente recusa habilitação; orienta manutenção |
| Windows | Preferências importadas sem autorização HKLM | Não liberam acesso por senha |
| Windows | Cópia portátil com serviço instalado autorizado | Não herda autorização do executável instalado |
| Windows | Serviço Manual em execução | Habilitação muda para Auto sem alterar PID |
| ConnectAdmin Windows | Preview client ligado/desligado | Marca e conexão de técnicos preservadas; sem card de cliente |
| macOS Intel/Apple Silicon | DMG atual | Logo, conexão, permissões TCC, ID e operação dos técnicos preservados |

Não presumir que IDs iguais visualmente bastem: reconectar de outro dispositivo,
testar senha anterior e conferir servidor usado. Na primeira migração do aplicativo
antigo, autorizar novamente no assistente com **preservar a credencial existente**.
Até esse consentimento, a política nativa exige clique, mesmo com preferências
antigas de acesso permanente. Nos upgrades seguintes, conferir persistência da
autorização na mesma máquina. Não copiar o backup de uma
máquina para outra; isso pode clonar identidade.

## Instalação permanente no Windows de teste

1. Abrir o console local do Windows de teste e encerrar atendimentos remotos.
2. Registrar o ID, a configuração de rede e o serviço atuais, sem publicar segredos.
3. Instalar o preview pelo fluxo nativo **Instalar**, aprovando UAC. Para laboratório
   sem certificado, não desativar SmartScreen ou Defender; tratar bloqueios pela
   política de laboratório e não distribuir a clientes. Produção requer assinatura.
4. Conferir `Get-Service -Name Connect` e
   `Get-CimInstance Win32_Service -Filter "Name='Connect'"`:
   caminho esperado, conta de serviço, estado Running e início Auto.
5. Em Configurações → Segurança, desbloquear como administrador e escolher
   **Habilitar acesso não supervisionado**. Confirmar autorização do responsável.
6. Guardar a credencial individual no cofre autorizado e confirmar. Testar acesso
   de um ConnectAdmin separado; o caminho de aprovação por clique permanece.
7. Testar tela bloqueada, logout e reinicialização manual. Comparar novamente o ID.
8. Testar renovação e revogação. Para remover o serviço, primeiro revogar o acesso,
   garantir console local e janela sem sessões; usar o comando nativo elevado
   do executável instalado `Connect.exe --uninstall-service`. Esse comando
   encerra processos; não executar durante atendimento. Não apagar diretórios de
   configuração ou desinstalar o produto para apenas revogar uma credencial.

`--install-service` é nativo, mas para/recria serviço e mata processos do aplicativo.
Não chamá-lo repetidamente como forma de verificar saúde. Se a instalação estiver
incompleta, reparar em manutenção local e confirmar os mesmos testes novamente.

## Testes de confiança e publicação

O parser PowerShell, CMS e casos negativos já passaram no runner Windows
([evidência](https://github.com/a2solucoesemti/rdgen/actions/runs/39269043305)).
Executar novamente `a2/tests/Test-UpdateTrust.ps1` em CI a cada mudança.
Depois, com o certificado real, validar EXE/MSI pelo `Test-A2Signature.ps1`.
Ensaiar também:

- Binário sem assinatura, certificado diferente, publicador errado e ausência de timestamp.
- Manifesto com um byte alterado, assinatura CMS alterada, certificado não confiável.
- Manifesto vencido, data futura, sequência repetida, replay de versão antiga.
- URL HTTP, redirect, domínio semelhante, caminho fora de `/updates/` e query string.
- ConnectAdmin no canal Connect, arquitetura errada e Windows incompatível.
- SHA-256 incorreto, truncamento, tamanho incorreto, MSI cujo ProductName/versão divergem.
- Falha de rede e duas preparações concorrentes. Nenhuma deve executar instalação.
- Pasta de staging com owner/ACL indevidos ou junction deve ser rejeitada.
- Compatibilidade de cadeia, revogação de certificado e operação com proxy corporativo.

A rotina de staging limita bytes durante streaming e duração do download.
Ainda não tem retry controlado nem agenda; homologar rede, cancelamento e
limites reais antes de automatizar execução.

## Upgrade transacional pendente

O código novo ainda não instala atualizações nem implementa rollback. Ensaiar,
antes de construir o executor: ID e credenciais nos contextos de usuário/SYSTEM,
versões MSI e UpgradeCode, transição EXE/MSI, arquivos bloqueados, falta de disco,
perda de energia, falha antes/depois do restart do serviço e reversão ao pacote
anterior assinado com restauração de estado. Não remover nem sobrescrever builds
antigos até homologar esse processo.

Não gerar duas releases diferentes com o mesmo ProductVersion MSI. É necessário
definir versão de distribuição A2 separada da tag upstream antes de automatizar
upgrades de customizações sobre RustDesk 1.4.9.

## macOS: assinatura separada

Code Signing OV Windows não assina o aplicativo macOS. Será necessário Apple
Developer ID Application, keychain temporário no runner, assinatura do bundle
e componentes internos com hardened runtime/entitlements compatíveis, criação
do DMG, assinatura do DMG, envio por `xcrun notarytool`, espera pelo resultado e
`xcrun stapler staple`. Verificar com `codesign --verify --deep --strict`,
`spctl --assess` e `stapler validate`, e testar em máquina limpa com Gatekeeper.

Não habilitar `--deep` como substituto do planejamento de assinatura interna.
Não desativar Gatekeeper. Guardar credenciais Apple e certificados apenas em
secrets/keychain do runner. Notarização/assinatura não foram executadas e o
workflow macOS atual não foi alterado nesta etapa.

Referências: [SSL.com e SignTool](https://www.ssl.com/how-to/using-your-code-signing-certificate/),
[notarização Apple](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution),
[verificação CMS no .NET](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.pkcs.signedcms.checksignature).
