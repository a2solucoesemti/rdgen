"""One source for Connect policy; never embed an unattended credential."""
import base64
import json


def configure(config, profile, unattended_controls=False):
    config = dict(config)
    if profile not in {"client", "admin"}:
        raise ValueError("Unknown A2 profile")
    if profile == "admin":
        # Preserve the existing technician profile.
        options = {"override-settings": {"view-style": "adaptive", "allow-auto-update": "N"}}
        name = "ConnectAdmin"
    else:
        name = "Connect"
        restrictions = {
            "access-mode": "custom",
            "enable-keyboard": "Y", "enable-clipboard": "Y",
            "enable-audio": "Y", "enable-file-transfer": "N",
            "enable-terminal": "N", "enable-tunnel": "N",
            "enable-remote-restart": "N", "enable-record-session": "N",
            "enable-block-input": "N", "enable-remote-printer": "N",
            "enable-camera": "N", "allow-remote-config-modification": "N",
            "direct-server": "N", "allow-auto-update": "N",
        }
        options = {"conn-type": "incoming", "override-settings": restrictions}
        if unattended_controls:
            # Initial behavior stays attended. Only a local administrator may
            # enable password access later; do not override this mutable choice.
            options["default-settings"] = {
                "approve-mode": "click",
                "verification-method": "use-permanent-password",
            }
        else:
            restrictions["approve-mode"] = "click"
    config.update(appname=name, exename=name)
    config["custom"] = base64.b64encode(json.dumps(
        options, separators=(",", ":")
    ).encode()).decode()
    return config
