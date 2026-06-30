# Satellite Tracker v3
Version 3 is a complete rewrite of the [first version of this project.](https://github.com/Akut-Luna/Satellite-Tracker-v1) (Don't ask what happened to version 2.)
I wrote the first version as part of my Bachelor Thesis at the University of Zurich. If you want the full understanding of what this project is about, please read the [full thesis (PDF)](./doc/Bachelor_Thesis.pdf). If you just need to know what has changed between version 1 and version 3, please read the [advanced patch notes (PDF)](./doc/Satellite_Tracker_v3.pdf).

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Akut-Luna/Satellite-Tracker-v3.git
cd Satellite-Tracker-v3
```

### 2. Create a virtual environment (optional but recomended)

Windows

```bash
python -m venv .venv
```

macOS/Linux

```bash
python3 -m venv .venv
```

### 3. Activate the virtual environment
**You will have to do this for every new terminal** but for some IDEs like VS Code opening a new integrated terminal in VS Code will usually activate the virtual environment automatically, assuming the interpreter is selected correctly (see step 6).

Windows

```bash
.venv\Scripts\activate
```

macOS/Linux

```bash
source .venv/bin/activate
```
### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Install default/example data & config
```bash
python ./install/setup.py
```

### 6. Select the Python interpreter (VS Code)
When using a virtual environment you may need to select the Python interpreter. Here is how to do it when you use VS Code as your IDE. 

1. Press Ctrl+Shift+P → Python: Select Interpreter.
2. Choose:

Windows:

```
.venv/Scripts/python.exe
```

or on macOS/Linux:

```
.venv/bin/python
```

### 7. Run the project.

```bash
python main/src/main.py
```
or as shortcut

```bash
python satellite_tracker.py
```
