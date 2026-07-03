const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const mode = process.argv[2] || "check";
const root = path.join(__dirname, "..");
const defaultPythonExecutable = "D:\\desktop_app\\anaconda\\envs\\mm_env\\python.exe";
const pythonExecutable = process.env.PYTHON_EXECUTABLE || defaultPythonExecutable;
const condaEnv = process.env.STAR_MANAGER_CONDA_ENV || "mm_env";

function getPythonEnvironmentRoot() {
  return path.dirname(pythonExecutable);
}

function getCondaBinaryArgs() {
  const libraryBin = path.join(getPythonEnvironmentRoot(), "Library", "bin");
  const pythonRoot = getPythonEnvironmentRoot();
  const binaryEntries = [
    [path.join(libraryBin, "libexpat.dll"), "."],
    [path.join(libraryBin, "libbz2.dll"), "."],
    [path.join(libraryBin, "ffi-8.dll"), "."],
    [
      path.join(
        pythonRoot,
        "Lib",
        "site-packages",
        "fmod_toolkit",
        "libfmod",
        "Windows",
        "x64",
        "fmod.dll"
      ),
      path.join("fmod_toolkit", "libfmod", "Windows", "x64")
    ]
  ];

  return binaryEntries.flatMap(([binaryPath, destination]) => {
    return fs.existsSync(binaryPath) ? ["--add-binary", `${binaryPath}${path.delimiter}${destination}`] : [];
  });
}

const pythonArgsByMode = {
  check: ["-m", "py_compile", "backend/app/server.py", "backend/app/bridge.py"],
  dev: ["backend/app/server.py"],
  "check-package-deps": ["scripts/check_package_deps.py"],
  pyinstaller: [
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--name",
    "star_manager_backend",
    "--distpath",
    "build/backend",
    "--workpath",
    "build/pyinstaller",
    "--specpath",
    "build",
    "--paths",
    "backend",
    "--paths",
    "backend/app",
    "--hidden-import",
    "pyexpat",
    "--hidden-import",
    "xml.parsers.expat",
    "--collect-all",
    "PIL",
    "--collect-all",
    "UnityPy",
    "--collect-all",
    "texture2ddecoder",
    "--collect-all",
    "etcpak",
    "--collect-all",
    "astc_encoder",
    "--collect-all",
    "fmod_toolkit",
    "--collect-all",
    "archspec",
    ...getCondaBinaryArgs(),
    "backend/app/server.py"
  ]
};

if (!pythonArgsByMode[mode]) {
  console.error(`Unknown python script mode: ${mode}`);
  process.exit(1);
}

const command = pythonExecutable || "conda";
const args = pythonExecutable
  ? pythonArgsByMode[mode]
  : ["run", "-n", condaEnv, "python", ...pythonArgsByMode[mode]];

const child = spawn(command, args, {
  cwd: root,
  stdio: "inherit",
  shell: false,
  windowsHide: true
});

child.on("exit", (code, signal) => {
  if (signal) {
    console.error(`Python process exited by signal ${signal}`);
    process.exit(1);
  }
  process.exit(code ?? 0);
});
