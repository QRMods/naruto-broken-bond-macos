#!/usr/bin/env python3
"""Build the private ARM64 macOS port of Naruto: The Broken Bond from the user's disc, entirely locally."""
import argparse
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PC = ROOT / 'upstream/broken-bond-recomp'
PS5 = ROOT / 'upstream/naruto-ps5'
SDK = PC / 'sdk'
PLUME = ROOT / 'upstream/plume'
BUILD = ROOT / 'build'
GAME = ROOT / 'game'
NAME = 'Naruto The Broken Bond'
APP = ROOT / f'dist/{NAME}.app'
ENV = dict(os.environ)
if Path('/Applications/Xcode.app/Contents/Developer').is_dir():
    ENV['DEVELOPER_DIR'] = '/Applications/Xcode.app/Contents/Developer'
ENV['CPM_SOURCE_CACHE'] = str(BUILD / 'dependencies')


def run(*args, cwd=ROOT):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, env=ENV, check=True)


def checkout(path, source):
    if not (path / '.git').exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()  # An uninitialized submodule's folder.
        run('git', 'clone', '--depth', '1', source['url'], path)
    current = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
    if current != source['commit']:
        dirty = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no',
                                         '--ignore-submodules'], text=True)
        if dirty:
            raise RuntimeError(f'Preserving edits in {path}; expected revision {source["commit"]}')
        run('git', '-C', path, 'fetch', '--depth', '1', 'origin', source['commit'])
        run('git', '-C', path, 'checkout', '--detach', source['commit'])


def pinned_clone(path, url, revision):
    """A dependency the PC port lists by revision (tools/native-renderer/dependencies.json)."""
    if path.is_dir() and any(path.iterdir()):
        return
    path.mkdir(parents=True, exist_ok=True)
    run('git', 'init', '-q', path)
    run('git', '-C', path, 'fetch', '--depth', '1', url, revision)
    run('git', '-C', path, 'checkout', '-q', '--detach', 'FETCH_HEAD')


def apply_patches(repo, patches):
    """Applies a stack of patches once; a changed stack replaces the applied one.

    The applied stack is recorded under build/applied-patches, so patches that
    touch the same lines (the PS5 and macOS ones) need no per-patch detection.
    """
    record = BUILD / 'applied-patches' / repo.relative_to(ROOT).as_posix().replace('/', '_')
    applied = sorted(record.glob('*.patch')) if record.is_dir() else []
    wanted = [path.read_bytes() for path in patches]
    if [path.read_bytes() for path in applied] == wanted:
        return
    if not applied and subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain',
                                                '--untracked-files=no', '--ignore-submodules'], text=True).strip():
        raise RuntimeError(f'Preserving edits in {repo}: it has changes that no recorded patch explains')
    for path in reversed(applied):
        run('git', '-C', repo, 'apply', '--reverse', path)
    if record.is_dir():
        shutil.rmtree(record)
    record.mkdir(parents=True)
    for index, path in enumerate(patches):
        run('git', '-C', repo, 'apply', path)
        shutil.copy2(path, record / f'{index:02d}-{path.name}')


def spirv_val(jobs):
    """spirv-val of the SDK's SPIRV-Tools, which the shader cache of the native renderer checks with."""
    spirv = SDK / 'thirdparty'
    run('cmake', '-S', spirv / 'spirv-tools', '-B', BUILD / 'spirv-tools', '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_OSX_ARCHITECTURES=arm64', f'-DSPIRV-Headers_SOURCE_DIR={spirv / "spirv-headers"}',
        '-DSPIRV_SKIP_TESTS=ON', '-DSPIRV_WERROR=OFF')
    run('cmake', '--build', BUILD / 'spirv-tools', '--target', 'spirv-val', '--parallel', jobs)
    return BUILD / 'spirv-tools/tools/spirv-val'


def manifest():
    """The PC port's codegen manifest for the local game files.

    A copy beside the PC port's (the codegen writes the module targets relative
    to its folder), excluded from that checkout's Git status, whose game paths
    point at game/.
    """
    quote = lambda path: json.dumps(str(path))
    value = lambda line: json.loads(line.split('=', 1)[1])
    lines = []
    for line in (PC / 'broken_bond_manifest.toml').read_text().splitlines():
        key = line.split('=', 1)[0].strip()
        if key == 'game_root':
            line = 'game_root = ' + quote(GAME)
        elif key == 'file_path':
            line = 'file_path = ' + quote(GAME / Path(value(line)).name)
        lines.append(line)
    text = '\n'.join(lines) + '\n'
    target = PC / 'broken_bond_manifest.macos.toml'
    exclude = Path(subprocess.check_output(['git', '-C', str(PC), 'rev-parse', '--git-path', 'info/exclude'],
                                           text=True).strip())
    if not exclude.is_absolute():
        exclude = PC / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    if target.name not in (exclude.read_text() if exclude.exists() else ''):
        with exclude.open('a') as stream:
            stream.write(f'/{target.name}\n')
    if not target.exists() or target.read_text() != text:
        target.write_text(text)
    return target


def settings_text(base, overrides):
    """The settings of `base` with each `key = value` line of `overrides` in place of its own."""
    lines = base.splitlines()
    keys = {line.split('=', 1)[0].strip(): index for index, line in enumerate(lines)
            if '=' in line and not line.lstrip().startswith('#')}
    for line in overrides.splitlines():
        if '=' not in line or line.lstrip().startswith('#'):
            continue
        key = line.split('=', 1)[0].strip()
        if key in keys:
            lines[keys[key]] = line
        else:
            lines.append(line)
    return '\n'.join(lines) + '\n'


def system_language():
    """The Mac's first preferred language as the settings name it.

    The menus' language (launcher_language) and the game's (user_language, an
    Xbox 360 language code: 1 English, 3 German, 4 French, 5 Spanish,
    6 Italian); English where the game or the menus lack it.
    """
    try:
        listed = subprocess.check_output(['defaults', 'read', '-g', 'AppleLanguages'], text=True)
        first = listed.split('"')[1].lower()
    except (subprocess.CalledProcessError, OSError, IndexError):
        first = 'en'
    prefix = first.split('-')[0]
    menus = {'es': 'es', 'fr': 'fr', 'de': 'de', 'it': 'it', 'ru': 'ru', 'pt': 'pt_BR'}.get(prefix, 'en')
    game = {'de': 3, 'fr': 4, 'es': 5, 'it': 6}.get(prefix, 1)
    return menus, game


def achievement_assets(resources):
    """The orb and the unlock sound of the achievement toast, from macos/assets.

    They are not this project's to publish (a console's logo and jingle), so
    they stay out of Git: whoever builds puts achievement-orb.png and
    achievement-unlocked.wav/.mp3/.m4a in macos/assets. Without them the toast
    shows a neutral orb and plays no sound.
    """
    source = ROOT / 'macos/assets'
    target = resources / 'achievements'
    target.mkdir(parents=True, exist_ok=True)
    orb = source / 'achievement-orb.png'
    if orb.is_file():
        shutil.copy2(orb, target / 'orb.png')
    else:
        (target / 'orb.png').unlink(missing_ok=True)
    sounds = [path for path in sorted(source.glob('achievement-unlocked.*'))
              if path.suffix.lower() in ('.wav', '.mp3', '.m4a', '.aif', '.aiff', '.caf')]
    if sounds:
        # 16-bit PCM WAV, which SDL plays without a decoder.
        run('afconvert', '-f', 'WAVE', '-d', 'LEI16@44100', sounds[0], target / 'unlock.wav')
    else:
        (target / 'unlock.wav').unlink(missing_ok=True)


def app_icon(resources):
    """The port's own icon (ui/broken_bond.png of the PC port) as the bundle's .icns."""
    source = PC / 'ui/broken_bond.png'
    if not source.is_file():
        return None
    iconset = BUILD / 'broken_bond.iconset'
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            name = f'icon_{size}x{size}{"@2x" if scale == 2 else ""}.png'
            run('sips', '-z', size * scale, size * scale, source, '--out', iconset / name)
    run('iconutil', '-c', 'icns', iconset, '-o', resources / 'broken_bond.icns')
    return 'broken_bond.icns'


def package():
    binaries = BUILD / 'app'
    contents = APP / 'Contents'
    macos = contents / 'MacOS'
    resources = contents / 'Resources'
    macos.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binaries / 'broken_bond', macos / 'broken_bond')
    for library in binaries.glob('*.dylib'):
        shutil.copy2(library, macos / library.name)
    shutil.copytree(binaries / 'vulkan', resources / 'vulkan', dirs_exist_ok=True)
    achievement_assets(resources)
    icon = app_icon(resources)
    # The PC port's default settings with the macOS ones over them (Vulkan,
    # keyboard and mouse, full screen, 30 FPS), which the game copies into a new
    # data folder.
    menus, game = system_language()
    defaults = settings_text((PC / 'packaging/broken_bond.toml').read_text(),
                             (ROOT / 'macos/broken_bond.toml').read_text() +
                             f'\nlauncher_language = "{menus}"\nuser_language = {game}\n')
    shutil.copytree(binaries / 'defaults', resources / 'defaults', dirs_exist_ok=True)
    (resources / 'defaults/broken_bond.toml').write_text(defaults)
    # The data folder is user/ of this checkout (settings, saves, logs and caches),
    # and the game is game/: a descriptor beside the executable selects the folder,
    # and the settings name the game and the folders the saves are in. In an app
    # bundle the game reads both from Resources (Contents/MacOS holds code only).
    (resources / 'data_location.json').write_text(json.dumps({'version': 1, 'mode': 'custom', 'path': str(ROOT / 'user')}))
    roots = {'user_data_root': ROOT / 'user', 'cache_root': ROOT / 'user/cache', 'custom_game_root': GAME}
    user_config = ROOT / 'user/broken_bond.toml'
    (ROOT / 'user/logs').mkdir(parents=True, exist_ok=True)
    if not user_config.exists():
        user_config.write_text(defaults + ''.join(f'{key} = {json.dumps(str(path))}\n' for key, path in roots.items()))
    else:
        # Settings from an earlier build: the keys this one adds (the game's
        # folder, the menus' language, the macOS defaults it lacks) are added;
        # the others stay as they are.
        text = user_config.read_text()
        present = {line.split('=', 1)[0].strip() for line in text.splitlines()
                   if '=' in line and not line.lstrip().startswith('#')}
        wanted = [('custom_game_root', json.dumps(str(GAME))), ('launcher_language', json.dumps(menus))]
        wanted += [(line.split('=', 1)[0].strip(), line.split('=', 1)[1].strip())
                   for line in (ROOT / 'macos/broken_bond.toml').read_text().splitlines()
                   if '=' in line and not line.lstrip().startswith('#')]
        added = ''.join(f'{key} = {value}\n' for key, value in wanted if key not in present)
        if added:
            with user_config.open('a') as stream:
                stream.write('\n' + added)
    if (macos / 'logs').exists():
        shutil.copytree(macos / 'logs', ROOT / 'evidence/initial-app-logs', dirs_exist_ok=True)
        shutil.rmtree(macos / 'logs')
    version = json.loads((ROOT / 'sources.json').read_text()).get('version', '0.2.0')
    info = {
        'CFBundleIdentifier': 'local.brokenbond.native',
        'CFBundleName': NAME,
        'CFBundleDisplayName': NAME,
        'CFBundleExecutable': 'broken_bond',
        'CFBundlePackageType': 'APPL',
        'CFBundleShortVersionString': version,
        'CFBundleVersion': '1',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '26.0',
        # A game for macOS: the controller's Home button then belongs to the game
        # while it is in front (it opens the achievements, not the Games app), and
        # Game Mode applies in full screen.
        'LSApplicationCategoryType': 'public.app-category.action-games',
    }
    if icon:
        info['CFBundleIconFile'] = icon
    with (contents / 'Info.plist').open('wb') as stream:
        plistlib.dump(info, stream)
    licenses = resources / 'licenses'
    licenses.mkdir(exist_ok=True)
    for source, name in ((PC / 'LICENSE', 'broken-bond-pc-GPL3.txt'), (PS5 / 'LICENSE', 'naruto-ps5-MIT.txt'),
                         (SDK / 'LICENSE', 'rexglue-BSD.txt')):
        shutil.copy2(source, licenses / name)
    shutil.copytree(PC / 'packaging/licenses', licenses / 'third-party', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'sources.json', resources / 'sources.json')
    for library in sorted(contents.rglob('*.dylib')):
        run('codesign', '--force', '--sign', '-', library)
    run('codesign', '--force', '--sign', '-', APP)
    # LaunchServices learns the new category now, not at some later scan.
    lsregister = Path('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework'
                      '/Support/lsregister')
    if lsregister.is_file():
        run(lsregister, '-f', APP)
    print(f'Application: {APP}', flush=True)


def game_source(given):
    """The disc image or the .7z holding it: --source, else the one in this folder."""
    if given:
        return given.resolve()
    found = [path for pattern in ('*.7z', '*.iso', '*/*.iso') for path in ROOT.glob(pattern)
             if not path.is_relative_to(ROOT / 'upstream') and not path.is_relative_to(BUILD)]
    if len(found) != 1:
        raise RuntimeError('Select your disc image (.iso or .7z) with --source /path/to/game')
    return found[0]


def prepare_sources(args):
    sources = json.loads((ROOT / 'sources.json').read_text())
    if not args.dev:
        checkout(PC, sources['pc'])
    checkout(PS5, sources['ps5'])
    checkout(SDK, sources['sdk'])
    checkout(PLUME, sources['plume'])
    run('git', '-C', SDK, 'submodule', 'update', '--init', '--depth', '1', '--jobs', args.jobs)
    run('git', '-C', PC, 'submodule', 'update', '--init', '--depth', '1', '--jobs', args.jobs,
        'third_party/rmlui', 'third_party/freetype')
    run('git', '-C', PLUME, 'submodule', 'update', '--init', '--depth', '1', '--jobs', args.jobs,
        'contrib/volk', 'contrib/Vulkan-Headers', 'contrib/VulkanMemoryAllocator')
    # XenosRecomp's dependencies, which the PC port pins by revision instead of
    # as submodules (the shader cache's translator, DXC, smol-v, Zstandard).
    pins = json.loads((PC / 'tools/native-renderer/dependencies.json').read_text())['xenosrecomp_thirdparty']
    for name, pin in pins.items():
        pinned_clone(PC / 'tools/xenosrecomp/thirdparty' / name, pin['url'], pin['revision'])
    # The PC port on macOS (macos/patches/pc, one commit each, written to go
    # upstream). --dev builds the PC checkout as it is (a branch with them).
    if not args.dev:
        apply_patches(PC, sorted((ROOT / 'macos/patches/pc').glob('*.patch')))
    # The PC port's SDK patches in its order, then macos/patches/sdk: the PS5
    # port's (16 KB page write watches, Vulkan submission and descriptor work,
    # frame pacing), adapted to follow them, and the macOS-specific ones.
    series = [line.split()[0] for line in (PC / 'patches/series').read_text().splitlines()
              if line.strip() and not line.lstrip().startswith('#')]
    apply_patches(SDK, [*(PC / 'patches' / name for name in series),
                        *sorted((ROOT / 'macos/patches/sdk').glob('*.patch'))])


def build_sdk(jobs):
    run('cmake', '-S', SDK, '-B', BUILD / 'sdk', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_OSX_ARCHITECTURES=arm64',
        f'-DCMAKE_INSTALL_PREFIX={BUILD / "sdk-install"}', f'-DCPM_SOURCE_CACHE={BUILD / "dependencies"}',
        '-DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON', '-DREXGLUE_ENABLE_TRACY=OFF', '-DREXGLUE_BUILD_TESTS=OFF',
        '-DREXGLUE_ENABLE_FIDELITYFX=OFF', '-DREXGLUE_ENABLE_PERF_COUNTERS=ON')
    run('cmake', '--build', BUILD / 'sdk', '--target', 'install', '--parallel', jobs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='the disc image (.iso) or the .7z holding it')
    parser.add_argument('--jobs', type=int, default=6)
    parser.add_argument('--package-only', action='store_true')
    parser.add_argument('--sdk-only', action='store_true', help='prepare the sources and build the SDK only')
    parser.add_argument('--dev', action='store_true',
                        help='build the PC checkout as it is, without its pinned revision and macOS patches')
    args = parser.parse_args()
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        parser.error('This build targets an Apple Silicon Mac.')
    if args.package_only:
        package()
        return
    for tool in ('git', 'cmake', 'codesign'):
        if not shutil.which(tool):
            parser.error(f'Missing tool: {tool}')
    prepare_sources(args)
    build_sdk(args.jobs)
    if args.sdk_only:
        return
    if not (GAME / 'default.xex').is_file():
        if GAME.exists() and any(GAME.iterdir()):
            raise RuntimeError(f'{GAME} lacks default.xex: remove it and run again to extract the game')
        run(sys.executable, '-I', ROOT / 'tools/extract-game.py', game_source(args.source), '--output', GAME)
    # The recompiled code first: the PC port's CMake takes its sources when it configures.
    run(BUILD / 'sdk-install/bin/rexglue', 'codegen', manifest(), cwd=PC)
    # The PC port's build reruns the codegen with its own manifest unless its
    # stamp says the code is current: it is.
    (PC / 'generated/default/codegen.build.stamp').touch()
    validator = spirv_val(args.jobs)
    # The PC port's own CMake, as on Linux: the native renderer on Vulkan
    # (MoltenVK), its shaders translated from game/xeshader.sdb.
    run('cmake', '-S', PC, '-B', BUILD / 'app', '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_OSX_ARCHITECTURES=arm64', f'-DCMAKE_PREFIX_PATH={BUILD / "sdk-install"}',
        '-DBROKENBOND_NATIVE_RENDERER=ON', f'-DNATIVE_RENDERER_PLUME_SOURCE={PLUME}',
        f'-DBROKENBOND_GAME_DIR={GAME}',
        f'-DBROKENBOND_SHADER_STORE={BUILD / "shader-store"}', f'-DBROKENBOND_SPIRV_VAL={validator}',
        # Sentry reports go to the PC port's own project: a macOS build sends none.
        '-DBROKENBOND_ENABLE_SENTRY=OFF')
    run('cmake', '--build', BUILD / 'app', '--target', 'broken_bond', '--parallel', args.jobs)
    package()


if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
        print(f'Build failed: {error}', file=sys.stderr)
        sys.exit(1)
