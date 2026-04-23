# Setting Up HEART on macOS

This guide is written for medical students, residents, and physicians who have not set up a command-line tool before. Follow each step in order.

**What you will need:**
- A Mac running macOS 12 (Monterey) or later
- An internet connection
- An OpenAI account (free to create; charges apply based on usage — typically $0.01–$0.10 per batch of cards)

**Time:** approximately 10 minutes on first setup.

---

## Step 1 — Download HEART

### Option A: Download as a ZIP (recommended for most users)

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

### Option B: Clone with git (for users comfortable with the terminal)

```
git clone https://github.com/MorrisGlr/clinical-anki-generator
```

---

## Step 2 — Get your OpenAI API key

HEART uses OpenAI to generate the enriched explanations on your flashcards. You need an API key to authorize this.

> **Note on cost:** API calls are billed by OpenAI based on usage. A typical batch of 40 cards costs roughly $0.40–$4.00 depending on the model. You set your own spending limits in your OpenAI account.

### Create your API key

1. Open your browser and go to: `https://platform.openai.com`

2. Sign in to your OpenAI account, or click **Sign up** to create one.
   (If you already use ChatGPT, you can sign in with the same account.)

3. Once signed in, click your profile icon or initials in the top-right corner.
   In the dropdown, click **API keys** (or navigate to **Dashboard → API keys**).

4. Click **Create new secret key**.

5. Give it a name like `HEART` (optional, for your own reference).

6. Click **Create secret key**.

7. A key starting with `sk-` will appear.
   **Copy it now** — it will not be shown again.
   Paste it into a temporary secure location (a notes app is fine for now).

### Optional: Set a spending limit

To avoid unexpected charges, set a monthly usage limit in your OpenAI account:
- Go to **Settings → Billing → Usage limits**
- Set a **Monthly budget** (e.g., $10)

---

## Step 3 — Open Terminal

Terminal is a built-in macOS app that lets you run commands.

1. Press **Command (⌘) + Space** to open Spotlight Search.

2. Type `Terminal` and press **Enter**.

3. A white (or black) window with a text cursor appears. This is Terminal.

---

## Step 4 — Navigate to the HEART folder

In Terminal, you need to tell it where the HEART folder is.

1. Type `cd ` (with a space after `cd`) but do not press Enter yet.

2. Open Finder and locate the `clinical-anki-generator-main` folder you downloaded.

3. Drag that folder from Finder into the Terminal window.
   The folder path will be inserted automatically — for example:
   `cd /Users/yourname/Desktop/clinical-anki-generator-main`

4. Press **Enter**.

   The Terminal prompt will now show the HEART folder name, confirming you are in the right place.

---

## Step 5 — Run the setup script

In Terminal, type the following command and press **Enter**:

```
./setup.sh
```

The script will:

1. Check that your Mac meets the requirements
2. Install Python if needed (it will tell you exactly what to run)
3. Set up a self-contained environment so HEART does not interfere with other software
4. Install HEART and its dependencies
5. Ask you to paste your OpenAI API key (the `sk-...` value you copied in Step 2)
6. Confirm everything is working

Follow any on-screen prompts. The whole process takes 1–3 minutes.

### If Python is not installed

The script will tell you if Python needs to be installed and give you the exact command or link to use. After installing Python, re-run `./setup.sh`.

---

## Step 6 — Verify the setup

After setup completes, run:

```
heart check
```

You should see output like this (all green checkmarks):

```
  ✓  Python 3.12.x
  ✓  OPENAI_API_KEY is set
  ✓  Input directory ./html_dump exists
  ✓  Output directory ./gen_anki exists and is writable
```

If any item shows a red ✗, see the Troubleshooting section below.

---

## Step 7 — Place your saved HTML files

Before running HEART, you need to save HTML pages from your question bank:

1. In your browser (Chrome or Firefox), open a completed question in UWorld, AMBOSS, or APGO.

2. Press **Command (⌘) + S** to save the page.

3. In the save dialog, make sure the format is set to **Web Page, Complete** (not "Web Archive" or "PDF").

4. Save the file into the `html_dump` folder inside your HEART directory.
   If `html_dump` does not exist yet, create it in Finder.

Repeat for each question you want to convert.

---

## Step 8 — Generate your flashcards

In Terminal (make sure you are still in the HEART folder):

```
heart --platform uworld
```

Replace `uworld` with `amboss`, `apgo`, or `nbme` depending on your question bank.

HEART will process each file and write a `.txt` output file to the `gen_anki/` folder.

---

## Activating HEART in future sessions

Each time you open a new Terminal window, you need to activate the environment before running `heart`:

```
source .venv/bin/activate
```

Then navigate to the HEART folder and run your command as usual.

---

## Troubleshooting

### `heart: command not found`

The virtual environment is not activated. Run:
```
source .venv/bin/activate
```
Then try again.

### `OPENAI_API_KEY is not set`

Your API key was not saved, or the `.env` file is missing. Run `./setup.sh` again — it will prompt you to enter your key.

Alternatively, open the `.env` file in any text editor and add:
```
OPENAI_API_KEY=sk-your-key-here
```

### `Python 3.10 or later not found`

Install Python from `https://www.python.org/downloads/` and re-run `./setup.sh`.

If you have Homebrew installed, you can run:
```
brew install python@3.12
```

### `Permission denied: ./setup.sh`

Run this once to make the script executable, then try again:
```
chmod +x setup.sh
```

### The script stops with an error about `pip`

Your Python installation may be missing `pip`. Run:
```
python3 -m ensurepip --upgrade
```
Then re-run `./setup.sh`.

### Cards are generated but the Anki import fails

Make sure the output `.txt` file from `gen_anki/` is imported using **File → Import** in Anki, with the field separator set to **Tab**. See the README for full import instructions.

---

## Getting help

If you run into an issue not covered here, open a GitHub issue at:
`https://github.com/MorrisGlr/clinical-anki-generator/issues`

Include the error message you see and the macOS version from **Apple menu → About This Mac**.
