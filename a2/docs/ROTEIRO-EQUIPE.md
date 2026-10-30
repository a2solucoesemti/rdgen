# Roteiro da equipe — preview de acesso permanente

Este pacote é para o Windows de testes. Não representa liberação para produção.
Não inclui atualizador instalando automaticamente. O certificado A2 ainda será
adquirido. Não desativar Defender/SmartScreen para executar o teste.

## Preparação

1. Ter console local ou acesso ao hipervisor, snapshot e instalador anterior.
2. Usar x86_64 em Intel/AMD e aarch64 em Windows ARM64. Não misturar arquiteturas.
3. Usar um ConnectAdmin já existente em outra máquina para testar as conexões.
4. Manter o cofre de senhas autorizado disponível. Não enviar senha por chat,
   por planilha de resultados ou por screenshot.
5. Conferir o SHA-256 do instalador contra `SHA256SUMS.txt` do pacote recebido.
   O hash é uma conferência de transporte; não substitui assinatura digital.

## Sequência A — instalação limpa

1. Registrar sistema, arquitetura e hash do arquivo usado.
2. Executar EXE e usar o botão nativo **Instalar**, aprovando UAC. Em snapshot
   separado, repetir com MSI. Não instalar os dois ao mesmo tempo como teste limpo.
3. Conferir ID, marca A2, servidor A2 e serviço Connect Running/Automatic.
4. Antes de habilitar, tentar conexão: deve exigir aprovação por clique.
5. Em Configurações → Segurança, desbloquear e escolher **Habilitar acesso não
   supervisionado**. Confirmar UAC/administração e consentimento. Guardar a senha
   individual no cofre e só então confirmar que foi salva.
6. Conectar pelo ConnectAdmin com a senha individual. Confirmar teclado,
   clipboard e áudio; arquivo, terminal e túnel devem continuar indisponíveis.
7. Bloquear a tela, testar novamente; encerrar sessão remota, fazer logout local
   e testar antes do login. Encerrar o atendimento, reiniciar manualmente e
   testar novamente antes do login. Comparar o ID em todos esses momentos.
8. Renovar a credencial, confirmar que a antiga deixa de funcionar em nova
   conexão e que a nova funciona. Revogar e confirmar que senha não autoriza
   nova conexão, mas a aprovação por clique continua funcionando.
9. Em outra instalação limpa, habilitar novamente e confirmar que a credencial
   é diferente. Guardá-la no cofre; não copiar configuração de identidade entre máquinas.

## Sequência B — atualização da instalação existente

Restaurar o snapshot original. Registrar ID e confirmar que a senha permanente
anterior funciona, quando existente. Instalar o preview sobre a instalação,
sem remover o produto antes. Fazer cada combinação EXE→EXE, MSI→MSI e EXE↔MSI
em snapshots separados.

Depois de instalar, conferir **ID idêntico**, chave/servidor A2,
inicialização/estado do serviço e permissões. Confirmar ausência de segunda
entrada em Aplicativos e segundo serviço.

Na primeira migração do aplicativo antigo, o acesso por senha permanece bloqueado
até nova autorização administrativa, mesmo que o arquivo antigo já configurasse
acesso permanente. No assistente, escolher **preservar a credencial existente**,
confirmar UAC e testar a senha anterior pelo ConnectAdmin. Não escolher renovação
nesse teste: isso alteraria a senha e invalidaria a prova de preservação.
Nos próximos upgrades desse modelo, verificar que a autorização da mesma máquina
continua válida sem refazer o assistente. Nunca copiar a autorização para outra máquina.

No MSI upstream 1.4.9 existe `AllowSameVersionUpgrades=yes`, mas isso não comprova
o comportamento dos nossos binários. Registrar também o resultado ao atualizar
de 1.4.9 para um preview 1.4.9. A futura atualização automática exigirá uma
versão de distribuição A2 crescente, ainda a definir.

## Casos de falha e consentimento

- Cancelar UAC/consentimento: acesso permanente não é habilitado.
- Tentar sem ser administrador: deve exigir autorização administrativa.
- Cancelar a confirmação de salvamento no cofre: deve voltar ao modo por clique.
- Serviço parado/ausente: a habilitação deve ser recusada.
- Renovar/revogar durante uma sessão: sessão atual continua; validar a mudança
  numa conexão posterior. Não executar instalação ou remoção de serviço durante atendimento.
- Reabrir aplicativo: estado exibido deve corresponder à política real.
- Copiar somente preferências antigas com acesso permanente: não deve dispensar
  o consentimento administrativo na máquina de destino.
- Executar uma cópia portátil enquanto a instalação está autorizada: essa cópia
  não deve herdar a autorização do serviço instalado.
- Habilitar em serviço com início Manual: deve passar a Automatic sem parar ou
  reiniciar o serviço. Registrar o PID antes/depois.

## Resultados para devolver

Preencher uma cópia local desta tabela. Não incluir senhas nem arquivos TOML.

| Campo | Resultado |
| --- | --- |
| Data / responsável | |
| Cliente fictício do laboratório | |
| Windows / build / arquitetura | |
| Arquivo / SHA-256 | |
| EXE ou MSI / limpa ou upgrade | |
| ID antes / depois (canal privado da equipe) | |
| Serviço Running / Automatic / caminho correto | |
| Aprovação por clique antes da habilitação | |
| UAC, consentimento e cancelamento | |
| Acesso antes do login / após logout / após reboot manual | |
| Senha anterior preservada no upgrade | |
| Renovação invalida senha antiga | |
| Revogação bloqueia nova conexão por senha | |
| Teclado / clipboard / áudio | |
| Arquivo / terminal / túnel bloqueados | |
| Sem produto ou serviço duplicado | |
| Marca A2 e servidor preservados | |
| Erros e reprodução (sem credenciais) | |

Qualquer divergência de ID, servidor, senha ou permissões reprova a migração.
Restaurar o snapshot para recuperação no laboratório; rollback automático ainda
não foi implementado. Não promover esse preview ao canal stable ou server.

## Cliente portátil — revisão de 30/10/2026

- Ao abrir o EXE sem instalação, o atendimento é iniciado no contexto do usuário,
  usando a rotina nativa. Não deve pedir clique em Iniciar serviço ou UAC só para
  abrir. A aprovação da conexão pelo cliente continua obrigatória.
- Testar também depois de usar Parar serviço no build antigo: reabrir o novo EXE
  deve voltar a registrar o atendimento. Não deve criar serviço Windows.
- O único botão de instalação continua sendo Instalar. Só a instalação permanente
  e as funções que exigem elevação podem solicitar administração do Windows.
- Fechar a janela e encerrar o aplicativo são operações diferentes no upstream;
  conferir o comportamento da bandeja. Não presumir acesso após logout/reboot no
  modo portátil.
- Testar ícones da janela, barra de tarefas, bandeja e instalador em escala de
  100%, 150% e 200%, em temas claro e escuro. Os ícones do cliente agora são
  separados dos ícones do ConnectAdmin.
- Na instalação existente, abrir o aplicativo não deve reparar, reinstalar ou
  reativar automaticamente um serviço que o administrador tenha parado.
