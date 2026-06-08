# Fortyfax packaging

## Current status

| Format | Tool | Source | Validation | Where it is published |
|---|---|---|---|---|
| RPM | `rpmbuild` | `packaging/rpm/fortyfax.spec` (Fedora Packaging Guidelines) | `rpmlint` (0 errors, filters in `fortyfax.rpmlintrc`) | Bitbucket Downloads + GitHub Release |
| DEB | `dpkg-buildpackage` | `debian/` (Debian Policy, debhelper-compat 13) | `lintian --fail-on error` | Bitbucket Downloads + GitHub Release |

- **Version**: single source of truth `fortyfax/__init__.py`; `build-pkg.sh` checks the alignment with the spec and `debian/changelog` and fails if they diverge. Coordinated bump: `./scripts/bump-version.sh X.Y.Z "note"`.
- **CI**: parallel builds on `fedora:latest` (RPM) and `debian:bookworm` (DEB) containers, both on Bitbucket Pipelines and GitHub Actions (releases on `v*` tags).
- **Shared files**: desktop file and PolicyKit policy in `data/`, used by both packaging flows.

## OpenSUSE Build Service (OBS) evaluation

### What it is

[OBS](https://build.opensuse.org) is openSUSE's public build service: from a single source it builds packages for **many distros and architectures** (openSUSE Tumbleweed/Leap, Fedora, RHEL/EPEL, Debian, Ubuntu, Arch...) and publishes **installable repositories** that users add to zypper/dnf/apt — with automatic updates on every release, without downloading files by hand.

### Pros

- **Repository for users**: `dnf config-manager addrepo ...` once, then updates arrive with the system. A much better experience than manually downloading from Downloads/Release.
- **openSUSE coverage**: today we offer nothing for zypper; OBS adds it almost for free.
- **Multi-version**: builds for Fedora N, N-1, Leap, Tumbleweed, etc. in parallel — catches breakages on distros we don't test (e.g. package renames).
- **Sources from the GitHub mirror**: the `obs_scm` service can fetch sources from the public mirror `github.com/fpellizz/fortyfax` on every tag — no change to the Bitbucket flow.
- **The spec already exists**: the bulk of the work (this repo) is done. Only conditional tweaks are needed (see below).

### Cons

- **One more system to maintain**: openSUSE account, `home:fpellizz:fortyfax` project, build monitoring (the target distros change over time).
- **Divergent package names**: the current spec uses Fedora names (`python3-gobject`, `webkitgtk6.0`, `libadwaita`); on openSUSE the `typelib(Gtk) = 4.0`-style provides or different names are needed → the spec must be conditionalized with `%if 0%{?suse_version}`.
- **DEB on OBS is more cumbersome**: it requires separate `.dsc` + `debian.tar.gz` and its own rules; since we already produce DEBs well in CI, it's better **not** to use OBS for the debs (at least at the beginning).
- **gpclient does not exist in any distro**: it stays a `Suggests`, the GlobalProtect user still has to add COPR/PPA — OBS does not solve this.

### Recommendation

**Yes, but with a reduced scope**: an OBS project `home:fpellizz:fortyfax` with targets **openSUSE Tumbleweed + Leap 15.6 + Fedora (last 2)**, RPM only. The DEBs stay with the existing CI. Estimated effort: half a day for the initial setup, then ~zero (tags come in on their own via `obs_scm` from the mirror).

### Setup (when it's decided to do it)

1. Account on https://idp-portal.suse.com → https://build.opensuse.org
2. `osc meta pkg home:fpellizz:fortyfax fortyfax -e` (or from the web UI)
3. `_service` file in the OBS package:

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

4. Copy of `packaging/rpm/fortyfax.spec` with conditionalized dependencies:

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

5. Targets in the project: `openSUSE_Tumbleweed`, `15.6`, `Fedora_43`, `Fedora_42`
6. Repo for users (example):
   ```bash
   # openSUSE
   zypper addrepo https://download.opensuse.org/repositories/home:fpellizz:fortyfax/openSUSE_Tumbleweed/home:fpellizz:fortyfax.repo
   # Fedora
   dnf config-manager addrepo --from-repofile=https://download.opensuse.org/repositories/home:fpellizz:fortyfax/Fedora_43/home:fpellizz:fortyfax.repo
   ```
