# AppSweep

AppSweep is a native Ubuntu application for safely reviewing and removing software installed through APT, Snap, and Flatpak.

It analyzes removal effects, protects critical system components, identifies application data, and supports verified rollback backups before removal.

## Features

- Detects desktop applications installed through APT
- Detects installed Snap applications
- Detects user and system Flatpak applications
- Shows package type, version, and installation scope
- Simulates APT removal before making changes
- Protects critical operating-system packages
- Protects Snap runtime and platform components
- Detects verified application-data directories
- Supports removal with a verified rollback backup
- Supports permanent removal without backup
- Uses PolicyKit for administrative authentication
- Refreshes the application list after removal

## Requirements

AppSweep targets Ubuntu 24.04 LTS and newer.

Required dependencies are installed automatically when the Debian package is installed through APT.

## Installation

Download the latest Debian package from the [AppSweep Releases page](https://github.com/mrshoaibxbd/appsweep/releases/latest).

For version 0.1.0, download [`appsweep_0.1.0_all.deb`](https://github.com/mrshoaibxbd/appsweep/releases/download/v0.1.0/appsweep_0.1.0_all.deb).

Install it with:

~~~bash
sudo apt install ./appsweep_0.1.0_all.deb
~~~

AppSweep will then appear in the Ubuntu application menu.

## Build from source

Install the build requirements:

~~~bash
sudo apt install \
  build-essential \
  debhelper \
  dh-python \
  devscripts \
  fakeroot \
  meson \
  ninja-build \
  python3 \
  python3-apt \
  python3-gi \
  python3-gi-cairo \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1
~~~

Clone and build:

~~~bash
git clone https://github.com/mrshoaibxbd/appsweep.git
cd appsweep
dpkg-buildpackage -us -uc -b
~~~

The generated package will be created one directory above the repository:

~~~text
../appsweep_0.1.0_all.deb
~~~

## Development

Create a development environment:

~~~bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install pytest ruff mypy
~~~

Run AppSweep directly:

~~~bash
PYTHONPATH=src python -m appsweep
~~~

Run the checks:

~~~bash
ruff format --check src tests
ruff check src tests
pytest
~~~

## Safety

AppSweep performs removal analysis before allowing package removal.

Critical packages and platform components are blocked by both the graphical application and the privileged helper.

User-created documents are not considered application leftovers. AppSweep only removes verified paths from supported application-data locations.

Report security issues according to [SECURITY.md](SECURITY.md).

## License

AppSweep is licensed under the GNU General Public License version 3 or later.

## Developer

**SHOAIB MAHMUD**

Website: [shoaib.tech](https://shoaib.tech)
