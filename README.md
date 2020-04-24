# Chinese Overlay
Detects Chinese text and displays an overlay with the corresponding pinyin, phrase translations and optionally a Google translation. Works on videos and anything else that can be visually captured from the screen.

![](screenshots/douyu.jpg)

## Usage
Prebuilt packages are made available for Windows that can be downloaded from the [Releases](/releases) page. Windows 10 1709 and a DirectX 12 compatible GPU will be required to use the DirectML provider (basically a neural network runtime that leverages DirectX12 to run the OCR on all modern GPUs). Alternatively, the much slower CPU backend can be used or any of the other onnxruntime execution providers (eg. CUDA).
To launch the overlay open any of the .bat files (eg. `overlay-pinyin.bat` or `overlay-google-trans.bat`). By default the overlay can toggled using the `F8` key. The translation overlay will be shown within the displayed window, which can also be resized to fit
whatever region you want to translated. By default only the pinyin is shown which is obtained from a dictionary.
The overlay can also be started by executing the program from the command line with the `ui` subcommand ´(`cli.exe ui`) which opens up more options that can be found by typing `cli.exe --help` and `cli.exe ui --help`.

## Running in Python instead of using prepackaged version
The [requirements file](/requirements.txt) contains all the necessary requirements and some optional ones. However to use the DirectML interface a modified version is required with [this](https://github.com/microsoft/onnxruntime/pull/3359) PR and [this](https://github.com/microsoft/onnxruntime/issues/3360) fix to make it work with the default Windows DirectML library). The program should work on non-Windows systems but it has not been tested much.

## Running a translation server
The project also contains an http server that can run OCR on received images and return the results. It can be started by specifying the `server` argument. This makes it possible to easily make frontends in other languages
or to use the OCR for any other purpose.