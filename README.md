# Fortyfax

> GUI nativa GTK4/Adwaita per [openfortivpn](https://github.com/adrienverge/openfortivpn) e [GlobalProtect-openconnect](https://github.com/yuezk/GlobalProtect-openconnect) con supporto completo per autenticazione **SAML/SSO**.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![GTK4](https://img.shields.io/badge/GTK-4.0-green)
![Adwaita](https://img.shields.io/badge/libadwaita-1.0-purple)
![License](https://img.shields.io/badge/license-GPL--3.0-orange)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)

---

## Panoramica

Fortyfax nasce per risolvere un problema concreto: collegarsi a VPN aziendali da Linux senza dover usare client proprietari (FortiClient, GlobalProtect) che su distribuzioni recenti hanno problemi di compatibilità.

L'applicazione supporta due backend VPN:

- **Fortinet/FortiGate** tramite `openfortivpn`
- **Palo Alto GlobalProtect** tramite `gpclient` (GlobalProtect-openconnect)

Funzionalità principali:

- **Login SAML/SSO**: webview integrata per Fortinet (cattura SVPNCOOKIE), browser di sistema per GlobalProtect
- **Auto-compilazione credenziali** (email/password) sul form dell'Identity Provider (Fortinet)
- **Login con username/password** classico con salvataggio password cifrata nel profilo
- **Gestione profili** multipli con editor grafico completo
- **Interfaccia nativa** che si integra con il desktop (GTK4 + libadwaita, compatibile GNOME e KDE Plasma)
- **Icona nel system tray** con stato connessione, menu contestuale e hide-on-close
- **Notifiche desktop** per connessione, disconnessione ed errori (GNOME e KDE)
- **DNS watchdog** per GlobalProtect: mantiene la configurazione DNS corretta sull'interfaccia VPN
- **Log in tempo reale** della connessione VPN
- **Verifica prerequisiti** con messaggi di errore esplicativi e istruzioni di fix

## Screenshot

> Per catturare gli screenshot: avvia Fortyfax, usa `Spectacle` (KDE) o `gnome-screenshot` (GNOME) e salva le immagini nella cartella `screenshots/`.

### Icona applicazione

![Fortyfax](icons/fortyfax_128.png)

L'icona nella system tray cambia colore in base allo stato della VPN:

| Stato | Icona | Colore |
| ----- | ----- | ------ |
| App avviata, nessuna VPN | ![Idle](icons/tray_idle_32.png) | Bianco |
| VPN connessa | ![Connesso](icons/tray_connected_32.png) | Verde |
| VPN disconnessa | ![Disconnesso](icons/tray_disconnected_32.png) | Grigio |
| Errore | ![Errore](icons/tray_error_32.png) | Giallo |

## Funzionalita

### Backend VPN supportati

| Backend | Client | Autenticazione | Note |
| ------- | ------ | -------------- | ---- |
| **Fortinet/FortiGate** | `openfortivpn` | SAML/SSO (webview integrata), Password | Cattura automatica SVPNCOOKIE, auto-fill credenziali IdP |
| **Palo Alto GlobalProtect** | `gpclient` | SAML/SSO (browser di sistema), Password | DNS watchdog, HIP report, fix OpenSSL legacy |

### Gestione Profili

- Creazione, modifica ed eliminazione profili VPN
- Selezione tipo VPN (Fortinet / GlobalProtect) con campi condizionali
- Validazione campi in tempo reale
- Configurazione completa: host, porta, realm, certificato trusted, argomenti extra
- Salvataggio sicuro in `~/.config/fortyfax/profiles/` (formato JSON)
- **Import/export profili** in formato JSON (dal menu hamburger o per singolo profilo)
- Esportazione in formato config nativo openfortivpn

### Rete (Fortinet)

- Gestione rotte VPN (attiva/disattiva)
- Configurazione DNS tramite tunnel
- PPP Peer DNS
- Half internet routes (`0.0.0.0/1` + `128.0.0.0/1`)
- Argomenti extra personalizzabili per openfortivpn

### Rete (GlobalProtect)

- **DNS watchdog**: monitora e mantiene la configurazione DNS corretta sull'interfaccia tun
- **Domini DNS extra**: forza domini di ricerca specifici su `systemd-resolved`
- **IP DNS VPN**: forza un server DNS specifico sull'interfaccia tunnel
- **HIP Report**: invia Host Identity Profile report al server
- **MTU configurabile**: per evitare packet loss su connessioni instabili
- **Disabilita DTLS**: forza TCP su HTTPS per maggiore stabilità
- **Fix OpenSSL legacy**: compatibilità con server VPN datati

### Interfaccia

- Design nativo con libadwaita (compatibile GNOME e KDE Plasma)
- Stato connessione con feedback visivo (icone, spinner, banner)
- **Icona nel system tray** (AppIndicator3):
  - Scudo colorato in base allo stato: bianco (idle), verde (connesso), grigio (disconnesso), giallo (errore)
  - Menu contestuale: stato, selezione profilo, connetti/disconnetti, mostra/nascondi, esci
  - Chiudere la finestra la nasconde nel tray (l'app resta attiva)
  - Compatibile con KDE Plasma, GNOME (con estensione AppIndicator), XFCE
- **Supporto temi Light/Dark**: selezione manuale (Chiaro, Scuro) o automatica dal sistema
- **Notifiche desktop**: notifiche native per connessione stabilita, disconnessione ed errori (compatibile GNOME/KDE via Gio.Notification)
- **Preferenze applicazione** accessibili dal menu (Ctrl+,), con toggle notifiche
- Viewer log integrato con scroll automatico
- Verifica prerequisiti accessibile dal menu

## Requisiti di sistema

**Dipendenze comuni:**

| Dipendenza | Versione minima | Fedora | Debian/Ubuntu |
| ---------- | --------------- | ------ | ------------- |
| Python | 3.10+ | `python3` | `python3` |
| GTK 4 | 4.0+ | `gtk4` | `gir1.2-gtk-4.0` |
| libadwaita | 1.0+ | `libadwaita` | `gir1.2-adw-1` |
| PyGObject | 3.42+ | `python3-gobject` | `python3-gi` |
| WebKitGTK | 6.0+ | `webkitgtk6.0` | `gir1.2-webkit-6.0` |
| libsecret | 1.0+ | `libsecret` | `gir1.2-secret-1` |
| PolicyKit | — | `polkit` | `polkitd` (Ubuntu 24.04+) / `policykit-1` (vecchie) |
| AppIndicator3 | — | `libappindicator-gtk3` | `gir1.2-appindicator3-0.1` |

**Dipendenze Fortinet (openfortivpn):**

| Dipendenza | Fedora | Debian/Ubuntu |
| ---------- | ------ | ------------- |
| openfortivpn | `openfortivpn` | `openfortivpn` |
| pppd | `ppp` | `ppp` |

**Dipendenze GlobalProtect (Palo Alto):**

| Dipendenza | Fedora | Debian/Ubuntu |
| ---------- | ------ | ------------- |
| gpclient | `globalprotect-openconnect` (COPR) | `globalprotect-openconnect` (PPA) |
| openconnect | `openconnect` | `openconnect` |
| vpnc-script | `vpnc-script` | `vpnc` |

## Installazione

### Installazione rapida (Fedora / RHEL)

```bash
# 1. Installa le dipendenze comuni + Fortinet
sudo dnf install -y openfortivpn python3-gobject gtk4 libadwaita \
    webkitgtk6.0 libsecret polkit ppp libappindicator-gtk3

# 1b. (Opzionale) Installa le dipendenze GlobalProtect
sudo dnf install -y openconnect vpnc-script
sudo dnf copr enable yuezk/globalprotect-openconnect
sudo dnf install -y globalprotect-openconnect

# 2. Clona il repository
git clone https://stazzo@bitbucket.org/decisyon/fortyfax.git
cd fortyfax

# 3. Installa (copia i file, crea .desktop e policy PolicyKit)
sudo ./install.sh

# 4. Avvia
fortyfax
```

### Installazione rapida (Debian / Ubuntu)

```bash
# 1. Installa le dipendenze comuni + Fortinet
sudo apt install -y openfortivpn python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-webkit-6.0 gir1.2-secret-1 polkitd ppp gir1.2-appindicator3-0.1

# 1b. (Opzionale) Installa le dipendenze GlobalProtect
sudo apt install -y openconnect vpnc
sudo add-apt-repository ppa:yuezk/globalprotect-openconnect
sudo apt install -y globalprotect-openconnect

# 2. Clona il repository
git clone https://stazzo@bitbucket.org/decisyon/fortyfax.git
cd fortyfax

# 3. Installa (copia i file, crea .desktop e policy PolicyKit)
sudo ./install.sh

# 4. Avvia
fortyfax
```

### Esecuzione senza installazione

```bash
git clone https://stazzo@bitbucket.org/decisyon/fortyfax.git
cd fortyfax
python3 ./fortyfax-bin
```

### Installazione da pacchetto (RPM / DEB)

I pacchetti pre-compilati sono disponibili nella sezione [Downloads](https://bitbucket.org/decisyon/fortyfax/downloads/) del repository. Vengono generati automaticamente dalla pipeline CI/CD ad ogni tag `v*`.

**Fedora / RHEL:**

```bash
sudo dnf install ./fortyfax-2.2.0-1.noarch.rpm
```

**Debian / Ubuntu:**

```bash
sudo apt install ./fortyfax_2.2.0_all.deb
```

I pacchetti installano automaticamente l'applicazione in `/usr/share/fortyfax`, il launcher in `/usr/bin/fortyfax`, il file `.desktop`, le icone e la policy PolicyKit.

### Build dei pacchetti

Per generare i pacchetti RPM e DEB dal sorgente:

```bash
# Prerequisito: fpm
sudo gem install fpm

# Build entrambi
./build-pkg.sh

# Solo RPM o solo DEB
./build-pkg.sh rpm
./build-pkg.sh deb
```

I pacchetti vengono generati nella cartella `dist/`.

### Verifica prerequisiti

L'applicazione include un checker integrato. Puoi eseguirlo standalone:

```bash
python3 -m fortyfax.check
```

Output di esempio:

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

Se manca qualcosa, il checker mostra il comando esatto per risolvere.

### Disinstallazione

```bash
sudo ./uninstall.sh
```

I profili in `~/.config/fortyfax/` **non** vengono rimossi.

## Utilizzo

### Primo avvio

1. Avvia `fortyfax`
2. Clicca **"+"** per creare un nuovo profilo VPN
3. Seleziona il **Tipo VPN**: Fortinet (openfortivpn) oppure GlobalProtect (Palo Alto)
4. Compila i campi (cambiano in base al tipo selezionato):
   - **Nome profilo**: un nome descrittivo (es. "VPN Ufficio")
   - **Host**: hostname o IP del server VPN (es. `vpn.azienda.com`)
   - **Porta**: di solito `443` (solo Fortinet)
   - **Metodo di autenticazione**: SAML/SSO oppure Username/Password
5. Salva il profilo

### Connessione Fortinet SAML/SSO

1. Seleziona il profilo Fortinet con autenticazione SAML
2. Clicca **"Connetti"**
3. Si apre una finestra browser integrata con la pagina di login del tuo IdP
4. Completa l'autenticazione (Azure AD, Okta, Google, ecc.)
5. Il cookie SVPNCOOKIE viene catturato automaticamente
6. La connessione VPN parte in automatico

### Connessione GlobalProtect

1. Seleziona il profilo GlobalProtect
2. Clicca **"Connetti"**
3. Per SSO: si apre **Chrome/Edge** (o il browser predefinito) con la pagina di login dell'IdP. Il password manager del browser ricorda le credenziali SSO.
4. Per Password: se la password è salvata nel profilo, la connessione parte automaticamente. Altrimenti viene chiesta.
5. La connessione VPN parte. Se configurati, i domini DNS extra vengono applicati automaticamente

**Scelta del browser SSO**: da **Preferenze > Browser SSO** puoi scegliere quale browser usare per il login GlobalProtect. In modalità "Automatico", Fortyfax cerca nell'ordine: Google Chrome/Chromium, Microsoft Edge, browser predefinito di sistema. Chrome e Edge hanno password manager integrati che ricordano le credenziali dell'Identity Provider.

**Campi specifici GlobalProtect:**

- **Gateway**: indirizzo del gateway specifico (opzionale, se il portale ne ha molti)
- **Domini DNS extra**: domini interni da risolvere via VPN (es. `azienda.com internal.net`)
- **IP DNS VPN**: IP del server DNS interno se l'autodiscovery fallisce
- **HIP Report**: abilita l'invio di Host Identity Profile (richiesto da alcuni server)
- **MTU**: abbassa il valore MTU per evitare packet loss (0 = default)
- **Disabilita DTLS**: forza TCP per connessioni più stabili
- **Fix OpenSSL legacy**: compatibilità con server VPN datati

### Credenziali salvate

Per qualsiasi profilo (SAML/SSO o Password), username e password possono essere salvati direttamente nell'editor del profilo:

1. Apri l'editor del profilo VPN (icona matita)
2. Seleziona il metodo di autenticazione (SAML/SSO o Password)
3. Compila i campi **Username** e **Password** (le label cambiano in base al metodo scelto)
4. Salva il profilo

**Per SAML/SSO**: al prossimo **"Connetti"**, la webview compilerà automaticamente i campi email e password nel form di login dell'Identity Provider (Keycloak, Microsoft, Okta, Google, ecc.).

**Per Password**: la connessione parte automaticamente senza chiedere nulla. Se la password non e salvata, viene chiesta con un dialog.

Le password sono **cifrate** (PBKDF2 + salt random) e salvate nel file JSON del profilo. La chiave di cifratura e in `~/.config/fortyfax/.secret` (permessi `0600`), generata automaticamente al primo utilizzo.

### Certificato trusted

Alla prima connessione, openfortivpn mostra l'hash SHA256 del certificato del server nel log. Copia quell'hash nel campo **"Certificato trusted"** del profilo per evitare il warning alle connessioni successive.

Puoi visualizzare il log cliccando l'icona terminale nella barra superiore.

### Import/export profili

**Esportazione singolo profilo**: Nella lista profili, clicca l'icona di salvataggio (💾) accanto al profilo desiderato per esportarlo in un file JSON.

**Esportazione tutti i profili**: Menu hamburger > **Esporta tutti i profili...** salva tutti i profili in un unico file JSON.

Le **password** (VPN e SSO) **non** vengono incluse nei file esportati per sicurezza.

**Importazione**: Menu hamburger > **Importa profili...** carica profili da un file JSON (sia singolo che multiplo). Ogni profilo importato riceve un nuovo identificativo, quindi non sovrascrive quelli esistenti.

Il formato del file e un JSON con questa struttura:

```json
{
  "fortyfax_version": "1.4.0",
  "profiles": [
    { "name": "VPN Ufficio", "host": "vpn.azienda.com", "port": 443, ... }
  ]
}
```

### Notifiche desktop

Fortyfax invia notifiche desktop quando:
- La VPN si **connette** con successo
- La VPN si **disconnette**
- Si verifica un **errore** di connessione

Le notifiche funzionano nativamente su **GNOME** e **KDE Plasma** (tramite `Gio.Notification` e xdg-desktop-portal). Possono essere disabilitate da **Preferenze > Notifiche**.

### Disconnessione

Clicca **"Disconnetti"** per terminare la connessione VPN in modo pulito.

## Struttura del progetto

```
fortyfax/
├── fortyfax-bin              # Launcher eseguibile
├── fortyfax-vpn-helper       # Helper per avvio/stop VPN (openfortivpn/gpclient) via pkexec
├── build-pkg.sh              # Script per generare pacchetti RPM e DEB
├── install.sh                # Script di installazione di sistema (alternativa ai pacchetti)
├── uninstall.sh              # Script di rimozione
├── README.md
├── LICENSE
├── icons/                    # Icone applicazione
│   ├── fortyfax.svg           # Icona app sorgente (SVG vettoriale)
│   └── fortyfax_*.png         # Icona app in varie dimensioni (16-512px)
└── fortyfax/                 # Package Python
    ├── __init__.py            # Metadati (versione, app_id)
    ├── __main__.py            # Entry point per `python -m fortyfax`
    ├── app.py                 # Applicazione Adwaita (lifecycle, menu, shortcuts)
    ├── auth.py                # Autenticazione SAML/SSO via WebKitGTK (Fortinet)
    ├── check.py               # Verifica prerequisiti di sistema (Fortinet + GlobalProtect)
    ├── connection.py          # Gestione connessione VPN (Fortinet + GlobalProtect + DNS watchdog)
    ├── credential_store.py    # Storage credenziali via libsecret (legacy, compatibilità)
    ├── distro.py              # Detection distro Linux e mappatura nomi pacchetti
    ├── crypto.py              # Cifratura locale password VPN (PBKDF2 + salt)
    ├── dialogs.py             # Dialog: editor profili, password, log viewer, preferenze
    ├── profile.py             # Modello dati profili + persistenza JSON
    ├── settings.py            # Impostazioni applicazione (tema, persistenza JSON)
    ├── tray.py                # Proxy tray icon (lancia sotto-processo GTK3)
    ├── tray_subprocess.py     # Sotto-processo GTK3 + AppIndicator3 per il tray
    └── window.py              # Finestra principale (lista profili, stato)
```

## Architettura

```
┌──────────────────────────────────────────────────────────┐
│                       Fortyfax                           │
│                  (GTK4 + libadwaita)                     │
├────────────┬────────────┬────────────────────────────────┤
│  Window    │  Dialogs   │   Auth                         │
│  - Lista   │  - Editor  │   - SAML webview (Fortinet)    │
│    profili │  - Password│   - Browser sistema (GP)       │
│  - Stato   │  - Log     │   - Cookie capture             │
├────────────┴────────────┼────────────────────────────────┤
│  Connection Manager     │   Tray Icon                    │
│  - Fortinet backend     │   - AppIndicator3              │
│  - GlobalProtect backend│   - Sotto-processo GTK3        │
│  - DNS Watchdog (GP)    │   - JSON pipe IPC              │
│  - Subprocess via pkexec│                                │
├─────────────────────────┴────────────────────────────────┤
│                  Profile Manager                         │
│  - CRUD profili JSON (Fortinet + GlobalProtect)          │
│  - ~/.config/fortyfax/profiles/                          │
│  - Import/export + validazione                           │
├──────────────────────────────────────────────────────────┤
│                 Sistema operativo                        │
│  fortyfax-vpn-helper ─ openfortivpn ─ pppd  (Fortinet)  │
│  fortyfax-vpn-helper ─ gpclient ─ openconnect (GP)      │
│  pkexec ─ PolicyKit (allow_active=yes)                   │
│  resolvectl ─ systemd-resolved (DNS watchdog GP)         │
└──────────────────────────────────────────────────────────┘
```

### Flusso SAML/SSO

```
Fortyfax            WebKitGTK              FortiGate              IdP
 │                      │                      │                    │
 │── open webview ─────>│                      │                    │
 │                      │── GET /remote/saml/ ─>│                    │
 │                      │<── redirect to IdP ───│                    │
 │                      │───────────────── redirect ───────────────>│
 │                      │                      │                    │
 │                      │     (utente si autentica nell'IdP)        │
 │                      │                      │                    │
 │                      │<──────────── POST SAML response ─────────│
 │                      │── POST assertion ────>│                    │
 │                      │<── Set-Cookie: SVPN ──│                    │
 │<── cookie captured ──│                      │                    │
 │                      │                      │                    │
 │── openfortivpn --cookie-on-stdin ──────────>│                    │
 │<── tunnel established ──────────────────────│                    │
```

## Configurazione

### File di profilo

I profili sono salvati in `~/.config/fortyfax/profiles/<uuid>.json`:

```json
{
  "name": "VPN Ufficio",
  "host": "vpn.azienda.com",
  "port": 443,
  "username": "utente",
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

Per i profili GlobalProtect si aggiungono i campi `gp_gateway`, `gp_extra_dns`, `gp_vpn_dns`, `gp_hip`, `gp_mtu`, `gp_no_dtls`, `gp_fix_openssl`.

### Cifratura password

Le password VPN sono cifrate con:

- **Chiave**: 32 byte random in `~/.config/fortyfax/.secret` (permessi `0600`)
- **Algoritmo**: PBKDF2-SHA256 (100.000 iterazioni) + XOR
- **Salt**: 16 byte random per ogni cifratura (lo stesso testo produce token diversi)
- **Formato**: base64(salt + dati_cifrati) nel campo `encrypted_password` del JSON

La chiave non lascia mai la macchina. Se il file `.secret` viene perso, le password devono essere reinserite. Le password **non** vengono incluse nell'export dei profili.

### Impostazioni applicazione

Le impostazioni globali sono salvate in `~/.config/fortyfax/settings.json`:

```json
{
  "theme": "system",
  "notifications": true,
  "sso_browser": "auto"
}
```

Valori disponibili per `notifications`: `true` (default) o `false`.

Valori disponibili per `sso_browser`:

- `"auto"` — cerca Chrome/Chromium, poi Edge, poi browser predefinito (default)
- `"chrome"` — forza Google Chrome o Chromium
- `"edge"` — forza Microsoft Edge
- `"xdg-open"` — usa il browser predefinito di sistema

Valori disponibili per `theme`:

- `"system"` — segue il tema del sistema operativo (default)
- `"light"` — forza il tema chiaro
- `"dark"` — forza il tema scuro

Le impostazioni sono accessibili dal menu hamburger > **Preferenze** (o `Ctrl+,`).

### PolicyKit

Lo script `install.sh` configura una policy PolicyKit che permette di avviare e terminare openfortivpn **senza richiesta di password** per l'utente attivo sulla sessione locale (`allow_active=yes`).

Questo avviene tramite lo script helper `fortyfax-vpn-helper` che:

- Accetta solo i comandi `start`, `stop`, `kill` e `dns`
- Supporta sia `openfortivpn` che `gpclient` come backend
- Verifica che il PID da terminare sia effettivamente un processo VPN

La policy viene installata in `/usr/share/polkit-1/actions/com.github.fortyfax.policy`.

## Troubleshooting

### L'autenticazione SSO non funziona

**Problema**: La finestra SSO non si apre o da errore.

**Soluzione**: Verifica che WebKitGTK 6.0 sia installato:
```bash
sudo dnf install webkitgtk6.0
python3 -c "import gi; gi.require_version('WebKit', '6.0'); print('OK')"
```

### Errore "Certificato non trusted"

**Problema**: openfortivpn rifiuta il certificato del server.

**Soluzione**: Connettiti una prima volta, apri il log (icona terminale), cerca la riga con l'hash SHA256 del certificato e incollalo nel campo "Certificato trusted" del profilo.

### pkexec non chiede la password / Permission denied

**Problema**: PolicyKit non funziona correttamente.

**Soluzione**:
```bash
# Riesegui l'installer per reinstallare la policy
sudo ./install.sh
```

### La connessione cade subito

**Problema**: openfortivpn si chiude dopo pochi secondi.

**Soluzione**: Controlla il log per errori specifici. Cause comuni:
- `pppd` non installato: `sudo dnf install ppp`
- Rotte in conflitto: prova ad attivare "Half internet routes" nel profilo
- DNS in conflitto: prova a disattivare "Imposta DNS" nel profilo

### L'icona nel system tray non appare

**Problema**: L'icona tray non e visibile nel pannello.

**Soluzione**:

1. Verifica che AppIndicator3 sia installato:
```bash
sudo dnf install libappindicator-gtk3
```

2. Su GNOME, installa l'estensione "AppIndicator and KStatusNotifierItem Support":
```bash
sudo dnf install gnome-shell-extension-appindicator
```
   Dopo l'installazione, riavvia la sessione o attiva l'estensione da GNOME Extensions.

Su KDE Plasma e XFCE il supporto AppIndicator e nativo.

### FortiClient vs Fortyfax

FortiClient per Linux (RPM) e compilato per EL7 e non funziona su Fedora recenti a causa di:
- RPM senza digest (rifiutato da `rpm` moderno)
- Dipendenza da `openssl/engine.h` rimosso in OpenSSL 3.x

Fortyfax risolve entrambi i problemi usando `openfortivpn` come backend.

### GlobalProtect: gpclient non trovato

**Problema**: Il checker mostra `gpclient` come mancante.

**Soluzione**: Installa GlobalProtect-openconnect dal COPR:

```bash
sudo dnf copr enable yuezk/globalprotect-openconnect
sudo dnf install globalprotect-openconnect
```

### GlobalProtect: DNS non funziona / siti interni irraggiungibili

**Problema**: Dopo la connessione GlobalProtect, i siti interni non sono raggiungibili.

**Soluzione**:

1. Nel profilo, aggiungi i domini interni nel campo **"Domini DNS extra"** (es. `azienda.com internal.net`)
2. Se serve, specifica l'IP del DNS interno nel campo **"IP DNS VPN"**
3. Il DNS watchdog di Fortyfax mantiene la configurazione attiva per tutta la durata della connessione

### GlobalProtect: errore SSL / handshake failed

**Problema**: La connessione fallisce con errori SSL.

**Soluzione**: Abilita **"Fix OpenSSL legacy"** nel profilo GlobalProtect.

### GlobalProtect: connessione instabile / packet loss

**Problema**: La connessione cade frequentemente o è molto lenta.

**Soluzione**:

- Abilita **"Disabilita DTLS"** per forzare TCP
- Abbassa l'**MTU** a `1200` o `1262`

## Contribuire

1. Fai un fork del repository
2. Crea un branch per la tua feature (`git checkout -b feature/nuova-funzionalita`)
3. Committa le modifiche (`git commit -m 'Aggiunge nuova funzionalita'`)
4. Pusha il branch (`git push origin feature/nuova-funzionalita`)
5. Apri una Pull Request

### Setup ambiente di sviluppo

```bash
git clone https://stazzo@bitbucket.org/decisyon/fortyfax.git
cd fortyfax

# Installa dipendenze — Fedora:
sudo dnf install -y openfortivpn python3-gobject gtk4 libadwaita \
    webkitgtk6.0 libsecret polkit ppp libappindicator-gtk3 \
    openconnect vpnc-script

# Installa dipendenze — Debian/Ubuntu:
sudo apt install -y openfortivpn python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
    gir1.2-webkit-6.0 gir1.2-secret-1 polkitd ppp \
    gir1.2-appindicator3-0.1 openconnect vpnc

# Esegui in modalita sviluppo
python3 ./fortyfax-bin

# Verifica prerequisiti (rileva automaticamente la distro)
python3 -m fortyfax.check
```

## Roadmap

- [x] Icona nel system tray con stato connessione
- [x] Import/export profili
- [x] Notifiche desktop (connect/disconnect)
- [x] Supporto tema Light/Dark con preferenze
- [x] Supporto GlobalProtect (Palo Alto) con DNS watchdog
- [ ] Auto-connect all'avvio del sistema
- [ ] Supporto multi-connessione simultanea
- [x] Packaging RPM/DEB

## Licenza

Questo progetto e rilasciato sotto licenza [GPL-3.0](LICENSE).

## Crediti

- [openfortivpn](https://github.com/adrienverge/openfortivpn) — il backend VPN
- [GTK](https://gtk.org/) / [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) — il toolkit grafico
- [WebKitGTK](https://webkitgtk.org/) — il motore web per l'autenticazione SAML
