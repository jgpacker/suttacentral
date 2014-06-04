"""Asset (CSS, JavaScript) compilation using webassets.

See: http://webassets.readthedocs.org/
"""

import logging
import webassets
from webassets.script import CommandLineEnvironment

import sc
from sc import config


def clean(older=False):
    """Remove outdated compiled assets."""

    maximum_ctime = None
    try:
        maximum_ctime = sc.webassets_manifest_path.stat().st_mtime
        maximum_ctime -= 60  # seconds
    except OSError:
        older = True

    cache_glob = sc.webassets_cache_dir.glob('*')
    css_glob = sc.compiled_css_dir.glob('*.css')
    js_glob = sc.compiled_js_dir.glob('*.js')
    paths = list(cache_glob) + list(css_glob) + list(js_glob)

    if not older:
        paths.append(sc.webassets_manifest_path)

    for path in paths:
        try:
            if not older or path.stat().st_ctime < maximum_ctime:
                path.unlink()
        except OSError:
            pass


def compile():
    """Compile assets."""

    log = logging.getLogger(__name__)
    cmd = CommandLineEnvironment(get_env(), log)
    cmd.build()

def build_sc_uid_expansion(env):
    from sc.scimm import table_reader
    import json, os.path
    filename = 'js/sc_uid_expansion_data.js'
    fullname = os.path.join(env.directory, filename)
    
    with open(fullname, 'w', encoding='UTF8') as outfile:
        data = {uid: [acro, name] for uid, acro, name in
            table_reader('uid_expansion')}
        
        outfile.write('sc.util.expand_uid_data = {}'.format(
            json.dumps(data, ensure_ascii=False)))
    
    return filename

def get_env():
    """Return the SuttaCentral webassets environment."""

    env = webassets.Environment(str(sc.static_dir), '/')
    env.auto_build = not config.compile_assets
    env.cache = str(sc.webassets_cache_dir)
    env.debug = not config.compile_assets
    env.manifest = 'json:{}'.format(sc.webassets_manifest_path)

    css_normalize = webassets.Bundle(
        'css/vendor/normalize-2.1.3.css'
    )

    css_utf8 = webassets.Bundle(
        'css/utf8.css'
    )

    css_main_free = webassets.Bundle(
        'css/main-free.scss',
        depends=('css/*.scss', 'css/*/*.scss'),
        filters='pyscss',
        output='css/compiled/main-free-%(version)s.css'
    )

    css_main_nonfree = webassets.Bundle(
        'css/main-nonfree.scss',
        depends=('css/*.scss', 'css/*/*.scss'),
        filters='pyscss',
        output='css/compiled/main-nonfree-%(version)s.css'
    )

    css_free = webassets.Bundle(
        css_normalize,
        css_main_free,
        css_utf8,
        filters='cssmin',
        output='css/compiled/free-%(version)s.css'
    )

    css_nonfree = webassets.Bundle(
        css_normalize,
        css_main_nonfree,
        css_utf8,
        filters='cssmin',
        output='css/compiled/nonfree-%(version)s.css'
    )

    env.register('css_free', css_free)
    env.register('css_nonfree', css_nonfree)
    
    sc_uid_expansion_data_file = build_sc_uid_expansion(env)
    
    js_core = webassets.Bundle(
        'js/vendor/ZeroClipboard-1.2.3.js',
        'js/vendor/jquery.hashchange-1.3.min.js',
        'js/vendor/jquery.easytabs.js',
        'js/sc_utility.js',
        'js/nav.js',
        'js/sc_functions.js',
        'js/sidebar.js',
        'js/sc_init.js',
        'js/sc_formatter.js',
        'js/sc_popupnotes.js',
        'js/data/zh2en-data-scripts-names.js',
        sc_uid_expansion_data_file,
        filters='rjsmin',
        output='js/compiled/core-%(version)s.js'
    )
    env.register('js_core', js_core)

    # For some reason, webassets does not create these directories if
    # they do not exist...
    if not sc.webassets_cache_dir.exists():
        sc.webassets_cache_dir.mkdir(parents=True)

    return env

def compress_static():
    """Pre-compress static data (for Nginx ngx_http_gzip_static_module)"""
    import plumbum
    try:
        compress_cmd = plumbum.local['zopfli']['--gzip']
    except plumbum.CommandNotFound:
        print('zopfli not available, falling back to gzip')
        compress_cmd = plumbum.local['gzip']['-9 -k']
    
    extensions = {'.js', '.css', '.svg', '.ttf'}
    files = set(sc.static_dir.glob('fonts/**/*'))
    files.update(sc.static_dir.glob('js/data/*'))
    files.update(sc.static_dir.glob('js/compiled/*'))
    files.update(sc.static_dir.glob('css/compiled/*'))
    to_process = []
    for file in sorted(files):
        if file.suffix == '.gz':
            if file.with_name(file.stem) not in files:
                # Remove if original does not exist anymore
                file.unlink()
            continue
        if file.suffix not in extensions:
            continue
        if file.with_suffix(file.suffix + '.gz') in files:
            continue
        to_process.append(file)
    if to_process:
        print('Compressing {} files'.format(len(to_process)))
        compress_cmd[to_process]()
        
    
