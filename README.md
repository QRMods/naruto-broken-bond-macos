# Naruto: The Broken Bond for macOS (Apple Silicon)

A native port of the Xbox 360 game to Macs with Apple chips. There is no emulator:
the game's PowerPC code is recompiled to ARM64 ahead of time, and the graphics run
through the PC port's native renderer, which takes the game's Direct3D calls and
draws them with Vulkan on top of Metal (MoltenVK).

It is the sequel's version of [naruto-rise-macos](https://github.com/QRMods/naruto-rise-macos)
and works the same way.

> [!IMPORTANT]
> **You need your own copy of the game.** This project contains no game files.
> It builds the game on your Mac from a disc image (`.iso`) of your Xbox 360 disc, or
> a `.7z` holding it. Neither the game nor anything generated from it is distributed here.

**Using an AI assistant (ChatGPT, Claude, Gemini…)?** Give it
[INSTALL.md](INSTALL.md). That guide is written for AI assistants: it has every
command, how to check that each step worked, and the fix for each known error.

## What you need

- A Mac with Apple Silicon (M1, M2, M3, M4 or newer). Intel Macs are not supported.
- macOS 26 (Tahoe) or newer.
- About 6 GB of free disk space, plus the space your `.iso` or `.7z` takes up. The build
  extracts the game straight from it, without writing a second disc image.
- An internet connection for the first build, which downloads the source code it needs.
- A disc image of your own **Naruto: The Broken Bond** Xbox 360 disc (Title ID
  `55530825`, `default.xex` version 0.0.0.3).

## Installation, step by step

Most steps use **Terminal**. To open it, press `Cmd + Space`, type `Terminal` and
press Enter. To run a command, paste it into the Terminal window and press Enter.

### 1. Install Xcode

1. Install **Xcode** from the [Mac App Store](https://apps.apple.com/app/xcode/id497799835).
   It is free, but large, so the download takes a while.
2. Open Xcode once. Accept the license and let it install its extra components.
   Then you can close it. You never need to use Xcode itself.

### 2. Install Homebrew, CMake and 7-Zip

[Homebrew](https://brew.sh) installs developer tools. Paste this into Terminal (it asks
for your Mac password; typing it shows nothing on screen, which is normal):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

When it finishes, it prints **Next steps** with two or three commands. Run them. They
make the `brew` command work. Then install CMake, and 7-Zip if your game is a `.7z`:

```bash
brew install cmake sevenzip
```

### 3. Download this project

This creates a `naruto-broken-bond-macos` folder in your home folder:

```bash
cd ~
```

```bash
git clone https://github.com/QRMods/naruto-broken-bond-macos.git
```

If macOS asks you to install the "command line developer tools", accept and run the
command again. Don't put the project in iCloud Drive, or in a Desktop or Documents
folder that syncs with iCloud: the build creates thousands of files.

### 4. Add your game

```bash
open ~/naruto-broken-bond-macos
```

A Finder window opens. Copy your `.iso` or `.7z` into that folder. It must be the only
`.iso` or `.7z` there.

### 5. Build the game

In that Finder window, double-click **Build.command**. A Terminal window opens and the
build starts. Or run it from Terminal:

```bash
cd ~/naruto-broken-bond-macos
```

```bash
./Build.command
```

The first build takes a long time: it downloads the source code, extracts your disc,
recompiles the whole game and translates its shaders. Leave the window open until it
ends with a line like this:

```
Application: /Users/you/naruto-broken-bond-macos/dist/Naruto The Broken Bond.app
```

If your game is somewhere else, give its location: type `./Build.command --source `
(with a space at the end), drag the file onto the Terminal window and press Enter.

After the first build, the game is extracted in `game/`. You can delete the `.iso` or
`.7z`, or move it somewhere else, if you need the space.

### 6. Play

Double-click **Play.command**, or open `dist/Naruto The Broken Bond.app`. To keep it
handy, drag the app from `dist/` to the Dock.

Keep the project folder where it is: the app finds the game and your saves through it.
Saves, settings, the cache and the logs are in its `user/` folder.

The game starts straight away, in full screen. Its menu (settings, controls,
achievements, language) opens in the game with **F1** (**fn+F1** on a MacBook keyboard).
The menus and the game use your Mac's language when the game has it. To get the PC
port's setup screen at every start instead, set `show_startup_menu = true` in
`user/broken_bond.toml`.

## Controls (keyboard and mouse)

| Controller | Keys |
| --- | --- |
| Left stick | W A S D |
| Camera (right stick) | Mouse, or arrow keys |
| A | Space |
| B | E or Backspace |
| X | J or left click |
| Y | K or right click |
| LB / RB | Q / R |
| LT / RT | Control / Shift |
| Left / right stick press | C / V or middle click |
| Start | Return or Esc |
| Back | Tab |
| D-pad | 1 2 3 4, or numeric keypad 8 2 4 6 |

A controller that works with SDL (Xbox, PlayStation and most others) works too. You can
change the keys in the game's menu (F1), or in `user/broken_bond.toml` (the `keybind_*`
lines). The controller's Guide (Xbox) or PS button opens the achievements list (below).

## Achievements

The game's achievements unlock as on the console. Each new one shows a toast at the
bottom of the screen, after the Xbox 360 one: a medal pops in, opens into a bar with
**Achievement unlocked**, the gamerscore, the name and the achievement's own icon, and
spins away, with the unlock sound. Unlocks are kept in `user/achievements/55530825.toml`.

To see them all, open **Achievements** in the game's menu (F1), or press the controller's
Guide button, also while a toast shows, as on the console. The list shows your progress
and gamerscore, and each achievement's icon, description and unlock date. Filter with
LB/RB (keys ‹ ›), sort with X (S), close with B (Esc). Secret achievements stay hidden
until you unlock them. The texts follow the game's language (`user_language`).

The Xbox orb in the toast and the unlock sound aren't part of this project. To have them,
put `achievement-orb.png` and `achievement-unlocked.mp3` (or `.wav` or `.m4a`) in
`macos/assets/` before building. Without them the toast shows a plain silver orb and
makes no sound.

The app's icon is the PC port's own unless you give it another picture, such as the
game's cover, which isn't part of this project. Put it in `macos/assets/` as
`app-icon.png` or `app-icon.jpg` before building (square, 1024×1024 is best). The build
gives it the shape of a macOS icon.

## Settings

Settings are in `user/broken_bond.toml`, created by the first build. Edit it with any
text editor, such as TextEdit. Type straight quotes (`"`), not curly ones: in TextEdit,
turn off **Edit ▸ Substitutions ▸ Smart Quotes**. Changes apply the next time you start
the game. Most of them can also be changed in the game's menu (F1).

| Setting | What it does |
| --- | --- |
| `user_language` | Game language: `1` English, `3` German, `4` French, `5` Spanish, `6` Italian. The first build takes your Mac's language, or English if the game lacks it. |
| `launcher_language` | Language of the menus: `"en"`, `"es"`, `"fr"`, `"de"`, `"it"`, `"pt_BR"`, `"ru"`. The first build takes your Mac's. |
| `show_startup_menu` | `false` (default on macOS) starts straight into the game; `true` opens the setup screen first. |
| `frame_rate` | `30` (default on macOS) is the game's own rate. From `60` up, extra frames are interpolated. |
| `skip_pipeline_draws` | `true` (default on macOS): an object whose shader is still compiling for Metal is left out for a moment instead of freezing the frame (below). |
| `fullscreen` | `true` (default on macOS): the whole screen, where macOS applies Game Mode. `false`: a window. Option+Return or F11 (fn+F11) switch while playing. |
| `vsync` | `true` or `false`. |
| `native_backend` | `"vulkan"`: the only renderer on macOS. |

To see the FPS in the window title, start the game from Terminal, inside the project
folder, with
`REX_NATIVE_FPS_TITLE=1 "dist/Naruto The Broken Bond.app/Contents/MacOS/broken_bond"`.

## Updating

```bash
cd ~/naruto-broken-bond-macos
```

```bash
git pull
```

Then run `./Build.command` again. Your saves and settings in `user/` are kept.

If the build then stops with `Preserving edits in ...`, the update moved one of the
source projects to a new version. Delete the old copy and build again:

```bash
rm -rf upstream/broken-bond-recomp build/applied-patches
```

## Troubleshooting

| Message | What to do |
| --- | --- |
| `This build targets an Apple Silicon Mac.` | Only Macs with Apple chips are supported. |
| `Missing tool: cmake` (or `git`) | Repeat step 2 (or install Xcode, step 1). |
| `Select your disc image (.iso or .7z) with --source` | There is no `.iso` or `.7z`, or more than one, in the project folder. Fix that, or use `--source`. |
| `Extracting a .7z needs 7-Zip` | Run `brew install sevenzip`. |
| `entries could not be read from the image` | The `.iso` or `.7z` is incomplete (a download that stopped). Download it again. |
| `You have not agreed to the Xcode license agreements` | Open Xcode once and accept the license. |
| `CMake 3.25 or higher is required` | Run `brew upgrade cmake`. |
| `Preserving edits in ...` | See [Updating](#updating). |
| `permission denied: ./Build.command` | You downloaded a ZIP instead of using `git clone`. Run `chmod +x Build.command Play.command`. |
| A download fails | Check your internet connection and run the build again. |
| The Mac gets very slow during the build | Build with fewer parallel jobs: `./Build.command --jobs 2`. |

To report a problem, open an [issue](https://github.com/QRMods/naruto-broken-bond-macos/issues)
and attach the newest log in `user/logs/`.

## Performance (MacBook Pro with M4)

| Scene | Frame rate |
| --- | --- |
| Logos, title screen and menus | Steady 30 FPS |
| Story Mode cutscenes | Steady 30 FPS |
| First fight (Story Mode) | Steady 60 FPS (fights run at 60, as on the console) |

The first time a new place or effect appears, its shaders compile for Metal and the
game can stop for a few seconds, mostly on a loading screen (about 8 s for the title
screen on the very first start). The second time it doesn't: the pipelines are kept in
`user/cache/` and prepared at the start.

## How it works

This repository doesn't copy the projects it builds on. `tools/build.py` clones them
into `upstream/` at the commits pinned in `sources.json`, applies the patches, extracts
the game into `game/` (`tools/extract-game.py`, straight from the `.iso` or `.7z`),
generates the recompiled code and builds the PC port with its own CMake, as on Linux:
the native renderer on Vulkan (MoltenVK), with the game's shaders translated at build
time (XenosRecomp, DXC, SPIR-V). Then it creates `dist/Naruto The Broken Bond.app`.
Sentry crash reporting, which reports to the PC port's own project, is off.

The macOS-specific parts are in `macos/`:

- `patches/pc/`: the changes to the PC port, one commit each (`git format-patch`),
  written so they can go upstream. They are the Rise of a Ninja port's, rebased onto
  Broken Bond's sources:
  1. Building and running on macOS: the platform layer (Mach, dyld, QoS classes), the
     Metal surface, the bundled Vulkan loader and the app bundle's resources.
  2. A quick close on Cmd+Q (below).
  3. The game in the process macOS launched, which macOS knows as the app (below).
  4. Creating in parallel the pipelines that small render targets wait for (below).
  5. The frame-rate and slow-frame (`[native-hitch]`) lines in the log, for `tools/`.
  6. The pipeline cache kept across sessions (below).
  7. Achievement toasts and the achievements list (below).
  8. No crash-report question or option in a build without Sentry (this one).
- `patches/sdk/`: SDK patches applied after the PC port's: the PS5 port's (16 KB page
  write watches, Vulkan submission and frame pacing), adapted to follow them, guest
  module loading, the Vulkan presenter, and `std::atomic<std::shared_ptr>` where libc++
  lacks it.
- `broken_bond.toml`: the macOS defaults over the PC port's (Vulkan, keyboard and mouse,
  full screen, 30 FPS, straight into the game, draw skipping on).

### New shaders without stutter

Each new shader combination is translated to Metal and compiled when it first appears,
which costs tens to hundreds of milliseconds on a Mac. On macOS:

- An object whose pipeline isn't ready yet is left out for that moment instead of
  freezing the frame (`skip_pipeline_draws`, the PC port's option, on by default here).
  The pipeline compiles on other threads and the object appears as soon as it's done.
- A draw into a small render target (under 640x360) is never skipped: some effects draw
  such a target once, a colour ramp or a lookup, and reuse it for many frames, so
  skipped it would stay wrong (in Rise of a Ninja the screen went black for the whole
  rage mode). Those draws wait for their pipeline, compiled in parallel with the others
  of their batch. Making every draw into a new full-size target wait as well froze the
  game for seconds after each load, so those draws still skip.
- Compiled pipelines are saved in `user/cache/native-vulkan-pipelines.bin`, and the PC
  port's list of the pipelines you've seen in `user/cache/pipelines/`, so later sessions
  prepare them up front.

### Achievements

The SDK keeps the achievements: the game reports them (`XGIUserWriteAchievements`), the
`AchievementManager` saves them. Its toast, though, is an ImGui dialog of the Xenos
presenter, so with the native renderer an unlock was saved and never shown. Patch 7
shows them in the menus' RmlUi instead: the toast, the list, the Guide button (which
reaches the menus even while the game doesn't receive it) and the game menu's tab. The
names, descriptions and icons come from the game's own data (its XDBF), in its language.
The menus' renderer has no shaders, so every image is made on the CPU at the exact pixel
size it shows at. They stay sharp at any window size.

To check the presentation without playing, start the game from Terminal with
`BROKENBOND_ACHIEVEMENT_PREVIEW=all` (every toast), `=list`, `=menu` or `=home` (a
press of the Home button), after `BROKENBOND_ACHIEVEMENT_PREVIEW_DELAY` seconds (15).
These unlock nothing; `=unlock` really unlocks the first locked achievement, so use it
only with a copy of `user/` (`--data_root=<copy>`).

### The app macOS sees

The app is a game for macOS (`LSApplicationCategoryType`), and it starts in full screen,
where macOS applies Game Mode. That needs macOS to know the game's process as the app,
which it does only for the process LaunchServices starts. The PC port runs the game in a
child of a diagnostics supervisor, an anonymous process to macOS, so patch 3 runs it in
the launched process instead. To bring the supervisor back for diagnosing a hang or a
crash, start the game with `BROKENBOND_INCIDENT_SUPERVISOR=1`.

The controller's Home button (Xbox, PS) reaches the game only while the game claims it,
which it does on every controller while it runs. macOS 26 acts on the press as well and
no app can stop it: for a game Apple hasn't listed for its Game Overlay, it opens the
Games app when the button is released. So for a few seconds after a press the game took,
the game closes the Games app the system opened (or hides it, if it was open already) and
stays in front: the button only opens the achievements.

### Quitting

On Cmd+Q the window waits while the renderer closes in order. On macOS the renderer may
itself be waiting for an image of the window, which only the waiting main thread gives
back, so the PC port's close could hang. On macOS the close writes the pipeline cache,
waits at most a second for the renderer and the game's threads, and ends the process.

### Updating the source projects

To move a source project to a new version, change its commit in `sources.json` and build
again. The PC port and the SDK carry the patches applied, so first delete
`upstream/broken-bond-recomp` and `build/applied-patches/`. If only the patches change,
building is enough: the applied ones are reverted and the new ones applied. If a patch
of `macos/patches/pc` no longer applies, apply the series with `git am -3` on a branch at
the new commit, resolve the conflicts and export it again with `git format-patch`.
`./Build.command --dev` builds the PC port's checkout as it is, for working on such a
branch.

### Known issues

- The NARUTO logo shows white in the main menu (it is orange on the title screen).
  Not checked yet against the console.
- New content stops the game for a moment the first time (see Performance).

## Credits

- [broken-bond-recomp](https://github.com/jorjbarbosa/broken-bond-recomp) (PC port):
  the recompilation, the application, the native renderer and its shader pipeline.
- [naruto-ps5](https://github.com/mshivam019/naruto-ps5): its SDK patch (write watching
  with 16 KB pages, Vulkan submissions, presentation pacing).
- [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk) and [Plume](https://github.com/renderbag/plume).

## License

macOS port by [alantero](https://github.com/alantero), published by
[QRMods](https://github.com/QRMods). Copyright (C) 2026 alantero.

The code in this repository is licensed under version 3 of the GNU General Public
License ([LICENSE](LICENSE), GPL-3.0-only), the same license as the PC port its patches
apply to. Each source project keeps its own license: naruto-ps5 and Plume (MIT) and the
ReXGlue SDK (BSD-3-Clause). The built app includes their notices in
`Contents/Resources/licenses/`.
