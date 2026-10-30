# Compilação local — notebook Windows x64

Pacote preparado em 30/10/2026 para o A2-NT0001 e outros notebooks Windows
Intel/AMD de 64 bits. Não depende de execuções ou artefatos do GitHub Actions.
A compilação Windows desta receita ainda precisa ser executada no notebook.

## Baixar e abrir

Opção Git, para continuar recebendo correções:

```powershell
git clone --branch feature/a2-unattended-update-foundation https://github.com/a2solucoesemti/rdgen.git C:\A2Connect\rdgen
cd C:\A2Connect\rdgen
```

Se o Git ainda não estiver instalado, usar o ZIP preparado no Mac e extrair todo
o conteúdo em `C:\A2Connect\rdgen`, inclusive a pasta oculta `.github`.
O ZIP é código e ferramentas de preparação; não contém um Connect já compilado.
Se o repositório exigir autenticação, usar o fluxo do Git Credential Manager;
nunca inserir tokens em scripts, arquivos versionados ou conversas.

## Preparar o notebook

Reservar uma pasta local NTFS, de preferência SSD, e cerca de 80 GB livres para
SDKs, código, dependências, intermediários e caches. Manter conectado à energia.
Não usar pasta de rede ou pasta sincronizada para a árvore de compilação.
Windows deve ter App Installer/winget disponível. A instalação de ferramentas
pode pedir UAC. Aceitar somente os instaladores oficiais esperados. Nenhum
reinício é solicitado automaticamente pelo pacote.

Na raiz do repositório, dar duplo clique em **PREPARAR-WINDOWS.cmd**.
Ou executar no PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\a2\local\Setup-LocalBuild.ps1 -Install
```

O parâmetro de política vale apenas para esse processo PowerShell; não muda a
política permanente do computador nem desativa Defender ou SmartScreen.
A preparação usa winget para Git, Python 3.11, Rustup, LLVM, NASM, .NET e Visual
Studio Build Tools 2022 com C++, ATL/MFC, toolset v142/v143 e SDK Windows.
Também baixa Flutter 3.24.5 e CMake 3.29.7 com conferência de SHA-256, além de
NuGet oficial. As licenças dos pacotes são aceitas pelo comando de instalação.
Sem `-Install`, o script apenas lista pré-requisitos ausentes.

Se houver pedido de reinicialização, reiniciar manualmente e repetir a
preparação. Em uma instalação existente do Visual Studio, o script tenta acrescentar os
componentes necessários pelo Visual Studio Installer. Se o instalador estiver
ocupado ou pedir confirmação, concluir essa etapa e repetir a preparação.

## Compilar

Após a preparação terminar, dar duplo clique em **COMPILAR-CONNECT.cmd**.
Ou executar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\a2\local\Build-Connect.ps1
```

A primeira execução pode levar horas e baixar vários GB. As seguintes reutilizam
caches. Os comandos preservam seus erros: se uma etapa falhar, o pacote não é
anunciado como concluído. Não execute duas compilações no mesmo BuildRoot.

Saída padrão:

```text
C:\A2ConnectBuild\output\Connect-x64-DATA-HORA-ID\
    Connect-x86_64.exe
    Connect-x86_64.msi
    SHA256SUMS.txt
    BUILD-INFO.json
    LEIA-PRIMEIRO.md
    TESTES-E-OPERACAO.md
C:\A2ConnectBuild\output\Connect-x64-DATA-HORA-ID.zip
C:\A2ConnectBuild\logs\
```

Para gerar primeiro apenas o EXE, usar `Build-Connect.ps1 -SkipMsi`.
Para uma pasta diferente, passar o mesmo `-BuildRoot D:\A2Build` nos dois scripts.
O caminho deve ser absoluto e sem espaços.

O padrão é Connect cliente com aprovação por clique, logo oficial enviada pelo
responsável e início do atendimento ao abrir o portátil. `-UnattendedControls`
é opcional e experimental; exige seus próprios testes. Não é necessário para
validar ícones ou o atendimento portátil.

## O que a receita faz

- Clona o RustDesk 1.4.9 no commit de `versions.json`, com submódulo hbb_common.
- Aplica os mesmos patches A2 versionados: nome Connect, servidor e chave pública
  A2, bloqueios de recursos, layout, ícones e atendimento portátil.
- Usa `a2/profiles.py` para a política e `client-config.json` para os dados públicos.
  Não contém senha permanente, tokens, certificado ou secrets do Actions.
- Compila vcpkg, gera as pontes Flutter/Rust localmente e usa o engine Flutter
  customizado do fluxo x64 existente. O engine é obtido do release upstream
  `main`; seu SHA-256 efetivo é registrado, sem alegar uma versão imutável.
- Compila WindowInjection no commit fixado e gera EXE autocontido e MSI WiX.
- Registra fingerprints, hashes e estado das assinaturas. Não assina produção,
  publica atualizações, instala Connect ou altera seus serviços.

As fontes ficam em `C:\A2ConnectBuild\work`, separadas da instalação do aplicativo.
Uma revisão diferente da receita cria outra pasta. Se uma preparação for
interrompida ou encontrar uma árvore modificada sem marcador, ela recusa
sobrescrever o trabalho. Preserve o log e use outro BuildRoot, ou peça revisão
da pasta antes de remover qualquer coisa. Não execute `git reset --hard` em
trabalho existente para tentar consertar a compilação.

## Limites e validação

Receita restrita a Windows x64, não ARM64, macOS ou Linux. Os scripts PowerShell
foram verificados com parser; a preparação Python foi exercitada contra o
upstream fixado. Isso não substitui compilar e testar o aplicativo no Windows.

Os binários locais são previews de laboratório. O certificado de assinatura A2
continua sendo uma etapa separada; não alterar nem desativar SmartScreen para
tentar distribuí-los. Homologar o EXE/MSI antes de enviar a um cliente.
Acesso permanente, preservação do ID em upgrade e atualização automática não
são comprovados pela compilação.

A pasta `.github` é obrigatória também no pacote ZIP. A receita não usa secrets
nem serviço de assinatura remoto. Todos os downloads de ferramentas vêm de
fontes oficiais; os hashes publicados de Flutter e CMake são conferidos.
A configuração pública A2 é intencionalmente versionada; não substituir por
credenciais de clientes.
