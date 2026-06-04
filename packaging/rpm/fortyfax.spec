Name:           fortyfax
Version:        2.3.4
Release:        1%{?dist}
Summary:        GUI for openfortivpn and GlobalProtect with SAML/SSO support

License:        GPL-3.0-only
URL:            https://bitbucket.org/decisyon/fortyfax
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel >= 3.10
BuildRequires:  desktop-file-utils

Requires:       python3 >= 3.10
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       webkitgtk6.0
Requires:       libsecret
Requires:       polkit
# Backend Fortinet (l'app funziona anche solo con GlobalProtect)
Recommends:     openfortivpn
Recommends:     ppp
# Icona nel system tray (opzionale, l'app degrada con grazia senza)
Recommends:     libappindicator-gtk3
# Backend GlobalProtect: globalprotect-openconnect non e' in Fedora
# (richiede il COPR yuezk/globalprotect-openconnect), quindi non e'
# dichiarabile nemmeno come Recommends.
Suggests:       openconnect
Suggests:       vpnc-script

%description
Fortyfax is a native GTK4/libadwaita GUI for openfortivpn (Fortinet
FortiGate) and GlobalProtect-openconnect (Palo Alto), with full
SAML/SSO authentication support, profile management, system tray
icon, desktop notifications and a DNS watchdog for GlobalProtect.

%prep
%autosetup

%build
# Applicazione Python pura installata in %%{_datadir}: nessuna build.

%install
# Applicazione
install -dm755 %{buildroot}%{_datadir}/%{name}
cp -a fortyfax %{buildroot}%{_datadir}/%{name}/fortyfax
find %{buildroot}%{_datadir}/%{name} -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find %{buildroot}%{_datadir}/%{name} -name '*.pyc' -delete
# Icone private: solo quelle del tray (AppIndicator le risolve via
# set_icon_theme_path su questa dir); l'icona dell'app sta nel tema
# hicolor di sistema, niente copie duplicate.
install -dm755 %{buildroot}%{_datadir}/%{name}/icons
install -m644 icons/tray_*.png icons/tray_*.svg %{buildroot}%{_datadir}/%{name}/icons/
install -m755 fortyfax-bin %{buildroot}%{_datadir}/%{name}/fortyfax-bin
install -m755 fortyfax-vpn-helper %{buildroot}%{_datadir}/%{name}/fortyfax-vpn-helper

# Launcher (symlink, il path /usr/bin/fortyfax-vpn-helper e' referenziato
# dalla annotazione exec.path della policy PolicyKit)
install -dm755 %{buildroot}%{_bindir}
ln -s ../share/%{name}/fortyfax-bin %{buildroot}%{_bindir}/fortyfax
ln -s ../share/%{name}/fortyfax-vpn-helper %{buildroot}%{_bindir}/fortyfax-vpn-helper

# Desktop file
install -Dm644 data/com.github.fortyfax.desktop \
    %{buildroot}%{_datadir}/applications/com.github.fortyfax.desktop

# PolicyKit policy
install -Dm644 data/com.github.fortyfax.policy \
    %{buildroot}%{_datadir}/polkit-1/actions/com.github.fortyfax.policy

# Icone hicolor
for size in 16 24 32 48 64 128 256 512; do
    install -Dm644 icons/fortyfax_${size}.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/com.github.fortyfax.png
done
install -Dm644 icons/fortyfax.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/com.github.fortyfax.svg

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/com.github.fortyfax.desktop

%files
%license LICENSE
%doc README.md
%{_datadir}/%{name}/
%{_bindir}/fortyfax
%{_bindir}/fortyfax-vpn-helper
%{_datadir}/applications/com.github.fortyfax.desktop
%{_datadir}/polkit-1/actions/com.github.fortyfax.policy
%{_datadir}/icons/hicolor/*/apps/com.github.fortyfax.png
%{_datadir}/icons/hicolor/scalable/apps/com.github.fortyfax.svg

%changelog
* Thu Jun 04 2026 Fabio Pellizzaro <fabio.pellizzaro@decisyon.com> - 2.3.4-1
- Packaging nativo conforme a Fedora Guidelines e Debian Policy (rpmbuild/dpkg-buildpackage), pyproject.toml, rimossi install.sh/uninstall.sh

* Wed Jun 03 2026 Fabio Pellizzaro <fabio.pellizzaro@decisyon.com> - 2.3.3-1
- Packaging conforme alle Fedora Packaging Guidelines (spec nativo, addio fpm)
- Fix avvio GlobalProtect (helper auto-SIGTERM) e messaggi di errore parlanti
