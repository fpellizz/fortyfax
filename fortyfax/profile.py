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
    sso_username: str = ""
    extra_args: str = ""
    vpn_type: str = "fortinet"  # "fortinet", "globalprotect"
    # GlobalProtect-specific fields
    gp_gateway: str = ""
    gp_extra_dns: str = ""  # space-separated domains
    gp_vpn_dns: str = ""  # forced DNS server IP
    gp_hip: bool = False
    gp_mtu: int = 0  # 0 = default (no override)
    gp_no_dtls: bool = False
    gp_fix_openssl: bool = False
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def display_host(self) -> str:
        if self.vpn_type == "globalprotect":
            return self.host
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

    def to_gpclient_args(self) -> list[str]:
        """Build gpclient CLI arguments from this profile."""
        args = ["connect", self.host]
        if self.gp_gateway:
            args += ["--gateway", self.gp_gateway]
        if self.username:
            args += ["--user", self.username]
        if self.gp_hip:
            args.append("--hip")
        if self.gp_mtu and self.gp_mtu > 0:
            args += ["--mtu", str(self.gp_mtu)]
        if self.gp_no_dtls:
            args.append("--no-dtls")
        if self.gp_fix_openssl:
            args.append("--fix-openssl")
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
        if self.vpn_type == "fortinet":
            if not (1 <= self.port <= 65535):
                errors.append("La porta deve essere tra 1 e 65535")
            if self.auth_method == "password" and not self.username.strip():
                errors.append("Lo username è obbligatorio per l'autenticazione con password")
        elif self.vpn_type == "globalprotect":
            if self.gp_mtu and not (0 <= self.gp_mtu <= 9000):
                errors.append("L'MTU deve essere tra 0 e 9000")
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

    def export_profiles(self, path: Path, profiles: list[VPNProfile] | None = None) -> int:
        """Export profiles to a JSON file. Returns number of profiles exported."""
        from . import __version__
        if profiles is None:
            profiles = self.load_all()
        data = {
            "fortyfax_version": __version__,
            "profiles": [],
        }
        for p in profiles:
            d = asdict(p)
            del d["uid"]  # don't export UIDs — new ones on import
            data["profiles"].append(d)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        return len(profiles)

    def import_profiles(self, path: Path) -> tuple[int, list[str]]:
        """Import profiles from a JSON file. Returns (count_imported, errors)."""
        errors = []
        try:
            raw = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            return 0, [f"Impossibile leggere il file: {e}"]

        profiles_data = raw.get("profiles") if isinstance(raw, dict) else raw
        if not isinstance(profiles_data, list):
            return 0, ["Formato file non valido: atteso un array di profili"]

        count = 0
        for i, item in enumerate(profiles_data):
            if not isinstance(item, dict):
                errors.append(f"Profilo #{i+1}: formato non valido")
                continue
            item.pop("uid", None)  # force new UID
            try:
                fields = {k: v for k, v in item.items() if k in VPNProfile.__dataclass_fields__}
                p = VPNProfile(**fields)
                validation = p.validate()
                if validation:
                    errors.append(f"Profilo «{p.name}»: {'; '.join(validation)}")
                    continue
                self.save(p)
                count += 1
            except (TypeError, ValueError) as e:
                errors.append(f"Profilo #{i+1}: {e}")
        return count, errors

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
