# NEUTRON EVO OS - VS Code Extension

> Automatically apply NEUTRON EVO OS to any workspace — Memory Stack, Skill Router, and Dream Cycle

## Features

- ✅ **Auto-inject CLAUDE.md** — Automatically apply context when opening a folder
- ✅ **5-Step Workflow** — /explore /spec /build /verify /ship
- ✅ **Configurable** — Customize which files to inject and exclude patterns
- ✅ **Commands** — Quick access via Command Palette
- ✅ **Skill Router** — Expert skill routing with CI audit
- ✅ **Dream Cycle** — Memory 2.0 pruning and distillation

## Installation

### From GitHub Releases (Recommended)

1. Download the `.vsix` file from [GitHub Releases](https://github.com/adamwang99/NEUTRON-EVO-OS/releases)
2. In VS Code: Extensions → `...` (top-right) → **Install from VSIX**
3. Select the downloaded file

Or use command line:
```bash
code --install-extension neutron-evo-os-4.0.0.vsix
```

### From Source

```bash
cd vscode-extension
npm install
npm run compile
# Press F5 to debug
```

## Usage

### Auto-Inject (Default)

When enabled, opening any folder will automatically create `CLAUDE.md` if it doesn't exist.

### Manual Apply

1. Open a workspace folder
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Type `NEUTRON EVO OS: Apply to Workspace`
4. Select template

## Configuration

Go to `Settings > NEUTRON EVO OS`:

| Setting | Default | Description |
|---------|---------|-------------|
| `neutronEvoOs.enabled` | `true` | Enable/disable extension |
| `neutronEvoOs.autoInject` | `true` | Auto-inject on folder open |
| `neutronEvoOs.files` | `["CLAUDE.md"]` | Files to inject |
| `neutronEvoOs.excludePatterns` | `["**/node_modules/**", ...]` | Folders to skip |

## Commands

| Command | Description |
|---------|-------------|
| `neutron-evo-os.apply` | Apply template to workspace |
| `neutron-evo-os.setup` | Quick setup wizard |
| `neutron-evo-os.openDocs` | Open documentation |
| `neutron-evo-os.dream` | Trigger Dream Cycle |
| `neutron-evo-os.status` | Show CI dashboard |

## License

MIT

