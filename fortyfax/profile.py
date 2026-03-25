"""VPN profile data model and storage."""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "fortyfax"
PROFILES_DIR = CONFIG_DIR / "profiles"


@dataclass
class VPNProfile:
    name: str = "Nuova Connessione"
    host: str = ""
    port: int = 443
    username: str = ""
    auth_method: str = "saml"  # "saml", "password"
    trusted_cert: str = ""
    realm: str = ""
    use_resolvconf: bool = True
    set_dns: bool = True
    set_routes: bool = True
    pppd_use_peerdns: bool = True
    half_internet_routes: bool = False
    extra_args: str = ""
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def display_host(self) -> str:
        return f"{self.host}:{self.port}" if self.port != 443 else self.host

    def to_openfortivpn_args(self, cookie: str = "") -> list[str]:
        """Build openfortivpn CLI arguments from this profile."""
        args = [f"{self.host}:{self.port}"]
        if self.username and self.auth_method == "password":
            args += ["-u", self.username]
        if self.trusted_cert:
            args += ["--trusted-cert", self.trusted_cert]
        if not self.set_routes:
            args.append("--no-routes")
        if not self.set_dns:
            args.append("--no-dns")
        if not self.pppd_use_peerdns:
            args.append("--pppd-no-peerdns")
        if self.half_internet_routes:
            args.append("--half-internet-routes")
        if cookie:
            args += ["--cookie-on-stdin"]
        if self.extra_args:
            args += self.extra_args.split()
        return args

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if not self.name.strip():
            errors.append("Il nome del profilo è obbligatorio")
        if not self.host.strip():
            errors.append("L'host del server VPN è obbligatorio")
        if not (1 <= self.port <= 65535):
            errors.append("La porta deve essere tra 1 e 65535")
        if self.auth_method == "password" and not self.username.strip():
            errors.append("Lo username è obbligatorio per l'autenticazione con password")
        return errors


class ProfileManager:
    """Manages VPN profiles on disk as JSON files."""

    def __init__(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, uid: str) -> Path:
        return PROFILES_DIR / f"{uid}.json"

    def save(self, profile: VPNProfile) -> None:
        data = asdict(profile)
        path = self._profile_path(profile.uid)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        tmp.replace(path)  # atomic on same filesystem

    def load(self, uid: str) -> VPNProfile | None:
        path = self._profile_path(uid)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return VPNProfile(**{k: v for k, v in data.items() if k in VPNProfile.__dataclass_fields__})
        except (json.JSONDecodeError, TypeError):
            return None

    def load_all(self) -> list[VPNProfile]:
        profiles = []
        for f in sorted(PROFILES_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                p = VPNProfile(**{k: v for k, v in data.items() if k in VPNProfile.__dataclass_fields__})
                profiles.append(p)
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return profiles

    def delete(self, uid: str) -> bool:
        path = self._profile_path(uid)
        if path.exists():
            path.unlink()
            return True
        return False

    def export_openfortivpn_config(self, profile: VPNProfile, path: Path) -> None:
        """Export profile as openfortivpn config file."""
        lines = [
            f"host = {profile.host}",
            f"port = {profile.port}",
        ]
        if profile.username:
            lines.append(f"username = {profile.username}")
        if profile.trusted_cert:
            lines.append(f"trusted-cert = {profile.trusted_cert}")
        if not profile.set_routes:
            lines.append("set-routes = 0")
        if not profile.set_dns:
            lines.append("set-dns = 0")
        if not profile.pppd_use_peerdns:
            lines.append("pppd-use-peerdns = 0")
        if profile.half_internet_routes:
            lines.append("half-internet-routes = 1")
        path.write_text("\n".join(lines) + "\n")
