# Inventário separado do servidor RustDesk

`windows/Get-A2Inventory.ps1 -Customer 'Empresa de teste'` consulta a instalação
local e emite JSON. Coleta nome da empresa, computador, ID, SO/build, versão,
tipo servidor/estação e estado/início do serviço. Não consulta senhas e não
envia dados a nenhum destino. O estado de atualização é `not-managed` até
existir um agente transacional com estado confirmado.

Não usar `Win32_Product`, que pode iniciar reparos de MSI. A coleta usa
`Win32_OperatingSystem`, `Win32_Service`, metadados do executável e `--get-id`.
Homologação da consulta do ID no contexto do serviço/SYSTEM continua pendente.

## Arquitetura proposta, ainda não implantada

Um serviço HTTPS próprio da A2, separado de hbbs/hbbr, recebe heartbeats de um
agente local. Cada instalação recebe identidade de inventário aleatória e
credencial individual por enrollment de uso único, curto e vinculado ao tenant.
Trocar o enrollment por certificado mTLS individual ou token de escopo restrito
protegido com DPAPI/ACL, com expiração, renovação e revogação.

O backend associa identidade do agente a tenant, computador e ID RustDesk, mas
não considera o ID RustDesk uma credencial de API. Autenticar cada requisição,
validar schema e tenant, limitar taxa/tamanho e registrar auditoria. Técnicos
usam SSO/MFA/RBAC por cliente. Cofre de senhas de acesso remoto é separado do
inventário, sem credenciais no heartbeat, painel, manifesto ou log.

Tabelas iniciais: tenants, devices, enrollment_grants, device_certificates,
heartbeats, release_channels, update_jobs e audit_events. Estado de atualização
deve distinguir offered/downloading/staged/authorized/installing/healthy/
rolled_back/failed/reboot_pending. Um evento staged nunca comprova instalação.

O futuro agente classifica Windows Server via ProductType e permite também
marcação administrativa de estação crítica. Política efetiva deve aplicar a
restrição mais forte. O servidor de inventário não autoriza sozinho instalações:
há política local consentida, autorização administrativa/janela e bloqueio por
sessão ativa no cliente. Não existe execução remota genérica de comandos nesta
proposta e não há dependência presumida de APIs Pro.

Antes de implementar, definir hospedagem, identidade do operador, retenção de
dados, backup, autenticação e vínculo com o cofre corporativo. Não foram criados
backend, banco, contas, certificados ou transmissão de inventário nesta etapa.
