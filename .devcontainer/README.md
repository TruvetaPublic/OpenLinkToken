# Dev Container

Dev Containers allow to codify a development environment with all required tools and dependencies and keep it alongside the code.

You can find more information using these resources:

- <https://code.visualstudio.com/docs/devcontainers/containers>
- <https://containers.dev>

**Note:** While this Dev Container is focused on VS Code to run in, it can also be used with other IDEs (e.g. JetBrains)

## Getting Started

### Running it

1. Open the project in VS Code.
1. Click on the green or blue `><` in the bottom left corner.
1. Select `Reopen in Container`.
1. Alternatively, if you don't see the green or blue `><` you can open the command palette and search for `Dev Containers: Reopen in Container`.

**Note 1:** VS Code should automatically detect that the project is a Dev Container and offer you to install the Dev Container Extension. If it doesn't, you can manually install it from the marketplace: `ms-vscode-remote.remote-containers`

**Note 2:** VS Code should automatically detect the `.devcontainer` folder and prompt you to reopen in the container. If it doesn't, you can manually select it from the command palette.

**Note 3:** The first time you run this it will take a few minutes to build the container.

### Zscaler SSL Inspection Support

If your organization uses Zscaler for SSL inspection, you'll need to configure the development container to trust Zscaler's root certificate:

1. **Export the Zscaler certificate from your system:**

   - **For macOS, Git Bash or WSL users:**

     ```bash
     ./.devcontainer/scripts/export_host_zscaler_cert.sh
     ```

   - **For Windows PowerShell users:**
     ```powershell
     .\.devcontainer\scripts\Export-ZscalerCert.ps1
     ```

2. **Build or rebuild the container:**
   The container will automatically detect and use the exported certificate.

For more details, see [Zscaler Certificate Management](./scripts/README.md).

### Keeping it relevant

If you end up needing additional tools, extensions or settings, please add them to the `.devcontainer/devcontainer.json` file. This will ensure that everyone has the same environment with everything needed.
