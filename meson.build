project(
  'appsweep',
  version: '0.1.0',
  meson_version: '>=1.3.0',
)

python = import('python').find_installation('python3')

app_libdir = join_paths(
  get_option('prefix'),
  'lib',
  'appsweep',
)

subdir('src')
subdir('data')
