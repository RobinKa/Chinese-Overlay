import subprocess
import os
from pathlib import Path
import shutil
import click


def write_text(path, text):
    """Writes a file to the path with the given text."""
    with open(path, "w") as text_file:
        text_file.write(text)

def write_script(path_without_ext, command, is_windows):
    """Writes a script for running the program with a command."""
    executable = "cli.exe" if is_windows else "./cli"
    path = "%s.%s" % (path_without_ext, "bat" if is_windows else "sh")
    write_text(path, "%s %s" % (executable, command))

@click.command()
def main():
    is_windows = os.name == "nt"
    print("Is windows:", is_windows)

    dist_base_path = Path("dist")
    dist_path = dist_base_path / "cli"

    command = [
        "pyinstaller",
        "--distpath", str(dist_base_path),
        "--add-data", "data/*;data/",
        "--add-data", "ui/views/overlay.qml;ui/views/",
        "cli.py"
    ]

    # Add dll that pyinstaller misses on Windows
    if is_windows:
        orig_dll_path = Path("C:/") / "Windows" / \
            "system32" / "vcruntime140_1.dll"
        command += ["--add-data", "%s;." % str(orig_dll_path)]

    print("Running", command)
    result = subprocess.run(command)
    result.check_returncode()

    # Write script files
    print("Writing scripts")
    write_script(dist_path / "overlay-google-trans", "ui --google-trans", is_windows)
    write_script(dist_path / "overlay-pinyin", "ui", is_windows)
    write_script(dist_path / "overlay-google-trans-cpu", "--execution-providers CPUExecutionProvider ui --google-trans", is_windows)
    write_script(dist_path / "overlay-pinyin-cpu", "--execution-providers CPUExecutionProvider ui", is_windows)

    # Zip results
    print("Zipping results")
    shutil.make_archive(dist_base_path / "overlay", "zip", dist_path)

    print("Done")


if __name__ == "__main__":
    main()
