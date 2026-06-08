# Fortyfax

> Native GTK4/Adwaita GUI for [openfortivpn](https://github.com/adrienverge/openfortivpn) and [GlobalProtect-openconnect](https://github.com/yuezk/GlobalProtect-openconnect) with full support for **SAML/SSO** authentication.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![GTK4](https://img.shields.io/badge/GTK-4.0-green)
![Adwaita](https://img.shields.io/badge/libadwaita-1.0-purple)
![License](https://img.shields.io/badge/license-GPL--3.0-orange)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)

> [!NOTE]
> The GitHub repository ([fpellizz/fortyfax](https://github.com/fpellizz/fortyfax)) is a **read-only mirror**, synchronized automatically. Development happens on [Bitbucket](https://bitbucket.org/decisyon/fortyfax): pull requests and issues should be filed there. Pre-built packages (RPM/DEB) can be downloaded from the [Downloads](https://bitbucket.org/decisyon/fortyfax/downloads/) section on Bitbucket.

---

## Overview

Fortyfax was born to solve a concrete problem: connecting to corporate VPNs from Linux without having to use proprietary clients (FortiClient, GlobalProtect) that have compatibility issues on recent distributions.

The application supports two VPN backends:

- **Fortinet/FortiGate** via `openfortivpn`
- **Palo Alto GlobalProtect** via `gpclient` (GlobalProtect-openconnect)

Main features:

- **SAML/SSO login**: integrated webview for Fortinet (captures SVPNCOOKIE), system browser for GlobalProtect
- **Credential auto-fill** (email/password) on the Identity Provider form (Fortinet)
- **Classic username/password login** with encrypted password saved in the profile
- **Multi-profile management** with a full graphical editor
- **Native interface** that integrates with the desktop (GTK4 + libadwaita, compatible with GNOME and KDE Plasma)
- **System tray icon** with connection status, context menu and hide-on-close
- **Desktop notifications** for connection, disconnection and errors (GNOME and KDE)
- **DNS watchdog** for GlobalProtect: keeps the correct DNS configuration on the VPN interface
- **Real-time logging** of the VPN connection
- **Prerequisite check** with explanatory error messages and fix instructions

## Screenshots

> To capture the screenshots: launch Fortyfax, use `Spectacle` (KDE) or `gnome-screenshot` (GNOME) and save the images in the `screenshots/` folder.

### Application icon

![Fortyfax](icons/fortyfax_128.png)

The system tray icon changes color depending on the VPN status:

| Status | Icon | Color |
| ------ | ---- | ----- |
| App started, no VPN | ![Idle](icons/tray_idle_32.png) | White |
| VPN connected | ![Connected](icons/tray_connected_32.png) | Green |
| VPN disconnected | ![Disconnected](icons/tray_disconnected_32.png) | Gray |
| Error | ![Error](icons/tray_error_32.png) | Yellow |

## Features

### Supported VPN backends

| Backend | Client | Authentication | Notes |
| ------- | ------ | -------------- | ----- |
| **Fortinet/FortiGate** | `openfortivpn` | SAML/SSO (integrated webview), Password | Automatic SVPNCOOKIE capture, IdP credential auto-fill |
| **Palo Alto GlobalProtect** | `gpclient` | SAML/SSO (system browser), Password | DNS watchdog, HIP report, OpenSSL legacy fix |

### Profile management

- Create, edit and delete VPN profiles
- VPN type selection (Fortinet / GlobalProtect) with conditional fields
- Real-time field validation
- Full configuration: host, port, realm, trusted certificate, extra arguments
- Secure storage in `~/.config/fortyfax/profiles/` (JSON format)
- **Profile import/export** in JSON format (from the hamburger menu or per single profile)
- Export in native openfortivpn config format

### Network (Fortinet)

- VPN route management (enable/disable)
- DNS configuration through the tunnel
- PPP Peer DNS
- Half internet routes (`0.0.0.0/1` + `128.0.0.0/1`)
- Customizable extra arguments for openfortivpn

### Network (GlobalProtect)

- **DNS watchdog**: monitors and keeps the correct DNS configuration on the tun interface
- **Extra DNS domains**: forces specific search domains on `systemd-resolved`
- **VPN DNS IP**: forces a specific DNS server on the tunnel interface
- **HIP Report**: sends a Host Identity Profile report to the server
- **Configurable MTU**: to avoid packet loss on unstable connections
- **Disable DTLS**: forces TCP over HTTPS for better stability
- **OpenSSL legacy fix**: compatibility with older VPN servers

### Interface

- Native design with libadwaita (compatible with GNOME and KDE Plasma)
- Connection status with visual feedback (icons, spinner, banner)
- **System tray icon** (AppIndicator3):
  - Shield colored by status: white (idle), green (connected), gray (disconnected), yellow (error)
  - Context menu: status, profile selection, connect/disconnect, show/hide, quit
  - Closing the window hides it in the tray (the app stays active)
  - Compatible with KDE Plasma, GNOME (with the AppIndicator extension), XFCE
- **Light/Dark theme support**: manual selection (Light, Dark) or automatic from the system
- **Desktop notifications**: native notifications for established connection, disconnection and errors (compatible with GNOME/KDE via Gio.Notification)
- **Application preferences** accessible from the menu (Ctrl+,), with a notifications toggle
- Integrated log viewer with automatic scroll
- Prerequisite check accessible from the menu

## System requirements

**Common dependencies:**

| Dependency | Minimum version | Fedora | Debian/Ubuntu |
| ---------- | --------------- | ------ | ------------- |
| Python | 3.10+ | `python3` | `python3` |
| GTK 4 | 4.0+ | `gtk4` | `gir1.2-gtk-4.0` |
| libadwaita | 1.0+ | `libadwaita` | `gir1.2-adw-1` |
| PyGObject | 3.42+ | `python3-gobject` | `python3-gi` |
| WebKitGTK | 6.0+ | `webkitgtk6.0` | `gir1.2-webkit-6.0` |
| libsecret | 1.0+ | `libsecret` | `gir1.2-secret-1` |
| PolicyKit | — | `polkit` | `polkitd` (Ubuntu 24.04+) / `policykit-1` (older) |
| AppIndicator3 | — | `libappindicator-gtk3` | `gir1.2-appindicator3-0.1` |

**Fortinet dependencies (openfortivpn):**

| Dependency | Fedora | Debian/Ubuntu |
| ---------- | ------ | ------------- |
| openfortivpn | `openfortivpn` | `openfortivpn` |
| pppd | `ppp` | `ppp` |

**GlobalProtect dependencies (Palo Alto):**

| Dependency | Fedora | Debian/Ubuntu |
| ---------- | ------ | ------------- |
| gpclient | `globalprotect-openconnect` (COPR) | `globalprotect-openconnect` (PPA) |
| openconnect | `openconnect` | `openconnect` |
| vpnc-script | `vpnc-script` | `vpnc` |

## Installation

### Install from package (recommended)

Pre-built packages are available in the [Downloads](https://bitbucket.org/decisyon/fortyfax/downloads/) section on Bitbucket and in the [Releases](https://github.com/fpellizz/fortyfax/releases) of the GitHub mirror. They are generated automatically by CI on every `v*` tag.

**Fedora / RHEL:**

```bash
sudo dnf install ./fortyfax-<version>-1.noarch.rpm
```

**Debian / Ubuntu:**

```bash
sudo apt install ./fortyfax_<version>_all.deb
```

The package installs the application, launcher, `.desktop` file, icons and PolicyKit policy, and automatically pulls in the common dependencies (GTK4, libadwaita, PyGObject, ...).

**GlobalProtect dependencies** (only if you use Palo Alto, not packaged in the distros):

```bash
# Fedora
sudo dnf install -y openconnect vpnc-script
sudo dnf copr enable yuezk/globalprotect-openconnect
sudo dnf install -y globalprotect-openconnect

# Debian / Ubuntu
sudo apt install -y openconnect vpnc
sudo add-apt-repository ppa:yuezk/globalprotect-openconnect
sudo apt install -y globalprotect-openconnect
```

### Running without installing

```bash
git clone https://bitbucket.org/decisyon/fortyfax.git
cd fortyfax
python3 ./fortyfax-bin

# (One-time) install the PolicyKit policy to avoid repeated password prompts:
sudo ./dev-setup-policy.sh
```

**Important note about passwords**: to connect to the VPN, Fortyfax must run `openfortivpn` or `gpclient` as root (via `pkexec`). To avoid typing the password on every connect/disconnect, you must:

- **Install the .rpm/.deb package** (preferred): the PolicyKit policy is installed automatically, no password required for the active user
- **Or run `sudo ./dev-setup-policy.sh`** once: installs the policy pointing to the current development path

Without one of these two things, every connect/disconnect will ask for the system password.

### Building the packages

The packages are built with the distros' native tools: `rpmbuild` with the spec in `packaging/rpm/` (Fedora Packaging Guidelines) and `dpkg-buildpackage` with the `debian/` directory (Debian Policy).

```bash
# RPM (requires: rpm-build, python3-devel, desktop-file-utils)
./build-pkg.sh rpm

# DEB (requires: debhelper, dpkg-dev)
./build-pkg.sh deb

# Both (requires both toolchains)
./build-pkg.sh
```

The packages are generated in the `dist/` folder. For a coordinated version bump (`__init__.py` + spec + `debian/changelog`) use `./scripts/bump-version.sh X.Y.Z`.

### Prerequisite check

The application includes a built-in checker. You can run it standalone:

```bash
python3 -m fortyfax.check
```

Example output (the checker currently prints in Italian):

```
╔══════════════════════════════════════════════════════╗
║            Fortyfax - Verifica Prerequisiti          ║
╠══════════════════════════════════════════════════════╣
║   ✓  Python >= 3.10       Python 3.14.3             ║
║   ✓  openfortivpn         Trovato: /usr/bin/...     ║
║   ✓  GTK 4                OK                        ║
║   ✓  libadwaita           OK                        ║
║   ✓  WebKitGTK 6.0        OK                        ║
║   ✓  libsecret            OK                        ║
║   ✓  pkexec (PolicyKit)   Trovato: /usr/bin/pkexec  ║
║   ✓  pppd                 Trovato                   ║
╚══════════════════════════════════════════════════════╝

✓ Tutti i prerequisiti sono soddisfatti!
```

If something is missing, the checker shows the exact command to fix it.

### Uninstallation

```bash
# Fedora / RHEL
sudo dnf remove fortyfax

# Debian / Ubuntu
sudo apt remove fortyfax
```

Profiles in `~/.config/fortyfax/` are **not** removed.

## Usage

### First launch

1. Launch `fortyfax`
2. Click **"+"** to create a new VPN profile
3. Select the **VPN type**: Fortinet (openfortivpn) or GlobalProtect (Palo Alto)
4. Fill in the fields (they change based on the selected type):
   - **Profile name**: a descriptive name (e.g. "Office VPN")
   - **Host**: hostname or IP of the VPN server (e.g. `vpn.company.com`)
   - **Port**: usually `443` (Fortinet only)
   - **Authentication method**: SAML/SSO or Username/Password
5. Save the profile

### Fortinet SAML/SSO connection

1. Select the Fortinet profile with SAML authentication
2. Click **"Connect"**
3. An integrated browser window opens with your IdP's login page
4. Complete authentication (Azure AD, Okta, Google, etc.)
5. The SVPNCOOKIE cookie is captured automatically
6. The VPN connection starts automatically

### GlobalProtect connection

1. Select the GlobalProtect profile
2. Click **"Connect"**
3. For SSO: **Chrome/Edge** (or the default browser) opens with the IdP login page. The browser's password manager remembers the SSO credentials.
4. For Password: if the password is saved in the profile, the connection starts automatically. Otherwise it is prompted.
5. The VPN connection starts. If configured, the extra DNS domains are applied automatically

**SSO browser choice**: from **Preferences > SSO Browser** you can choose which browser to use for GlobalProtect login. In "Automatic" mode, Fortyfax searches in this order: Google Chrome/Chromium, Microsoft Edge, system default browser. Chrome and Edge have built-in password managers that remember the Identity Provider credentials.

**GlobalProtect-specific fields:**

- **Gateway**: address of the specific gateway (optional, if the portal has many)
- **Extra DNS domains**: internal domains to resolve over the VPN (e.g. `company.com internal.net`)
- **VPN DNS IP**: IP of the internal DNS server if autodiscovery fails
- **HIP Report**: enables sending the Host Identity Profile (required by some servers)
- **MTU**: lower the MTU value to avoid packet loss (0 = default)
- **Disable DTLS**: forces TCP for more stable connections
- **OpenSSL legacy fix**: compatibility with older VPN servers

### Saved credentials

For any profile (SAML/SSO or Password), username and password can be saved directly in the profile editor:

1. Open the VPN profile editor (pencil icon)
2. Select the authentication method (SAML/SSO or Password)
3. Fill in the **Username** and **Password** fields (the labels change based on the chosen method)
4. Save the profile

**For SAML/SSO**: on the next **"Connect"**, the webview will automatically fill the email and password fields in the Identity Provider's login form (Keycloak, Microsoft, Okta, Google, etc.).

**For Password**: the connection starts automatically without asking anything. If the password is not saved, it is prompted with a dialog.

Passwords are **encrypted** (PBKDF2 + random salt) and saved in the profile's JSON file. The encryption key is in `~/.config/fortyfax/.secret` (permissions `0600`), generated automatically on first use.

### Trusted certificate

On the first connection, openfortivpn shows the SHA256 hash of the server certificate in the log. Copy that hash into the profile's **"Trusted certificate"** field to avoid the warning on subsequent connections.

You can view the log by clicking the terminal icon in the top bar.

### Profile import/export

**Export a single profile**: In the profile list, click the save icon (💾) next to the desired profile to export it to a JSON file.

**Export all profiles**: Hamburger menu > **Export all profiles...** saves all profiles into a single JSON file.

**Passwords** (VPN and SSO) are **not** included in the exported files for security reasons.

**Import**: Hamburger menu > **Import profiles...** loads profiles from a JSON file (either single or multiple). Each imported profile gets a new identifier, so it does not overwrite existing ones.

The file format is JSON with this structure:

```json
{
  "fortyfax_version": "1.4.0",
  "profiles": [
    { "name": "Office VPN", "host": "vpn.company.com", "port": 443, ... }
  ]
}
```

### Desktop notifications

Fortyfax sends desktop notifications when:
- The VPN **connects** successfully
- The VPN **disconnects**
- A connection **error** occurs

Notifications work natively on **GNOME** and **KDE Plasma** (via `Gio.Notification` and xdg-desktop-portal). They can be disabled from **Preferences > Notifications**.

### Disconnection

Click **"Disconnect"** to cleanly terminate the VPN connection.

## Project structure

```
fortyfax/
├── fortyfax-bin              # Executable launcher
├── fortyfax-vpn-helper       # Helper to start/stop the VPN (openfortivpn/gpclient) via pkexec
├── build-pkg.sh              # Script to generate RPM and DEB packages (rpmbuild/dpkg-buildpackage)
├── packaging/rpm/            # RPM spec + rpmlintrc (Fedora Packaging Guidelines)
├── debian/                   # Debian packaging (control, rules, changelog, ...)
├── data/                     # Desktop file and PolicyKit policy
├── scripts/                  # bump-version.sh and maintenance utilities
├── dev-setup-policy.sh       # Installs the PolicyKit policy for the dev path (avoids password prompts)
├── README.md
├── LICENSE
├── icons/                    # Application icons
│   ├── fortyfax.svg           # Source app icon (vector SVG)
│   └── fortyfax_*.png         # App icon in various sizes (16-512px)
└── fortyfax/                 # Python package
    ├── __init__.py            # Metadata (version, app_id)
    ├── __main__.py            # Entry point for `python -m fortyfax`
    ├── app.py                 # Adwaita application (lifecycle, menu, shortcuts)
    ├── auth.py                # SAML/SSO authentication via WebKitGTK (Fortinet)
    ├── check.py               # System prerequisite check (Fortinet + GlobalProtect)
    ├── connection.py          # VPN connection management (Fortinet + GlobalProtect + DNS watchdog)
    ├── credential_store.py    # Credential storage via libsecret (legacy, compatibility)
    ├── distro.py              # Linux distro detection and package name mapping
    ├── crypto.py              # Local VPN password encryption (PBKDF2 + salt)
    ├── dialogs.py             # Dialogs: profile editor, password, log viewer, preferences
    ├── profile.py             # Profile data model + JSON persistence
    ├── settings.py            # Application settings (theme, JSON persistence)
    ├── tray.py                # Tray icon proxy (launches a GTK3 sub-process)
    ├── tray_subprocess.py     # GTK3 + AppIndicator3 sub-process for the tray
    └── window.py              # Main window (profile list, status)
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                       Fortyfax                           │
│                  (GTK4 + libadwaita)                     │
├────────────┬────────────┬────────────────────────────────┤
│  Window    │  Dialogs   │   Auth                         │
│  - Profile │  - Editor  │   - SAML webview (Fortinet)    │
│    list    │  - Password│   - System browser (GP)        │
│  - Status  │  - Log     │   - Cookie capture             │
├────────────┴────────────┼────────────────────────────────┤
│  Connection Manager     │   Tray Icon                    │
│  - Fortinet backend     │   - AppIndicator3              │
│  - GlobalProtect backend│   - GTK3 sub-process           │
│  - DNS Watchdog (GP)    │   - JSON pipe IPC              │
│  - Subprocess via pkexec│                                │
├─────────────────────────┴────────────────────────────────┤
│                  Profile Manager                         │
│  - JSON profile CRUD (Fortinet + GlobalProtect)          │
│  - ~/.config/fortyfax/profiles/                          │
│  - Import/export + validation                            │
├──────────────────────────────────────────────────────────┤
│                  Operating system                        │
│  fortyfax-vpn-helper ─ openfortivpn ─ pppd  (Fortinet)  │
│  fortyfax-vpn-helper ─ gpclient ─ openconnect (GP)      │
│  pkexec ─ PolicyKit (allow_active=yes)                   │
│  resolvectl ─ systemd-resolved (DNS watchdog GP)         │
└──────────────────────────────────────────────────────────┘
```

### SAML/SSO flow

```
Fortyfax            WebKitGTK              FortiGate              IdP
 │                      │                      │                    │
 │── open webview ─────>│                      │                    │
 │                      │── GET /remote/saml/ ─>│                    │
 │                      │<── redirect to IdP ───│                    │
 │                      │───────────────── redirect ───────────────>│
 │                      │                      │                    │
 │                      │     (user authenticates with the IdP)     │
 │                      │                      │                    │
 │                      │<──────────── POST SAML response ─────────│
 │                      │── POST assertion ────>│                    │
 │                      │<── Set-Cookie: SVPN ──│                    │
 │<── cookie captured ──│                      │                    │
 │                      │                      │                    │
 │── openfortivpn --cookie-on-stdin ──────────>│                    │
 │<── tunnel established ──────────────────────│                    │
```

## Configuration

### Profile file

Profiles are saved in `~/.config/fortyfax/profiles/<uuid>.json`:

```json
{
  "name": "Office VPN",
  "host": "vpn.company.com",
  "port": 443,
  "username": "user",
  "auth_method": "password",
  "encrypted_password": "base64...",
  "trusted_cert": "a1b2c3d4e5f6...",
  "realm": "",
  "vpn_type": "fortinet",
  "set_dns": true,
  "set_routes": true,
  "pppd_use_peerdns": true,
  "half_internet_routes": false,
  "extra_args": "",
  "uid": "550e8400-e29b-41d4-a716-446655440000"
}
```

For GlobalProtect profiles the fields `gp_gateway`, `gp_extra_dns`, `gp_vpn_dns`, `gp_hip`, `gp_mtu`, `gp_no_dtls`, `gp_fix_openssl` are added.

### Password encryption

VPN passwords are encrypted with:

- **Key**: 32 random bytes in `~/.config/fortyfax/.secret` (permissions `0600`)
- **Algorithm**: PBKDF2-SHA256 (100,000 iterations) + XOR
- **Salt**: 16 random bytes for each encryption (the same text produces different tokens)
- **Format**: base64(salt + encrypted_data) in the `encrypted_password` field of the JSON

The key never leaves the machine. If the `.secret` file is lost, the passwords must be re-entered. Passwords are **not** included in the profile export.

### Application settings

The global settings are saved in `~/.config/fortyfax/settings.json`:

```json
{
  "theme": "system",
  "notifications": true,
  "sso_browser": "auto"
}
```

Available values for `notifications`: `true` (default) or `false`.

Available values for `sso_browser`:

- `"auto"` — searches for Chrome/Chromium, then Edge, then the default browser (default)
- `"chrome"` — forces Google Chrome or Chromium
- `"edge"` — forces Microsoft Edge
- `"xdg-open"` — uses the system default browser

Available values for `theme`:

- `"system"` — follows the operating system theme (default)
- `"light"` — forces the light theme
- `"dark"` — forces the dark theme

The settings are accessible from the hamburger menu > **Preferences** (or `Ctrl+,`).

### PolicyKit

The package installs a PolicyKit policy that allows starting and terminating openfortivpn **without a password prompt** for the active user on the local session (`allow_active=yes`).

This happens through the helper script `fortyfax-vpn-helper` which:

- Accepts only the `start`, `stop`, `kill` and `dns` commands
- Supports both `openfortivpn` and `gpclient` as backends
- Verifies that the PID to terminate is actually a VPN process

The policy is installed in `/usr/share/polkit-1/actions/com.github.fortyfax.policy`.

## Troubleshooting

### SSO authentication does not work

**Problem**: The SSO window does not open or returns an error.

**Solution**: Verify that WebKitGTK 6.0 is installed:
```bash
sudo dnf install webkitgtk6.0
python3 -c "import gi; gi.require_version('WebKit', '6.0'); print('OK')"
```

### "Certificate not trusted" error

**Problem**: openfortivpn rejects the server certificate.

**Solution**: Connect a first time, open the log (terminal icon), find the line with the certificate's SHA256 hash and paste it into the profile's "Trusted certificate" field.

### pkexec does not ask for the password / Permission denied

**Problem**: PolicyKit is not working correctly.

**Solution**:
```bash
# Reinstall the package to restore the policy
sudo dnf reinstall fortyfax        # Fedora/RHEL
sudo apt reinstall fortyfax        # Debian/Ubuntu
```

### The connection drops immediately

**Problem**: openfortivpn closes after a few seconds.

**Solution**: Check the log for specific errors. Common causes:
- `pppd` not installed: `sudo dnf install ppp`
- Conflicting routes: try enabling "Half internet routes" in the profile
- Conflicting DNS: try disabling "Set DNS" in the profile

### The system tray icon does not appear

**Problem**: The tray icon is not visible in the panel.

**Solution**:

1. Verify that AppIndicator3 is installed:
```bash
sudo dnf install libappindicator-gtk3
```

2. On GNOME, install the "AppIndicator and KStatusNotifierItem Support" extension:
```bash
sudo dnf install gnome-shell-extension-appindicator
```
   After installing, restart the session or enable the extension from GNOME Extensions.

On KDE Plasma and XFCE, AppIndicator support is native.

### FortiClient vs Fortyfax

FortiClient for Linux (RPM) is built for EL7 and does not work on recent Fedora because of:
- RPM without digest (rejected by modern `rpm`)
- Dependency on `openssl/engine.h`, removed in OpenSSL 3.x

Fortyfax solves both problems by using `openfortivpn` as the backend.

### GlobalProtect: gpclient not found

**Problem**: The checker shows `gpclient` as missing.

**Solution**: Install GlobalProtect-openconnect from the COPR:

```bash
sudo dnf copr enable yuezk/globalprotect-openconnect
sudo dnf install globalprotect-openconnect
```

### GlobalProtect: DNS does not work / internal sites unreachable

**Problem**: After the GlobalProtect connection, internal sites are unreachable.

**Solution**:

1. In the profile, add the internal domains in the **"Extra DNS domains"** field (e.g. `company.com internal.net`)
2. If needed, specify the internal DNS IP in the **"VPN DNS IP"** field
3. Fortyfax's DNS watchdog keeps the configuration active for the whole duration of the connection

### GlobalProtect: SSL error / handshake failed

**Problem**: The connection fails with SSL errors.

**Solution**: Enable **"OpenSSL legacy fix"** in the GlobalProtect profile.

### GlobalProtect: unstable connection / packet loss

**Problem**: The connection drops frequently or is very slow.

**Solution**:

- Enable **"Disable DTLS"** to force TCP
- Lower the **MTU** to `1200` or `1262`

## Contributing

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

### Development environment setup

```bash
git clone https://bitbucket.org/decisyon/fortyfax.git
cd fortyfax

# Install dependencies — Fedora:
sudo dnf install -y openfortivpn python3-gobject gtk4 libadwaita \
    webkitgtk6.0 libsecret polkit ppp libappindicator-gtk3 \
    openconnect vpnc-script

# Install dependencies — Debian/Ubuntu:
sudo apt install -y openfortivpn python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-webkit-6.0 gir1.2-secret-1 polkitd ppp \
    gir1.2-appindicator3-0.1 openconnect vpnc

# Run in development mode
python3 ./fortyfax-bin

# Prerequisite check (auto-detects the distro)
python3 -m fortyfax.check
```

## Roadmap

- [x] System tray icon with connection status
- [x] Profile import/export
- [x] Desktop notifications (connect/disconnect)
- [x] Light/Dark theme support with preferences
- [x] GlobalProtect (Palo Alto) support with DNS watchdog
- [ ] Auto-connect at system startup
- [ ] Simultaneous multi-connection support
- [x] RPM/DEB packaging

## License

This project is released under the [GPL-3.0](LICENSE) license.

## Credits

- [openfortivpn](https://github.com/adrienverge/openfortivpn) — the VPN backend
- [GTK](https://gtk.org/) / [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) — the graphical toolkit
- [WebKitGTK](https://webkitgtk.org/) — the web engine for SAML authentication
