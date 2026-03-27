# Fortyfax

> GUI nativa GTK4/Adwaita per [openfortivpn](https://github.com/adrienverge/openfortivpn) con supporto completo per autenticazione **SAML/SSO** tramite webview integrata.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![GTK4](https://img.shields.io/badge/GTK-4.0-green)
![Adwaita](https://img.shields.io/badge/libadwaita-1.0-purple)
![License](https://img.shields.io/badge/license-GPL--3.0-orange)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey)

---

## Panoramica

Fortyfax nasce per risolvere un problema concreto: collegarsi a VPN Fortinet/FortiGate da Linux senza dover usare il client proprietario FortiClient (che su distribuzioni recenti ha problemi di compatibilità con OpenSSL 3.x e RPM senza digest).

L'applicazione wrappa `openfortivpn` fornendo:

- **Login SAML/SSO** tramite webview WebKitGTK integrata con cattura automatica del cookie `SVPNCOOKIE`
- **Login con username/password** classico
- **Gestione profili** multipli con editor grafico completo
- **Interfaccia nativa GNOME** che si integra con il desktop (GTK4 + libadwaita)
- **Icona nel system tray** con stato connessione, menu contestuale e hide-on-close
- **Log in tempo reale** della connessione VPN
- **Verifica prerequisiti** con messaggi di errore esplicativi e istruzioni di fix

## Screenshot

*TODO: aggiungere screenshot dell'interfaccia*

## Funzionalita

### Autenticazione

| Metodo | Supporto | Descrizione |
|--------|----------|-------------|
| SAML/SSO | Completo | Webview integrata, cattura automatica SVPNCOOKIE, compatibile con qualsiasi IdP (Azure AD, Okta, Google, ecc.) |
| Username/Password | Completo | Dialog sicuro con password mascherata |

### Gestione Profili

- Creazione, modifica ed eliminazione profili VPN
- Validazione campi in tempo reale
- Configurazione completa: host, porta, realm, certificato trusted, argomenti extra
- Salvataggio sicuro in `~/.config/fortyfax/profiles/` (formato JSON)
- Esportazione in formato config nativo openfortivpn

### Rete

- Gestione rotte VPN (attiva/disattiva)
- Configurazione DNS tramite tunnel
- PPP Peer DNS
- Half internet routes (`0.0.0.0/1` + `128.0.0.0/1`)
- Argomenti extra personalizzabili per openfortivpn

### Interfaccia

- Design nativo GNOME con libadwaita
- Stato connessione con feedback visivo (icone, spinner, banner)
- **Icona nel system tray** (AppIndicator3):
  - Icona che cambia in base allo stato: verde (connesso), trasparente (disconnesso), rosso (errore)
  - Menu contestuale: stato, selezione profilo, connetti/disconnetti, mostra/nascondi, esci
  - Chiudere la finestra la nasconde nel tray (l'app resta attiva)
  - Compatibile con KDE Plasma, GNOME (con estensione AppIndicator), XFCE
- **Supporto temi Light/Dark**: selezione manuale (Chiaro, Scuro) o automatica dal sistema
- **Preferenze applicazione** accessibili dal menu (Ctrl+,)
- Viewer log integrato con scroll automatico
- Verifica prerequisiti accessibile dal menu

## Requisiti di sistema

| Dipendenza | Versione minima | Pacchetto Fedora | Note |
|------------|----------------|------------------|------|
| Python | 3.10+ | `python3` | |
| GTK 4 | 4.0+ | `gtk4` | |
| libadwaita | 1.0+ | `libadwaita` | |
| PyGObject | 3.42+ | `python3-gobject` | Binding Python per GTK |
| WebKitGTK | 6.0+ | `webkitgtk6.0` | Per autenticazione SAML/SSO |
| libsecret | 1.0+ | `libsecret` | Storage sicuro credenziali |
| openfortivpn | 1.17+ | `openfortivpn` | Backend VPN |
| PolicyKit | — | `polkit` | Elevazione privilegi per la connessione |
| AppIndicator3 | — | `libappindicator-gtk3` | Icona nel system tray |
| pppd | — | `ppp` | Richiesto da openfortivpn |

## Installazione

### Installazione rapida (Fedora)

```bash
# 1. Installa le dipendenze
sudo dnf install -y openfortivpn python3-gobject gtk4 libadwaita \
    webkitgtk6.0 libsecret polkit ppp libappindicator-gtk3

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
3. Compila i campi:
   - **Nome profilo**: un nome descrittivo (es. "VPN Ufficio")
   - **Host**: hostname o IP del FortiGate (es. `vpn.azienda.com`)
   - **Porta**: di solito `443`
   - **Metodo di autenticazione**: SAML/SSO oppure Username/Password
   - **Realm**: se richiesto dal tuo FortiGate (opzionale)
4. Salva il profilo

### Connessione SAML/SSO

1. Seleziona il profilo con autenticazione SAML
2. Clicca **"Connetti"**
3. Si apre una finestra browser integrata con la pagina di login del tuo IdP
4. Completa l'autenticazione (Azure AD, Okta, Google, ecc.)
5. Il cookie SVPNCOOKIE viene catturato automaticamente
6. La connessione VPN parte in automatico

### Connessione con password

1. Seleziona il profilo con autenticazione password
2. Clicca **"Connetti"**
3. Inserisci la password nel dialog
4. La connessione VPN parte

### Certificato trusted

Alla prima connessione, openfortivpn mostra l'hash SHA256 del certificato del server nel log. Copia quell'hash nel campo **"Certificato trusted"** del profilo per evitare il warning alle connessioni successive.

Puoi visualizzare il log cliccando l'icona terminale nella barra superiore.

### Disconnessione

Clicca **"Disconnetti"** per terminare la connessione VPN in modo pulito.

## Struttura del progetto

```
fortyfax/
├── fortyfax-bin              # Launcher eseguibile
├── fortyfax-vpn-helper       # Helper per avvio/stop openfortivpn via pkexec
├── install.sh                # Script di installazione di sistema
├── uninstall.sh              # Script di rimozione
├── README.md
├── LICENSE
├── icons/                    # Icone applicazione e tray
│   ├── app_icon_dark*.png     # Icona app (sfondo scuro)
│   ├── app_icon_light*.png    # Icona app (sfondo chiaro)
│   ├── tray_icon*.png         # Icona tray (connesso/in corso)
│   ├── tray_icon_gray*.png    # Icona tray (disconnesso)
│   └── notif_icon*.png        # Icona notifica/connesso
└── fortyfax/                 # Package Python
    ├── __init__.py            # Metadati (versione, app_id)
    ├── __main__.py            # Entry point per `python -m fortyfax`
    ├── app.py                 # Applicazione Adwaita (lifecycle, menu, shortcuts)
    ├── auth.py                # Autenticazione SAML/SSO via WebKitGTK
    ├── check.py               # Verifica prerequisiti di sistema
    ├── connection.py          # Gestione processo openfortivpn
    ├── dialogs.py             # Dialog: editor profili, password, log viewer, preferenze
    ├── profile.py             # Modello dati profili + persistenza JSON
    ├── settings.py            # Impostazioni applicazione (tema, persistenza JSON)
    ├── tray.py                # Proxy tray icon (lancia sotto-processo GTK3)
    ├── tray_subprocess.py     # Sotto-processo GTK3 + AppIndicator3 per il tray
    └── window.py              # Finestra principale (lista profili, stato)
```

## Architettura

```
┌─────────────────────────────────────────────────┐
│                   Fortyfax                      │
│              (GTK4 + libadwaita)                │
├────────────┬────────────┬───────────────────────┤
│  Window    │  Dialogs   │   Auth (WebKitGTK)    │
│  - Lista   │  - Editor  │   - SAML webview      │
│    profili │  - Password│   - Cookie capture     │
│  - Stato   │  - Log     │   - SVPNCOOKIE         │
├────────────┴────────────┼───────────────────────┤
│  Connection Manager     │   Tray Icon            │
│  - Subprocess via pkexec│   - AppIndicator3      │
│  - Monitor stdout       │   - Sotto-processo GTK3│
│  - Cookie/pwd via stdin │   - JSON pipe IPC      │
├─────────────────────────┴───────────────────────┤
│              Profile Manager                     │
│  - CRUD profili JSON                            │
│  - ~/.config/fortyfax/profiles/                 │
│  - Validazione + export config                  │
├─────────────────────────────────────────────────┤
│           Sistema operativo                      │
│  fortyfax-vpn-helper ─ openfortivpn ─ pppd      │
│  pkexec ─ PolicyKit (allow_active=yes)           │
└─────────────────────────────────────────────────┘
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
  "username": "",
  "auth_method": "saml",
  "trusted_cert": "a1b2c3d4e5f6...",
  "realm": "",
  "use_resolvconf": true,
  "set_dns": true,
  "set_routes": true,
  "pppd_use_peerdns": true,
  "half_internet_routes": false,
  "extra_args": "",
  "uid": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Impostazioni applicazione

Le impostazioni globali sono salvate in `~/.config/fortyfax/settings.json`:

```json
{
  "theme": "system"
}
```

Valori disponibili per `theme`:

- `"system"` — segue il tema del sistema operativo (default)
- `"light"` — forza il tema chiaro
- `"dark"` — forza il tema scuro

Le impostazioni sono accessibili dal menu hamburger > **Preferenze** (o `Ctrl+,`).

### PolicyKit

Lo script `install.sh` configura una policy PolicyKit che permette di avviare e terminare openfortivpn **senza richiesta di password** per l'utente attivo sulla sessione locale (`allow_active=yes`).

Questo avviene tramite lo script helper `fortyfax-vpn-helper` che:
- Accetta solo i comandi `start`, `stop` e `kill`
- Verifica che il PID da terminare sia effettivamente un processo `openfortivpn`

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

# Installa dipendenze
sudo dnf install -y openfortivpn python3-gobject gtk4 libadwaita \
    webkitgtk6.0 libsecret polkit ppp libappindicator-gtk3

# Esegui in modalita sviluppo
python3 ./fortyfax-bin

# Verifica prerequisiti
python3 -m fortyfax.check
```

## Roadmap

- [x] Icona nel system tray con stato connessione
- [ ] Auto-connect all'avvio del sistema
- [ ] Import/export profili
- [ ] Supporto multi-connessione simultanea
- [ ] Notifiche desktop (connect/disconnect)
- [x] Supporto tema Light/Dark con preferenze
- [ ] Packaging RPM/Flatpak

## Licenza

Questo progetto e rilasciato sotto licenza [GPL-3.0](LICENSE).

## Crediti

- [openfortivpn](https://github.com/adrienverge/openfortivpn) — il backend VPN
- [GTK](https://gtk.org/) / [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) — il toolkit grafico
- [WebKitGTK](https://webkitgtk.org/) — il motore web per l'autenticazione SAML
