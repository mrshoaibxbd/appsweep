launcher_configuration = configuration_data()
launcher_configuration.set('APP_LIBDIR', app_libdir)

configure_file(
  input: 'appsweep.in',
  output: 'appsweep',
  configuration: launcher_configuration,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

install_data(
  'tech.shoaib.AppSweep.desktop',
  install_dir: join_paths(
    get_option('datadir'),
    'applications',
  ),
)

install_data(
  'tech.shoaib.AppSweep.metainfo.xml',
  install_dir: join_paths(
    get_option('datadir'),
    'metainfo',
  ),
)

install_data(
  'tech.shoaib.AppSweep.svg',
  install_dir: join_paths(
    get_option('datadir'),
    'icons',
    'hicolor',
    'scalable',
    'apps',
  ),
)

install_data(
  'tech.shoaib.AppSweep.policy',
  install_dir: join_paths(
    get_option('datadir'),
    'polkit-1',
    'actions',
  ),
)

install_data(
  '../helper/appsweep-helper',
  install_dir: get_option('libexecdir'),
  install_mode: 'rwxr-xr-x',
)
