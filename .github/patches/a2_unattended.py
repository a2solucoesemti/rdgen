"""Opt-in Windows UI extension, using RustDesk IPC, never password CLI args.

Run after the existing A2 branding patches inside the upstream checkout.
Fails closed if the expected upstream interface changes.
"""
import os
from pathlib import Path


def apply(root):
    path = root / "flutter/lib/desktop/pages/desktop_setting_page.dart"
    source = path.read_text(encoding="utf-8")
    marker = "                password(context),"
    anchor = "  Widget password(BuildContext context) {"
    if source.count(marker) != 1 or source.count(anchor) != 1:
        raise ValueError("Unsupported upstream Security settings layout")
    if "Widget a2Unattended" in source:
        raise ValueError("A2 unattended patch already applied")
    source = source.replace("import 'dart:io';", "import 'dart:io';\nimport 'dart:math' as a2math;\nimport 'dart:ffi' as a2ffi;\nimport 'package:ffi/ffi.dart' show calloc, StringUtf16Pointer;\nimport 'package:win32/win32.dart' as a2win32;", 1)
    source = source.replace(marker, "                a2Unattended(context),", 1)
    widget = r'''
  bool a2CredentialBusy = false;

  Future<void> a2RequestPolicy(bool enabled) async {
    final response = await bind.mainGetCommon(key: enabled ? 'a2-consent-enable' : 'a2-consent-disable');
    if (response != 'requested') {
      throw Exception('A autorização administrativa da política não foi concluída.');
    }
    for (var attempt = 0; attempt < 50; attempt++) {
      final state = await bind.mainGetCommon(key: 'a2-unattended-consent');
      if (state == (enabled ? 'true' : 'false')) return;
      if (state == 'unknown') throw Exception('O serviço não confirmou o estado da autorização.');
      await Future.delayed(const Duration(milliseconds: 200));
    }
    throw Exception('Não foi possível confirmar a política com o serviço. Verifique o estado antes de tentar novamente.');
  }

  bool a2ServiceRunning() {
    if (!isWindows) return false;
    final manager = a2win32.OpenSCManager(a2ffi.nullptr, a2ffi.nullptr, a2win32.SC_MANAGER_CONNECT);
    if (manager == 0) return false;
    try {
      final name = 'Connect'.toNativeUtf16(allocator: calloc);
      try {
        final service = a2win32.OpenService(manager, name, a2win32.SERVICE_QUERY_STATUS);
        if (service == 0) return false;
        try {
          final status = calloc<a2win32.SERVICE_STATUS>();
          try {
            return a2win32.QueryServiceStatus(service, status) != 0 &&
                status.ref.dwCurrentState == 0x00000004; // SERVICE_RUNNING (winsvc.h)
          } finally { calloc.free(status); }
        } finally { a2win32.CloseServiceHandle(service); }
      } finally { calloc.free(name); }
    } finally { a2win32.CloseServiceHandle(manager); }
  }

  Widget a2Unattended(BuildContext context) {
    return ChangeNotifierProvider.value(
      value: gFFI.serverModel,
      child: Consumer<ServerModel>(builder: (context, model, _) {
        final enabled = (model.approveMode == 'password' || model.approveMode == defaultOptionApproveMode) &&
            model.verificationMethod == kUsePermanentPassword;
        Future<void> change(bool revoke) async {
          if (a2CredentialBusy) return;
          setState(() => a2CredentialBusy = true);
          try {
            if (!isWindows || (!revoke && (!bind.mainIsInstalled() ||
                (await bind.mainGetCommon(key: 'a2-is-installed-exe')) != 'true' ||
                (await bind.mainGetCommon(key: 'a2-service-policy-version')) != '1'))) {
              throw Exception('Instale o Connect pelo botão Instalar antes de habilitar acesso permanente.');
            }
            // Require OS administration on every action, even with an unlock PIN.
            if (!await callMainCheckSuperUserPermission()) return;
            if (!context.mounted) return;
            final accepted = await showDialog<bool>(context: context,
              builder: (ctx) => AlertDialog(
                title: Text(revoke ? 'Revogar acesso permanente' : 'Habilitar acesso não supervisionado'),
                content: Text(revoke
                    ? 'Revogar a senha permanente e voltar à aprovação por clique?'
                    : 'Autorizo o acesso permanente a este computador. Usaremos uma credencial individual, que deve estar no cofre autorizado da A2. O Windows solicitará autorização para salvar esta política.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
                  TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Confirmar')),
                ],
              ));
            if (accepted != true) return;
            if (!revoke && !a2ServiceRunning()) {
              throw Exception('O serviço Connect precisa estar instalado e em execução.');
            }
            final machinePolicy = await bind.mainGetCommon(key: 'a2-unattended-consent');
            if (revoke || machinePolicy == 'true') {
              await a2RequestPolicy(false);
            } else if (machinePolicy != 'false') {
              throw Exception('Instale o preview completo: o serviço não confirmou suporte à política A2.');
            }
            // This card never installs, stops or restarts the service.
            // Installation/service management stays in the native installation UI.
            if (revoke) {
              await model.setApproveMode('click');
              if (await bind.mainGetOption(key: kOptionApproveMode) != 'click') {
                throw Exception('Não foi possível restaurar a aprovação por clique.');
              }
              if (!await bind.mainSetPermanentPasswordWithResult(password: '')) {
                throw Exception('Política desabilitada, mas o serviço não confirmou a remoção da senha. Verifique antes de concluir a revogação.');
              }
            } else {
              // Require an already running native Windows service. Do not start
              // or reinstall it here: upstream install_service kills processes.
              if (!a2ServiceRunning()) {
                throw Exception('O serviço Connect precisa estar instalado e em execução. Use a instalação nativa numa janela sem sessões remotas.');
              }
              var keepExisting = false;
              if (!enabled && (await bind.mainGetCommon(key: 'local-permanent-password-set')) == 'true') {
                if (!context.mounted) return;
                final choice = await showDialog<String>(context: context, builder: (ctx) => AlertDialog(
                  title: const Text('Credencial existente'),
                  content: const Text('Há uma credencial local salva. Preserve-a se ela for individual e já estiver no cofre autorizado; escolha gerar outra para renová-la.'),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
                    TextButton(onPressed: () => Navigator.pop(ctx, 'new'), child: const Text('Gerar nova')),
                    TextButton(onPressed: () => Navigator.pop(ctx, 'keep'), child: const Text('Preservar credencial individual')),
                  ],
                ));
                if (choice == null) return;
                keepExisting = choice == 'keep';
              }
              // The native machine gate remains closed until elevated policy approval.
              await model.setApproveMode('click');
              if (await bind.mainGetOption(key: kOptionApproveMode) != 'click') {
                throw Exception('Política de aprovação bloqueada; credencial não alterada.');
              }
              if (keepExisting) {
                if (await bind.mainGetCommon(key: 'local-permanent-password-set') != 'true') {
                  throw Exception('O serviço não confirmou a credencial existente.');
                }
              } else {
                final random = a2math.Random.secure();
                final credential = base64Url.encode(List<int>.generate(24, (_) => random.nextInt(256)));
                // Never send the plaintext via arguments, files, environment or logs.
                if (!context.mounted) return;
                final saved = await showDialog<bool>(context: context,
                  barrierDismissible: false,
                  builder: (ctx) => AlertDialog(
                    title: const Text('Guarde a credencial individual'),
                    content: SelectableText(credential),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
                      TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Salvei no cofre autorizado')),
                    ],
                  ));
                if (saved != true) return;
                if (!await bind.mainSetPermanentPasswordWithResult(password: credential)) {
                  throw Exception('O serviço não confirmou a gravação da credencial. A política permanece desabilitada.');
                }
              }
              await model.setVerificationMethod(kUsePermanentPassword);
              await a2RequestPolicy(true);
              // Keep the existing local approval path in addition to password access.
              await model.setApproveMode(defaultOptionApproveMode);
              if (await bind.mainGetOption(key: kOptionVerificationMethod) != kUsePermanentPassword ||
                  await bind.mainGetOption(key: kOptionApproveMode) != defaultOptionApproveMode) {
                await model.setApproveMode('click');
                throw Exception('Não foi possível habilitar a política; aprovação por clique restaurada.');
              }
            }
          } catch (e) {
            if (context.mounted) {
              await showDialog<void>(context: context, builder: (ctx) => AlertDialog(
                title: const Text('Acesso permanente'),
                content: Text(e.toString()),
                actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Fechar'))],
              ));
            }
          } finally {
            await model.updatePasswordModel();
            if (mounted) setState(() => a2CredentialBusy = false);
          }
        }
        return _Card(title: 'Acesso não supervisionado', children: [
          Text(enabled ? 'Acesso permanente habilitado (requer serviço em execução)' : 'Acesso permanente desabilitado'),
          _SubButton(enabled ? 'Renovar credencial individual' : 'Habilitar acesso não supervisionado',
              () => change(false), !locked && !a2CredentialBusy),
          _SubButton('Revogar acesso permanente', () => change(true), !locked && !a2CredentialBusy),
        ]);
      }),
    );
  }

'''
    source = source.replace(anchor, widget + anchor, 1)
    path.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    if os.environ.get("A2_PROFILE") == "client" and os.environ.get("A2_UNATTENDED_CONTROLS") == "true":
        apply(Path("."))
        print("Applied opt-in A2 unattended Security card")
    else:
        print("Skipped A2 unattended Security card")
