# Setting Up CAST

This guide is written for medical students, residents, and physicians who have not set up a command-line tool before. Follow the section for your operating system.

**What you will need:**
- An internet connection
- An OpenAI account (free to create; charges apply based on usage — typically $0.01–$0.10 per batch of cards)

**Time:** approximately 10 minutes on first setup.

**Jump to your platform:**
- [macOS](#macos)
- [Windows](#windows)
- [Linux (Ubuntu)](#linux-ubuntu)

---

## Get your OpenAI API key

CAST uses OpenAI to generate the enriched explanations on your flashcards. You need an API key to authorize this. This step is the same on all platforms.

> **Note on cost:** API calls are billed by OpenAI based on usage. A typical batch of 40 cards costs roughly $0.40–$4.00 depending on the model. You set your own spending limits in your OpenAI account.

1. Open your browser and go to: `https://platform.openai.com`

2. Sign in to your OpenAI account, or click **Sign up** to create one.
   (If you already use ChatGPT, you can sign in with the same account.)

3. Once signed in, click your profile icon or initials in the top-right corner.
   In the dropdown, click **API keys** (or navigate to **Dashboard → API keys**).

4. Click **Create new secret key**.

5. Give it a name like `CAST` (optional, for your own reference).

6. Click **Create secret key**.

7. A key starting with `sk-` will appear.
   **Copy it now** — it will not be shown again.
   Paste it into a secure temporary location (a notes app is fine for now).

### Optional: Set a spending limit

To avoid unexpected charges, set a monthly usage limit in your OpenAI account:
- Go to **Settings → Billing → Usage limits**
- Set a **Monthly budget** (e.g., $10)

---

## macOS

### Step 1 — Download CAST

**Option A: Download as a ZIP (recommended for most users)**

1. Open your browser and go to:
   `https://github.com/MorrisGlr/clinical-anki-generator`

2. Click the green **Code** button near the top right of the page.
   A small dropdown menu appears.

3. Click **Download ZIP**.
   Your browser will download a file named `clinical-anki-generator-main.zip`.

4. Open your **Downloads** folder in Finder.
   Double-click the ZIP file to unzip it.
   A folder named `clinical-anki-generator-main` will appear.

5. Move that folder somewhere easy to find — for example, your Desktop or Documents folder.

**Option B: Clone with git (for users comfortable with the terminal)**

```
git clone https://github.com/MorrisGlr/clinical-anki-generator
```

### Step 2 — Open Terminal

Terminal is a built-in macOS app that lets you run commands.

1. Press **Command (⌘) + Space** to open Spotlight Search.
2. Type `Terminal` and press **Enter**.
3. A white (or black) window with a text cursor appears. This is Terminal.

### Step 3 — Navigate to the CAST folder

1. Type `cd ` (with a space after `cd`) but do not press Enter yet.
2. Open Finder and locate the `clinical-anki-generator-main` folder you downloaded.
3. Drag that folder from Finder into the Terminal window.
   The folder path will be inserted automatically.
4. Press **Enter**.

### Step 4 — Run the setup script

In Terminal, type the following command and press **Enter**:

```
./setup.sh
```

The script will:
1. Check that your Mac meets the requirements
2. Install Python if needed (it will tell you exactly what to run)
3. Set up a self-contained environment
4. Install CAST and its dependencies
5. Ask you to paste your OpenAI API key
6. Confirm everything is working

Follow any on-screen prompts. The whole process takes 1–3 minutes.

**If Python is not installed:** the script will tell you and give you the exact command. After installing Python, re-run `./setup.sh`.

### Step 5 — Verify the setup

```
cast check
```

You should see all green checkmarks. If any item shows a red ✗, see Troubleshooting below.

### Activate CAST in future sessions

Each time you open a new Terminal window:

```
source .venv/bin/activate
```

### macOS Troubleshooting

**`cast: command not found`** — The virtual environment is not activated. Run `source .venv/bin/activate`.

**`OPENAI_API_KEY is not set`** — Run `./setup.sh` again, or open `.env` in any text editor and add: `OPENAI_API_KEY=sk-your-key-here`

**`Python 3.10 or later not found`** — Install from `https://www.python.org/downloads/`. With Homebrew: `brew install python@3.12`

**`Permission denied: ./setup.sh`** — Run `chmod +x setup.sh` once, then try again.

---

## Windows

### Step 1 — Download CAST

1. Open your browser and go to:
   `https://github.com/MorrisGlr/clinical-anki-generator`

2. Click the green **Code** button near the top right.

3. Click **Download ZIP**.
   Your browser will download `clinical-anki-generator-main.zip`.

4. Open your **Downloads** folder in File Explorer.
   Right-click the ZIP and select **Extract All**.

5. Move the extracted folder somewhere easy to find — for example, your Desktop.

### Step 2 — Open PowerShell

1. Press **Windows + S** and type `PowerShell`.
2. Click **Windows PowerShell** (not "PowerShell ISE").
3. A blue window with a text cursor appears.

### Step 3 — Navigate to the CAST folder

1. Type `cd ` (with a space) but do not press Enter yet.
2. Open File Explorer and navigate to the `clinical-anki-generator-main` folder.
3. Click the address bar at the top of File Explorer to highlight the path.
4. Copy the path (Ctrl+C) and paste it after `cd ` in PowerShell.
5. Press **Enter**.

### Step 4 — Allow the setup script to run (one-time)

Windows blocks unsigned PowerShell scripts by default. Run this once to allow local scripts:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Type `Y` and press **Enter** when prompted.

### Step 5 — Run the setup script

```
.\setup.ps1
```

The script will:
1. Check that your Windows installation meets the requirements
2. Install Python if needed (it will give you the exact command)
3. Set up a self-contained environment
4. Install CAST and its dependencies
5. Ask you to paste your OpenAI API key
6. Confirm everything is working

Follow any on-screen prompts. The whole process takes 1–3 minutes.

**If Python is not installed:** the script will suggest:
```
winget install Python.Python.3.12
```
After installing, close and reopen PowerShell, then re-run `.\setup.ps1`.

### Step 6 — Verify the setup

```
cast check
```

You should see all `[OK]` lines. If any show `[X]`, see Troubleshooting below.

### Activate CAST in future sessions

Each time you open a new PowerShell window:

```
.\.venv\Scripts\Activate.ps1
```

### Windows Troubleshooting

**`cast: The term 'cast' is not recognized`** — The virtual environment is not activated. Run `.\.venv\Scripts\Activate.ps1`.

**`OPENAI_API_KEY is not set`** — Run `.\setup.ps1` again, or open `.env` in Notepad and add: `OPENAI_API_KEY=sk-your-key-here`

**`Python 3.10 or later not found`** — Install from `https://www.python.org/downloads/`. Check **"Add Python to PATH"** during installation. Then close and reopen PowerShell.

**`running scripts is disabled on this system`** — Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` and try again.

**`pip is not recognized`** — Your Python installation may be incomplete. Re-install Python from python.org, ensuring "Add Python to PATH" is checked.

---

## Linux (Ubuntu)

### Step 1 — Download CAST

**Option A: Download as a ZIP**

1. Open your browser and go to:
   `https://github.com/MorrisGlr/clinical-anki-generator`

2. Click the green **Code** button, then **Download ZIP**.

3. Open your **Downloads** folder in Files.
   Right-click the ZIP and select **Extract Here**.

4. Move the extracted folder somewhere easy to find — for example, your home directory.

**Option B: Clone with git**

```
git clone https://github.com/MorrisGlr/clinical-anki-generator
```

### Step 2 — Open Terminal

Press **Ctrl + Alt + T**, or search for "Terminal" in your application launcher.

### Step 3 — Navigate to the CAST folder

```
cd ~/clinical-anki-generator-main
```

Replace `~` with the actual path if you moved the folder elsewhere.

### Step 4 — Run the setup script

```
./setup.sh
```

If you see "Permission denied", make the script executable first:

```
chmod +x setup.sh && ./setup.sh
```

The script will:
1. Detect that you are on Linux
2. Install Python if needed (it will give you the exact `apt` command)
3. Set up a self-contained virtual environment
4. Install CAST and its dependencies
5. Ask you to paste your OpenAI API key
6. Confirm everything is working

**If Python is not installed:** the script will suggest:
```
sudo apt update && sudo apt install python3.12 python3.12-venv
```
After installing, re-run `./setup.sh`.

### Step 5 — Verify the setup

```
cast check
```

You should see all green checkmarks. If any show a red ✗, see Troubleshooting below.

### Activate CAST in future sessions

Each time you open a new Terminal window:

```
source .venv/bin/activate
```

### Linux Troubleshooting

**`cast: command not found`** — The virtual environment is not activated. Run `source .venv/bin/activate`.

**`OPENAI_API_KEY is not set`** — Run `./setup.sh` again, or open `.env` in any text editor and add: `OPENAI_API_KEY=sk-your-key-here`

**`Python 3.10 or later not found`** — Run: `sudo apt update && sudo apt install python3.12 python3.12-venv`

**`Permission denied: ./setup.sh`** — Run `chmod +x setup.sh` once, then try again.

**`No module named venv`** — Install venv separately: `sudo apt install python3.12-venv`

---

## Saving HTML files (all platforms)

Before running CAST, you need to save HTML pages from your question bank:

1. In your browser (Chrome or Firefox), open a completed question in UWorld, AMBOSS, or APGO.

2. Press **Ctrl+S** (Windows/Linux) or **Command (⌘)+S** (macOS) to save the page.

3. In the save dialog, make sure the format is set to **Web Page, Complete** (not "Web Archive" or "PDF").

4. Save the file into the `html_dump` folder inside your CAST directory.

Repeat for each question you want to convert.

---

## Generate your flashcards (all platforms)

In your terminal (make sure your virtual environment is activated and you are in the CAST folder):

```
cast --platform uworld
```

Replace `uworld` with `amboss`, `apgo`, or `nbme` depending on your question bank.

CAST will process each file and write a `.txt` output file to the `gen_anki/` folder.

---

## Getting help

If you run into an issue not covered here, open a GitHub issue at:
`https://github.com/MorrisGlr/clinical-anki-generator/issues`

Include the error message you see and your operating system version.
