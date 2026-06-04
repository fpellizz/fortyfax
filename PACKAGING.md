# Packaging di Fortyfax

## Stato attuale

| Formato | Strumento | Sorgente | Validazione | Dove si pubblica |
|---|---|---|---|---|
| RPM | `rpmbuild` | `packaging/rpm/fortyfax.spec` (Fedora Packaging Guidelines) | `rpmlint` (0 errori, filtri in `fortyfax.rpmlintrc`) | Bitbucket Downloads + GitHub Release |
| DEB | `dpkg-buildpackage` | `debian/` (Debian Policy, debhelper-compat 13) | `lintian --fail-on error` | Bitbucket Downloads + GitHub Release |

- **Versione**: fonte unica `fortyfax/__init__.py`; `build-pkg.sh` verifica l'allineamento con spec e `debian/changelog` e fallisce se divergono. Bump coordinato: `./scripts/bump-version.sh X.Y.Z "nota"`.
- **CI**: build paralleli su container `fedora:latest` (RPM) e `debian:bookworm` (DEB), sia su Bitbucket Pipelines che su GitHub Actions (release sui tag `v*`).
- **File condivisi**: desktop file e policy PolicyKit in `data/`, usati da entrambi i packaging.

## Valutazione OpenSUSE Build Service (OBS)

### Cos'è

[OBS](https://build.opensuse.org) è il servizio di build pubblico di openSUSE: da un'unica sorgente builda pacchetti per **molte distro e architetture** (openSUSE Tumbleweed/Leap, Fedora, RHEL/EPEL, Debian, Ubuntu, Arch...) e pubblica **repository installabili** che gli utenti aggiungono a zypper/dnf/apt — con aggiornamenti automatici a ogni release, senza scaricare file a mano.

### Pro

- **Repository per gli utenti**: `dnf config-manager addrepo ...` una volta sola, poi gli aggiornamenti arrivano col sistema. Esperienza molto migliore del download manuale da Downloads/Release.
- **Copertura openSUSE**: oggi non offriamo nulla per zypper; OBS la aggiunge quasi gratis.
- **Multi-versione**: builda per Fedora N, N-1, Leap, Tumbleweed, ecc. in parallelo — intercetta rotture su distro che non testiamo (es. rinomini di pacchetti).
- **Sorgenti dal mirror GitHub**: il servizio `obs_scm` può scaricare i sorgenti dal mirror pubblico `github.com/fpellizz/fortyfax` a ogni tag — nessun cambiamento al flusso Bitbucket.
- **Lo spec c'è già**: il grosso del lavoro (questo repo) è fatto. Servono solo ritocchi condizionali (vedi sotto).

### Contro

- **Un sistema in più da mantenere**: account openSUSE, progetto `home:fpellizz:fortyfax`, monitoraggio build (le distro target cambiano nel tempo).
- **Nomi dei pacchetti divergenti**: lo spec attuale usa nomi Fedora (`python3-gobject`, `webkitgtk6.0`, `libadwaita`); su openSUSE servono i provides `typelib(Gtk) = 4.0`-style o nomi diversi → lo spec va condizionato con `%if 0%{?suse_version}`.
- **DEB su OBS è più macchinoso**: richiede `.dsc` + `debian.tar.gz` separati e regole proprie; visto che i DEB li produciamo già bene in CI, conviene **non** usare OBS per i deb (almeno all'inizio).
- **gpclient non esiste in nessuna distro**: resta `Suggests`, l'utente GlobalProtect deve comunque aggiungere COPR/PPA — OBS non risolve questo.

### Raccomandazione

**Sì, ma con scope ridotto**: progetto OBS `home:fpellizz:fortyfax` con target **openSUSE Tumbleweed + Leap 15.6 + Fedora (ultime 2)**, solo RPM. I DEB restano alla CI esistente. Effort stimato: mezza giornata per il setup iniziale, poi ~zero (i tag arrivano da soli via `obs_scm` dal mirror).

### Setup (quando si decide di farlo)

1. Account su https://idp-portal.suse.com → https://build.opensuse.org
2. `osc meta pkg home:fpellizz:fortyfax fortyfax -e` (o dalla web UI)
3. File `_service` nel package OBS:

```xml
<services>
  <service name="obs_scm">
    <param name="url">https://github.com/fpellizz/fortyfax.git</param>
    <param name="scm">git</param>
    <param name="revision">master</param>
    <param name="versionformat">@PARENT_TAG@</param>
    <param name="versionrewrite-pattern">v(.*)</param>
  </service>
  <service name="tar" mode="buildtime"/>
  <service name="recompress" mode="buildtime">
    <param name="compression">gz</param>
  </service>
  <service name="set_version" mode="buildtime"/>
</services>
```

4. Copia di `packaging/rpm/fortyfax.spec` con le dipendenze condizionate:

```spec
%if 0%{?suse_version}
Requires:       python3-gobject
Requires:       typelib(Gtk) = 4.0
Requires:       typelib(Adw) = 1
Requires:       typelib(WebKit) = 6.0
Requires:       typelib(Secret) = 1
%else
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       webkitgtk6.0
Requires:       libsecret
%endif
```

5. Target nel progetto: `openSUSE_Tumbleweed`, `15.6`, `Fedora_43`, `Fedora_42`
6. Repo per gli utenti (esempio):
   ```bash
   # openSUSE
   zypper addrepo https://download.opensuse.org/repositories/home:fpellizz:fortyfax/openSUSE_Tumbleweed/home:fpellizz:fortyfax.repo
   # Fedora
   dnf config-manager addrepo --from-repofile=https://download.opensuse.org/repositories/home:fpellizz:fortyfax/Fedora_43/home:fpellizz:fortyfax.repo
   ```
